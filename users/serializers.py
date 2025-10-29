from django.contrib.auth import authenticate
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from rest_framework.validators import UniqueValidator

from .models import User, Role, Permission, UserRole, RolePermission, AccessToken


class UserSerializer(serializers.ModelSerializer):
    """
    Сериализатор для модели User.
    """

    full_name = serializers.CharField(read_only=True)
    roles = serializers.SerializerMethodField()
    permissions = serializers.SerializerMethodField()
    avatar_url = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "username",
            "first_name",
            "last_name",
            "full_name",
            "phone",
            "date_of_birth",
            "avatar",
            "avatar_url",
            "ip_address",
            "is_email_verified",
            "is_phone_verified",
            "is_active",
            "is_staff",
            "is_superuser",
            "date_joined",
            "last_login",
            "roles",
            "permissions",
        ]
        read_only_fields = ["id", "date_joined", "last_login"]

    def get_roles(self, obj):
        """Получить роли пользователя."""
        return [ur.role.name for ur in obj.user_roles.all()]

    def get_permissions(self, obj):
        """Получить разрешения пользователя."""
        permissions = set()
        for user_role in obj.user_roles.all():
            for role_perm in user_role.role.role_permissions.all():
                permissions.add(role_perm.permission.codename)
        return list(permissions)

    def get_avatar_url(self, obj):
        """Получить URL аватара."""
        if obj.avatar:
            return obj.avatar.url
        return None


class UserCreateSerializer(serializers.ModelSerializer):
    """
    Сериализатор для создания пользователя.
    """

    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = [
            "email",
            "username",
            "password",
            "password_confirm",
            "first_name",
            "last_name",
            "phone",
            "date_of_birth",
        ]

    def validate(self, data):
        if data["password"] != data["password_confirm"]:
            raise serializers.ValidationError(_("Пароли не совпадают"))
        return data

    def create(self, validated_data):
        validated_data.pop("password_confirm")
        user = User.objects.create_user(**validated_data)
        return user


class UserUpdateSerializer(serializers.ModelSerializer):
    """
    Сериализатор для обновления пользователя.
    """

    class Meta:
        model = User
        fields = [
            "email",
            "username",
            "first_name",
            "last_name",
            "phone",
            "date_of_birth",
            "avatar",
            "is_active",
            "is_staff",
            "is_superuser",
        ]


class RoleSerializer(serializers.ModelSerializer):
    """
    Сериализатор для модели Role.
    """

    user_count = serializers.SerializerMethodField()
    permission_count = serializers.SerializerMethodField()

    class Meta:
        model = Role
        fields = [
            "id",
            "name",
            "description",
            "is_system_role",
            "created_at",
            "updated_at",
            "user_count",
            "permission_count",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def get_user_count(self, obj):
        return obj.user_roles.count()

    def get_permission_count(self, obj):
        return obj.role_permissions.count()


class PermissionSerializer(serializers.ModelSerializer):
    """
    Сериализатор для модели Permission.
    """

    role_count = serializers.SerializerMethodField()

    class Meta:
        model = Permission
        fields = [
            "id",
            "name",
            "codename",
            "description",
            "is_system_permission",
            "created_at",
            "updated_at",
            "role_count",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def get_role_count(self, obj):
        return obj.role_permissions.count()


class UserRoleSerializer(serializers.ModelSerializer):
    """
    Сериализатор для модели UserRole.
    """

    user_email = serializers.CharField(source="user.email", read_only=True)
    role_name = serializers.CharField(source="role.name", read_only=True)
    assigned_by_email = serializers.CharField(
        source="assigned_by.email", read_only=True
    )

    class Meta:
        model = UserRole
        fields = [
            "id",
            "user",
            "user_email",
            "role",
            "role_name",
            "assigned_by",
            "assigned_by_email",
            "assigned_at",
        ]
        read_only_fields = ["id", "assigned_at"]


class RolePermissionSerializer(serializers.ModelSerializer):
    """
    Сериализатор для модели RolePermission.
    """

    role_name = serializers.CharField(source="role.name", read_only=True)
    permission_name = serializers.CharField(source="permission.name", read_only=True)
    permission_codename = serializers.CharField(
        source="permission.codename", read_only=True
    )
    assigned_by_email = serializers.CharField(
        source="assigned_by.email", read_only=True
    )

    class Meta:
        model = RolePermission
        fields = [
            "id",
            "role",
            "role_name",
            "permission",
            "permission_name",
            "permission_codename",
            "assigned_by",
            "assigned_by_email",
            "assigned_at",
        ]
        read_only_fields = ["id", "assigned_at"]


class AccessTokenSerializer(serializers.ModelSerializer):
    """
    Сериализатор для модели AccessToken.
    """

    user_email = serializers.CharField(source="user.email", read_only=True)
    is_expired = serializers.BooleanField(read_only=True)
    time_until_expiry = serializers.SerializerMethodField()

    class Meta:
        model = AccessToken
        fields = [
            "id",
            "user",
            "user_email",
            "token",
            "expires_at",
            "is_active",
            "created_at",
            "last_used_at",
            "ip_address",
            "user_agent",
            "is_expired",
            "time_until_expiry",
        ]
        read_only_fields = ["id", "token", "created_at", "last_used_at"]

    def get_time_until_expiry(self, obj):
        """Получить время до истечения токена."""
        if obj.is_expired:
            return None
        return (obj.expires_at - timezone.now()).total_seconds()


# Authentication Serializers


class LoginSerializer(serializers.Serializer):
    """
    Сериализатор для входа в систему.
    """

    email = serializers.EmailField()
    password = serializers.CharField()

    def validate(self, data):
        user = authenticate(email=data["email"], password=data["password"])
        if not user:
            raise serializers.ValidationError(_("Неверный email или пароль"))
        if not user.is_active:
            raise serializers.ValidationError(_("Аккаунт не активирован"))
        data["user"] = user
        return data


class ChangePasswordSerializer(serializers.Serializer):
    """
    Сериализатор для изменения пароля.
    """

    old_password = serializers.CharField()
    new_password = serializers.CharField(min_length=8)
    new_password_confirm = serializers.CharField()

    def validate_old_password(self, value):
        if not self.context["request"].user.check_password(value):
            raise serializers.ValidationError(_("Неверный текущий пароль"))
        return value

    def validate(self, data):
        if data["new_password"] != data["new_password_confirm"]:
            raise serializers.ValidationError(_("Пароли не совпадают"))
        return data


# Statistics Serializers


class UserStatsSerializer(serializers.Serializer):
    """
    Сериализатор для статистики пользователей.
    """

    total_users = serializers.IntegerField()
    active_users = serializers.IntegerField()
    staff_users = serializers.IntegerField()
    superuser_count = serializers.IntegerField()
    role_distribution = serializers.ListField()
    verified_emails = serializers.IntegerField()
    verified_phones = serializers.IntegerField()


class RoleStatsSerializer(serializers.Serializer):
    """
    Сериализатор для статистики ролей.
    """

    total_roles = serializers.IntegerField()
    system_roles = serializers.IntegerField()
    permission_distribution = serializers.ListField()
    user_role_distribution = serializers.ListField()
