# printables/admin.py
from django.contrib import admin, messages

from .models import PrintableRequest


@admin.register(PrintableRequest)
class PrintableRequestAdmin(admin.ModelAdmin):
    list_display = ("token", "status", "attempts", "moment", "child_age", "utm_source", "created_at", "sent_at")
    list_filter = ("status", "moment", "marketing_opt_in", "utm_source")
    search_fields = ("email", "token")
    date_hierarchy = "created_at"
    readonly_fields = [f.name for f in PrintableRequest._meta.fields]
    actions = ["retry_selected"]

    def has_add_permission(self, request):
        return False

    @admin.action(description="Retry (requeue failed requests)")
    def retry_selected(self, request, queryset):
        updated = queryset.filter(status=PrintableRequest.Status.FAILED, purged_at__isnull=True).update(
            status=PrintableRequest.Status.QUEUED, attempts=0, last_error="", next_attempt_at=None
        )
        self.message_user(request, f"Requeued {updated} request(s).", messages.SUCCESS)
