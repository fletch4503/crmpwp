import uuid
from django.db import models
from django.utils.translation import gettext_lazy as _

from users.models import User
from companies.models import Company
from contacts.models import Contact


class Project(models.Model):
    """
    Модель проекта.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="projects", verbose_name=_("user")
    )
    title = models.CharField(_("title"), max_length=200)
    description = models.TextField(_("description"), blank=True)

    # Связанные сущности
    company = models.ForeignKey(
        Company,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="projects",
        verbose_name=_("company"),
    )
    contact = models.ForeignKey(
        Contact,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="projects",
        verbose_name=_("contact"),
    )

    # Идентификаторы из email
    inn = models.CharField(
        _("ИНН"), max_length=12, blank=True, help_text=_("ИНН из email")
    )
    project_number = models.CharField(
        _("project number"),
        max_length=50,
        blank=True,
        help_text=_("Номер проекта из email"),
    )

    # Статус и приоритет
    STATUS_CHOICES = [
        ("new", _("New")),
        ("in_progress", _("In Progress")),
        ("on_hold", _("On Hold")),
        ("completed", _("Completed")),
        ("cancelled", _("Cancelled")),
    ]
    status = models.CharField(
        _("status"), max_length=20, choices=STATUS_CHOICES, default="new"
    )

    PRIORITY_CHOICES = [
        ("low", _("Low")),
        ("medium", _("Medium")),
        ("high", _("High")),
        ("urgent", _("Urgent")),
    ]
    priority = models.CharField(
        _("priority"), max_length=20, choices=PRIORITY_CHOICES, default="medium"
    )

    # Даты
    created_at = models.DateTimeField(_("created at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("updated at"), auto_now=True)
    deadline = models.DateField(_("deadline"), blank=True, null=True)
    completed_at = models.DateTimeField(_("completed at"), blank=True, null=True)

    # Дополнительная информация
    tags = models.JSONField(_("tags"), default=list, blank=True)
    notes = models.TextField(_("notes"), blank=True)

    # Системные поля
    is_active = models.BooleanField(_("active"), default=True)
    source_email_id = models.CharField(
        _("source email id"),
        max_length=255,
        blank=True,
        help_text=_("ID email из которого создан проект"),
    )

    class Meta:
        verbose_name = _("project")
        verbose_name_plural = _("projects")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "status"]),
            models.Index(fields=["user", "priority"]),
            models.Index(fields=["user", "inn"]),
            models.Index(fields=["user", "project_number"]),
            models.Index(fields=["user", "created_at"]),
            models.Index(fields=["user", "deadline"]),
            models.Index(fields=["company", "status"]),
            models.Index(fields=["contact", "status"]),
        ]

    def __str__(self):
        return f"{self.title} ({self.get_status_display()})"

    @property
    def is_overdue(self):
        """Проверяет, просрочен ли проект."""
        if self.deadline and self.status not in ["completed", "cancelled"]:
            from django.utils import timezone

            return timezone.now().date() > self.deadline
        return False

    @property
    def days_until_deadline(self):
        """Количество дней до дедлайна."""
        if self.deadline:
            from django.utils import timezone

            today = timezone.now().date()
            if self.deadline >= today:
                return (self.deadline - today).days
            else:
                return -(today - self.deadline).days
        return None

    @property
    def progress_percentage(self):
        """Процент выполнения проекта на основе email переписки."""
        total_emails = self.emails.count()
        if total_emails == 0:
            return 0

        # Простая логика: чем больше email, тем выше прогресс
        # В реальном проекте можно использовать более сложную логику
        if self.status == "completed":
            return 100
        elif self.status == "in_progress":
            return min(80, total_emails * 10)
        elif self.status == "on_hold":
            return min(30, total_emails * 5)
        else:
            return min(10, total_emails * 2)

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


class ProjectEmail(models.Model):
    """
    Email связанный с проектом.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="emails",
        verbose_name=_("project"),
    )

    # Информация о email
    message_id = models.CharField(_("message id"), max_length=255, unique=True)
    subject = models.CharField(_("subject"), max_length=500)
    sender = models.EmailField(_("sender"))
    recipients = models.JSONField(_("recipients"), default=list)  # Список получателей
    body = models.TextField(_("body"))

    # Метаданные
    received_at = models.DateTimeField(_("received at"))
    has_attachments = models.BooleanField(_("has attachments"), default=False)
    attachments_count = models.PositiveIntegerField(_("attachments count"), default=0)

    # Парсинг данных
    parsed_inn = models.CharField(_("parsed ИНН"), max_length=12, blank=True)
    parsed_project_number = models.CharField(
        _("parsed project number"), max_length=50, blank=True
    )
    parsed_contacts = models.JSONField(_("parsed contacts"), default=list, blank=True)

    # Системные поля
    is_processed = models.BooleanField(_("processed"), default=False)
    processing_errors = models.JSONField(
        _("processing errors"), default=list, blank=True
    )

    created_at = models.DateTimeField(_("created at"), auto_now_add=True)

    class Meta:
        verbose_name = _("project email")
        verbose_name_plural = _("project emails")
        ordering = ["-received_at"]
        indexes = [
            models.Index(fields=["project", "-received_at"]),
            models.Index(fields=["message_id"]),
            models.Index(fields=["sender"]),
            models.Index(fields=["parsed_inn"]),
            models.Index(fields=["parsed_project_number"]),
            models.Index(fields=["is_processed"]),
        ]

    def __str__(self):
        return f"{self.subject} ({self.sender})"

    @property
    def recipients_list(self):
        """Получить список получателей."""
        return self.recipients if isinstance(self.recipients, list) else []

    @property
    def parsed_contacts_list(self):
        """Получить список распознанных контактов."""
        return self.parsed_contacts if isinstance(self.parsed_contacts, list) else []


class ProjectNote(models.Model):
    """
    Заметка к проекту.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="project_notes",
        verbose_name=_("project"),
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="project_notes",
        verbose_name=_("user"),
    )

    title = models.CharField(_("title"), max_length=200)
    content = models.TextField(_("content"))

    NOTE_TYPES = [
        ("general", _("General")),
        ("meeting", _("Meeting")),
        ("call", _("Call")),
        ("decision", _("Decision")),
        ("issue", _("Issue")),
        ("solution", _("Solution")),
    ]
    note_type = models.CharField(
        _("note type"), max_length=20, choices=NOTE_TYPES, default="general"
    )

    is_important = models.BooleanField(_("important"), default=False)
    is_private = models.BooleanField(_("private"), default=False)  # Только для автора

    created_at = models.DateTimeField(_("created at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("updated at"), auto_now=True)

    class Meta:
        verbose_name = _("project note")
        verbose_name_plural = _("project notes")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["project", "is_important"]),
            models.Index(fields=["project", "note_type"]),
            models.Index(fields=["user", "created_at"]),
            models.Index(fields=["project", "is_private"]),
        ]

    def __str__(self):
        return f"{self.project.title} - {self.title}"


class ProjectAttachment(models.Model):
    """
    Вложение к проекту (из email).
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project_email = models.ForeignKey(
        ProjectEmail,
        on_delete=models.CASCADE,
        related_name="attachments",
        verbose_name=_("project email"),
    )

    filename = models.CharField(_("filename"), max_length=255)
    content_type = models.CharField(_("content type"), max_length=100)
    size = models.PositiveIntegerField(_("size (bytes)"))

    # Файл хранится в файловой системе
    file_path = models.CharField(_("file path"), max_length=500)

    # Метаданные
    is_downloaded = models.BooleanField(_("downloaded"), default=False)
    download_errors = models.TextField(_("download errors"), blank=True)

    created_at = models.DateTimeField(_("created at"), auto_now_add=True)

    class Meta:
        verbose_name = _("project attachment")
        verbose_name_plural = _("project attachments")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["project_email", "is_downloaded"]),
            models.Index(fields=["content_type"]),
        ]

    def __str__(self):
        return f"{self.filename} ({self.project_email.subject})"

    @property
    def size_mb(self):
        """Размер файла в МБ."""
        return round(self.size / (1024 * 1024), 2) if self.size else 0


class ProjectStatusHistory(models.Model):
    """
    История изменения статусов проекта.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="status_history",
        verbose_name=_("project"),
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="project_status_changes",
        verbose_name=_("user"),
    )

    old_status = models.CharField(
        _("old status"), max_length=20, choices=Project.STATUS_CHOICES
    )
    new_status = models.CharField(
        _("new status"), max_length=20, choices=Project.STATUS_CHOICES
    )

    # Причина изменения
    reason = models.TextField(_("reason"), blank=True)

    changed_at = models.DateTimeField(_("changed at"), auto_now_add=True)

    class Meta:
        verbose_name = _("project status history")
        verbose_name_plural = _("project status history")
        ordering = ["-changed_at"]
        indexes = [
            models.Index(fields=["project", "-changed_at"]),
            models.Index(fields=["user", "-changed_at"]),
            models.Index(fields=["old_status", "new_status"]),
        ]

    def __str__(self):
        return f"{self.project.title}: {self.old_status} → {self.new_status}"
