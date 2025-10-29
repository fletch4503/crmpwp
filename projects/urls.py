from django.urls import path
from . import views

app_name = "projects"

urlpatterns = [
    # Основные страницы проектов
    path("", views.ProjectListView.as_view(), name="project_list"),
    path("create/", views.ProjectCreateView.as_view(), name="project_create"),
    path("<uuid:pk>/", views.ProjectDetailView.as_view(), name="project_detail"),
    path("<uuid:pk>/update/", views.ProjectUpdateView.as_view(), name="project_update"),
    path("<uuid:pk>/delete/", views.ProjectDeleteView.as_view(), name="project_delete"),
    # API endpoints
    path("api/", views.ProjectAPIView.as_view(), name="api_projects"),
    path(
        "api/<uuid:project_id>/",
        views.ProjectDetailAPIView.as_view(),
        name="api_project_detail",
    ),
    # AJAX endpoints
    path("ajax/search/", views.project_search_ajax, name="project_search_ajax"),
    path(
        "ajax/<uuid:project_id>/update-status/",
        views.update_project_status_ajax,
        name="update_project_status_ajax",
    ),
    path(
        "ajax/<uuid:project_id>/add-note/",
        views.add_project_note_ajax,
        name="add_project_note_ajax",
    ),
    path(
        "ajax/<uuid:project_id>/emails/",
        views.get_project_emails_ajax,
        name="get_project_emails_ajax",
    ),
]
