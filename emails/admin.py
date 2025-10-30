from django.contrib import admin
from django.db.models import Count, Sum, Avg
from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html

from .models import EmailCredentials, EmailMessage, EmailSyncLog


class EmailMessageInline(admin.TabularInline):
    """
    Inline для email сообщений в credentials.
    """

    model = EmailMessage
    extra = 0
    readonly_fields = ("subject", "received_at", "is_read")
    fields = ("subject", "received_at", "is_read")
    ordering = ("-received_at",)
    show_change_link = True


@admin.register(EmailCredentials)
class EmailCredentialsAdmin(admin.ModelAdmin):
    """
    Админка для учетных данных email.
    """

    list_display = (
        "email",
        "user",
        "server",
        "is_active",
        "messages_count",
        "last_sync",
        "created_at",
    )
    list_filter = ("is_active", "created_at", "user")
    search_fields = ("email", "server", "user__email")
    readonly_fields = ("id", "created_at", "updated_at", "password")
    ordering = ("-created_at",)
    inlines = [EmailMessageInline]

    fieldsets = (
        (None, {"fields": ("user", "email", "server", "password")}),
        (
            _("Настройки"),
            {
                "fields": ("use_ssl", "is_active"),
            },
        ),
        (
            _("Статистика"),
            {
                "fields": ("messages_count", "last_sync"),
                "classes": ("collapse",),
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
                messages_count=Count("emails"),
            )
        )

    def messages_count(self, obj):
        """Количество сообщений."""
        return obj.messages_count

    messages_count.short_description = _("Сообщений")
    messages_count.admin_order_field = "messages_count"

    def last_sync(self, obj):
        """Последняя синхронизация."""
        last_log = obj.sync_logs.order_by("-started_at").first()
        if last_log:
            return format_html(
                '<span class="{}">{}</span>',
                "text-success" if last_log.status == "success" else "text-danger",
                last_log.started_at.strftime("%d.%m.%Y %H:%M"),
            )
        return "-"

    last_sync.short_description = _("Последняя синхронизация")


@admin.register(EmailMessage)
class EmailMessageAdmin(admin.ModelAdmin):
    """
    Админка для email сообщений.
    """

    list_display = (
        "subject_short",
        "sender",
        "credentials",
        "received_at",
        "is_read",
        "is_important",
        "has_attachments",
        "is_processed",
    )
    list_filter = (
        "is_read",
        "is_important",
        "has_attachments",
        "is_processed",
        "received_at",
        "credentials__user",
    )
    search_fields = ("subject", "body", "sender", "recipients_to")
    readonly_fields = ("id", "parsed_inn", "created_at", "updated_at")
    ordering = ("-received_at",)

    fieldsets = (
        (None, {"fields": ("credentials", "subject", "body")}),
        (
            _("Отправитель и получатели"),
            {
                "fields": (
                    "sender",
                    "recipients_to",
                    "recipients_cc",
                    "recipients_bcc",
                ),
            },
        ),
        (
            _("Статус"),
            {
                "fields": (
                    "is_read",
                    "is_important",
                    "has_attachments",
                    "is_processed",
                ),
            },
        ),
        (
            _("Парсинг"),
            {
                "fields": ("parsed_inn", "related_company", "related_project"),
            },
        ),
        (
            _("Даты"),
            {
                "fields": ("received_at", "created_at", "updated_at"),
                "classes": ("collapse",),
            },
        ),
    )

    def subject_short(self, obj):
        """Короткий заголовок."""
        return obj.subject[:50] + "..." if len(obj.subject) > 50 else obj.subject

    subject_short.short_description = _("Тема")
    subject_short.admin_order_field = "subject"

    def changelist_view(self, request, extra_context=None):
        """Добавить статистику на страницу списка."""
        response = super().changelist_view(request, extra_context)

        if hasattr(response, "context_data"):
            stats = self.get_email_stats()
            response.context_data["email_stats"] = stats

        return response

    def get_email_stats(self):
        """Получить статистику email."""
        total = EmailMessage.objects.count()
        unread = EmailMessage.objects.filter(is_read=False).count()
        important = EmailMessage.objects.filter(is_important=True).count()
        with_attachments = EmailMessage.objects.filter(has_attachments=True).count()
        processed = EmailMessage.objects.filter(is_processed=True).count()
        with_inn = (
            EmailMessage.objects.exclude(parsed_inn__isnull=True)
            .exclude(parsed_inn="")
            .count()
        )

        return {
            "total": total,
            "unread": unread,
            "important": important,
            "with_attachments": with_attachments,
            "processed": processed,
            "with_inn": with_inn,
            "unread_percent": (unread / total * 100) if total > 0 else 0,
            "processed_percent": (processed / total * 100) if total > 0 else 0,
            "inn_parsed_percent": (with_inn / total * 100) if total > 0 else 0,
        }


@admin.register(EmailSyncLog)
class EmailSyncLogAdmin(admin.ModelAdmin):
    """
    Админка для логов синхронизации email.
    """

    list_display = (
        "credentials",
        "status",
        "started_at",
        "duration_display",
        "emails_fetched",
        "emails_processed",
    )
    list_filter = ("status", "started_at", "credentials__user")
    search_fields = ("credentials__email",)
    readonly_fields = (
        "id",
        "started_at",
        "completed_at",
        "duration_seconds",
        "duration_display",
    )
    ordering = ("-started_at",)

    fieldsets = (
        (None, {"fields": ("credentials", "status")}),
        (
            _("Время выполнения"),
            {
                "fields": (
                    "started_at",
                    "completed_at",
                    "duration_seconds",
                    "duration_display",
                ),
            },
        ),
        (
            _("Результаты"),
            {
                "fields": ("emails_fetched", "emails_processed", "emails_skipped"),
            },
        ),
        (
            _("Ошибки"),
            {
                "fields": ("errors", "warnings"),
                "classes": ("collapse",),
            },
        ),
    )

    def duration_display(self, obj):
        """Длительность синхронизации."""
        return obj.duration_display

    duration_display.short_description = _("Длительность")
    duration_display.admin_order_field = "duration_seconds"

    def changelist_view(self, request, extra_context=None):
        """Добавить статистику на страницу списка."""
        response = super().changelist_view(request, extra_context)

        if hasattr(response, "context_data"):
            stats = self.get_sync_stats()
            response.context_data["sync_stats"] = stats

        return response

    def get_sync_stats(self):
        """Получить статистику синхронизаций."""
        total = EmailSyncLog.objects.count()
        successful = EmailSyncLog.objects.filter(status="success").count()
        failed = EmailSyncLog.objects.filter(status="failed").count()

        total_messages = (
            EmailSyncLog.objects.aggregate(total=Sum("messages_processed"))["total"]
            or 0
        )

        avg_duration = (
            EmailSyncLog.objects.filter(status="success")
            .exclude(duration__isnull=True)
            .aggregate(avg=Avg("duration"))["avg"]
        )

        return {
            "total": total,
            "successful": successful,
            "failed": failed,
            "success_rate": (successful / total * 100) if total > 0 else 0,
            "total_messages": total_messages,
            "avg_duration": avg_duration.total_seconds() if avg_duration else 0,
        }
