from django.contrib import admin
from django.db.models import Count, Sum
from django.utils.translation import gettext_lazy as _

# from django.utils.html import format_html

from .models import Company, Order, Payment


class OrderInline(admin.TabularInline):
    """
    Inline для заказов в компании.
    """

    model = Order
    extra = 0
    readonly_fields = ("created_at",)
    fields = ("number", "amount", "created_at")
    ordering = ("-created_at",)


class PaymentInline(admin.TabularInline):
    """
    Inline для оплат в компании.
    """

    model = Payment
    extra = 0
    readonly_fields = ("payment_date",)
    fields = ("order", "amount", "payment_date")
    ordering = ("-payment_date",)


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    """
    Админка для компаний.
    """

    list_display = (
        "name",
        "inn",
        "user",
        "orders_count",
        "total_orders_amount",
        "payments_count",
        "total_payments_amount",
        "created_at",
    )
    list_filter = ("created_at", "user")
    search_fields = ("name", "inn", "address")
    readonly_fields = ("id", "created_at", "updated_at")
    ordering = ("-created_at",)
    inlines = [OrderInline, PaymentInline]

    fieldsets = (
        (None, {"fields": ("name", "inn", "address")}),
        (
            _("Финансовая информация"),
            {
                "fields": (
                    "orders_count",
                    "total_orders_amount",
                    "payments_count",
                    "total_payments_amount",
                ),
                "classes": ("collapse",),
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
                orders_count=Count("orders"),
                payments_count=Count("payments"),
                total_orders_amount=Sum("orders__amount"),
                total_payments_amount=Sum("payments__amount"),
            )
        )

    def orders_count(self, obj):
        """Количество заказов."""
        return obj.orders_count

    orders_count.short_description = _("Заказов")
    orders_count.admin_order_field = "orders_count"

    def total_orders_amount(self, obj):
        """Общая сумма заказов."""
        return f"{obj.total_orders_amount or 0:,.0f} ₽"

    total_orders_amount.short_description = _("Сумма заказов")
    total_orders_amount.admin_order_field = "total_orders_amount"

    def payments_count(self, obj):
        """Количество оплат."""
        return obj.payments_count

    payments_count.short_description = _("Оплат")
    payments_count.admin_order_field = "payments_count"

    def total_payments_amount(self, obj):
        """Общая сумма оплат."""
        return f"{obj.total_payments_amount or 0:,.0f} ₽"

    total_payments_amount.short_description = _("Сумма оплат")
    total_payments_amount.admin_order_field = "total_payments_amount"

    def changelist_view(self, request, extra_context=None):
        """Добавить статистику на страницу списка."""
        response = super().changelist_view(request, extra_context)

        if hasattr(response, "context_data"):
            stats = self.get_company_stats()
            response.context_data["company_stats"] = stats

        return response

    def get_company_stats(self):
        """Получить статистику компаний."""
        total = Company.objects.count()
        with_inn = Company.objects.exclude(inn__isnull=True).exclude(inn="").count()
        total_orders = Order.objects.count()
        total_payments = Payment.objects.count()
        total_orders_amount = Order.objects.aggregate(Sum("amount"))["amount__sum"] or 0
        total_payments_amount = (
            Payment.objects.aggregate(Sum("amount"))["amount__sum"] or 0
        )

        return {
            "total": total,
            "with_inn": with_inn,
            "inn_percent": (with_inn / total * 100) if total > 0 else 0,
            "total_orders": total_orders,
            "total_payments": total_payments,
            "total_orders_amount": total_orders_amount,
            "total_payments_amount": total_payments_amount,
            "avg_order_amount": (
                (total_orders_amount / total_orders) if total_orders > 0 else 0
            ),
        }


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    """
    Админка для заказов.
    """

    list_display = ("order_number", "company", "amount", "created_at")
    list_filter = ("created_at", "company")
    search_fields = ("number", "company__name", "company__inn")
    readonly_fields = ("id", "created_at")
    ordering = ("-created_at",)

    fieldsets = (
        (None, {"fields": ("company", "number", "amount")}),
        (
            _("Даты"),
            {
                "fields": ("created_at",),
                "classes": ("collapse",),
            },
        ),
    )

    def get_queryset(self, request):
        """Оптимизировать запросы."""
        return super().get_queryset(request).select_related("company")


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    """
    Админка для оплат.
    """

    list_display = ("company", "order", "amount", "payment_date")
    list_filter = ("payment_date", "company", "order")
    search_fields = ("company__name", "company__inn", "order__number")
    readonly_fields = ("id",)
    ordering = ("-payment_date",)

    fieldsets = ((None, {"fields": ("company", "order", "amount", "payment_date")}),)

    def get_queryset(self, request):
        """Оптимизировать запросы."""
        return super().get_queryset(request).select_related("company", "order")
