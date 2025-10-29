import uuid
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _
from phonenumber_field.modelfields import PhoneNumberField
from .managers import UserManager


class User(AbstractUser):
    """
    Кастомная модель пользователя с расширенными полями.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(_("email address"), unique=True)
    phone = PhoneNumberField(_("phone number"), blank=True, null=True)
    date_of_birth = models.DateField(_("date of birth"), blank=True, null=True)
    avatar = models.ImageField(_("avatar"), upload_to="avatars/", blank=True, null=True)
    ip_address = models.GenericIPAddressField(_("IP address"), blank=True, null=True)
    is_email_verified = models.BooleanField(_("email verified"), default=False)
    is_phone_verified = models.BooleanField(_("phone verified"), default=False)
    last_login_ip = models.GenericIPAddressField(
        _("last login IP"), blank=True, null=True
    )
    created_at = models.DateTimeField(_("created at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("updated at"), auto_now=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]

    class Meta:
        verbose_name = _("user")
        verbose_name_plural = _("users")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.email} ({self.get_full_name() or self.username})"

    def get_full_name(self):
        """
        Возвращает полное имя пользователя.
        """
        full_name = f"{self.first_name} {self.last_name}".strip()
        return full_name if full_name else self.username

    @property
    def is_admin(self):
        """Проверяет, является ли пользователь администратором."""
        return self.is_superuser or self.is_staff

    @property
    def has_verified_contact(self):
        """Проверяет, имеет ли пользователь верифицированный контакт."""
        return self.is_email_verified or self.is_phone_verified


class Role(models.Model):
    """
    Модель роли для системы RBAC.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(_("name"), max_length=100, unique=True)
    description = models.TextField(_("description"), blank=True)
    is_system_role = models.BooleanField(_("system role"), default=False)
    created_at = models.DateTimeField(_("created at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("updated at"), auto_now=True)

    class Meta:
        verbose_name = _("role")
        verbose_name_plural = _("roles")
        ordering = ["name"]

    def __str__(self):
        return self.name


class Permission(models.Model):
    """
    Модель разрешения для системы RBAC.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(_("name"), max_length=100, unique=True)
    codename = models.CharField(_("codename"), max_length=100, unique=True)
    description = models.TextField(_("description"), blank=True)
    is_system_permission = models.BooleanField(_("system permission"), default=False)
    created_at = models.DateTimeField(_("created at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("updated at"), auto_now=True)

    class Meta:
        verbose_name = _("permission")
        verbose_name_plural = _("permissions")
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.codename})"


class UserRole(models.Model):
    """
    Связь между пользователями и ролями.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="user_roles")
    role = models.ForeignKey(Role, on_delete=models.CASCADE, related_name="user_roles")
    assigned_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_roles",
    )
    assigned_at = models.DateTimeField(_("assigned at"), auto_now_add=True)

    class Meta:
        verbose_name = _("user role")
        verbose_name_plural = _("user roles")
        unique_together = ["user", "role"]
        ordering = ["-assigned_at"]

    def __str__(self):
        return f"{self.user} - {self.role}"


class RolePermission(models.Model):
    """
    Связь между ролями и разрешениями.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    role = models.ForeignKey(
        Role, on_delete=models.CASCADE, related_name="role_permissions"
    )
    permission = models.ForeignKey(
        Permission, on_delete=models.CASCADE, related_name="role_permissions"
    )
    assigned_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_permissions",
    )
    assigned_at = models.DateTimeField(_("assigned at"), auto_now_add=True)

    class Meta:
        verbose_name = _("role permission")
        verbose_name_plural = _("role permissions")
        unique_together = ["role", "permission"]
        ordering = ["-assigned_at"]

    def __str__(self):
        return f"{self.role} - {self.permission}"


class AccessToken(models.Model):
    """
    Модель токена доступа с ограниченным временем жизни.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="access_tokens"
    )
    token = models.CharField(_("token"), max_length=255, unique=True)
    expires_at = models.DateTimeField(_("expires at"))
    is_active = models.BooleanField(_("is active"), default=True)
    created_at = models.DateTimeField(_("created at"), auto_now_add=True)
    last_used_at = models.DateTimeField(_("last used at"), blank=True, null=True)
    ip_address = models.GenericIPAddressField(_("IP address"), blank=True, null=True)
    user_agent = models.TextField(_("user agent"), blank=True)

    class Meta:
        verbose_name = _("access token")
        verbose_name_plural = _("access tokens")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user} - {self.token[:20]}..."

    @property
    def is_expired(self):
        """Проверяет, истек ли токен."""
        from django.utils import timezone

        return timezone.now() > self.expires_at
