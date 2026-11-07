# moments/admin.py
from django.contrib import admin, messages

from .models import Moment


@admin.register(Moment)
class MomentAdmin(admin.ModelAdmin):
    list_display = ("short_name", "age_band", "status", "reviewed_by", "published_at", "updated_at")
    list_filter = ("status", "age_band")
    search_fields = ("title", "short_name", "summary")
    prepopulated_fields = {"slug": ("short_name",)}
    readonly_fields = ("reviewed_by", "reviewed_at", "created_at", "updated_at")
    actions = ["publish_selected", "send_back_to_draft"]
    fieldsets = (
        (None, {"fields": ("short_name", "title", "slug", "age_band", "summary")}),
        ("Content", {"fields": ("why_it_helps", "tips", "sample_name", "sample_story")}),
        ("Search", {"fields": ("seo_title", "meta_description")}),
        ("Review", {"fields": ("status", "published_at", "reviewed_by", "reviewed_at", "created_at", "updated_at")}),
    )

    def save_model(self, request, obj, form, change):
        # Publishing from the edit page works the same as the list action:
        # fill in the publish date and record who reviewed it.
        if obj.status == Moment.Status.PUBLISHED and (obj.published_at is None or obj.reviewed_by is None):
            obj.publish(user=request.user)
            return
        super().save_model(request, obj, form, change)

    @admin.action(description="Publish (marks as reviewed by you)")
    def publish_selected(self, request, queryset):
        for moment in queryset:
            moment.publish(user=request.user)
        self.message_user(request, f"Published {queryset.count()} moment(s).", messages.SUCCESS)

    @admin.action(description="Send back to draft")
    def send_back_to_draft(self, request, queryset):
        updated = queryset.update(status=Moment.Status.DRAFT)
        self.message_user(request, f"{updated} moment(s) moved to draft.", messages.WARNING)
