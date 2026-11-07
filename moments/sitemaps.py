# moments/sitemaps.py
from urllib.parse import urlparse

from django.conf import settings
from django.contrib.sitemaps import Sitemap

from .models import Moment


class MomentSitemap(Sitemap):
    changefreq = "monthly"
    priority = 0.7

    def items(self):
        return Moment.objects.published()

    def lastmod(self, obj):
        return obj.updated_at

    def get_domain(self, site=None):
        # Behind flipwhizz.com/stories, list flipwhizz.com URLs, not the origin host.
        if settings.PUBLIC_BASE_URL:
            return urlparse(settings.PUBLIC_BASE_URL).netloc
        return super().get_domain(site)

    def get_protocol(self, protocol=None):
        if settings.PUBLIC_BASE_URL:
            return urlparse(settings.PUBLIC_BASE_URL).scheme
        return super().get_protocol(protocol)
