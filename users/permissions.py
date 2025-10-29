from django.contrib.auth.models import AnonymousUser
from rest_framework.permissions import BasePermission

from .models import UserRole, RolePermission


class IsAdmin(BasePermission):
    """
    Проверка, является ли пользователь администратором.
    """

    def has_permission(self, request, view):
        if isinstance(request.user, AnonymousUser):
            return False
        return request.user.is_superuser or request.user.is_staff


class RBACPermission(BasePermission):
    """
    Проверка разрешений на основе ролей (RBAC).
    """

    def __init__(self, required_permissions=None):
        self.required_permissions = required_permissions or []

    def has_permission(self, request, view):
        if isinstance(request.user, AnonymousUser):
            return False

        # Администраторы имеют все разрешения
        if request.user.is_superuser:
            return True

        # Получить все разрешения пользователя через роли
        user_permissions = set()
        for user_role in request.user.user_roles.all():
            for role_perm in user_role.role.role_permissions.all():
                user_permissions.add(role_perm.permission.codename)

        # Проверить наличие требуемых разрешений
        if isinstance(self.required_permissions, str):
            return self.required_permissions in user_permissions
        elif isinstance(self.required_permissions, list):
            return all(perm in user_permissions for perm in self.required_permissions)

        return False


class IsOwnerOrAdmin(BasePermission):
    """
    Проверка, является ли пользователь владельцем объекта или администратором.
    """

    def has_object_permission(self, request, view, obj):
        if isinstance(request.user, AnonymousUser):
            return False

        # Администраторы имеют доступ ко всем объектам
        if request.user.is_superuser or request.user.is_staff:
            return True

        # Проверить, является ли пользователь владельцем объекта
        if hasattr(obj, "user"):
            return obj.user == request.user

        return False


class CanManageUsers(RBACPermission):
    """
    Разрешение на управление пользователями.
    """

    def __init__(self):
        super().__init__(["add_users", "change_users", "delete_users"])


class CanManageRoles(RBACPermission):
    """
    Разрешение на управление ролями.
    """

    def __init__(self):
        super().__init__(["manage_roles"])


class CanManagePermissions(RBACPermission):
    """
    Разрешение на управление разрешениями.
    """

    def __init__(self):
        super().__init__(["manage_permissions"])


class CanViewUsers(RBACPermission):
    """
    Разрешение на просмотр пользователей.
    """

    def __init__(self):
        super().__init__(["view_users"])


class CanViewLogs(RBACPermission):
    """
    Разрешение на просмотр логов.
    """

    def __init__(self):
        super().__init__(["view_logs"])


class CanManageSystem(RBACPermission):
    """
    Разрешение на управление системой.
    """

    def __init__(self):
        super().__init__(["manage_system"])


def check_user_permission(user, permission_codename):
    """
    Проверка наличия разрешения у пользователя на основе ролей (RBAC).
    """
    from django.contrib.auth.models import AnonymousUser

    if isinstance(user, AnonymousUser):
        return False

    # Администраторы имеют все разрешения
    if user.is_superuser:
        return True

    # Получить все разрешения пользователя через роли
    user_permissions = set()
    for user_role in user.user_roles.all():
        for role_perm in user_role.role.role_permissions.all():
            user_permissions.add(role_perm.permission.codename)

    # Проверить наличие требуемого разрешения
    return permission_codename in user_permissions
