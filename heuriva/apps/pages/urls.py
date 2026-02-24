from django.urls import path

from . import views

app_name = "pages"


urlpatterns = [
    path("", views.index, name="index"),
    path("robots.txt", views.robots),
    path("__heartbeat__", views.heartbeat),
]
