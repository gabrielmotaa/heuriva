from django.urls import path

from . import views

app_name = "analysis"

urlpatterns = [
    # Projects
    path("projects/", views.project_list, name="project_list"),
    path("projects/new/", views.project_create, name="project_create"),
    path("projects/<str:short_id>/", views.project_detail, name="project_detail"),
    path("projects/<str:short_id>/edit/", views.project_update, name="project_update"),
    # Analysis
    path(
        "projects/<str:project_short_id>/analysis/new/",
        views.analysis_create,
        name="analysis_create",
    ),
    path("analysis/<str:short_id>/", views.analysis_detail, name="analysis_detail"),
]
