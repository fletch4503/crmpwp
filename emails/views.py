import json
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_POST
from django.views.generic import (
    ListView,
    DetailView,
    CreateView,
    UpdateView,
    DeleteView,
    TemplateView,
)
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from users.permissions import RBACPermission, check_user_permission
from .forms import (
    EmailCredentialsForm,
    EmailProcessingRuleForm,
    EmailSearchForm,
    EmailTestConnectionForm,
    EmailImportForm,
)
from .models import EmailCredentials, EmailMessage, EmailProcessingRule, EmailSyncLog
from .tasks import sync_user_emails, process_email_message
from .utils import EmailProcessor


class EmailCredentialsView(LoginRequiredMixin, TemplateView):
    """
    Управление учетными данными Exchange.
    """

    template_name = "emails/credentials.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Получаем или создаем учетные данные пользователя
        credentials, created = EmailCredentials.objects.get_or_create(
            user=self.request.user, defaults={"email": self.request.user.email}
        )

        context["credentials"] = credentials
        context["credentials_form"] = EmailCredentialsForm(
            instance=credentials, user=self.request.user
        )
        context["test_form"] = EmailTestConnectionForm()
        context["import_form"] = EmailImportForm()

        # Логи синхронизации
        context["sync_logs"] = EmailSyncLog.objects.filter(
            credentials=credentials
        ).order_by("-started_at")[:10]

        return context

    def post(self, request, *args, **kwargs):
        credentials, created = EmailCredentials.objects.get_or_create(
            user=request.user, defaults={"email": request.user.email}
        )

        if "save_credentials" in request.POST:
            form = EmailCredentialsForm(
                request.POST, instance=credentials, user=request.user
            )
            if form.is_valid():
                form.save()
                messages.success(request, _("Email credentials saved successfully."))

                # Запускаем тестовую синхронизацию
                sync_user_emails.delay(request.user.id, credentials.id)
                messages.info(request, _("Email synchronization started."))

                return redirect("emails:credentials")

        elif "test_connection" in request.POST:
            form = EmailTestConnectionForm(request.POST)
            if form.is_valid():
                # Тестируем подключение
                try:
                    from exchangelib import (
                        Credentials,
                        Account,
                        Configuration,
                        DELEGATE,
                    )

                    creds = Credentials(
                        username=form.cleaned_data["email"],
                        password=form.cleaned_data["password"],
                    )

                    config = Configuration(
                        server=form.cleaned_data["server"], credentials=creds
                    )

                    account = Account(
                        primary_smtp_address=form.cleaned_data["email"],
                        config=config,
                        autodiscover=False,
                        access_type=DELEGATE,
                    )

                    # Проверяем подключение
                    inbox_count = account.inbox.total_count
                    messages.success(
                        request,
                        _("Connection successful! Found %(count)d messages in inbox.")
                        % {"count": inbox_count},
                    )

                except Exception as e:
                    messages.error(
                        request, _("Connection failed: %(error)s") % {"error": str(e)}
                    )

                return redirect("emails:credentials")

        return self.get(request, *args, **kwargs)


class EmailMessageListView(LoginRequiredMixin, ListView):
    """
    Список email сообщений пользователя.
    """

    model = EmailMessage
    template_name = "emails/email_list.html"
    context_object_name = "emails"
    paginate_by = 50

    def get_queryset(self):
        queryset = EmailMessage.objects.filter(user=self.request.user).select_related(
            "related_company", "related_project"
        )

        # Поиск
        search_query = self.request.GET.get("q", "")
        if search_query:
            queryset = queryset.filter(
                Q(subject__icontains=search_query)
                | Q(sender__icontains=search_query)
                | Q(body_text__icontains=search_query)
                | Q(parsed_inn__icontains=search_query)
            )

        # Фильтры
        sender = self.request.GET.get("sender", "")
        if sender:
            queryset = queryset.filter(sender__icontains=sender)

        has_attachments = self.request.GET.get("has_attachments")
        if has_attachments:
            queryset = queryset.filter(has_attachments=True)

        is_important = self.request.GET.get("is_important")
        if is_important:
            queryset = queryset.filter(is_important=True)

        is_read = self.request.GET.get("is_read")
        if is_read == "read":
            queryset = queryset.filter(is_read=True)
        elif is_read == "unread":
            queryset = queryset.filter(is_read=False)

        date_from = self.request.GET.get("date_from")
        if date_from:
            queryset = queryset.filter(received_at__date__gte=date_from)

        date_to = self.request.GET.get("date_to")
        if date_to:
            queryset = queryset.filter(received_at__date__lte=date_to)

        parsed_inn = self.request.GET.get("parsed_inn")
        if parsed_inn:
            queryset = queryset.filter(parsed_inn=parsed_inn)

        related_to_project = self.request.GET.get("related_to_project")
        if related_to_project:
            queryset = queryset.exclude(related_project__isnull=True)

        return queryset.order_by("-received_at")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["search_form"] = EmailSearchForm(data=self.request.GET)

        # Статистика
        emails = EmailMessage.objects.filter(user=self.request.user)
        context["stats"] = {
            "total_emails": emails.count(),
            "unread_emails": emails.filter(is_read=False).count(),
            "important_emails": emails.filter(is_important=True).count(),
            "emails_with_attachments": emails.filter(has_attachments=True).count(),
            "parsed_inn_count": emails.exclude(parsed_inn__isnull=True).count(),
            "related_to_projects": emails.exclude(related_project__isnull=True).count(),
        }

        return context


class EmailMessageDetailView(LoginRequiredMixin, DetailView):
    """
    Детальная информация о email сообщении.
    """

    model = EmailMessage
    template_name = "emails/email_detail.html"
    context_object_name = "email"

    def get_queryset(self):
        return (
            EmailMessage.objects.filter(user=self.request.user)
            .select_related("related_company", "related_project")
            .prefetch_related("attachments")
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        email = self.get_object()

        # Помечаем как прочитанное
        if not email.is_read:
            email.is_read = True
            email.save()

        # Получаем связанные проекты и компании
        context["related_projects"] = []
        context["related_companies"] = []

        if email.parsed_inn:
            from companies.models import Company
            from projects.models import Project

            context["related_companies"] = Company.objects.filter(
                user=self.request.user, inn=email.parsed_inn, is_active=True
            )

            context["related_projects"] = Project.objects.filter(
                user=self.request.user, inn=email.parsed_inn, is_active=True
            )

        return context


class EmailProcessingRuleListView(LoginRequiredMixin, ListView):
    """
    Список правил обработки email.
    """

    model = EmailProcessingRule
    template_name = "emails/rules_list.html"
    context_object_name = "rules"
    paginate_by = 20

    def get_queryset(self):
        return EmailProcessingRule.objects.filter(user=self.request.user).order_by(
            "priority"
        )


class EmailProcessingRuleCreateView(LoginRequiredMixin, CreateView):
    """
    Создание правила обработки email.
    """

    model = EmailProcessingRule
    form_class = EmailProcessingRuleForm
    template_name = "emails/rule_form.html"
    success_url = reverse_lazy("emails:rules_list")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        messages.success(self.request, _("Processing rule created successfully."))
        return super().form_valid(form)


class EmailProcessingRuleUpdateView(LoginRequiredMixin, UpdateView):
    """
    Обновление правила обработки email.
    """

    model = EmailProcessingRule
    form_class = EmailProcessingRuleForm
    template_name = "emails/rule_form.html"
    success_url = reverse_lazy("emails:rules_list")

    def get_queryset(self):
        return EmailProcessingRule.objects.filter(user=self.request.user)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        messages.success(self.request, _("Processing rule updated successfully."))
        return super().form_valid(form)


# AJAX Views


@login_required
def email_search_ajax(request):
    """
    AJAX поиск email сообщений.
    """
    query = request.GET.get("q", "")
    sender = request.GET.get("sender", "")
    has_attachments = request.GET.get("has_attachments", "").lower() == "true"
    is_important = request.GET.get("is_important", "").lower() == "true"
    is_read = request.GET.get("is_read", "")
    date_from = request.GET.get("date_from", "")
    date_to = request.GET.get("date_to", "")
    parsed_inn = request.GET.get("parsed_inn", "")
    related_to_project = request.GET.get("related_to_project", "").lower() == "true"

    emails = EmailMessage.objects.filter(user=request.user).select_related(
        "related_company", "related_project"
    )

    if query:
        emails = emails.filter(
            Q(subject__icontains=query)
            | Q(sender__icontains=query)
            | Q(body_text__icontains=query)
            | Q(parsed_inn__icontains=query)
        )

    if sender:
        emails = emails.filter(sender__icontains=sender)

    if has_attachments:
        emails = emails.filter(has_attachments=True)

    if is_important:
        emails = emails.filter(is_important=True)

    if is_read == "read":
        emails = emails.filter(is_read=True)
    elif is_read == "unread":
        emails = emails.filter(is_read=False)

    if date_from:
        emails = emails.filter(received_at__date__gte=date_from)

    if date_to:
        emails = emails.filter(received_at__date__lte=date_to)

    if parsed_inn:
        emails = emails.filter(parsed_inn=parsed_inn)

    if related_to_project:
        emails = emails.exclude(related_project__isnull=True)

    emails = emails[:100]  # Ограничение результатов

    data = [
        {
            "id": str(email.id),
            "subject": email.subject,
            "sender": email.sender,
            "received_at": email.received_at.strftime("%d.%m.%Y %H:%M"),
            "is_read": email.is_read,
            "is_important": email.is_important,
            "has_attachments": email.has_attachments,
            "parsed_inn": email.parsed_inn or "",
            "related_company": (
                email.related_company.name if email.related_company else ""
            ),
            "related_project": (
                email.related_project.title if email.related_project else ""
            ),
        }
        for email in emails
    ]

    return JsonResponse({"emails": data})


@login_required
@require_POST
def mark_email_read_ajax(request, email_id):
    """
    AJAX пометка email как прочитанного/непрочитанного.
    """
    try:
        email = EmailMessage.objects.get(id=email_id, user=request.user)
        email.is_read = not email.is_read
        email.save()

        return JsonResponse({"success": True, "is_read": email.is_read})

    except EmailMessage.DoesNotExist:
        return JsonResponse({"success": False, "error": "Email not found"})


@login_required
@require_POST
def toggle_email_important_ajax(request, email_id):
    """
    AJAX переключение важности email.
    """
    try:
        email = EmailMessage.objects.get(id=email_id, user=request.user)
        email.is_important = not email.is_important
        email.save()

        return JsonResponse({"success": True, "is_important": email.is_important})

    except EmailMessage.DoesNotExist:
        return JsonResponse({"success": False, "error": "Email not found"})


@login_required
@require_POST
def link_email_to_project_ajax(request, email_id, project_id):
    """
    AJAX привязка email к проекту.
    """
    try:
        email = EmailMessage.objects.get(id=email_id, user=request.user)
        from projects.models import Project

        project = Project.objects.get(id=project_id, user=request.user, is_active=True)

        email.related_project = project
        email.save()

        # Создаем запись в истории проекта
        from projects.models import ProjectEmail

        ProjectEmail.objects.get_or_create(
            project=project,
            message_id=email.message_id,
            defaults={
                "subject": email.subject,
                "sender": email.sender,
                "recipients": email.all_recipients,
                "body": email.body_text or email.body_html,
                "received_at": email.received_at,
                "has_attachments": email.has_attachments,
                "attachments_count": email.attachments.count(),
                "parsed_inn": email.parsed_inn,
                "parsed_project_number": email.parsed_project_number,
                "parsed_contacts": email.parsed_contacts,
            },
        )

        return JsonResponse({"success": True, "project_title": project.title})

    except EmailMessage.DoesNotExist:
        return JsonResponse({"success": False, "error": "Email not found"})
    except Project.DoesNotExist:
        return JsonResponse({"success": False, "error": "Project not found"})


@login_required
@require_POST
def sync_emails_now_ajax(request):
    """
    AJAX запуск синхронизации email.
    """
    try:
        credentials = EmailCredentials.objects.get(user=request.user, is_active=True)
        sync_user_emails.delay(request.user.id, credentials.id)

        return JsonResponse(
            {"success": True, "message": "Email synchronization started"}
        )

    except EmailCredentials.DoesNotExist:
        return JsonResponse(
            {"success": False, "error": "Email credentials not configured"}
        )


@login_required
def get_email_stats_ajax(request):
    """
    AJAX получение статистики email.
    """
    emails = EmailMessage.objects.filter(user=request.user)

    stats = {
        "total_emails": emails.count(),
        "unread_emails": emails.filter(is_read=False).count(),
        "important_emails": emails.filter(is_important=True).count(),
        "emails_with_attachments": emails.filter(has_attachments=True).count(),
        "parsed_inn_count": emails.exclude(parsed_inn__isnull=True).count(),
        "related_to_projects": emails.exclude(related_project__isnull=True).count(),
        "today_emails": emails.filter(
            received_at__date=request.user.date_joined.date()
        ).count(),
    }

    return JsonResponse({"stats": stats})


# API Views


class EmailAPIView(APIView):
    """
    API для управления email сообщениями.
    """

    permission_classes = [IsAuthenticated, RBACPermission]
    required_permissions = ["view_project"]  # Используем project permissions для email

    def get(self, request):
        """Получить список email сообщений пользователя."""
        emails = EmailMessage.objects.filter(user=request.user).select_related(
            "related_company", "related_project"
        )

        data = [
            {
                "id": str(email.id),
                "message_id": email.message_id,
                "subject": email.subject,
                "sender": email.sender,
                "recipients_to": email.recipients_to,
                "received_at": email.received_at.isoformat(),
                "is_read": email.is_read,
                "is_important": email.is_important,
                "has_attachments": email.has_attachments,
                "parsed_inn": email.parsed_inn,
                "parsed_project_number": email.parsed_project_number,
                "related_company": (
                    {
                        "id": str(email.related_company.id),
                        "name": email.related_company.name,
                        "inn": email.related_company.inn,
                    }
                    if email.related_company
                    else None
                ),
                "related_project": (
                    {
                        "id": str(email.related_project.id),
                        "title": email.related_project.title,
                    }
                    if email.related_project
                    else None
                ),
            }
            for email in emails
        ]

        return Response(data)


class EmailSyncAPIView(APIView):
    """
    API для управления синхронизацией email.
    """

    permission_classes = [IsAuthenticated, RBACPermission]
    required_permissions = ["view_project"]

    def post(self, request):
        """Запустить синхронизацию email."""
        try:
            credentials = EmailCredentials.objects.get(
                user=request.user, is_active=True
            )
            sync_user_emails.delay(request.user.id, credentials.id)

            return Response(
                {
                    "message": "Email synchronization started",
                    "credentials_id": str(credentials.id),
                }
            )

        except EmailCredentials.DoesNotExist:
            return Response(
                {"error": "Email credentials not configured"},
                status=status.HTTP_400_BAD_REQUEST,
            )
