# moments/models.py
from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils import timezone

from core.urls_helpers import public_url


class MomentQuerySet(models.QuerySet):
    def published(self):
        return self.filter(status=Moment.Status.PUBLISHED, published_at__lte=timezone.now())


class Moment(models.Model):
    """A moment in a child's life that a personal story can help with.

    Each published Moment becomes a page at /moments/<slug>/ and an entry in
    the JSON API. Nothing goes live until a person has reviewed it.
    """

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        IN_REVIEW = "in_review", "In review"
        PUBLISHED = "published", "Published"

    class AgeBand(models.TextChoices):
        TODDLER = "1-3", "1 to 3"
        PRESCHOOL = "3-5", "3 to 5"
        EARLY_PRIMARY = "5-8", "5 to 8"

    slug = models.SlugField(max_length=120, unique=True)
    title = models.CharField(max_length=160, help_text="e.g. A story for a new baby brother or sister")
    short_name = models.CharField(max_length=80, help_text="e.g. New baby sibling")
    age_band = models.CharField(max_length=10, choices=AgeBand.choices, default=AgeBand.PRESCHOOL)

    summary = models.TextField(help_text="One or two sentences shown on cards and in search results.")
    why_it_helps = models.TextField(help_text="The educator's note: why a personal story helps here.")
    tips = models.TextField(blank=True, help_text="One tip per line. Shown as a list.")
    sample_story = models.TextField(help_text="Short sample story. Use {name} where the child's name goes.")
    sample_name = models.CharField(max_length=40, default="Alex")

    seo_title = models.CharField(max_length=70, blank=True)
    meta_description = models.CharField(max_length=160, blank=True)

    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    published_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = MomentQuerySet.as_manager()

    class Meta:
        ordering = ["short_name"]
        indexes = [models.Index(fields=["status", "published_at"])]

    def __str__(self):
        return self.short_name

    def get_absolute_url(self):
        return reverse("moments:detail", args=[self.slug])

    @property
    def page_title(self):
        return self.seo_title or self.title

    @property
    def description(self):
        return self.meta_description or self.summary[:160]

    @property
    def sample_story_rendered(self):
        return self.sample_story.replace("{name}", self.sample_name)

    @property
    def tip_list(self):
        return [line.strip() for line in self.tips.splitlines() if line.strip()]

    def publish(self, user=None):
        now = timezone.now()
        self.status = self.Status.PUBLISHED
        self.reviewed_by = user or self.reviewed_by
        self.reviewed_at = now
        self.published_at = self.published_at or now
        self.save()

    def to_api_dict(self, request=None):
        url = self.get_absolute_url()
        if request is not None:
            url = public_url(request, url)
        return {
            "slug": self.slug,
            "title": self.title,
            "short_name": self.short_name,
            "age_band": self.age_band,
            "summary": self.summary,
            "url": url,
            "published_at": self.published_at.isoformat() if self.published_at else None,
            "updated_at": self.updated_at.isoformat(),
        }
