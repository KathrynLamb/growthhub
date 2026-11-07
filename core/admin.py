# core/admin.py
from django.contrib import admin

from .models import Incident


@admin.register(Incident)
class IncidentAdmin(admin.ModelAdmin):
    list_display = ("title", "severity", "started_at", "resolved_at", "is_open")
    list_filter = ("severity",)
    search_fields = ("title", "impact", "root_cause")
    date_hierarchy = "started_at"

    @admin.display(boolean=True, description="Open")
    def is_open(self, obj):
        return obj.is_open
