import json
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q, Count, Prefetch
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
)
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from users.permissions import RBACPermission, check_user_permission
from .forms import (
    ProjectForm,
    ProjectStatusUpdateForm,
    ProjectNoteForm,
    ProjectSearchForm,
    ProjectEmailFilterForm,
)
from .models import Project, ProjectEmail, ProjectNote


class ProjectListView(LoginRequiredMixin, ListView):
    """
    Список проектов пользователя.
    """

    model = Project
    template_name = "projects/project_list.html"
    context_object_name = "projects"
    paginate_by = 20

    def get_queryset(self):
        queryset = (
            Project.objects.filter(user=self.request.user, is_active=True)
            .select_related("company", "contact")
            .prefetch_related(
                Prefetch(
                    "emails", queryset=ProjectEmail.objects.order_by("-received_at")[:5]
                )
            )
        )

        # Поиск
        search_query = self.request.GET.get("q", "")
        if search_query:
            queryset = queryset.filter(
                Q(title__icontains=search_query)
                | Q(description__icontains=search_query)
                | Q(inn__icontains=search_query)
                | Q(project_number__icontains=search_query)
                | Q(company__name__icontains=search_query)
                | Q(contact__first_name__icontains=search_query)
                | Q(contact__last_name__icontains=search_query)
            )

        # Фильтры
        status_filter = self.request.GET.get("status", "")
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        priority_filter = self.request.GET.get("priority", "")
        if priority_filter:
            queryset = queryset.filter(priority=priority_filter)

        company_id = self.request.GET.get("company", "")
        if company_id:
            queryset = queryset.filter(company_id=company_id)

        contact_id = self.request.GET.get("contact", "")
        if contact_id:
            queryset = queryset.filter(contact_id=contact_id)

        inn_filter = self.request.GET.get("inn", "")
        if inn_filter:
            queryset = queryset.filter(inn=inn_filter)

        project_number_filter = self.request.GET.get("project_number", "")
        if project_number_filter:
            queryset = queryset.filter(project_number=project_number_filter)

        if self.request.GET.get("has_deadline"):
            queryset = queryset.exclude(deadline__isnull=True)

        if self.request.GET.get("is_overdue"):
            queryset = queryset.filter(
                deadline__lt=(
                    self.request.user.date_joined.date()
                    if hasattr(self.request.user, "date_joined")
                    else None
                )
            )

        # Фильтр по тегам
        tags = self.request.GET.get("tags", "")
        if tags:
            tag_list = [tag.strip() for tag in tags.split(",") if tag.strip()]
            for tag in tag_list:
                queryset = queryset.filter(tags__contains=[tag])

        return queryset.order_by("-created_at")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["search_form"] = ProjectSearchForm(
            user=self.request.user, data=self.request.GET
        )

        # Статистика
        projects = Project.objects.filter(user=self.request.user, is_active=True)
        context["stats"] = {
            "total_projects": projects.count(),
            "active_projects": projects.filter(status="in_progress").count(),
            "completed_projects": projects.filter(status="completed").count(),
            "overdue_projects": sum(1 for p in projects if p.is_overdue),
            "new_projects": projects.filter(status="new").count(),
        }

        return context


class ProjectDetailView(LoginRequiredMixin, DetailView):
    """
    Детальная информация о проекте.
    """

    model = Project
    template_name = "projects/project_detail.html"
    context_object_name = "project"

    def get_queryset(self):
        return (
            Project.objects.filter(user=self.request.user, is_active=True)
            .select_related("company", "contact")
            .prefetch_related(
                Prefetch(
                    "emails", queryset=ProjectEmail.objects.order_by("-received_at")
                ),
                Prefetch(
                    "project_notes",
                    queryset=ProjectNote.objects.select_related("user").order_by(
                        "-created_at"
                    ),
                ),
                "status_history",
            )
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        project = self.get_object()

        # Email переписка
        email_filter_form = ProjectEmailFilterForm(self.request.GET)
        emails = project.emails.all()

        # Применяем фильтры
        if email_filter_form.is_valid():
            if email_filter_form.cleaned_data.get("sender"):
                emails = emails.filter(
                    sender__icontains=email_filter_form.cleaned_data["sender"]
                )
            if email_filter_form.cleaned_data.get("date_from"):
                emails = emails.filter(
                    received_at__date__gte=email_filter_form.cleaned_data["date_from"]
                )
            if email_filter_form.cleaned_data.get("date_to"):
                emails = emails.filter(
                    received_at__date__lte=email_filter_form.cleaned_data["date_to"]
                )
            if email_filter_form.cleaned_data.get("has_attachments"):
                emails = emails.filter(has_attachments=True)
            if email_filter_form.cleaned_data.get("search_body"):
                emails = emails.filter(
                    body__icontains=email_filter_form.cleaned_data["search_body"]
                )

        context["emails"] = emails[:50]  # Ограничение для производительности
        context["email_filter_form"] = email_filter_form

        # Заметки
        context["notes"] = project.project_notes.filter(
            Q(is_private=False) | Q(user=self.request.user)
        ).select_related("user")[:20]

        # История статусов
        context["status_history"] = project.status_history.select_related(
            "user"
        ).order_by("-changed_at")[:10]

        # Формы
        context["status_form"] = ProjectStatusUpdateForm(
            instance=project, user=self.request.user
        )
        context["note_form"] = ProjectNoteForm(project=project, user=self.request.user)

        # Статистика
        context["stats"] = {
            "total_emails": project.emails.count(),
            "emails_with_attachments": project.emails.filter(
                has_attachments=True
            ).count(),
            "total_notes": project.project_notes.count(),
            "private_notes": project.project_notes.filter(is_private=True).count(),
            "important_notes": project.project_notes.filter(is_important=True).count(),
            "status_changes": project.status_history.count(),
        }

        return context


class ProjectCreateView(LoginRequiredMixin, CreateView):
    """
    Создание нового проекта.
    """

    model = Project
    form_class = ProjectForm
    template_name = "projects/project_form.html"
    success_url = reverse_lazy("projects:project_list")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        messages.success(self.request, _("Project created successfully."))
        return super().form_valid(form)


class ProjectUpdateView(LoginRequiredMixin, UpdateView):
    """
    Обновление проекта.
    """

    model = Project
    form_class = ProjectForm
    template_name = "projects/project_form.html"
    success_url = reverse_lazy("projects:project_list")

    def get_queryset(self):
        return Project.objects.filter(user=self.request.user, is_active=True)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        messages.success(self.request, _("Project updated successfully."))
        return super().form_valid(form)


class ProjectDeleteView(LoginRequiredMixin, DeleteView):
    """
    Удаление проекта (мягкое удаление).
    """

    model = Project
    template_name = "projects/project_confirm_delete.html"
    success_url = reverse_lazy("projects:project_list")

    def get_queryset(self):
        return Project.objects.filter(user=self.request.user, is_active=True)

    def delete(self, request, *args, **kwargs):
        project = self.get_object()
        project.is_active = False
        project.save()
        messages.success(request, _("Project deleted successfully."))
        return redirect(self.success_url)


# AJAX Views


@login_required
def project_search_ajax(request):
    """
    AJAX поиск проектов.
    """
    query = request.GET.get("q", "")
    status_filter = request.GET.get("status", "")
    priority_filter = request.GET.get("priority", "")
    company_id = request.GET.get("company", "")
    contact_id = request.GET.get("contact", "")
    inn = request.GET.get("inn", "")
    project_number = request.GET.get("project_number", "")
    has_deadline = request.GET.get("has_deadline", "").lower() == "true"
    is_overdue = request.GET.get("is_overdue", "").lower() == "true"
    tags = request.GET.get("tags", "")

    projects = Project.objects.filter(user=request.user, is_active=True).select_related(
        "company", "contact"
    )

    if query:
        projects = projects.filter(
            Q(title__icontains=query)
            | Q(description__icontains=query)
            | Q(inn__icontains=query)
            | Q(project_number__icontains=query)
            | Q(company__name__icontains=query)
            | Q(contact__first_name__icontains=query)
            | Q(contact__last_name__icontains=query)
        )

    if status_filter:
        projects = projects.filter(status=status_filter)

    if priority_filter:
        projects = projects.filter(priority=priority_filter)

    if company_id:
        projects = projects.filter(company_id=company_id)

    if contact_id:
        projects = projects.filter(contact_id=contact_id)

    if inn:
        projects = projects.filter(inn=inn)

    if project_number:
        projects = projects.filter(project_number=project_number)

    if has_deadline:
        projects = projects.exclude(deadline__isnull=True)

    if is_overdue:
        projects = projects.filter(
            deadline__lt=(
                request.user.date_joined.date()
                if hasattr(request.user, "date_joined")
                else None
            )
        )

    if tags:
        tag_list = [tag.strip() for tag in tags.split(",") if tag.strip()]
        for tag in tag_list:
            projects = projects.filter(tags__contains=[tag])

    projects = projects[:50]  # Ограничение результатов

    data = [
        {
            "id": str(project.id),
            "title": project.title,
            "status": project.get_status_display(),
            "priority": project.get_priority_display(),
            "company": project.company.name if project.company else "",
            "contact": project.contact.full_name if project.contact else "",
            "inn": project.inn or "",
            "project_number": project.project_number or "",
            "deadline": project.deadline.isoformat() if project.deadline else None,
            "is_overdue": project.is_overdue,
            "progress": project.progress_percentage,
            "created_at": project.created_at.strftime("%d.%m.%Y"),
        }
        for project in projects
    ]

    return JsonResponse({"projects": data})


@login_required
@require_POST
def update_project_status_ajax(request, project_id):
    """
    AJAX обновление статуса проекта.
    """
    try:
        project = Project.objects.get(id=project_id, user=request.user)
        form = ProjectStatusUpdateForm(
            request.POST, instance=project, user=request.user
        )

        if form.is_valid():
            updated_project = form.save()
            return JsonResponse(
                {
                    "success": True,
                    "status": updated_project.get_status_display(),
                    "status_value": updated_project.status,
                    "is_overdue": updated_project.is_overdue,
                }
            )
        else:
            return JsonResponse({"success": False, "errors": form.errors})
    except Project.DoesNotExist:
        return JsonResponse({"success": False, "error": "Project not found"})


@login_required
@require_POST
def add_project_note_ajax(request, project_id):
    """
    AJAX добавление заметки к проекту.
    """
    try:
        project = Project.objects.get(id=project_id, user=request.user)
        form = ProjectNoteForm(request.POST, project=project, user=request.user)

        if form.is_valid():
            note = form.save()
            return JsonResponse(
                {
                    "success": True,
                    "note": {
                        "id": str(note.id),
                        "title": note.title,
                        "content": (
                            note.content[:100] + "..."
                            if len(note.content) > 100
                            else note.content
                        ),
                        "note_type": note.get_note_type_display(),
                        "is_important": note.is_important,
                        "is_private": note.is_private,
                        "created_at": note.created_at.strftime("%d.%m.%Y %H:%M"),
                        "user": note.user.get_full_name() or note.user.username,
                    },
                }
            )
        else:
            return JsonResponse({"success": False, "errors": form.errors})
    except Project.DoesNotExist:
        return JsonResponse({"success": False, "error": "Project not found"})


@login_required
def get_project_emails_ajax(request, project_id):
    """
    AJAX получение email переписки проекта.
    """
    try:
        project = Project.objects.get(id=project_id, user=request.user)

        # Применяем фильтры
        emails = project.emails.all().order_by("-received_at")

        sender = request.GET.get("sender", "")
        if sender:
            emails = emails.filter(sender__icontains=sender)

        date_from = request.GET.get("date_from", "")
        if date_from:
            emails = emails.filter(received_at__date__gte=date_from)

        date_to = request.GET.get("date_to", "")
        if date_to:
            emails = emails.filter(received_at__date__lte=date_to)

        if request.GET.get("has_attachments"):
            emails = emails.filter(has_attachments=True)

        search_body = request.GET.get("search_body", "")
        if search_body:
            emails = emails.filter(body__icontains=search_body)

        emails = emails[:100]  # Ограничение для производительности

        data = [
            {
                "id": str(email.id),
                "subject": email.subject,
                "sender": email.sender,
                "recipients": email.recipients_list,
                "received_at": email.received_at.strftime("%d.%m.%Y %H:%M"),
                "has_attachments": email.has_attachments,
                "attachments_count": email.attachments_count,
                "body_preview": (
                    email.body[:200] + "..." if len(email.body) > 200 else email.body
                ),
            }
            for email in emails
        ]

        return JsonResponse({"emails": data})

    except Project.DoesNotExist:
        return JsonResponse({"success": False, "error": "Project not found"})


# API Views


class ProjectAPIView(APIView):
    """
    API для управления проектами.
    """

    permission_classes = [IsAuthenticated, RBACPermission]
    required_permissions = ["view_project"]

    def get(self, request):
        """Получить список проектов пользователя."""
        projects = Project.objects.filter(
            user=request.user, is_active=True
        ).select_related("company", "contact")
        data = [
            {
                "id": str(project.id),
                "title": project.title,
                "description": project.description,
                "status": project.status,
                "priority": project.priority,
                "company": (
                    {
                        "id": str(project.company.id),
                        "name": project.company.name,
                        "inn": project.company.inn,
                    }
                    if project.company
                    else None
                ),
                "contact": (
                    {
                        "id": str(project.contact.id),
                        "name": project.contact.full_name,
                        "email": project.contact.email,
                    }
                    if project.contact
                    else None
                ),
                "inn": project.inn,
                "project_number": project.project_number,
                "deadline": project.deadline.isoformat() if project.deadline else None,
                "is_overdue": project.is_overdue,
                "progress_percentage": project.progress_percentage,
                "created_at": project.created_at.isoformat(),
            }
            for project in projects
        ]

        return Response(data)

    def post(self, request):
        """Создать новый проект."""
        if not check_user_permission(request.user, "add_project"):
            return Response(
                {"error": "Недостаточно прав доступа"}, status=status.HTTP_403_FORBIDDEN
            )

        project_data = request.data.copy()
        project_data["user"] = request.user.id

        try:
            project = Project.objects.create(
                user=request.user,
                title=project_data["title"],
                description=project_data.get("description", ""),
                status=project_data.get("status", "new"),
                priority=project_data.get("priority", "medium"),
                inn=project_data.get("inn"),
                project_number=project_data.get("project_number"),
                tags=project_data.get("tags", []),
            )

            # Связываем с компанией и контактом если указаны
            if project_data.get("company_id"):
                from companies.models import Company

                try:
                    company = Company.objects.get(
                        id=project_data["company_id"], user=request.user
                    )
                    project.company = company
                    project.save()
                except Company.DoesNotExist:
                    pass

            if project_data.get("contact_id"):
                from contacts.models import Contact

                try:
                    contact = Contact.objects.get(
                        id=project_data["contact_id"], user=request.user
                    )
                    project.contact = contact
                    project.save()
                except Contact.DoesNotExist:
                    pass

            return Response(
                {"id": str(project.id), "message": "Проект создан"},
                status=status.HTTP_201_CREATED,
            )

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class ProjectDetailAPIView(APIView):
    """
    API для детальной работы с проектом.
    """

    permission_classes = [IsAuthenticated, RBACPermission]
    required_permissions = ["view_project"]

    def get(self, request, project_id):
        """Получить детальную информацию о проекте."""
        try:
            project = Project.objects.get(
                id=project_id, user=request.user, is_active=True
            )

            data = {
                "id": str(project.id),
                "title": project.title,
                "description": project.description,
                "status": project.status,
                "priority": project.priority,
                "company": (
                    {
                        "id": str(project.company.id),
                        "name": project.company.name,
                        "inn": project.company.inn,
                    }
                    if project.company
                    else None
                ),
                "contact": (
                    {
                        "id": str(project.contact.id),
                        "name": project.contact.full_name,
                        "email": project.contact.email,
                    }
                    if project.contact
                    else None
                ),
                "inn": project.inn,
                "project_number": project.project_number,
                "deadline": project.deadline.isoformat() if project.deadline else None,
                "is_overdue": project.is_overdue,
                "progress_percentage": project.progress_percentage,
                "tags": project.tags,
                "notes": project.notes,
                "emails_count": project.emails.count(),
                "notes_count": project.project_notes.count(),
                "created_at": project.created_at.isoformat(),
                "updated_at": project.updated_at.isoformat(),
            }

            return Response(data)

        except Project.DoesNotExist:
            return Response(
                {"error": "Проект не найден"}, status=status.HTTP_404_NOT_FOUND
            )

    def put(self, request, project_id):
        """Обновить проект."""
        if not check_user_permission(request.user, "change_project"):
            return Response(
                {"error": "Недостаточно прав доступа"}, status=status.HTTP_403_FORBIDDEN
            )

        try:
            project = Project.objects.get(
                id=project_id, user=request.user, is_active=True
            )

            # Обновление полей
            for field in [
                "title",
                "description",
                "status",
                "priority",
                "inn",
                "project_number",
                "deadline",
                "tags",
                "notes",
            ]:
                if field in request.data:
                    setattr(project, field, request.data[field])

            project.save()

            return Response({"message": "Проект обновлен"})

        except Project.DoesNotExist:
            return Response(
                {"error": "Проект не найден"}, status=status.HTTP_404_NOT_FOUND
            )

    def delete(self, request, project_id):
        """Удалить проект (мягкое удаление)."""
        if not check_user_permission(request.user, "delete_project"):
            return Response(
                {"error": "Недостаточно прав доступа"}, status=status.HTTP_403_FORBIDDEN
            )

        try:
            project = Project.objects.get(
                id=project_id, user=request.user, is_active=True
            )
            project.is_active = False
            project.save()

            return Response({"message": "Проект удален"})

        except Project.DoesNotExist:
            return Response(
                {"error": "Проект не найден"}, status=status.HTTP_404_NOT_FOUND
            )
