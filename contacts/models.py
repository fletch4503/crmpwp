import uuid
from django.db import models
from django.utils.translation import gettext_lazy as _
from phonenumber_field.modelfields import PhoneNumberField

from users.models import User


class Contact(models.Model):
    """
    Модель контакта пользователя.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="contacts", verbose_name=_("user")
    )
    first_name = models.CharField(_("first name"), max_length=100)
    last_name = models.CharField(_("last name"), max_length=100, blank=True)
    email = models.EmailField(_("email address"), blank=True)
    phone = PhoneNumberField(_("phone number"), blank=True, null=True)
    company = models.CharField(_("company"), max_length=200, blank=True)
    position = models.CharField(_("position"), max_length=100, blank=True)
    address = models.TextField(_("address"), blank=True)
    notes = models.TextField(_("notes"), blank=True)

    # Социальные сети и мессенджеры
    telegram = models.CharField(_("telegram"), max_length=100, blank=True)
    whatsapp = models.CharField(_("whatsapp"), max_length=100, blank=True)
    linkedin = models.URLField(_("linkedin"), blank=True)
    website = models.URLField(_("website"), blank=True)

    # Метаданные
    is_active = models.BooleanField(_("active"), default=True)
    is_favorite = models.BooleanField(_("favorite"), default=False)
    tags = models.JSONField(_("tags"), default=list, blank=True)

    created_at = models.DateTimeField(_("created at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("updated at"), auto_now=True)

    class Meta:
        verbose_name = _("contact")
        verbose_name_plural = _("contacts")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "email"]),
            models.Index(fields=["user", "phone"]),
            models.Index(fields=["user", "first_name", "last_name"]),
            models.Index(fields=["user", "company"]),
            models.Index(fields=["user", "is_favorite"]),
        ]

    def __str__(self):
        full_name = f"{self.first_name} {self.last_name}".strip()
        if self.company:
            return f"{full_name} ({self.company})"
        return full_name

    @property
    def full_name(self):
        """Полное имя контакта."""
        return f"{self.first_name} {self.last_name}".strip()

    @property
    def display_name(self):
        """Отображаемое имя для списков."""
        name = self.full_name
        if self.company:
            name += f" - {self.company}"
        return name

    @property
    def primary_contact(self):
        """Основной способ связи."""
        if self.email:
            return f"📧 {self.email}"
        elif self.phone:
            return f"📱 {self.phone}"
        elif self.telegram:
            return f"✈️ @{self.telegram}"
        return _("No contact information")

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


class ContactGroup(models.Model):
    """
    Группа контактов для организации.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="contact_groups",
        verbose_name=_("user"),
    )
    name = models.CharField(_("name"), max_length=100)
    description = models.TextField(_("description"), blank=True)
    color = models.CharField(_("color"), max_length=7, default="#3B82F6")  # Hex color
    contacts = models.ManyToManyField(
        Contact, related_name="groups", blank=True, verbose_name=_("contacts")
    )

    created_at = models.DateTimeField(_("created at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("updated at"), auto_now=True)

    class Meta:
        verbose_name = _("contact group")
        verbose_name_plural = _("contact groups")
        ordering = ["name"]
        unique_together = ["user", "name"]

    def __str__(self):
        return f"{self.user.email} - {self.name}"

    @property
    def contacts_count(self):
        """Количество контактов в группе."""
        return self.contacts.count()


class ContactInteraction(models.Model):
    """
    История взаимодействия с контактом.
    """

    INTERACTION_TYPES = [
        ("call", _("Call")),
        ("email", _("Email")),
        ("meeting", _("Meeting")),
        ("note", _("Note")),
        ("task", _("Task")),
        ("other", _("Other")),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    contact = models.ForeignKey(
        Contact,
        on_delete=models.CASCADE,
        related_name="interactions",
        verbose_name=_("contact"),
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="contact_interactions",
        verbose_name=_("user"),
    )
    interaction_type = models.CharField(
        _("type"), max_length=20, choices=INTERACTION_TYPES, default="note"
    )
    title = models.CharField(_("title"), max_length=200)
    description = models.TextField(_("description"), blank=True)
    date = models.DateTimeField(_("date"), auto_now_add=True)

    # Дополнительные поля в зависимости от типа
    duration = models.PositiveIntegerField(
        _("duration (minutes)"), blank=True, null=True
    )  # Для звонков
    outcome = models.CharField(
        _("outcome"), max_length=100, blank=True
    )  # Результат взаимодействия

    created_at = models.DateTimeField(_("created at"), auto_now_add=True)

    class Meta:
        verbose_name = _("contact interaction")
        verbose_name_plural = _("contact interactions")
        ordering = ["-date"]
        indexes = [
            models.Index(fields=["contact", "-date"]),
            models.Index(fields=["user", "-date"]),
            models.Index(fields=["interaction_type", "-date"]),
        ]

    def __str__(self):
        return f"{self.contact} - {self.get_interaction_type_display()} - {self.title}"


class ContactImport(models.Model):
    """
    История импорта контактов.
    """

    STATUS_CHOICES = [
        ("pending", _("Pending")),
        ("processing", _("Processing")),
        ("completed", _("Completed")),
        ("failed", _("Failed")),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="contact_imports",
        verbose_name=_("user"),
    )
    filename = models.CharField(_("filename"), max_length=255)
    file_format = models.CharField(_("format"), max_length=10)  # csv, vcard, etc.
    status = models.CharField(
        _("status"), max_length=20, choices=STATUS_CHOICES, default="pending"
    )
    total_contacts = models.PositiveIntegerField(_("total contacts"), default=0)
    imported_contacts = models.PositiveIntegerField(_("imported contacts"), default=0)
    errors = models.JSONField(_("errors"), default=list, blank=True)

    created_at = models.DateTimeField(_("created at"), auto_now_add=True)
    completed_at = models.DateTimeField(_("completed at"), blank=True, null=True)

    class Meta:
        verbose_name = _("contact import")
        verbose_name_plural = _("contact imports")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.email} - {self.filename} ({self.status})"

    @property
    def success_rate(self):
        """Процент успешного импорта."""
        if self.total_contacts == 0:
            return 0
        return round((self.imported_contacts / self.total_contacts) * 100, 1)
