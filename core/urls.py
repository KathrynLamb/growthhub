# core/urls.py
from django.urls import path

from . import cron, views

app_name = "core"

urlpatterns = [
    path("", views.home, name="home"),
    path("healthz", views.healthz, name="healthz"),
    path("robots.txt", views.robots_txt, name="robots"),
    path("internal/cron/", cron.run_cron, name="cron"),
]
