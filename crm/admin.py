from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import gettext_lazy as _
from django.db.models import Count
from django.urls import reverse
from django.utils.html import format_html

from .models import *  # Import all models from crm app if any


# Custom admin site
class CRMAdminSite(admin.AdminSite):
    """
    Кастомный сайт админки для CRM.
    """

    site_header = _("CRM Pro - Администрирование")
    site_title = _("CRM Pro Admin")
    index_title = _("Панель управления CRM")

    def get_app_list(self, request):
        """
        Кастомизация списка приложений в админке.
        """
        app_list = super().get_app_list(request)

        # Группировка приложений
        app_order = [
            "users",
            "contacts",
            "companies",
            "projects",
            "emails",
            "django_celery_beat",
            "django_celery_results",
            "auth",
            "guardian",
            "admin",
            "sessions",
            "contenttypes",
        ]

        app_dict = {app["app_label"]: app for app in app_list}

        ordered_apps = []
        for app_label in app_order:
            if app_label in app_dict:
                ordered_apps.append(app_dict[app_label])

        # Добавить остальные приложения
        for app in app_list:
            if app["app_label"] not in app_order:
                ordered_apps.append(app)

        return ordered_apps


# Create admin site instance
crm_admin_site = CRMAdminSite(name="crm_admin")

# Register the admin site
admin.site = crm_admin_site


# Custom admin classes for built-in models
@admin.register(admin.models.LogEntry)
class LogEntryAdmin(admin.ModelAdmin):
    """
    Админка для логов действий.
    """

    list_display = (
        "action_time",
        "user",
        "content_type",
        "object_repr",
        "action_flag",
        "change_message",
    )
    list_filter = ("action_time", "action_flag", "content_type", "user")
    search_fields = ("object_repr", "change_message", "user__email")
    readonly_fields = (
        "action_time",
        "user",
        "content_type",
        "object_id",
        "object_repr",
        "action_flag",
        "change_message",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


# Dashboard stats
class DashboardStatsAdmin(admin.ModelAdmin):
    """
    Базовый класс для админок с статистикой.
    """

    def changelist_view(self, request, extra_context=None):
        """Добавляет статистику на страницу списка."""
        response = super().changelist_view(request, extra_context)

        if hasattr(response, "context_data"):
            stats = self.get_dashboard_stats()
            response.context_data["dashboard_stats"] = stats

        return response

    def get_dashboard_stats(self):
        """Переопределить в дочерних классах для добавления статистики."""
        return {}
