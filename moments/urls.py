# moments/urls.py
from django.urls import path

from . import views

app_name = "moments"

urlpatterns = [
    path("moments/", views.moment_list, name="list"),
    path("moments/<slug:slug>/", views.moment_detail, name="detail"),
    path("api/moments/", views.api_moment_list, name="api_list"),
    path("api/moments/<slug:slug>/", views.api_moment_detail, name="api_detail"),
]
