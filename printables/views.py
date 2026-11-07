# printables/views.py
from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_GET, require_http_methods

from moments.models import Moment

from .forms import PrintableRequestForm
from .limits import LimitExceeded, check_limits, client_ip, hash_ip
from .pipeline import process_now


def _is_ajax(request):
    return request.headers.get("x-requested-with") == "XMLHttpRequest"


@require_http_methods(["GET", "POST"])
def request_printable(request):
    initial = {}
    slug = request.GET.get("moment")
    if slug:
        moment = Moment.objects.published().filter(slug=slug).first()
        if moment:
            initial["moment"] = moment

    if request.method == "GET":
        return render(request, "printables/form.html", {"form": PrintableRequestForm(initial=initial)})

    form = PrintableRequestForm(request.POST)
    error = None
    if form.is_valid():
        ip_hash = hash_ip(client_ip(request))
        try:
            check_limits(form.cleaned_data["email"], ip_hash)
        except LimitExceeded as exc:
            error = exc.message
        else:
            printable = form.save(commit=False)
            printable.ip_hash = ip_hash
            printable.utm_source = request.GET.get("utm_source", "")[:60]
            printable.utm_medium = request.GET.get("utm_medium", "")[:60]
            printable.utm_campaign = request.GET.get("utm_campaign", "")[:60]
            printable.save()
            if settings.PRINTABLE_PROCESS_INLINE:
                # Make and send it now. If this fails, the request stays queued
                # with a backoff and the scheduled retry picks it up, so the
                # parent still sees the "on its way" page either way.
                process_now(printable.pk)
            thanks_url = reverse("printables:thanks")
            if _is_ajax(request):
                return JsonResponse({"ok": True, "redirect": thanks_url}, status=201)
            return redirect(thanks_url)

    if _is_ajax(request):
        payload = {"ok": False, "errors": form.errors.get_json_data() if form.errors else {}}
        if error:
            payload["message"] = error
        return JsonResponse(payload, status=429 if error else 400)
    return render(request, "printables/form.html", {"form": form, "error": error}, status=429 if error else 400)


@require_GET
def thanks(request):
    return render(request, "printables/thanks.html")
