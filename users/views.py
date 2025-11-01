from datetime import timedelta
from django.contrib import messages
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.views import LogoutView
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db.models import Q
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_POST
from django.views.generic import (
    TemplateView,
    ListView,
    DetailView,
    CreateView,
    UpdateView,
    DeleteView,
    FormView,
)
from django.core.cache import cache
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .forms import (
    CustomUserCreationForm,
    CustomUserChangeForm,
    ProfileUpdateForm,
    TokenGenerationForm,
    CustomLoginForm,
    CustomSignupForm,
)

# from .allauth_forms import CustomSignupForm, CustomLoginForm
from .models import User, Role, Permission, UserRole, RolePermission, AccessToken
from .permissions import IsAdmin, RBACPermission


class DashboardView(LoginRequiredMixin, TemplateView):
    """
    Главная страница дашборда.
    """

    template_name = "dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Статистика для дашборда
        context["stats"] = self.get_dashboard_stats()
        context["recent_emails"] = self.get_recent_emails()
        context["recent_projects"] = self.get_recent_projects()

        return context

    def get_dashboard_stats(self):
        """Получить статистику для дашборда."""
        from emails.models import EmailMessage
        from projects.models import Project
        from companies.models import Company
        from contacts.models import Contact

        return {
            "emails_total": EmailMessage.objects.filter(user=self.request.user).count(),
            "emails_unread": EmailMessage.objects.filter(
                user=self.request.user, is_read=False
            ).count(),
            "projects_total": Project.objects.filter(user=self.request.user).count(),
            "projects_completed": Project.objects.filter(
                user=self.request.user, status="completed"
            ).count(),
            "companies_total": Company.objects.filter(user=self.request.user).count(),
            "companies_with_inn": Company.objects.filter(
                user=self.request.user, inn__isnull=False
            )
            .exclude(inn="")
            .count(),
            "contacts_total": Contact.objects.filter(user=self.request.user).count(),
            "contacts_verified": Contact.objects.filter(user=self.request.user)
            .filter(Q(is_email_verified=True) | Q(is_phone_verified=True))
            .count(),
        }

    def get_recent_emails(self):
        """Получить последние email."""
        from emails.models import EmailMessage

        return (
            EmailMessage.objects.filter(user=self.request.user)
            .select_related("related_company", "related_project")
            .order_by("-received_at")[:5]
        )

    def get_recent_projects(self):
        """Получить последние активные проекты."""
        from projects.models import Project

        return Project.objects.filter(user=self.request.user, is_active=True).order_by(
            "-created_at"
        )[:5]


class ProfileView(LoginRequiredMixin, UpdateView):
    """
    Просмотр и редактирование профиля пользователя.
    """

    model = User
    form_class = ProfileUpdateForm
    template_name = "users/partials/profile.html"
    success_url = reverse_lazy("users:profile")

    def get_object(self, **kwargs):
        return self.request.user

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Получаем роль пользователя для отображения в профиле
        try:
            user_role = UserRole.objects.select_related("role").get(
                user=self.request.user
            )
            context["user_role"] = user_role
        except UserRole.DoesNotExist:
            context["user_role"] = None
        return context

    def form_valid(self, form):
        messages.success(self.request, _("Профиль успешно обновлен."))
        # Если запрос через HTMX, возвращаем только сообщения
        if self.request.headers.get('HX-Request'):
            from django.template.loader import render_to_string
            messages_html = render_to_string('partials/messages.html', {'messages': messages.get_messages(self.request)}, self.request)
            response = HttpResponse(messages_html)
            response['HX-Trigger'] = 'profileUpdated'
            return response
        return super().form_valid(form)


class AdminRequiredMixin(UserPassesTestMixin):
    """Mixin для проверки прав администратора"""

    def test_func(self):
        return self.request.user.is_superuser


class UserListView(AdminRequiredMixin, ListView):
    """Представление списка пользователей для администраторов"""

    model = User
    template_name = "users/partials/user_list.html"
    context_object_name = "users"
    paginate_by = 20

    def get_queryset(self):
        return (
            User.objects.select_related()
            .prefetch_related("user_roles__role", "access_tokens")
            .all()
        )


class TokenListView(LoginRequiredMixin, ListView):
    """
    Список токенов доступа пользователя.
    """

    model = AccessToken
    template_name = "users/token_list.html"
    context_object_name = "tokens"
    paginate_by = 20

    def get_queryset(self):
        return AccessToken.objects.filter(user=self.request.user).order_by(
            "-created_at"
        )


class TokenCreateView(LoginRequiredMixin, FormView):
    """
    Создание нового токена доступа.
    """

    form_class = TokenGenerationForm
    template_name = "users/token_create.html"
    success_url = reverse_lazy("users:token_list")

    def form_valid(self, form):
        from datetime import timedelta
        from django.utils import timezone

        # Создаем токен
        expires_at = timezone.now() + timedelta(
            hours=form.cleaned_data["expires_in_hours"]
        )

        AccessToken.objects.create(
            user=self.request.user,
            expires_at=expires_at,
        )

        messages.success(self.request, _("Токен доступа успешно создан."))
        return super().form_valid(form)


class TokenDeleteView(LoginRequiredMixin, DeleteView):
    """
    Удаление токена доступа.
    """

    model = AccessToken
    success_url = reverse_lazy("users:token_list")

    def get_queryset(self):
        return AccessToken.objects.filter(user=self.request.user)

    def delete(self, request, *args, **kwargs):
        messages.success(request, _("Токен доступа удален."))
        return super().delete(request, *args, **kwargs)


# API Views


class DashboardStatsAPIView(APIView):
    """
    API для получения статистики дашборда.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        from emails.models import EmailMessage
        from projects.models import Project
        from companies.models import Company
        from contacts.models import Contact

        stats = {
            "emails_total": EmailMessage.objects.filter(user=request.user).count(),
            "unread_emails": EmailMessage.objects.filter(
                user=request.user, is_read=False
            ).count(),
            "projects_total": Project.objects.filter(user=request.user).count(),
            "projects_completed": Project.objects.filter(
                user=request.user, status="completed"
            ).count(),
            "companies_total": Company.objects.filter(user=request.user).count(),
            "companies_with_inn": Company.objects.filter(
                user=request.user, inn__isnull=False
            )
            .exclude(inn="")
            .count(),
            "contacts_total": Contact.objects.filter(user=request.user).count(),
            "contacts_verified": Contact.objects.filter(user=request.user)
            .filter(Q(is_email_verified=True) | Q(is_phone_verified=True))
            .count(),
        }

        return Response(stats)


class RecentActivityAPIView(APIView):
    """
    API для получения недавней активности.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        activities = []

        # Недавние email
        from emails.models import EmailMessage

        recent_emails = EmailMessage.objects.filter(user=request.user).order_by(
            "-received_at"
        )[:3]

        for email in recent_emails:
            activities.append(
                {
                    "type": "email",
                    "icon": "envelope",
                    "color": "blue",
                    "description": f"Получен email: {email.subject[:50]}...",
                    "time": email.received_at.strftime("%H:%M"),
                }
            )

        # Недавние проекты
        from projects.models import Project

        recent_projects = Project.objects.filter(user=request.user).order_by(
            "-created_at"
        )[:3]

        for project in recent_projects:
            activities.append(
                {
                    "type": "project",
                    "icon": "project-diagram",
                    "color": "green",
                    "description": f"Создан проект: {project.title[:50]}...",
                    "time": project.created_at.strftime("%H:%M"),
                }
            )

        # Сортируем по времени (новые сверху)
        activities.sort(key=lambda x: x["time"], reverse=True)

        return Response({"activities": activities[:10]})


class SystemHealthAPIView(APIView):
    """
    API для проверки здоровья системы.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Проверка базы данных
        try:
            User.objects.count()
            db_status = True
        except Exception:
            db_status = False

        # Проверка Redis
        try:
            from django.core.cache import cache

            cache.set("health_check", "ok", 10)
            redis_status = cache.get("health_check") == "ok"
        except Exception:
            redis_status = False

        # Проверка email синхронизации
        try:
            from emails.models import EmailSyncLog

            last_sync = (
                EmailSyncLog.objects.filter(
                    credentials__user=request.user,
                    started_at__gte=timezone.now() - timedelta(hours=1),
                )
                .order_by("-started_at")
                .first()
            )

            email_sync_status = last_sync and last_sync.status == "success"
        except Exception:
            email_sync_status = False

        return Response(
            {
                "database": db_status,
                "redis": redis_status,
                "email_sync": email_sync_status,
            }
        )


# AJAX Views


@login_required
@require_POST
def revoke_token_ajax(request, token_id):
    """
    AJAX view для отзыва токена.
    """
    try:
        token = AccessToken.objects.get(id=token_id, user=request.user)
        token.is_active = False
        token.save()

        return JsonResponse({"success": True})
    except AccessToken.DoesNotExist:
        return JsonResponse({"success": False, "error": "Token not found"}, status=404)


@login_required
def user_settings_ajax(request):
    """
    AJAX view для получения настроек пользователя.
    """
    return JsonResponse(
        {
            "email_notifications": getattr(request.user, "email_notifications", True),
            "sms_notifications": getattr(request.user, "sms_notifications", False),
            "theme": getattr(request.user, "theme", "light"),
            "language": getattr(request.user, "language", "ru"),
        }
    )


@login_required
@require_POST
def update_user_settings_ajax(request):
    """
    AJAX view для обновления настроек пользователя.
    """

    # Обновляем настройки (здесь можно добавить поля в модель User)
    # Пока просто возвращаем успех
    return JsonResponse({"success": True})


@login_required
def clear_messages_ajax(request):
    """
    AJAX view для очистки сообщений.
    """
    from django.template.loader import render_to_string
    return HttpResponse('<div id="messages" class="mb-2 shadow-lg"></div>')


class SettingsView(LoginRequiredMixin, TemplateView):
    """
    Страница настроек пользователя.
    """

    template_name = "users/settings.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["user"] = self.request.user
        return context


class CustomLoginView(FormView):
    """
    Кастомная страница входа с использованием подготовленного шаблона.
    """

    template_name = "users/partials/login.html"
    form_class = CustomLoginForm
    success_url = reverse_lazy("users:dashboard")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["request"] = self.request
        return kwargs

    def form_valid(self, form):
        email = form.cleaned_data.get("login")
        password = form.cleaned_data.get("password")
        user = authenticate(self.request, username=email, password=password)

        if user is not None:
            login(self.request, user)

            # Создаем токен доступа с временем действия 1 час
            expires_at = timezone.now() + timedelta(hours=1)
            AccessToken.objects.create(
                user=user,
                expires_at=expires_at,
            )

            # Добавляем сообщение для отображения через toast
            messages.success(self.request, _("Вход выполнен успешно!"))
            return super().form_valid(form)
        else:
            messages.error(self.request, _("Неверный email или пароль."))
            return self.form_invalid(form)

    def form_invalid(self, form):
        messages.error(self.request, _("Ошибка входа. Проверьте введенные данные."))
        return super().form_invalid(form)


class CustomRegisterView(FormView):
    """
    Кастомная страница регистрации с использованием подготовленного шаблона.
    """

    template_name = "users/partials/register.html"
    form_class = CustomSignupForm
    success_url = reverse_lazy("users:dashboard")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["request"] = self.request
        return kwargs

    def form_valid(self, form):
        user = form.save(self.request)
        if user:
            # Автоматический вход после регистрации
            login(self.request, user)
            messages.success(
                self.request, _("Регистрация прошла успешно! Добро пожаловать!")
            )
            return super().form_valid(form)
        else:
            messages.error(self.request, _("Ошибка при регистрации."))
            return self.form_invalid(form)

    def form_invalid(self, form):
        messages.error(
            self.request, _("Ошибка регистрации. Проверьте введенные данные.")
        )
        return super().form_invalid(form)


class CustomLogoutView(LogoutView):
    """
    Кастомная страница выхода с редиректом на страницу входа.
    """

    next_page = reverse_lazy("users:login")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        cache.clear()
        context.update(
            {
                "title": _("Logged out"),
                "subtitle": None,
                **(self.extra_context or {}),
            }
        )
        return context
