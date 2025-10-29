from django.urls import path
from django.contrib.auth import views as auth_views

from . import views

app_name = "users"

urlpatterns = [
    # Dashboard
    path("", views.DashboardView.as_view(), name="dashboard"),
    path("dashboard/", views.DashboardView.as_view(), name="dashboard"),
    # Profile
    path("profile/", views.ProfileView.as_view(), name="profile"),
    # Settings
    path("settings/", views.SettingsView.as_view(), name="settings"),
    # Tokens
    path("tokens/", views.TokenListView.as_view(), name="token_list"),
    path("tokens/create/", views.TokenCreateView.as_view(), name="token_create"),
    path(
        "tokens/<uuid:pk>/delete/", views.TokenDeleteView.as_view(), name="token_delete"
    ),
    # API
    path(
        "api/dashboard/stats/",
        views.DashboardStatsAPIView.as_view(),
        name="api_dashboard_stats",
    ),
    path(
        "api/dashboard/activity/",
        views.RecentActivityAPIView.as_view(),
        name="api_recent_activity",
    ),
    path(
        "api/system/health/",
        views.SystemHealthAPIView.as_view(),
        name="api_system_health",
    ),
    # AJAX
    path(
        "ajax/tokens/<uuid:token_id>/revoke/",
        views.revoke_token_ajax,
        name="ajax_revoke_token",
    ),
    path("ajax/settings/", views.user_settings_ajax, name="ajax_user_settings"),
    path(
        "ajax/settings/update/",
        views.update_user_settings_ajax,
        name="ajax_update_settings",
    ),
]
