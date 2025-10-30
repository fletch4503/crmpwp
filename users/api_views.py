from django.contrib.auth import authenticate, login, logout
from django.db.models import Count, Q
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from rest_framework import status, viewsets, generics
from rest_framework.decorators import action, api_view
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.authtoken.models import Token
from logly import logger
from .models import User, Role, Permission, UserRole, RolePermission, AccessToken
from .permissions import IsAdmin, RBACPermission
from .serializers import (
    UserSerializer,
    UserCreateSerializer,
    UserUpdateSerializer,
    RoleSerializer,
    PermissionSerializer,
    UserRoleSerializer,
    RolePermissionSerializer,
    AccessTokenSerializer,
    LoginSerializer,
    ChangePasswordSerializer,
    UserStatsSerializer,
    RoleStatsSerializer,
)


cons_levels = {"DEBUG": True, "INFO": True, "WARN": True}
cust_color = {"INFO": "GREEN", "ERROR": "BRIGHT_RED"}


def configure_logging():
    logger.configure(
        level="INFO",
        json=False,
        color=True,
        # console=True,                 # Вывод в log-файлы
        # console_levels=cons_levels,   # Вывод в log-файлы
        level_colors=cust_color,
        # color_callback=custom_color,
        auto_sink=True,
        # auto_sink_levels=a_sink_levels,
    )


class UserViewSet(viewsets.ModelViewSet):
    """
    ViewSet для управления пользователями.
    """

    queryset = User.objects.all().order_by("-date_joined")
    permission_classes = [IsAuthenticated, IsAdmin]

    def get_serializer_class(self):
        if self.action == "create":
            return UserCreateSerializer
        elif self.action in ["update", "partial_update"]:
            return UserUpdateSerializer
        return UserSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        # Фильтры
        email = self.request.query_params.get("email")
        is_active = self.request.query_params.get("is_active")
        role = self.request.query_params.get("role")

        if email:
            queryset = queryset.filter(email__icontains=email)
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == "true")
        if role:
            queryset = queryset.filter(
                user_roles__role__name__icontains=role
            ).distinct()

        return queryset

    @action(detail=True, methods=["post"])
    def activate(self, request, pk=None):
        """Активация пользователя."""
        user = self.get_object()
        user.is_active = True
        user.save()
        return Response({"status": "Пользователь активирован"})

    @action(detail=True, methods=["post"])
    def deactivate(self, request, pk=None):
        """Деактивация пользователя."""
        user = self.get_object()
        user.is_active = False
        user.save()
        return Response({"status": "Пользователь деактивирован"})

    @action(detail=False, methods=["get"])
    def me(self, request):
        """Получение данных текущего пользователя."""
        serializer = UserSerializer(request.user)
        return Response(serializer.data)


class RoleViewSet(viewsets.ModelViewSet):
    """
    ViewSet для управления ролями.
    """

    queryset = Role.objects.all().order_by("name")
    serializer_class = RoleSerializer
    permission_classes = [IsAuthenticated, IsAdmin]

    def get_queryset(self):
        queryset = super().get_queryset()
        name = self.request.query_params.get("name")
        if name:
            queryset = queryset.filter(name__icontains=name)
        return queryset


class PermissionViewSet(viewsets.ModelViewSet):
    """
    ViewSet для управления разрешениями.
    """

    queryset = Permission.objects.all().order_by("name")
    serializer_class = PermissionSerializer
    permission_classes = [IsAuthenticated, IsAdmin]

    def get_queryset(self):
        queryset = super().get_queryset()
        name = self.request.query_params.get("name")
        codename = self.request.query_params.get("codename")
        if name:
            queryset = queryset.filter(name__icontains=name)
        if codename:
            queryset = queryset.filter(codename__icontains=codename)
        return queryset


class AccessTokenViewSet(viewsets.ModelViewSet):
    """
    ViewSet для управления токенами доступа.
    """

    queryset = AccessToken.objects.all().order_by("-created_at")
    serializer_class = AccessTokenSerializer
    permission_classes = [IsAuthenticated, IsAdmin]

    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.query_params.get("user")
        is_active = self.request.query_params.get("is_active")

        if user:
            queryset = queryset.filter(user__email__icontains=user)
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == "true")

        return queryset

    @action(detail=True, methods=["post"])
    def revoke(self, request, pk=None):
        """Отзыв токена."""
        token = self.get_object()
        token.is_active = False
        token.save()
        return Response({"status": "Токен отозван"})


# Nested ViewSets


class UserRoleViewSet(viewsets.ModelViewSet):
    """
    ViewSet для управления ролями пользователя.
    """

    queryset = UserRole.objects.all().order_by("-assigned_at")
    serializer_class = UserRoleSerializer
    permission_classes = [IsAuthenticated, IsAdmin]

    def get_queryset(self):
        return self.queryset.filter(user=self.get_parents_query_dict()["user"])


class UserAccessTokenViewSet(viewsets.ModelViewSet):
    """
    ViewSet для управления токенами пользователя.
    """

    queryset = AccessToken.objects.all().order_by("-created_at")
    serializer_class = AccessTokenSerializer
    permission_classes = [IsAuthenticated, IsAdmin]

    def get_queryset(self):
        return self.queryset.filter(user=self.get_parents_query_dict()["user"])


class RolePermissionViewSet(viewsets.ModelViewSet):
    """
    ViewSet для управления разрешениями роли.
    """

    queryset = RolePermission.objects.all().order_by("-assigned_at")
    serializer_class = RolePermissionSerializer
    permission_classes = [IsAuthenticated, IsAdmin]

    def get_queryset(self):
        return self.queryset.filter(role=self.get_parents_query_dict()["role"])


# Authentication Views


class LoginAPIView(APIView):
    """
    API для входа в систему.
    """

    permission_classes = []

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            user = authenticate(
                email=serializer.validated_data["email"],
                password=serializer.validated_data["password"],
            )
            if user:
                login(request, user)
                token, created = Token.objects.get_or_create(user=user)
                return Response({"token": token.key, "user": UserSerializer(user).data})
            return Response(
                {"error": "Неверные учетные данные"},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LogoutAPIView(APIView):
    """
    API для выхода из системы.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        request.user.auth_token.delete()
        logout(request)
        return Response({"status": "Выход выполнен"})


class CurrentUserAPIView(APIView):
    """
    API для получения данных текущего пользователя.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = UserSerializer(request.user)
        return Response(serializer.data)


class ChangePasswordAPIView(APIView):
    """
    API для изменения пароля.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(
            data=request.data, context={"request": request}
        )
        if serializer.is_valid():
            user = request.user
            user.set_password(serializer.validated_data["new_password"])
            user.save()
            return Response({"status": "Пароль изменен"})
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# Bulk Operations


class BulkAssignRoleAPIView(APIView):
    """
    API для массового назначения роли пользователям.
    """

    permission_classes = [IsAuthenticated, IsAdmin]

    def post(self, request):
        user_ids = request.data.get("user_ids", [])
        role_id = request.data.get("role_id")

        if not user_ids or not role_id:
            return Response(
                {"error": "Необходимо указать user_ids и role_id"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            role = Role.objects.get(id=role_id)
            users = User.objects.filter(id__in=user_ids)

            created_count = 0
            for user in users:
                _, created = UserRole.objects.get_or_create(
                    user=user, role=role, defaults={"assigned_by": request.user}
                )
                if created:
                    created_count += 1

            return Response({"status": f"Роль назначена {created_count} пользователям"})

        except Role.DoesNotExist:
            return Response(
                {"error": "Роль не найдена"}, status=status.HTTP_404_NOT_FOUND
            )


class BulkRevokeRoleAPIView(APIView):
    """
    API для массового отзыва роли у пользователей.
    """

    permission_classes = [IsAuthenticated, IsAdmin]

    def post(self, request):
        user_ids = request.data.get("user_ids", [])
        role_id = request.data.get("role_id")

        if not user_ids or not role_id:
            return Response(
                {"error": "Необходимо указать user_ids и role_id"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        deleted_count = UserRole.objects.filter(
            user_id__in=user_ids, role_id=role_id
        ).delete()[0]

        return Response({"status": f"Роль отозвана у {deleted_count} пользователей"})


class BulkAssignPermissionAPIView(APIView):
    """
    API для массового назначения разрешения ролям.
    """

    permission_classes = [IsAuthenticated, IsAdmin]

    def post(self, request):
        role_ids = request.data.get("role_ids", [])
        permission_id = request.data.get("permission_id")

        if not role_ids or not permission_id:
            return Response(
                {"error": "Необходимо указать role_ids и permission_id"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            permission = Permission.objects.get(id=permission_id)
            roles = Role.objects.filter(id__in=role_ids)

            created_count = 0
            for role in roles:
                _, created = RolePermission.objects.get_or_create(
                    role=role,
                    permission=permission,
                    defaults={"assigned_by": request.user},
                )
                if created:
                    created_count += 1

            return Response({"status": f"Разрешение назначено {created_count} ролям"})

        except Permission.DoesNotExist:
            return Response(
                {"error": "Разрешение не найдено"}, status=status.HTTP_404_NOT_FOUND
            )


# Statistics Views


class UserStatsAPIView(APIView):
    """
    API для получения статистики пользователей.
    """

    permission_classes = [IsAuthenticated, IsAdmin]

    def get(self, request):
        total_users = User.objects.count()
        active_users = User.objects.filter(is_active=True).count()
        staff_users = User.objects.filter(is_staff=True).count()
        superuser_count = User.objects.filter(is_superuser=True).count()

        # Статистика по ролям
        role_stats = (
            UserRole.objects.values("role__name")
            .annotate(count=Count("user", distinct=True))
            .order_by("-count")
        )

        # Статистика верификации
        verified_emails = User.objects.filter(is_email_verified=True).count()
        verified_phones = User.objects.filter(is_phone_verified=True).count()

        return Response(
            {
                "total_users": total_users,
                "active_users": active_users,
                "staff_users": staff_users,
                "superuser_count": superuser_count,
                "role_distribution": list(role_stats),
                "verified_emails": verified_emails,
                "verified_phones": verified_phones,
            }
        )


class RoleStatsAPIView(APIView):
    """
    API для получения статистики ролей.
    """

    permission_classes = [IsAuthenticated, IsAdmin]

    def get(self, request):
        total_roles = Role.objects.count()
        system_roles = Role.objects.filter(is_system_role=True).count()

        # Статистика по разрешениям
        permission_stats = (
            RolePermission.objects.values("permission__name")
            .annotate(count=Count("role", distinct=True))
            .order_by("-count")
        )

        # Распределение пользователей по ролям
        user_role_distribution = (
            UserRole.objects.values("role__name")
            .annotate(user_count=Count("user", distinct=True))
            .order_by("-user_count")
        )

        return Response(
            {
                "total_roles": total_roles,
                "system_roles": system_roles,
                "permission_distribution": list(permission_stats),
                "user_role_distribution": list(user_role_distribution),
            }
        )
