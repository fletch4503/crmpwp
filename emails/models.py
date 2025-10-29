import uuid
from django.db import models
from django.utils.translation import gettext_lazy as _

from users.models import User


class EmailCredentials(models.Model):
    """
    Модель для хранения учетных данных Exchange.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="email_credentials",
        verbose_name=_("user"),
    )

    # Exchange настройки
    server = models.CharField(
        _("Exchange server"), max_length=255, help_text=_("e.g., outlook.office365.com")
    )
    email = models.EmailField(_("email address"))
    username = models.CharField(
        _("username"), max_length=255, help_text=_("Usually same as email")
    )
    password = models.CharField(_("password"), max_length=255)

    # Настройки подключения
    use_ssl = models.BooleanField(_("use SSL"), default=True)
    port = models.PositiveIntegerField(_("port"), default=993)
    timeout = models.PositiveIntegerField(_("timeout (seconds)"), default=30)

    # Статус и настройки
    is_active = models.BooleanField(_("active"), default=True)
    last_sync = models.DateTimeField(_("last sync"), blank=True, null=True)
    sync_interval = models.PositiveIntegerField(
        _("sync interval (minutes)"), default=15
    )

    # Статистика
    total_emails_processed = models.PositiveIntegerField(
        _("total emails processed"), default=0
    )
    last_error = models.TextField(_("last error"), blank=True)
    last_error_time = models.DateTimeField(_("last error time"), blank=True, null=True)

    created_at = models.DateTimeField(_("created at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("updated at"), auto_now=True)

    class Meta:
        verbose_name = _("email credentials")
        verbose_name_plural = _("email credentials")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.email} ({self.user.email})"

    @property
    def is_connected(self):
        """Проверяет, активно ли подключение."""
        if not self.is_active:
            return False

        # Простая проверка - если была синхронизация в последние 2 интервала
        if self.last_sync:
            from django.utils import timezone

            time_diff = timezone.now() - self.last_sync
            max_diff = timezone.timedelta(minutes=self.sync_interval * 2)
            return time_diff < max_diff

        return False

    @property
    def connection_status(self):
        """Возвращает статус подключения."""
        if not self.is_active:
            return _("Disabled")
        elif self.is_connected:
            return _("Connected")
        elif self.last_error:
            return _("Error")
        else:
            return _("Not connected")


class EmailMessage(models.Model):
    """
    Модель для хранения email сообщений.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="emails", verbose_name=_("user")
    )
    credentials = models.ForeignKey(
        EmailCredentials,
        on_delete=models.CASCADE,
        related_name="emails",
        verbose_name=_("credentials"),
    )

    # IMAP данные
    message_id = models.CharField(_("message ID"), max_length=255, unique=True)
    uid = models.CharField(_("UID"), max_length=50, blank=True)

    # Заголовки
    subject = models.CharField(_("subject"), max_length=500)
    sender = models.EmailField(_("sender"))
    recipients_to = models.JSONField(_("To recipients"), default=list)
    recipients_cc = models.JSONField(_("CC recipients"), default=list)
    recipients_bcc = models.JSONField(_("BCC recipients"), default=list)

    # Содержание
    body_text = models.TextField(_("text body"), blank=True)
    body_html = models.TextField(_("HTML body"), blank=True)

    # Метаданные
    received_at = models.DateTimeField(_("received at"))
    sent_at = models.DateTimeField(_("sent at"), blank=True, null=True)
    size = models.PositiveIntegerField(_("size (bytes)"), default=0)

    # Флаги
    is_read = models.BooleanField(_("read"), default=False)
    is_important = models.BooleanField(_("important"), default=False)
    has_attachments = models.BooleanField(_("has attachments"), default=False)

    # Парсинг данных
    parsed_inn = models.CharField(_("parsed ИНН"), max_length=12, blank=True)
    parsed_project_number = models.CharField(
        _("parsed project number"), max_length=50, blank=True
    )
    parsed_contacts = models.JSONField(_("parsed contacts"), default=list, blank=True)

    # Связанные объекты
    related_company = models.ForeignKey(
        "companies.Company",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="related_emails",
        verbose_name=_("related company"),
    )
    related_project = models.ForeignKey(
        "projects.Project",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="source_emails",
        verbose_name=_("related project"),
    )

    # Статус обработки
    is_processed = models.BooleanField(_("processed"), default=False)
    processing_errors = models.JSONField(
        _("processing errors"), default=list, blank=True
    )

    created_at = models.DateTimeField(_("created at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("updated at"), auto_now=True)

    class Meta:
        verbose_name = _("email message")
        verbose_name_plural = _("email messages")
        ordering = ["-received_at"]
        indexes = [
            models.Index(fields=["user", "-received_at"]),
            models.Index(fields=["credentials", "-received_at"]),
            models.Index(fields=["message_id"]),
            models.Index(fields=["sender"]),
            models.Index(fields=["parsed_inn"]),
            models.Index(fields=["parsed_project_number"]),
            models.Index(fields=["is_processed"]),
            models.Index(fields=["related_company"]),
            models.Index(fields=["related_project"]),
        ]

    def __str__(self):
        return f"{self.subject} ({self.sender})"

    @property
    def all_recipients(self):
        """Все получатели."""
        return self.recipients_to + self.recipients_cc + self.recipients_bcc

    @property
    def size_mb(self):
        """Размер в МБ."""
        return round(self.size / (1024 * 1024), 2) if self.size else 0

    @property
    def body_preview(self):
        """Предварительный просмотр тела письма."""
        if self.body_text:
            return (
                self.body_text[:200] + "..."
                if len(self.body_text) > 200
                else self.body_text
            )
        elif self.body_html:
            # Простое извлечение текста из HTML
            import re

            clean_text = re.sub(r"<[^>]+>", "", self.body_html)
            return clean_text[:200] + "..." if len(clean_text) > 200 else clean_text
        return ""


class EmailAttachment(models.Model):
    """
    Модель для вложений email.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.ForeignKey(
        EmailMessage,
        on_delete=models.CASCADE,
        related_name="attachments",
        verbose_name=_("email"),
    )

    filename = models.CharField(_("filename"), max_length=255)
    content_type = models.CharField(_("content type"), max_length=100)
    size = models.PositiveIntegerField(_("size (bytes)"))

    # Файл хранится в файловой системе
    file_path = models.CharField(_("file path"), max_length=500)

    # Метаданные
    content_id = models.CharField(_("content ID"), max_length=255, blank=True)
    is_inline = models.BooleanField(_("inline attachment"), default=False)

    # Статус загрузки
    is_downloaded = models.BooleanField(_("downloaded"), default=False)
    download_errors = models.TextField(_("download errors"), blank=True)

    created_at = models.DateTimeField(_("created at"), auto_now_add=True)

    class Meta:
        verbose_name = _("email attachment")
        verbose_name_plural = _("email attachments")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["email", "is_downloaded"]),
            models.Index(fields=["content_type"]),
            models.Index(fields=["is_inline"]),
        ]

    def __str__(self):
        return f"{self.filename} ({self.email.subject})"

    @property
    def size_mb(self):
        """Размер файла в МБ."""
        return round(self.size / (1024 * 1024), 2) if self.size else 0


class EmailProcessingRule(models.Model):
    """
    Правила обработки входящих email.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="email_rules",
        verbose_name=_("user"),
    )

    name = models.CharField(_("name"), max_length=100)
    description = models.TextField(_("description"), blank=True)

    # Условия
    sender_contains = models.CharField(_("sender contains"), max_length=255, blank=True)
    subject_contains = models.CharField(
        _("subject contains"), max_length=255, blank=True
    )
    body_contains = models.CharField(_("body contains"), max_length=255, blank=True)

    # Действия
    auto_create_project = models.BooleanField(_("auto create project"), default=False)
    auto_create_contact = models.BooleanField(_("auto create contact"), default=False)
    mark_as_important = models.BooleanField(_("mark as important"), default=False)

    # Приоритет (меньше число = выше приоритет)
    priority = models.PositiveIntegerField(_("priority"), default=100)

    is_active = models.BooleanField(_("active"), default=True)
    created_at = models.DateTimeField(_("created at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("updated at"), auto_now=True)

    class Meta:
        verbose_name = _("email processing rule")
        verbose_name_plural = _("email processing rules")
        ordering = ["priority", "created_at"]
        indexes = [
            models.Index(fields=["user", "priority"]),
            models.Index(fields=["user", "is_active"]),
        ]

    def __str__(self):
        return f"{self.name} (приоритет: {self.priority})"

    def matches_email(self, email_message):
        """
        Проверяет, соответствует ли правило email сообщению.
        """
        if (
            self.sender_contains
            and self.sender_contains.lower() not in email_message.sender.lower()
        ):
            return False

        if (
            self.subject_contains
            and self.subject_contains.lower() not in email_message.subject.lower()
        ):
            return False

        if self.body_contains:
            body_text = (email_message.body_text or "") + (
                email_message.body_html or ""
            )
            if self.body_contains.lower() not in body_text.lower():
                return False

        return True


class EmailSyncLog(models.Model):
    """
    Лог синхронизации email.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    credentials = models.ForeignKey(
        EmailCredentials,
        on_delete=models.CASCADE,
        related_name="sync_logs",
        verbose_name=_("credentials"),
    )

    # Статистика синхронизации
    emails_fetched = models.PositiveIntegerField(_("emails fetched"), default=0)
    emails_processed = models.PositiveIntegerField(_("emails processed"), default=0)
    emails_skipped = models.PositiveIntegerField(_("emails skipped"), default=0)
    attachments_downloaded = models.PositiveIntegerField(
        _("attachments downloaded"), default=0
    )

    # Время выполнения
    started_at = models.DateTimeField(_("started at"))
    completed_at = models.DateTimeField(_("completed at"), blank=True, null=True)
    duration_seconds = models.PositiveIntegerField(_("duration (seconds)"), default=0)

    # Статус
    STATUS_CHOICES = [
        ("success", _("Success")),
        ("partial", _("Partial success")),
        ("failed", _("Failed")),
    ]
    status = models.CharField(
        _("status"), max_length=20, choices=STATUS_CHOICES, default="success"
    )

    # Ошибки
    errors = models.JSONField(_("errors"), default=list, blank=True)
    warnings = models.JSONField(_("warnings"), default=list, blank=True)

    created_at = models.DateTimeField(_("created at"), auto_now_add=True)

    class Meta:
        verbose_name = _("email sync log")
        verbose_name_plural = _("email sync logs")
        ordering = ["-started_at"]
        indexes = [
            models.Index(fields=["credentials", "-started_at"]),
            models.Index(fields=["status"]),
        ]

    def __str__(self):
        return f"Sync {self.credentials.email} - {self.status} ({self.started_at})"

    @property
    def duration_display(self):
        """Отображение длительности."""
        if self.duration_seconds < 60:
            return f"{self.duration_seconds} сек"
        elif self.duration_seconds < 3600:
            minutes = self.duration_seconds // 60
            seconds = self.duration_seconds % 60
            return f"{minutes}:{seconds:02d}"
        else:
            hours = self.duration_seconds // 3600
            minutes = (self.duration_seconds % 3600) // 60
            return f"{hours}:{minutes:02d}"
