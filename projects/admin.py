from django.contrib import admin
from django.db.models import Count
from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html

from .models import Project


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    """
    Админка для проектов.
    """

    list_display = (
        "title",
        "user",
        "status",
        "priority",
        "inn",
        "emails_count",
        "created_at",
        "is_active",
    )
    list_filter = ("status", "priority", "is_active", "created_at", "user")
    search_fields = ("title", "description", "inn", "user__email")
    readonly_fields = ("id", "created_at", "updated_at")
    ordering = ("-created_at",)

    fieldsets = (
        (None, {"fields": ("title", "description", "status", "priority")}),
        (
            _("Финансовая информация"),
            {
                "fields": ("inn",),
            },
        ),
        (
            _("Статистика"),
            {
                "fields": ("deadline",),
                "classes": ("collapse",),
            },
        ),
        (
            _("Настройки"),
            {
                "fields": ("is_active",),
            },
        ),
        (
            _("Связи"),
            {
                "fields": ("user",),
            },
        ),
        (
            _("Даты"),
            {
                "fields": ("created_at", "updated_at"),
                "classes": ("collapse",),
            },
        ),
    )

    def get_queryset(self, request):
        """Оптимизировать запросы с аннотациями."""
        return (
            super()
            .get_queryset(request)
            .select_related("user")
            .annotate(
                emails_count=Count("emails"),
            )
        )

    def emails_count(self, obj):
        """Количество связанных email."""
        return obj.emails_count

    emails_count.short_description = _("Email сообщений")
    emails_count.admin_order_field = "emails_count"

    def changelist_view(self, request, extra_context=None):
        """Добавить статистику на страницу списка."""
        response = super().changelist_view(request, extra_context)

        if hasattr(response, "context_data"):
            stats = self.get_project_stats()
            response.context_data["project_stats"] = stats

        return response

    def get_project_stats(self):
        """Получить статистику проектов."""
        total = Project.objects.count()
        active = Project.objects.filter(is_active=True).count()
        completed = Project.objects.filter(status="completed").count()

        # Статистика по статусам
        status_stats = (
            Project.objects.values("status")
            .annotate(count=Count("id"))
            .order_by("-count")
        )

        # Статистика по приоритетам
        priority_stats = (
            Project.objects.values("priority")
            .annotate(count=Count("id"))
            .order_by("-count")
        )

        # Проекты с ИНН
        with_inn = Project.objects.exclude(inn__isnull=True).exclude(inn="").count()

        return {
            "total": total,
            "active": active,
            "completed": completed,
            "active_percent": (active / total * 100) if total > 0 else 0,
            "completed_percent": (completed / total * 100) if total > 0 else 0,
            "with_inn": with_inn,
            "inn_percent": (with_inn / total * 100) if total > 0 else 0,
            "status_distribution": list(status_stats),
            "priority_distribution": list(priority_stats),
        }
