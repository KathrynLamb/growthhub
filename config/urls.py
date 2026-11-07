# config/urls.py
from django.contrib import admin
from django.contrib.sitemaps.views import sitemap
from django.urls import include, path

from moments.sitemaps import MomentSitemap

sitemaps = {"moments": MomentSitemap}

urlpatterns = [
    path("admin/", admin.site.urls),
    path("sitemap.xml", sitemap, {"sitemaps": sitemaps}, name="sitemap"),
    path("", include("core.urls")),
    path("", include("moments.urls")),
    path("free-printable/", include("printables.urls")),
]

admin.site.site_header = "FlipWhizz Growth Hub"
admin.site.site_title = "Growth Hub"
