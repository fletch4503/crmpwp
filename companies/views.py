import json
from decimal import Decimal
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q, Sum, Count
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
    CompanyForm,
    OrderForm,
    PaymentForm,
    CompanyNoteForm,
    CompanySearchForm,
    OrderSearchForm,
)
from .models import Company, Order, Payment, CompanyNote


class CompanyListView(LoginRequiredMixin, ListView):
    """
    Список компаний пользователя.
    """

    model = Company
    template_name = "companies/company_list.html"
    context_object_name = "companies"
    paginate_by = 20

    def get_queryset(self):
        queryset = Company.objects.filter(user=self.request.user, is_active=True)

        # Поиск
        search_query = self.request.GET.get("q", "")
        if search_query:
            queryset = queryset.filter(
                Q(name__icontains=search_query)
                | Q(inn__icontains=search_query)
                | Q(email__icontains=search_query)
                | Q(contact_person__icontains=search_query)
            )

        # Фильтры
        company_type = self.request.GET.get("company_type", "")
        if company_type:
            queryset = queryset.filter(company_type=company_type)

        status_filter = self.request.GET.get("status", "")
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        if self.request.GET.get("has_debt"):
            queryset = queryset.filter(current_debt__gt=0)

        # Фильтр по тегам
        tags = self.request.GET.get("tags", "")
        if tags:
            tag_list = [tag.strip() for tag in tags.split(",") if tag.strip()]
            for tag in tag_list:
                queryset = queryset.filter(tags__contains=[tag])

        return queryset.select_related()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["search_form"] = CompanySearchForm(data=self.request.GET)

        # Статистика
        companies = Company.objects.filter(user=self.request.user, is_active=True)
        context["stats"] = {
            "total_companies": companies.count(),
            "clients": companies.filter(company_type="client").count(),
            "suppliers": companies.filter(company_type="supplier").count(),
            "partners": companies.filter(company_type="partner").count(),
            "total_debt": companies.aggregate(total=Sum("current_debt"))["total"]
            or Decimal("0"),
            "overdue_orders": (
                Order.objects.filter(
                    user=self.request.user,
                    status__in=["confirmed", "in_progress"],
                    due_date__lt=self.request.user.date_joined.date(),
                ).count()
                if hasattr(self.request.user, "date_joined")
                else 0
            ),
        }

        return context


class CompanyDetailView(LoginRequiredMixin, DetailView):
    """
    Детальная информация о компании.
    """

    model = Company
    template_name = "companies/company_detail.html"
    context_object_name = "company"

    def get_queryset(self):
        return Company.objects.filter(user=self.request.user, is_active=True)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        company = self.get_object()

        # Заказы компании
        context["orders"] = Order.objects.filter(company=company).select_related()[:10]

        # Платежи компании
        context["payments"] = Payment.objects.filter(company=company).select_related()[
            :10
        ]

        # Заметки о компании
        context["notes"] = CompanyNote.objects.filter(company=company).select_related(
            "user"
        )[:5]

        # Статистика
        context["stats"] = {
            "total_orders": Order.objects.filter(company=company).count(),
            "total_payments": Payment.objects.filter(company=company).count(),
            "paid_amount": Payment.objects.filter(
                company=company, status="confirmed"
            ).aggregate(total=Sum("amount"))["total"]
            or Decimal("0"),
            "unpaid_amount": company.unpaid_orders_amount,
        }

        # Формы для добавления
        context["note_form"] = CompanyNoteForm(company=company, user=self.request.user)

        return context


class CompanyCreateView(LoginRequiredMixin, CreateView):
    """
    Создание новой компании.
    """

    model = Company
    form_class = CompanyForm
    template_name = "companies/company_form.html"
    success_url = reverse_lazy("companies:company_list")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        messages.success(self.request, _("Company created successfully."))
        return super().form_valid(form)


class CompanyUpdateView(LoginRequiredMixin, UpdateView):
    """
    Обновление компании.
    """

    model = Company
    form_class = CompanyForm
    template_name = "companies/company_form.html"
    success_url = reverse_lazy("companies:company_list")

    def get_queryset(self):
        return Company.objects.filter(user=self.request.user, is_active=True)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        messages.success(self.request, _("Company updated successfully."))
        return super().form_valid(form)


class CompanyDeleteView(LoginRequiredMixin, DeleteView):
    """
    Удаление компании (мягкое удаление).
    """

    model = Company
    template_name = "companies/company_confirm_delete.html"
    success_url = reverse_lazy("companies:company_list")

    def get_queryset(self):
        return Company.objects.filter(user=self.request.user, is_active=True)

    def delete(self, request, *args, **kwargs):
        company = self.get_object()
        company.is_active = False
        company.save()
        messages.success(request, _("Company deleted successfully."))
        return redirect(self.success_url)


class OrderListView(LoginRequiredMixin, ListView):
    """
    Список заказов пользователя.
    """

    model = Order
    template_name = "companies/order_list.html"
    context_object_name = "orders"
    paginate_by = 20

    def get_queryset(self):
        queryset = Order.objects.filter(user=self.request.user).select_related(
            "company"
        )

        # Поиск
        search_query = self.request.GET.get("q", "")
        if search_query:
            queryset = queryset.filter(
                Q(order_number__icontains=search_query)
                | Q(title__icontains=search_query)
                | Q(company__name__icontains=search_query)
            )

        # Фильтры
        status_filter = self.request.GET.get("status", "")
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        company_id = self.request.GET.get("company", "")
        if company_id:
            queryset = queryset.filter(company_id=company_id)

        date_from = self.request.GET.get("date_from", "")
        if date_from:
            queryset = queryset.filter(order_date__gte=date_from)

        date_to = self.request.GET.get("date_to", "")
        if date_to:
            queryset = queryset.filter(order_date__lte=date_to)

        return queryset.order_by("-order_date")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["search_form"] = OrderSearchForm(
            user=self.request.user, data=self.request.GET
        )

        # Статистика
        orders = Order.objects.filter(user=self.request.user)
        context["stats"] = {
            "total_orders": orders.count(),
            "total_amount": orders.aggregate(total=Sum("amount"))["total"]
            or Decimal("0"),
            "paid_amount": Payment.objects.filter(
                order__user=self.request.user, status="confirmed"
            ).aggregate(total=Sum("amount"))["total"]
            or Decimal("0"),
            "pending_orders": orders.filter(status__in=["draft", "confirmed"]).count(),
        }

        return context


class OrderDetailView(LoginRequiredMixin, DetailView):
    """
    Детальная информация о заказе.
    """

    model = Order
    template_name = "companies/order_detail.html"
    context_object_name = "order"

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user).select_related("company")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        order = self.get_object()

        # Платежи по заказу
        context["payments"] = Payment.objects.filter(order=order).select_related("user")

        # Статистика платежей
        context["payment_stats"] = {
            "total_paid": order.paid_amount,
            "remaining": order.remaining_amount,
            "is_paid": order.is_paid,
            "payment_count": Payment.objects.filter(order=order).count(),
        }

        return context


class OrderCreateView(LoginRequiredMixin, CreateView):
    """
    Создание нового заказа.
    """

    model = Order
    form_class = OrderForm
    template_name = "companies/order_form.html"
    success_url = reverse_lazy("companies:order_list")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        messages.success(self.request, _("Order created successfully."))
        return super().form_valid(form)


class OrderUpdateView(LoginRequiredMixin, UpdateView):
    """
    Обновление заказа.
    """

    model = Order
    form_class = OrderForm
    template_name = "companies/order_form.html"
    success_url = reverse_lazy("companies:order_list")

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        messages.success(self.request, _("Order updated successfully."))
        return super().form_valid(form)


class PaymentListView(LoginRequiredMixin, ListView):
    """
    Список платежей пользователя.
    """

    model = Payment
    template_name = "companies/payment_list.html"
    context_object_name = "payments"
    paginate_by = 20

    def get_queryset(self):
        return (
            Payment.objects.filter(user=self.request.user)
            .select_related("company", "order")
            .order_by("-payment_date")
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Статистика платежей
        payments = Payment.objects.filter(user=self.request.user)
        context["stats"] = {
            "total_payments": payments.count(),
            "total_amount": payments.filter(status="confirmed").aggregate(
                total=Sum("amount")
            )["total"]
            or Decimal("0"),
            "pending_payments": payments.filter(status="pending").count(),
            "this_month": payments.filter(
                payment_date__month=(
                    self.request.user.date_joined.month
                    if hasattr(self.request.user, "date_joined")
                    else 1
                )
            ).count(),
        }

        return context


class PaymentCreateView(LoginRequiredMixin, CreateView):
    """
    Создание нового платежа.
    """

    model = Payment
    form_class = PaymentForm
    template_name = "companies/payment_form.html"
    success_url = reverse_lazy("companies:payment_list")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        messages.success(self.request, _("Payment created successfully."))
        return super().form_valid(form)


# AJAX Views


@login_required
def company_search_ajax(request):
    """
    AJAX поиск компаний.
    """
    query = request.GET.get("q", "")
    company_type = request.GET.get("company_type", "")
    status_filter = request.GET.get("status", "")
    has_debt = request.GET.get("has_debt", "").lower() == "true"
    tags = request.GET.get("tags", "")

    companies = Company.objects.filter(user=request.user, is_active=True)

    if query:
        companies = companies.filter(
            Q(name__icontains=query)
            | Q(inn__icontains=query)
            | Q(email__icontains=query)
            | Q(contact_person__icontains=query)
        )

    if company_type:
        companies = companies.filter(company_type=company_type)

    if status_filter:
        companies = companies.filter(status=status_filter)

    if has_debt:
        companies = companies.filter(current_debt__gt=0)

    if tags:
        tag_list = [tag.strip() for tag in tags.split(",") if tag.strip()]
        for tag in tag_list:
            companies = companies.filter(tags__contains=[tag])

    companies = companies[:50]  # Ограничение результатов

    data = [
        {
            "id": str(company.id),
            "name": company.name,
            "inn": company.inn,
            "company_type": company.get_company_type_display(),
            "status": company.get_status_display(),
            "current_debt": float(company.current_debt),
            "email": company.email or "",
            "phone": company.phone or "",
        }
        for company in companies
    ]

    return JsonResponse({"companies": data})


@login_required
@require_POST
def add_company_note_ajax(request, company_id):
    """
    AJAX добавление заметки о компании.
    """
    try:
        company = Company.objects.get(id=company_id, user=request.user)
        form = CompanyNoteForm(request.POST, company=company, user=request.user)

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
                        "created_at": note.created_at.strftime("%d.%m.%Y %H:%M"),
                    },
                }
            )
        else:
            return JsonResponse({"success": False, "errors": form.errors})
    except Company.DoesNotExist:
        return JsonResponse({"success": False, "error": "Company not found"})


@login_required
def get_company_stats_ajax(request, company_id):
    """
    AJAX получение статистики компании.
    """
    try:
        company = Company.objects.get(id=company_id, user=request.user)

        stats = {
            "total_orders": Order.objects.filter(company=company).count(),
            "total_payments": Payment.objects.filter(company=company).count(),
            "paid_amount": float(
                Payment.objects.filter(company=company, status="confirmed").aggregate(
                    total=Sum("amount")
                )["total"]
                or Decimal("0")
            ),
            "unpaid_amount": float(company.unpaid_orders_amount),
            "available_credit": float(company.available_credit),
            "current_debt": float(company.current_debt),
        }

        return JsonResponse({"success": True, "stats": stats})

    except Company.DoesNotExist:
        return JsonResponse({"success": False, "error": "Company not found"})


# API Views


class CompanyAPIView(APIView):
    """
    API для управления компаниями.
    """

    permission_classes = [IsAuthenticated, RBACPermission]
    required_permissions = ["view_company"]

    def get(self, request):
        """Получить список компаний пользователя."""
        companies = Company.objects.filter(user=request.user, is_active=True)
        data = [
            {
                "id": str(company.id),
                "name": company.name,
                "inn": company.inn,
                "company_type": company.company_type,
                "status": company.status,
                "current_debt": float(company.current_debt),
                "credit_limit": float(company.credit_limit),
                "email": company.email,
                "phone": company.phone,
            }
            for company in companies
        ]

        return Response(data)

    def post(self, request):
        """Создать новую компанию."""
        if not check_user_permission(request.user, "add_company"):
            return Response(
                {"error": "Недостаточно прав доступа"}, status=status.HTTP_403_FORBIDDEN
            )

        company_data = request.data.copy()
        company_data["user"] = request.user.id

        try:
            company = Company.objects.create(
                user=request.user,
                name=company_data["name"],
                inn=company_data["inn"],
                legal_address=company_data.get("legal_address", ""),
                company_type=company_data.get("company_type", "client"),
                tags=company_data.get("tags", []),
            )

            return Response(
                {"id": str(company.id), "message": "Компания создана"},
                status=status.HTTP_201_CREATED,
            )

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class OrderAPIView(APIView):
    """
    API для управления заказами.
    """

    permission_classes = [IsAuthenticated, RBACPermission]
    required_permissions = [
        "view_project"
    ]  # Используем project permissions для заказов

    def get(self, request):
        """Получить список заказов пользователя."""
        orders = Order.objects.filter(user=request.user).select_related("company")
        data = [
            {
                "id": str(order.id),
                "order_number": order.order_number,
                "title": order.title,
                "company": {
                    "id": str(order.company.id),
                    "name": order.company.name,
                    "inn": order.company.inn,
                },
                "amount": float(order.amount),
                "status": order.status,
                "paid_amount": float(order.paid_amount),
                "remaining_amount": float(order.remaining_amount),
                "is_paid": order.is_paid,
                "order_date": order.order_date.isoformat(),
            }
            for order in orders
        ]

        return Response(data)

    def post(self, request):
        """Создать новый заказ."""
        if not check_user_permission(request.user, "add_project"):
            return Response(
                {"error": "Недостаточно прав доступа"}, status=status.HTTP_403_FORBIDDEN
            )

        order_data = request.data.copy()

        try:
            # Проверяем существование компании
            company = Company.objects.get(
                id=order_data["company_id"], user=request.user
            )

            order = Order.objects.create(
                user=request.user,
                company=company,
                order_number=order_data["order_number"],
                title=order_data["title"],
                description=order_data.get("description", ""),
                amount=Decimal(str(order_data["amount"])),
                status=order_data.get("status", "draft"),
            )

            return Response(
                {"id": str(order.id), "message": "Заказ создан"},
                status=status.HTTP_201_CREATED,
            )

        except Company.DoesNotExist:
            return Response(
                {"error": "Компания не найдена"}, status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
