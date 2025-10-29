from django.urls import path
from . import views

app_name = "companies"

urlpatterns = [
    # Основные страницы компаний
    path("", views.CompanyListView.as_view(), name="company_list"),
    path("create/", views.CompanyCreateView.as_view(), name="company_create"),
    path("<uuid:pk>/", views.CompanyDetailView.as_view(), name="company_detail"),
    path("<uuid:pk>/update/", views.CompanyUpdateView.as_view(), name="company_update"),
    path("<uuid:pk>/delete/", views.CompanyDeleteView.as_view(), name="company_delete"),
    # Заказы
    path("orders/", views.OrderListView.as_view(), name="order_list"),
    path("orders/create/", views.OrderCreateView.as_view(), name="order_create"),
    path("orders/<uuid:pk>/", views.OrderDetailView.as_view(), name="order_detail"),
    path(
        "orders/<uuid:pk>/update/", views.OrderUpdateView.as_view(), name="order_update"
    ),
    # Платежи
    path("payments/", views.PaymentListView.as_view(), name="payment_list"),
    path("payments/create/", views.PaymentCreateView.as_view(), name="payment_create"),
    # API endpoints
    path("api/", views.CompanyAPIView.as_view(), name="api_companies"),
    path("api/orders/", views.OrderAPIView.as_view(), name="api_orders"),
    # AJAX endpoints
    path("ajax/search/", views.company_search_ajax, name="company_search_ajax"),
    path(
        "ajax/<uuid:company_id>/add-note/",
        views.add_company_note_ajax,
        name="add_company_note_ajax",
    ),
    path(
        "ajax/<uuid:company_id>/stats/",
        views.get_company_stats_ajax,
        name="get_company_stats_ajax",
    ),
]
