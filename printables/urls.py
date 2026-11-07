# printables/urls.py
from django.urls import path

from . import views

app_name = "printables"

urlpatterns = [
    path("", views.request_printable, name="request"),
    path("thanks/", views.thanks, name="thanks"),
]
