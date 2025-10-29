from django.urls import path
from . import views

app_name = "emails"

urlpatterns = [
    # Основные страницы email
    path("", views.EmailMessageListView.as_view(), name="email_list"),
    path("<uuid:pk>/", views.EmailMessageDetailView.as_view(), name="email_detail"),
    # Настройки учетных данных
    path("credentials/", views.EmailCredentialsView.as_view(), name="credentials"),
    # Правила обработки
    path("rules/", views.EmailProcessingRuleListView.as_view(), name="rules_list"),
    path(
        "rules/create/",
        views.EmailProcessingRuleCreateView.as_view(),
        name="rule_create",
    ),
    path(
        "rules/<uuid:pk>/update/",
        views.EmailProcessingRuleUpdateView.as_view(),
        name="rule_update",
    ),
    # API endpoints
    path("api/", views.EmailAPIView.as_view(), name="api_emails"),
    path("api/sync/", views.EmailSyncAPIView.as_view(), name="api_sync"),
    # AJAX endpoints
    path("ajax/search/", views.email_search_ajax, name="email_search_ajax"),
    path(
        "ajax/<uuid:email_id>/mark-read/",
        views.mark_email_read_ajax,
        name="mark_email_read_ajax",
    ),
    path(
        "ajax/<uuid:email_id>/toggle-important/",
        views.toggle_email_important_ajax,
        name="toggle_email_important_ajax",
    ),
    path(
        "ajax/<uuid:email_id>/link-project/<uuid:project_id>/",
        views.link_email_to_project_ajax,
        name="link_email_to_project_ajax",
    ),
    path("ajax/sync-now/", views.sync_emails_now_ajax, name="sync_emails_now_ajax"),
    path("ajax/stats/", views.get_email_stats_ajax, name="get_email_stats_ajax"),
]
