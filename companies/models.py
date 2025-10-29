import uuid
from decimal import Decimal
from django.db import models
from django.utils.translation import gettext_lazy as _

from users.models import User


class Company(models.Model):
    """
    Модель компании.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="companies", verbose_name=_("user")
    )
    name = models.CharField(_("name"), max_length=200)
    inn = models.CharField(
        _("ИНН"), max_length=12, unique=True, help_text=_("10 or 12 digits")
    )
    legal_address = models.TextField(_("legal address"))
    actual_address = models.TextField(_("actual address"), blank=True)
    phone = models.CharField(_("phone"), max_length=20, blank=True)
    email = models.EmailField(_("email"), blank=True)
    website = models.URLField(_("website"), blank=True)

    # Контактное лицо
    contact_person = models.CharField(_("contact person"), max_length=100, blank=True)
    contact_position = models.CharField(
        _("contact position"), max_length=100, blank=True
    )

    # Финансовая информация
    credit_limit = models.DecimalField(
        _("credit limit"),
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text=_("in rubles"),
    )
    current_debt = models.DecimalField(
        _("current debt"),
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text=_("in rubles"),
    )

    # Статус и тип
    COMPANY_TYPES = [
        ("client", _("Client")),
        ("supplier", _("Supplier")),
        ("partner", _("Partner")),
        ("competitor", _("Competitor")),
    ]
    company_type = models.CharField(
        _("company type"), max_length=20, choices=COMPANY_TYPES, default="client"
    )

    STATUS_CHOICES = [
        ("active", _("Active")),
        ("inactive", _("Inactive")),
        ("blocked", _("Blocked")),
    ]
    status = models.CharField(
        _("status"), max_length=20, choices=STATUS_CHOICES, default="active"
    )

    # Дополнительная информация
    notes = models.TextField(_("notes"), blank=True)
    tags = models.JSONField(_("tags"), default=list, blank=True)

    is_active = models.BooleanField(_("active"), default=True)
    created_at = models.DateTimeField(_("created at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("updated at"), auto_now=True)

    class Meta:
        verbose_name = _("company")
        verbose_name_plural = _("companies")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "inn"]),
            models.Index(fields=["user", "name"]),
            models.Index(fields=["user", "company_type"]),
            models.Index(fields=["user", "status"]),
            models.Index(fields=["user", "is_active"]),
        ]
        unique_together = ["user", "inn"]

    def __str__(self):
        return f"{self.name} (ИНН: {self.inn})"

    @property
    def available_credit(self):
        """Доступный кредитный лимит."""
        return self.credit_limit - self.current_debt

    @property
    def total_orders_amount(self):
        """Общая сумма заказов."""
        return self.orders.aggregate(total=models.Sum("amount"))["total"] or Decimal(
            "0"
        )

    @property
    def total_payments_amount(self):
        """Общая сумма платежей."""
        return self.payments.aggregate(total=models.Sum("amount"))["total"] or Decimal(
            "0"
        )

    @property
    def unpaid_orders_amount(self):
        """Сумма неоплаченных заказов."""
        paid_orders = self.payments.values_list("order", flat=True)
        unpaid_orders = self.orders.exclude(id__in=paid_orders)
        return unpaid_orders.aggregate(total=models.Sum("amount"))["total"] or Decimal(
            "0"
        )

    def get_tags_list(self):
        """Получить список тегов."""
        return self.tags if isinstance(self.tags, list) else []

    def add_tag(self, tag):
        """Добавить тег."""
        if tag not in self.tags:
            self.tags.append(tag)
            self.save()

    def remove_tag(self, tag):
        """Удалить тег."""
        if tag in self.tags:
            self.tags.remove(tag)
            self.save()


class Order(models.Model):
    """
    Модель заказа.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="orders",
        verbose_name=_("company"),
    )
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="orders", verbose_name=_("user")
    )

    # Информация о заказе
    order_number = models.CharField(_("order number"), max_length=50, unique=True)
    title = models.CharField(_("title"), max_length=200)
    description = models.TextField(_("description"), blank=True)

    # Финансовая информация
    amount = models.DecimalField(
        _("amount"), max_digits=12, decimal_places=2, help_text=_("in rubles")
    )
    currency = models.CharField(_("currency"), max_length=3, default="RUB")

    # Статусы
    ORDER_STATUS_CHOICES = [
        ("draft", _("Draft")),
        ("confirmed", _("Confirmed")),
        ("in_progress", _("In Progress")),
        ("completed", _("Completed")),
        ("cancelled", _("Cancelled")),
    ]
    status = models.CharField(
        _("status"), max_length=20, choices=ORDER_STATUS_CHOICES, default="draft"
    )

    # Даты
    order_date = models.DateField(_("order date"), auto_now_add=True)
    due_date = models.DateField(_("due date"), blank=True, null=True)
    completion_date = models.DateField(_("completion date"), blank=True, null=True)

    # Дополнительная информация
    priority = models.CharField(
        _("priority"),
        max_length=20,
        choices=[
            ("low", _("Low")),
            ("medium", _("Medium")),
            ("high", _("High")),
            ("urgent", _("Urgent")),
        ],
        default="medium",
    )

    notes = models.TextField(_("notes"), blank=True)
    created_at = models.DateTimeField(_("created at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("updated at"), auto_now=True)

    class Meta:
        verbose_name = _("order")
        verbose_name_plural = _("orders")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["company", "status"]),
            models.Index(fields=["user", "status"]),
            models.Index(fields=["order_number"]),
            models.Index(fields=["order_date"]),
            models.Index(fields=["due_date"]),
        ]
        unique_together = ["company", "order_number"]

    def __str__(self):
        return f"Заказ #{self.order_number} - {self.company.name}"

    @property
    def paid_amount(self):
        """Оплаченная сумма."""
        return self.payments.aggregate(total=models.Sum("amount"))["total"] or Decimal(
            "0"
        )

    @property
    def remaining_amount(self):
        """Оставшаяся сумма к оплате."""
        return self.amount - self.paid_amount

    @property
    def is_paid(self):
        """Проверяет, полностью ли оплачен заказ."""
        return self.paid_amount >= self.amount

    @property
    def payment_status(self):
        """Статус оплаты."""
        paid = self.paid_amount
        if paid == 0:
            return _("Not paid")
        elif paid < self.amount:
            return _("Partially paid")
        else:
            return _("Fully paid")


class Payment(models.Model):
    """
    Модель платежа.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="payments",
        verbose_name=_("company"),
    )
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="payments",
        verbose_name=_("order"),
        blank=True,
        null=True,
    )
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="payments", verbose_name=_("user")
    )

    # Информация о платеже
    amount = models.DecimalField(
        _("amount"), max_digits=12, decimal_places=2, help_text=_("in rubles")
    )
    currency = models.CharField(_("currency"), max_length=3, default="RUB")

    # Способы оплаты
    PAYMENT_METHODS = [
        ("cash", _("Cash")),
        ("bank_transfer", _("Bank Transfer")),
        ("card", _("Card")),
        ("check", _("Check")),
        ("other", _("Other")),
    ]
    payment_method = models.CharField(
        _("payment method"),
        max_length=20,
        choices=PAYMENT_METHODS,
        default="bank_transfer",
    )

    # Документы
    payment_number = models.CharField(_("payment number"), max_length=50, blank=True)
    invoice_number = models.CharField(_("invoice number"), max_length=50, blank=True)

    # Даты
    payment_date = models.DateField(_("payment date"))
    received_date = models.DateField(_("received date"), auto_now_add=True)

    # Статус
    PAYMENT_STATUS_CHOICES = [
        ("pending", _("Pending")),
        ("confirmed", _("Confirmed")),
        ("rejected", _("Rejected")),
    ]
    status = models.CharField(
        _("status"), max_length=20, choices=PAYMENT_STATUS_CHOICES, default="pending"
    )

    # Дополнительная информация
    notes = models.TextField(_("notes"), blank=True)
    created_at = models.DateTimeField(_("created at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("updated at"), auto_now=True)

    class Meta:
        verbose_name = _("payment")
        verbose_name_plural = _("payments")
        ordering = ["-payment_date"]
        indexes = [
            models.Index(fields=["company", "status"]),
            models.Index(fields=["order", "status"]),
            models.Index(fields=["user", "status"]),
            models.Index(fields=["payment_date"]),
            models.Index(fields=["received_date"]),
        ]

    def __str__(self):
        return f"Платеж {self.amount} руб. - {self.company.name}"

    def save(self, *args, **kwargs):
        """При сохранении платежа обновляем текущий долг компании."""
        super().save(*args, **kwargs)

        if self.status == "confirmed":
            # Обновляем текущий долг компании
            if self.order:
                # Для заказов уменьшаем долг
                self.company.current_debt = max(
                    0, self.company.current_debt - self.amount
                )
            else:
                # Для других платежей увеличиваем долг (авансы и т.д.)
                self.company.current_debt += self.amount

            self.company.save()


class CompanyNote(models.Model):
    """
    Заметки о компании.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="company_notes",
        verbose_name=_("company"),
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="company_notes",
        verbose_name=_("user"),
    )

    title = models.CharField(_("title"), max_length=200)
    content = models.TextField(_("content"))

    NOTE_TYPES = [
        ("general", _("General")),
        ("meeting", _("Meeting")),
        ("call", _("Call")),
        ("negotiation", _("Negotiation")),
        ("complaint", _("Complaint")),
        ("praise", _("Praise")),
    ]
    note_type = models.CharField(
        _("note type"), max_length=20, choices=NOTE_TYPES, default="general"
    )

    is_important = models.BooleanField(_("important"), default=False)
    created_at = models.DateTimeField(_("created at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("updated at"), auto_now=True)

    class Meta:
        verbose_name = _("company note")
        verbose_name_plural = _("company notes")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["company", "is_important"]),
            models.Index(fields=["user", "created_at"]),
            models.Index(fields=["note_type"]),
        ]

    def __str__(self):
        return f"{self.company.name} - {self.title}"
