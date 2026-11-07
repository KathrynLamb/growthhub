# moments/views.py
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_GET

from .models import Moment


@require_GET
def moment_list(request):
    moments = Moment.objects.published()
    age = request.GET.get("age")
    if age in Moment.AgeBand.values:
        moments = moments.filter(age_band=age)
    return render(
        request,
        "moments/list.html",
        {"moments": moments, "age_bands": Moment.AgeBand.choices, "selected_age": age},
    )


@require_GET
def moment_detail(request, slug):
    moment = get_object_or_404(Moment.objects.published(), slug=slug)
    related = Moment.objects.published().filter(age_band=moment.age_band).exclude(pk=moment.pk)[:3]
    return render(request, "moments/detail.html", {"moment": moment, "related": related})


# --- JSON API ---------------------------------------------------------------
# Read-only and public: only published content is exposed. FlipWhizz (Next.js)
# uses this to show "stories for moments" links on its own pages.


def _cors(response):
    response["Access-Control-Allow-Origin"] = "*"
    response["Cache-Control"] = "public, max-age=300"
    return response


@require_GET
def api_moment_list(request):
    moments = Moment.objects.published()
    age = request.GET.get("age")
    if age:
        if age not in Moment.AgeBand.values:
            return _cors(JsonResponse({"error": f"Unknown age band '{age}'."}, status=400))
        moments = moments.filter(age_band=age)
    data = [m.to_api_dict(request) for m in moments]
    return _cors(JsonResponse({"count": len(data), "results": data}))


@require_GET
def api_moment_detail(request, slug):
    try:
        moment = Moment.objects.published().get(slug=slug)
    except Moment.DoesNotExist:
        return _cors(JsonResponse({"error": "Not found."}, status=404))
    payload = moment.to_api_dict(request)
    payload.update({"why_it_helps": moment.why_it_helps, "tips": moment.tip_list})
    return _cors(JsonResponse(payload))
