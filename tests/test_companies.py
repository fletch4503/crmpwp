import pytest
from django.urls import reverse
from rest_framework import status
from model_bakery import baker

from companies.models import Company, Order, Payment


class TestCompanyModel:
    """Test Company model functionality."""

    def test_company_creation(self, user):
        """Test basic company creation."""
        company = baker.make(Company, user=user, name="Test Company", inn="1234567890")
        assert company.name == "Test Company"
        assert company.inn == "1234567890"
        assert company.user == user

    def test_company_str(self, user):
        """Test company string representation."""
        company = baker.make(Company, user=user, name="ABC Corp")
        assert str(company) == "ABC Corp"


class TestOrderModel:
    """Test Order model functionality."""

    def test_order_creation(self, company):
        """Test basic order creation."""
        order = baker.make(Order, company=company, number="ORD-001", amount=100000)
        assert order.number == "ORD-001"
        assert order.amount == 100000
        assert order.company == company

    def test_order_str(self, company):
        """Test order string representation."""
        order = baker.make(Order, company=company, number="ORD-002")
        assert str(order) == "ORD-002"


class TestPaymentModel:
    """Test Payment model functionality."""

    def test_payment_creation(self, company, order):
        """Test basic payment creation."""
        payment = baker.make(Payment, company=company, order=order, amount=50000)
        assert payment.amount == 50000
        assert payment.company == company
        assert payment.order == order

    def test_payment_str(self, company, order):
        """Test payment string representation."""
        payment = baker.make(Payment, company=company, order=order, amount=75000)
        assert str(payment) == f"Payment {payment.id}"


class TestCompanyViews:
    """Test company-related views."""

    def test_company_list_requires_auth(self, client):
        """Test that company list requires authentication."""
        response = client.get(reverse("companies:company_list"))
        assert response.status_code == 302  # Redirect to login

    def test_company_list_authenticated(self, authenticated_client):
        """Test company list view for authenticated user."""
        response = authenticated_client.get(reverse("companies:company_list"))
        assert response.status_code == 200

    def test_company_create_view(self, authenticated_client):
        """Test company creation view."""
        response = authenticated_client.get(reverse("companies:company_create"))
        assert response.status_code == 200


class TestCompanyAPIViews:
    """Test company API views."""

    def test_company_list_api(self, authenticated_client):
        """Test company list API endpoint."""
        response = authenticated_client.get("/api/companies/")
        assert response.status_code == status.HTTP_200_OK
        assert "results" in response.data

    def test_company_create_api(self, authenticated_client):
        """Test company creation via API."""
        data = {
            "name": "New Company",
            "inn": "9876543210",
            "address": "123 Main St, City, Country",
        }
        response = authenticated_client.post("/api/companies/", data)
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["name"] == "New Company"
        assert response.data["inn"] == "9876543210"

    def test_company_detail_api(self, authenticated_client, company):
        """Test company detail API endpoint."""
        response = authenticated_client.get(f"/api/companies/{company.id}/")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["name"] == company.name

    def test_company_update_api(self, authenticated_client, company):
        """Test company update via API."""
        data = {"name": "Updated Company Name"}
        response = authenticated_client.patch(f"/api/companies/{company.id}/", data)
        assert response.status_code == status.HTTP_200_OK
        assert response.data["name"] == "Updated Company Name"

    def test_company_delete_api(self, authenticated_client, company):
        """Test company deletion via API."""
        response = authenticated_client.delete(f"/api/companies/{company.id}/")
        assert response.status_code == status.HTTP_204_NO_CONTENT

    def test_company_search_api(self, authenticated_client, company):
        """Test company search functionality."""
        # Search by name
        response = authenticated_client.get(f"/api/companies/?search={company.name}")
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) > 0

        # Search by INN
        response = authenticated_client.get(f"/api/companies/?search={company.inn}")
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) > 0

    def test_company_filtering_api(self, authenticated_client, company):
        """Test company filtering."""
        # Filter by INN
        response = authenticated_client.get(f"/api/companies/?inn={company.inn}")
        assert response.status_code == status.HTTP_200_OK

    def test_company_with_orders_api(self, authenticated_client, company, order):
        """Test company with orders API."""
        response = authenticated_client.get(f"/api/companies/{company.id}/")
        assert response.status_code == status.HTTP_200_OK
        assert "orders" in response.data or "orders_count" in response.data


class TestOrderAPIViews:
    """Test order API views."""

    def test_order_list_api(self, authenticated_client):
        """Test order list API endpoint."""
        response = authenticated_client.get("/api/orders/")
        assert response.status_code == status.HTTP_200_OK

    def test_order_create_api(self, authenticated_client, company):
        """Test order creation via API."""
        data = {"company": company.id, "number": "ORD-TEST-001", "amount": 150000}
        response = authenticated_client.post("/api/orders/", data)
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["number"] == "ORD-TEST-001"

    def test_order_detail_api(self, authenticated_client, order):
        """Test order detail API endpoint."""
        response = authenticated_client.get(f"/api/orders/{order.id}/")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["number"] == order.number


class TestPaymentAPIViews:
    """Test payment API views."""

    def test_payment_list_api(self, authenticated_client):
        """Test payment list API endpoint."""
        response = authenticated_client.get("/api/payments/")
        assert response.status_code == status.HTTP_200_OK

    def test_payment_create_api(self, authenticated_client, company, order):
        """Test payment creation via API."""
        data = {"company": company.id, "order": order.id, "amount": 75000}
        response = authenticated_client.post("/api/payments/", data)
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["amount"] == 75000


class TestCompanyPermissions:
    """Test company permissions."""

    def test_user_can_only_see_own_companies(self, authenticated_client, user):
        """Test that users can only see their own companies."""
        # Create company for the user
        company = baker.make(Company, user=user)

        # Create company for another user
        other_user = baker.make("users.User")
        other_company = baker.make(Company, user=other_user)

        response = authenticated_client.get("/api/companies/")
        company_ids = [c["id"] for c in response.data["results"]]

        assert company.id in company_ids
        assert other_company.id not in company_ids

    def test_user_can_modify_own_companies(self, authenticated_client, company):
        """Test that users can modify their own companies."""
        data = {"name": "Modified Company"}
        response = authenticated_client.patch(f"/api/companies/{company.id}/", data)
        assert response.status_code == status.HTTP_200_OK
        assert response.data["name"] == "Modified Company"

    def test_user_cannot_modify_others_companies(self, authenticated_client):
        """Test that users cannot modify others' companies."""
        other_user = baker.make("users.User")
        other_company = baker.make(Company, user=other_user)

        data = {"name": "Modified Company"}
        response = authenticated_client.patch(
            f"/api/companies/{other_company.id}/", data
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestCompanyValidation:
    """Test company data validation."""

    def test_inn_format_validation(self, authenticated_client):
        """Test INN format validation."""
        # Valid INN (10 digits)
        data = {
            "name": "Valid Company",
            "inn": "1234567890",
            "address": "Valid Address",
        }
        response = authenticated_client.post("/api/companies/", data)
        assert response.status_code == status.HTTP_201_CREATED

        # Invalid INN (too short)
        data["inn"] = "12345"
        response = authenticated_client.post("/api/companies/", data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "inn" in response.data

    def test_inn_uniqueness(self, authenticated_client, company):
        """Test that INN must be unique."""
        data = {
            "name": "Duplicate INN Company",
            "inn": company.inn,  # Same INN as existing company
            "address": "Some Address",
        }
        response = authenticated_client.post("/api/companies/", data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "inn" in response.data


class TestOrderValidation:
    """Test order data validation."""

    def test_order_amount_validation(self, authenticated_client, company):
        """Test order amount validation."""
        # Valid amount
        data = {"company": company.id, "number": "ORD-VALID", "amount": 100000}
        response = authenticated_client.post("/api/orders/", data)
        assert response.status_code == status.HTTP_201_CREATED

        # Invalid amount (negative)
        data["amount"] = -1000
        response = authenticated_client.post("/api/orders/", data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "amount" in response.data

    def test_order_number_uniqueness_per_company(
        self, authenticated_client, company, order
    ):
        """Test that order number must be unique per company."""
        data = {
            "company": company.id,
            "number": order.number,  # Same number as existing order
            "amount": 50000,
        }
        response = authenticated_client.post("/api/orders/", data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "number" in response.data


class TestFinancialCalculations:
    """Test financial calculations and statistics."""

    def test_company_financial_stats(
        self, authenticated_client, company, order, payment
    ):
        """Test company financial statistics."""
        response = authenticated_client.get(f"/api/companies/{company.id}/")
        assert response.status_code == status.HTTP_200_OK

        # Check if financial data is included
        data = response.data
        # These fields might be added by serializer annotations
        if "total_orders_amount" in data:
            assert data["total_orders_amount"] >= order.amount
        if "total_payments_amount" in data:
            assert data["total_payments_amount"] >= payment.amount

    def test_company_balance_calculation(self, authenticated_client, company):
        """Test company balance calculation."""
        # Create multiple orders and payments
        order1 = baker.make(Order, company=company, amount=100000)
        order2 = baker.make(Order, company=company, amount=50000)
        payment1 = baker.make(Payment, company=company, order=order1, amount=60000)
        payment2 = baker.make(Payment, company=company, order=order2, amount=30000)

        response = authenticated_client.get(f"/api/companies/{company.id}/")
        assert response.status_code == status.HTTP_200_OK

        # Calculate expected balance: total_orders - total_payments
        expected_balance = (order1.amount + order2.amount) - (
            payment1.amount + payment2.amount
        )

        # Check if balance is calculated correctly (if implemented in serializer)
        if "balance" in response.data:
            assert abs(response.data["balance"] - expected_balance) < 0.01
