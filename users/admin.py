from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import gettext_lazy as _
from guardian.admin import GuardedModelAdmin

from .models import User, Role, Permission, UserRole, RolePermission, AccessToken


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    """
    Админка для кастомной модели пользователя.
    """

    list_display = (
        "email",
        "username",
        "first_name",
        "last_name",
        "is_active",
        "is_staff",
        "is_email_verified",
        "created_at",
    )
    list_filter = (
        "is_active",
        "is_staff",
        "is_superuser",
        "is_email_verified",
        "is_phone_verified",
        "created_at",
    )
    search_fields = ("email", "username", "first_name", "last_name", "phone")
    ordering = ("-created_at",)
    readonly_fields = ("id", "created_at", "updated_at", "last_login")

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        (
            _("Personal info"),
            {
                "fields": (
                    "username",
                    "first_name",
                    "last_name",
                    "phone",
                    "date_of_birth",
                    "avatar",
                )
            },
        ),
        (_("Verification"), {"fields": ("is_email_verified", "is_phone_verified")}),
        (
            _("Permissions"),
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                ),
            },
        ),
        (
            _("Important dates"),
            {"fields": ("last_login", "date_joined", "created_at", "updated_at")},
        ),
        (_("IP tracking"), {"fields": ("ip_address", "last_login_ip")}),
    )

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "email",
                    "username",
                    "password1",
                    "password2",
                    "first_name",
                    "last_name",
                    "phone",
                ),
            },
        ),
    )


@admin.register(Role)
class RoleAdmin(GuardedModelAdmin):
    """
    Админка для ролей.
    """

    list_display = ("name", "description", "is_system_role", "created_at")
    list_filter = ("is_system_role", "created_at")
    search_fields = ("name", "description")
    readonly_fields = ("id", "created_at", "updated_at")

    fieldsets = (
        (None, {"fields": ("name", "description")}),
        (_("System"), {"fields": ("is_system_role",)}),
        (
            _("Timestamps"),
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )


@admin.register(Permission)
class PermissionAdmin(GuardedModelAdmin):
    """
    Админка для разрешений.
    """

    list_display = (
        "name",
        "codename",
        "description",
        "is_system_permission",
        "created_at",
    )
    list_filter = ("is_system_permission", "created_at")
    search_fields = ("name", "codename", "description")
    readonly_fields = ("id", "created_at", "updated_at")

    fieldsets = (
        (None, {"fields": ("name", "codename", "description")}),
        (_("System"), {"fields": ("is_system_permission",)}),
        (
            _("Timestamps"),
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )


@admin.register(UserRole)
class UserRoleAdmin(GuardedModelAdmin):
    """
    Админка для связи пользователей и ролей.
    """

    list_display = ("user", "role", "assigned_by", "assigned_at")
    list_filter = ("role", "assigned_at", "assigned_by")
    search_fields = ("user__email", "user__username", "role__name")
    readonly_fields = ("id", "assigned_at")
    raw_id_fields = ("user", "role", "assigned_by")

    fieldsets = (
        (None, {"fields": ("user", "role", "assigned_by")}),
        (_("Timestamps"), {"fields": ("assigned_at",), "classes": ("collapse",)}),
    )


@admin.register(RolePermission)
class RolePermissionAdmin(GuardedModelAdmin):
    """
    Админка для связи ролей и разрешений.
    """

    list_display = ("role", "permission", "assigned_by", "assigned_at")
    list_filter = ("role", "permission", "assigned_at", "assigned_by")
    search_fields = ("role__name", "permission__name", "permission__codename")
    readonly_fields = ("id", "assigned_at")
    raw_id_fields = ("role", "permission", "assigned_by")

    fieldsets = (
        (None, {"fields": ("role", "permission", "assigned_by")}),
        (_("Timestamps"), {"fields": ("assigned_at",), "classes": ("collapse",)}),
    )


@admin.register(AccessToken)
class AccessTokenAdmin(GuardedModelAdmin):
    """
    Админка для токенов доступа.
    """

    list_display = (
        "user",
        "token_short",
        "expires_at",
        "is_active",
        "last_used_at",
        "created_at",
    )
    list_filter = ("is_active", "expires_at", "created_at", "last_used_at")
    search_fields = ("user__email", "user__username", "token")
    readonly_fields = ("id", "token", "created_at", "last_used_at")
    raw_id_fields = ("user",)

    fieldsets = (
        (None, {"fields": ("user", "token", "expires_at", "is_active")}),
        (_("Usage"), {"fields": ("last_used_at", "ip_address", "user_agent")}),
        (_("Timestamps"), {"fields": ("created_at",), "classes": ("collapse",)}),
    )

    def token_short(self, obj):
        """Отображает сокращенную версию токена."""
        return f"{obj.token[:20]}..."

    token_short.short_description = _("Token")
