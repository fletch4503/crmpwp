# import json
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q, Count
from django.http import JsonResponse
from django.shortcuts import (
    # render,
    redirect,
    # get_object_or_404,
)
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_POST
from django.views.generic import (
    ListView,
    DetailView,
    CreateView,
    UpdateView,
    DeleteView,
    # TemplateView,
    # FormView,
)
from rest_framework import status

# from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from users.permissions import (
    RBACPermission,
    check_user_permission,
)
from .forms import (
    ContactForm,
    ContactGroupForm,
    ContactInteractionForm,
    # ContactImportForm,
    ContactSearchForm,
)
from .models import (
    Contact,
    ContactGroup,
    ContactInteraction,
    # ContactImport,
)


class ContactListView(LoginRequiredMixin, ListView):
    """
    Список контактов пользователя.
    """

    model = Contact
    template_name = "contacts/contact_list.html"
    context_object_name = "contacts"
    paginate_by = 20

    def get_queryset(self):
        queryset = Contact.objects.filter(user=self.request.user, is_active=True)

        # Поиск
        search_query = self.request.GET.get("q", "")
        if search_query:
            queryset = queryset.filter(
                Q(first_name__icontains=search_query)
                | Q(last_name__icontains=search_query)
                | Q(email__icontains=search_query)
                | Q(phone__icontains=search_query)
                | Q(company__icontains=search_query)
            )

        # Фильтр по группе
        group_id = self.request.GET.get("group", "")
        if group_id:
            queryset = queryset.filter(groups__id=group_id)

        # Только избранные
        if self.request.GET.get("favorites"):
            queryset = queryset.filter(is_favorite=True)

        # Фильтр по тегам
        tags = self.request.GET.get("tags", "")
        if tags:
            tag_list = [tag.strip() for tag in tags.split(",") if tag.strip()]
            for tag in tag_list:
                queryset = queryset.filter(tags__contains=[tag])

        return queryset.select_related()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["search_form"] = ContactSearchForm(
            user=self.request.user, data=self.request.GET
        )
        context["groups"] = ContactGroup.objects.filter(user=self.request.user)
        context["total_contacts"] = Contact.objects.filter(
            user=self.request.user, is_active=True
        ).count()
        context["favorite_contacts"] = Contact.objects.filter(
            user=self.request.user, is_favorite=True
        ).count()
        return context


class ContactDetailView(LoginRequiredMixin, DetailView):
    """
    Детальная информация о контакте.
    """

    model = Contact
    template_name = "contacts/contact_detail.html"
    context_object_name = "contact"

    def get_queryset(self):
        return Contact.objects.filter(user=self.request.user, is_active=True)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        contact = self.get_object()
        context["interactions"] = ContactInteraction.objects.filter(
            contact=contact
        ).select_related("user")[:10]
        context["groups"] = contact.groups.all()
        context["interaction_form"] = ContactInteractionForm(
            contact=contact, user=self.request.user
        )
        return context


class ContactCreateView(LoginRequiredMixin, CreateView):
    """
    Создание нового контакта.
    """

    model = Contact
    form_class = ContactForm
    template_name = "contacts/contact_form.html"
    success_url = reverse_lazy("contacts:contact_list")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        messages.success(self.request, _("Contact created successfully."))
        return super().form_valid(form)


class ContactUpdateView(LoginRequiredMixin, UpdateView):
    """
    Обновление контакта.
    """

    model = Contact
    form_class = ContactForm
    template_name = "contacts/contact_form.html"
    success_url = reverse_lazy("contacts:contact_list")

    def get_queryset(self):
        return Contact.objects.filter(user=self.request.user, is_active=True)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        messages.success(self.request, _("Contact updated successfully."))
        return super().form_valid(form)


class ContactDeleteView(LoginRequiredMixin, DeleteView):
    """
    Удаление контакта (мягкое удаление).
    """

    model = Contact
    template_name = "contacts/contact_confirm_delete.html"
    success_url = reverse_lazy("contacts:contact_list")

    def get_queryset(self):
        return Contact.objects.filter(user=self.request.user, is_active=True)

    def delete(self, request, *args, **kwargs):
        contact = self.get_object()
        contact.is_active = False
        contact.save()
        messages.success(request, _("Contact deleted successfully."))
        return redirect(self.success_url)


class ContactGroupListView(LoginRequiredMixin, ListView):
    """
    Список групп контактов.
    """

    model = ContactGroup
    template_name = "contacts/group_list.html"
    context_object_name = "groups"

    def get_queryset(self):
        return ContactGroup.objects.filter(user=self.request.user).annotate(
            contacts_count=Count("contacts")
        )


class ContactGroupCreateView(LoginRequiredMixin, CreateView):
    """
    Создание группы контактов.
    """

    model = ContactGroup
    form_class = ContactGroupForm
    template_name = "contacts/group_form.html"
    success_url = reverse_lazy("contacts:group_list")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        messages.success(self.request, _("Group created successfully."))
        return super().form_valid(form)


class ContactGroupUpdateView(LoginRequiredMixin, UpdateView):
    """
    Обновление группы контактов.
    """

    model = ContactGroup
    form_class = ContactGroupForm
    template_name = "contacts/group_form.html"
    success_url = reverse_lazy("contacts:group_list")

    def get_queryset(self):
        return ContactGroup.objects.filter(user=self.request.user)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        messages.success(self.request, _("Group updated successfully."))
        return super().form_valid(form)


class ContactGroupDeleteView(LoginRequiredMixin, DeleteView):
    """
    Удаление группы контактов.
    """

    model = ContactGroup
    template_name = "contacts/group_confirm_delete.html"
    success_url = reverse_lazy("contacts:group_list")

    def get_queryset(self):
        return ContactGroup.objects.filter(user=self.request.user)

    def delete(self, request, *args, **kwargs):
        messages.success(request, _("Group deleted successfully."))
        return super().delete(request, *args, **kwargs)


# AJAX Views


@login_required
def contact_search_ajax(request):
    """
    AJAX поиск контактов.
    """
    query = request.GET.get("q", "")
    group_id = request.GET.get("group", "")
    favorites_only = request.GET.get("favorites", "").lower() == "true"
    tags = request.GET.get("tags", "")

    contacts = Contact.objects.filter(user=request.user, is_active=True)

    if query:
        contacts = contacts.filter(
            Q(first_name__icontains=query)
            | Q(last_name__icontains=query)
            | Q(email__icontains=query)
            | Q(phone__icontains=query)
            | Q(company__icontains=query)
        )

    if group_id:
        contacts = contacts.filter(groups__id=group_id)

    if favorites_only:
        contacts = contacts.filter(is_favorite=True)

    if tags:
        tag_list = [tag.strip() for tag in tags.split(",") if tag.strip()]
        for tag in tag_list:
            contacts = contacts.filter(tags__contains=[tag])

    contacts = contacts[:50]  # Ограничение результатов

    data = [
        {
            "id": str(contact.id),
            "name": contact.full_name,
            "email": contact.email or "",
            "phone": str(contact.phone) if contact.phone else "",
            "company": contact.company or "",
            "is_favorite": contact.is_favorite,
            "tags": contact.tags,
        }
        for contact in contacts
    ]

    return JsonResponse({"contacts": data})


@login_required
@require_POST
def toggle_favorite_ajax(request, contact_id):
    """
    AJAX переключение статуса избранного контакта.
    """
    try:
        contact = Contact.objects.get(id=contact_id, user=request.user)
        contact.is_favorite = not contact.is_favorite
        contact.save()
        return JsonResponse({"success": True, "is_favorite": contact.is_favorite})
    except Contact.DoesNotExist:
        return JsonResponse({"success": False, "error": "Contact not found"})


@login_required
@require_POST
def add_interaction_ajax(request, contact_id):
    """
    AJAX добавление взаимодействия с контактом.
    """
    try:
        contact = Contact.objects.get(id=contact_id, user=request.user)
        form = ContactInteractionForm(request.POST, contact=contact, user=request.user)

        if form.is_valid():
            interaction = form.save()
            return JsonResponse(
                {
                    "success": True,
                    "interaction": {
                        "id": str(interaction.id),
                        "type": interaction.get_interaction_type_display(),
                        "title": interaction.title,
                        "date": interaction.date.strftime("%d.%m.%Y %H:%M"),
                    },
                }
            )
        else:
            return JsonResponse({"success": False, "errors": form.errors})
    except Contact.DoesNotExist:
        return JsonResponse({"success": False, "error": "Contact not found"})


@login_required
@require_POST
def add_contact_to_group_ajax(request):
    """
    AJAX добавление контакта в группу.
    """
    contact_id = request.POST.get("contact_id")
    group_id = request.POST.get("group_id")
    action = request.POST.get("action", "add")

    try:
        contact = Contact.objects.get(id=contact_id, user=request.user)
        group = ContactGroup.objects.get(id=group_id, user=request.user)

        if action == "add":
            group.contacts.add(contact)
            message = _("Contact added to group")
        elif action == "remove":
            group.contacts.remove(contact)
            message = _("Contact removed from group")
        else:
            return JsonResponse({"success": False, "error": "Invalid action"})

        return JsonResponse({"success": True, "message": message})

    except (Contact.DoesNotExist, ContactGroup.DoesNotExist):
        return JsonResponse({"success": False, "error": "Contact or group not found"})


# API Views


class ContactAPIView(APIView):
    """
    API для управления контактами.
    """

    permission_classes = [IsAuthenticated, RBACPermission]
    required_permissions = ["view_contact"]

    def get(self, request):
        """Получить список контактов пользователя."""
        contacts = Contact.objects.filter(user=request.user, is_active=True)
        data = [
            {
                "id": str(contact.id),
                "first_name": contact.first_name,
                "last_name": contact.last_name,
                "email": contact.email,
                "phone": str(contact.phone) if contact.phone else None,
                "company": contact.company,
                "is_favorite": contact.is_favorite,
                "tags": contact.tags,
            }
            for contact in contacts
        ]

        return Response(data)

    def post(self, request):
        """Создать новый контакт."""
        if not check_user_permission(request.user, "add_contact"):
            return Response(
                {"error": "Недостаточно прав доступа"}, status=status.HTTP_403_FORBIDDEN
            )

        contact_data = request.data.copy()
        contact_data["user"] = request.user.id

        # Здесь должна быть сериализация через DRF Serializer
        # Пока используем простую логику
        try:
            contact = Contact.objects.create(
                user=request.user,
                first_name=contact_data["first_name"],
                last_name=contact_data.get("last_name", ""),
                email=contact_data.get("email"),
                phone=contact_data.get("phone"),
                company=contact_data.get("company", ""),
                tags=contact_data.get("tags", []),
            )

            return Response(
                {"id": str(contact.id), "message": "Контакт создан"},
                status=status.HTTP_201_CREATED,
            )

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class ContactDetailAPIView(APIView):
    """
    API для детальной работы с контактом.
    """

    permission_classes = [IsAuthenticated, RBACPermission]
    required_permissions = ["view_contact"]

    def get(self, request, contact_id):
        """Получить детальную информацию о контакте."""
        try:
            contact = Contact.objects.get(
                id=contact_id, user=request.user, is_active=True
            )

            data = {
                "id": str(contact.id),
                "first_name": contact.first_name,
                "last_name": contact.last_name,
                "email": contact.email,
                "phone": str(contact.phone) if contact.phone else None,
                "company": contact.company,
                "position": contact.position,
                "address": contact.address,
                "notes": contact.notes,
                "telegram": contact.telegram,
                "whatsapp": contact.whatsapp,
                "linkedin": contact.linkedin,
                "website": contact.website,
                "is_favorite": contact.is_favorite,
                "tags": contact.tags,
                "groups": [str(group.id) for group in contact.groups.all()],
                "created_at": contact.created_at,
                "updated_at": contact.updated_at,
            }

            return Response(data)

        except Contact.DoesNotExist:
            return Response(
                {"error": "Контакт не найден"}, status=status.HTTP_404_NOT_FOUND
            )

    def put(self, request, contact_id):
        """Обновить контакт."""
        if not check_user_permission(request.user, "change_contact"):
            return Response(
                {"error": "Недостаточно прав доступа"}, status=status.HTTP_403_FORBIDDEN
            )

        try:
            contact = Contact.objects.get(
                id=contact_id, user=request.user, is_active=True
            )

            # Обновление полей
            for field in [
                "first_name",
                "last_name",
                "email",
                "phone",
                "company",
                "position",
                "address",
                "notes",
                "telegram",
                "whatsapp",
                "linkedin",
                "website",
                "is_favorite",
                "tags",
            ]:
                if field in request.data:
                    setattr(contact, field, request.data[field])

            contact.save()

            return Response({"message": "Контакт обновлен"})

        except Contact.DoesNotExist:
            return Response(
                {"error": "Контакт не найден"}, status=status.HTTP_404_NOT_FOUND
            )

    def delete(self, request, contact_id):
        """Удалить контакт (мягкое удаление)."""
        if not check_user_permission(request.user, "delete_contact"):
            return Response(
                {"error": "Недостаточно прав доступа"}, status=status.HTTP_403_FORBIDDEN
            )

        try:
            contact = Contact.objects.get(
                id=contact_id, user=request.user, is_active=True
            )
            contact.is_active = False
            contact.save()

            return Response({"message": "Контакт удален"})

        except Contact.DoesNotExist:
            return Response(
                {"error": "Контакт не найден"}, status=status.HTTP_404_NOT_FOUND
            )
