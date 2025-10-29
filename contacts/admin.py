from django.contrib import admin
from django.db.models import Count
from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html

from .models import Contact


@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    """
    Админка для контактов.
    """

    list_display = (
        "get_full_name",
        "email",
        "phone",
        "company",
        "user",
        "is_email_verified",
        "is_phone_verified",
        "created_at",
    )
    list_filter = (
        "is_email_verified",
        "is_phone_verified",
        "created_at",
        "user",
        "company",
    )
    search_fields = ("first_name", "last_name", "email", "phone", "company")
    readonly_fields = ("id", "created_at", "updated_at")
    ordering = ("-created_at",)

    fieldsets = (
        (None, {"fields": ("first_name", "last_name", "email", "phone")}),
        (
            _("Компания"),
            {
                "fields": ("company",),
            },
        ),
        (
            _("Верификация"),
            {
                "fields": ("is_email_verified", "is_phone_verified"),
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

    def get_full_name(self, obj):
        """Получить полное имя контакта."""
        return obj.get_full_name()

    get_full_name.short_description = _("Полное имя")
    get_full_name.admin_order_field = "last_name"

    def get_queryset(self, request):
        """Оптимизировать запросы."""
        return super().get_queryset(request).select_related("user")

    def changelist_view(self, request, extra_context=None):
        """Добавить статистику на страницу списка."""
        response = super().changelist_view(request, extra_context)

        if hasattr(response, "context_data"):
            stats = self.get_contact_stats()
            response.context_data["contact_stats"] = stats

        return response

    def get_contact_stats(self):
        """Получить статистику контактов."""
        total = Contact.objects.count()
        verified_emails = Contact.objects.filter(is_email_verified=True).count()
        verified_phones = Contact.objects.filter(is_phone_verified=True).count()
        with_company = Contact.objects.exclude(company="").count()

        return {
            "total": total,
            "verified_emails": verified_emails,
            "verified_phones": verified_phones,
            "with_company": with_company,
            "email_verified_percent": (
                (verified_emails / total * 100) if total > 0 else 0
            ),
            "phone_verified_percent": (
                (verified_phones / total * 100) if total > 0 else 0
            ),
        }
