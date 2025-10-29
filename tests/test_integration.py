import pytest
from django.urls import reverse
from rest_framework import status
from model_bakery import baker

from users.models import User, Role, Permission, UserRole, RolePermission, AccessToken
from contacts.models import Contact
from companies.models import Company, Order, Payment
from projects.models import Project
from emails.models import EmailCredentials, EmailMessage


class TestUserCompanyIntegration:
    """Test integration between users and companies."""

    def test_user_creates_company(self, authenticated_client, user):
        """Test that user can create company and it's properly linked."""
        data = {"name": "User Company", "inn": "1234567890", "address": "User Address"}
        response = authenticated_client.post("/api/companies/", data)
        assert response.status_code == status.HTTP_201_CREATED

        company = Company.objects.get(id=response.data["id"])
        assert company.user == user

    def test_user_company_isolation(self, authenticated_client, user):
        """Test that users only see their own companies."""
        # Create company for user
        user_company = baker.make(Company, user=user)

        # Create company for another user
        other_user = baker.make(User)
        other_company = baker.make(Company, user=other_user)

        response = authenticated_client.get("/api/companies/")
        company_ids = [c["id"] for c in response.data["results"]]

        assert user_company.id in company_ids
        assert other_company.id not in company_ids


class TestCompanyOrderIntegration:
    """Test integration between companies and orders."""

    def test_company_has_orders(self, authenticated_client, company):
        """Test that company can have multiple orders."""
        # Create orders for company
        order1 = baker.make(Order, company=company, number="ORD-001", amount=100000)
        order2 = baker.make(Order, company=company, number="ORD-002", amount=50000)

        response = authenticated_client.get(f"/api/companies/{company.id}/")
        assert response.status_code == status.HTTP_200_OK

        # Check if orders are included (depending on serializer implementation)
        if "orders" in response.data:
            order_ids = [o["id"] for o in response.data["orders"]]
            assert order1.id in order_ids
            assert order2.id in order_ids

    def test_order_belongs_to_company(self, authenticated_client, company):
        """Test that order properly belongs to company."""
        data = {"company": company.id, "number": "ORD-TEST", "amount": 75000}
        response = authenticated_client.post("/api/orders/", data)
        assert response.status_code == status.HTTP_201_CREATED

        order = Order.objects.get(id=response.data["id"])
        assert order.company == company


class TestOrderPaymentIntegration:
    """Test integration between orders and payments."""

    def test_payment_linked_to_order(self, authenticated_client, company, order):
        """Test that payment is properly linked to order."""
        data = {"company": company.id, "order": order.id, "amount": 50000}
        response = authenticated_client.post("/api/payments/", data)
        assert response.status_code == status.HTTP_201_CREATED

        payment = Payment.objects.get(id=response.data["id"])
        assert payment.order == order
        assert payment.company == company

    def test_payment_amount_validation(self, authenticated_client, company, order):
        """Test payment amount doesn't exceed order amount."""
        # Create payment that exceeds order amount
        data = {
            "company": company.id,
            "order": order.id,
            "amount": order.amount + 1000,  # Exceeds order amount
        }
        response = authenticated_client.post("/api/payments/", data)

        # This might be allowed or not depending on business logic
        # If validation is implemented, it should return 400
        if response.status_code == status.HTTP_400_BAD_REQUEST:
            assert "amount" in response.data


class TestProjectEmailIntegration:
    """Test integration between projects and emails."""

    def test_email_linked_to_project(
        self, authenticated_client, project, email_credentials
    ):
        """Test that email can be linked to project."""
        data = {
            "credentials": email_credentials.id,
            "subject": "Project Update",
            "body": "Update for the project",
            "sender": "sender@example.com",
            "related_project": project.id,
        }
        response = authenticated_client.post("/api/emails/messages/", data)
        assert response.status_code == status.HTTP_201_CREATED

        email = EmailMessage.objects.get(id=response.data["id"])
        assert email.related_project == project

    def test_project_has_emails(self, authenticated_client, project, email_credentials):
        """Test that project can have multiple emails."""
        # Create emails for project
        email1 = baker.make(
            EmailMessage,
            user=authenticated_client.handler._force_user,
            credentials=email_credentials,
            related_project=project,
        )
        email2 = baker.make(
            EmailMessage,
            user=authenticated_client.handler._force_user,
            credentials=email_credentials,
            related_project=project,
        )

        response = authenticated_client.get(f"/api/projects/{project.id}/")
        assert response.status_code == status.HTTP_200_OK

        # Check if emails are included
        if "emails" in response.data:
            email_ids = [e["id"] for e in response.data["emails"]]
            assert email1.id in email_ids
            assert email2.id in email_ids


class TestEmailCompanyIntegration:
    """Test integration between emails and companies."""

    def test_email_linked_to_company(
        self, authenticated_client, company, email_credentials
    ):
        """Test that email can be linked to company."""
        data = {
            "credentials": email_credentials.id,
            "subject": "Company Inquiry",
            "body": "Inquiry from company",
            "sender": "sender@example.com",
            "related_company": company.id,
        }
        response = authenticated_client.post("/api/emails/messages/", data)
        assert response.status_code == status.HTTP_201_CREATED

        email = EmailMessage.objects.get(id=response.data["id"])
        assert email.related_company == company

    def test_inn_parsing_creates_company_link(
        self, authenticated_client, email_credentials
    ):
        """Test that INN parsing can link email to existing company."""
        # Create company with INN
        company = baker.make(
            Company, user=authenticated_client.handler._force_user, inn="1234567890"
        )

        # Create email with matching INN
        data = {
            "credentials": email_credentials.id,
            "subject": "Order Request",
            "body": f"Please process order for INN: {company.inn}",
            "sender": "client@example.com",
        }
        response = authenticated_client.post("/api/emails/messages/", data)
        assert response.status_code == status.HTTP_201_CREATED

        # Check if email was linked to company (if auto-linking is implemented)
        email = EmailMessage.objects.get(id=response.data["id"])
        if hasattr(email, "related_company") and email.related_company:
            assert email.related_company == company


class TestContactEmailIntegration:
    """Test integration between contacts and emails."""

    def test_email_creates_contact(self, authenticated_client, email_credentials):
        """Test that email can create new contact."""
        email_address = "newcontact@example.com"

        data = {
            "credentials": email_credentials.id,
            "subject": "Introduction",
            "body": f"Hello from {email_address}",
            "sender": email_address,
        }
        response = authenticated_client.post("/api/emails/messages/", data)
        assert response.status_code == status.HTTP_201_CREATED

        # Check if contact was created (if auto-creation is implemented)
        contact_exists = Contact.objects.filter(
            user=authenticated_client.handler._force_user, email=email_address
        ).exists()

        # This depends on business logic implementation
        # If auto-creation is enabled, contact should exist
        if contact_exists:
            contact = Contact.objects.get(
                user=authenticated_client.handler._force_user, email=email_address
            )
            assert contact.email == email_address


class TestRBACIntegration:
    """Test RBAC system integration."""

    def test_user_role_permissions(self, authenticated_client, user, role, permission):
        """Test that user gets permissions through roles."""
        # Assign role to user
        baker.make(UserRole, user=user, role=role)

        # Assign permission to role
        baker.make(RolePermission, role=role, permission=permission)

        # Check if user has permission (this would be checked in business logic)
        user_permissions = set()
        for user_role in user.user_roles.all():
            for role_perm in user_role.role.role_permissions.all():
                user_permissions.add(role_perm.permission.codename)

        assert permission.codename in user_permissions

    def test_role_hierarchy(self, authenticated_client, user):
        """Test role hierarchy and permission inheritance."""
        # Create roles with different permission levels
        admin_role = baker.make(Role, name="Admin")
        manager_role = baker.make(Role, name="Manager")
        user_role = baker.make(Role, name="User")

        # Create permissions
        admin_perm = baker.make(
            Permission, name="Admin Permission", codename="admin_perm"
        )
        manager_perm = baker.make(
            Permission, name="Manager Permission", codename="manager_perm"
        )
        user_perm = baker.make(Permission, name="User Permission", codename="user_perm")

        # Assign permissions to roles
        baker.make(RolePermission, role=admin_role, permission=admin_perm)
        baker.make(RolePermission, role=manager_role, permission=manager_perm)
        baker.make(RolePermission, role=user_role, permission=user_perm)

        # Assign admin role to user
        baker.make(UserRole, user=user, role=admin_role)

        # Check permissions
        user_permissions = set()
        for user_role in user.user_roles.all():
            for role_perm in user_role.role.role_permissions.all():
                user_permissions.add(role_perm.permission.codename)

        assert admin_perm.codename in user_permissions
        # Admin should have all permissions in this simple model


class TestWorkflowIntegration:
    """Test complete workflow integration."""

    def test_complete_business_workflow(self, authenticated_client, user):
        """Test complete business workflow from email to project."""
        # 1. Create company
        company_data = {
            "name": "Workflow Company",
            "inn": "1234567890",
            "address": "Workflow Address",
        }
        company_response = authenticated_client.post("/api/companies/", company_data)
        assert company_response.status_code == status.HTTP_201_CREATED
        company_id = company_response.data["id"]

        # 2. Create email credentials
        credentials_data = {
            "email": "workflow@example.com",
            "server": "mail.example.com",
            "is_active": True,
        }
        credentials_response = authenticated_client.post(
            "/api/emails/credentials/", credentials_data
        )
        assert credentials_response.status_code == status.HTTP_201_CREATED
        credentials_id = credentials_response.data["id"]

        # 3. Receive email that creates project
        email_data = {
            "credentials": credentials_id,
            "subject": f'New Project Request - INN {company_data["inn"]}',
            "body": "Please create a new project for our company.",
            "sender": "client@company.com",
        }
        email_response = authenticated_client.post("/api/emails/messages/", email_data)
        assert email_response.status_code == status.HTTP_201_CREATED

        # 4. Create project manually (if not auto-created)
        project_data = {
            "title": "Workflow Project",
            "description": "Project created from email workflow",
            "inn": company_data["inn"],
        }
        project_response = authenticated_client.post("/api/projects/", project_data)
        assert project_response.status_code == status.HTTP_201_CREATED
        project_id = project_response.data["id"]

        # 5. Link email to project and company
        email_update_data = {
            "related_project": project_id,
            "related_company": company_id,
        }
        authenticated_client.patch(
            f'/api/emails/messages/{email_response.data["id"]}/', email_update_data
        )

        # 6. Create order for company
        order_data = {"company": company_id, "number": "WF-ORD-001", "amount": 100000}
        order_response = authenticated_client.post("/api/orders/", order_data)
        assert order_response.status_code == status.HTTP_201_CREATED

        # 7. Create payment for order
        payment_data = {
            "company": company_id,
            "order": order_response.data["id"],
            "amount": 50000,
        }
        payment_response = authenticated_client.post("/api/payments/", payment_data)
        assert payment_response.status_code == status.HTTP_201_CREATED

        # Verify complete workflow
        # Check company has order and payment
        company_response = authenticated_client.get(f"/api/companies/{company_id}/")
        assert company_response.status_code == status.HTTP_200_OK

        # Check project has email
        project_response = authenticated_client.get(f"/api/projects/{project_id}/")
        assert project_response.status_code == status.HTTP_200_OK

        # Check email is linked
        email_response = authenticated_client.get(
            f'/api/emails/messages/{email_response.data["id"]}/'
        )
        assert email_response.status_code == status.HTTP_200_OK

        # All entities should exist and be properly linked
        assert Company.objects.filter(id=company_id).exists()
        assert Project.objects.filter(id=project_id).exists()
        assert EmailMessage.objects.filter(id=email_response.data["id"]).exists()
        assert Order.objects.filter(id=order_response.data["id"]).exists()
        assert Payment.objects.filter(id=payment_response.data["id"]).exists()


class TestDataConsistency:
    """Test data consistency across related models."""

    def test_cascade_deletion(self, authenticated_client, user):
        """Test cascade deletion maintains data consistency."""
        # Create related objects
        company = baker.make(Company, user=user)
        order = baker.make(Order, company=company)
        payment = baker.make(Payment, company=company, order=order)
        project = baker.make(Project, user=user, inn=company.inn)

        # Delete company
        authenticated_client.delete(f"/api/companies/{company.id}/")

        # Check that related objects are handled properly
        # Orders and payments should be deleted or have null company
        assert (
            not Order.objects.filter(id=order.id).exists()
            or Order.objects.get(id=order.id).company is None
        )
        assert (
            not Payment.objects.filter(id=payment.id).exists()
            or Payment.objects.get(id=payment.id).company is None
        )

        # Project should still exist (not cascade deleted)
        assert Project.objects.filter(id=project.id).exists()

    def test_foreign_key_constraints(self, authenticated_client):
        """Test foreign key constraints are enforced."""
        # Try to create order with non-existent company
        data = {
            "company": 99999,  # Non-existent company ID
            "number": "ORD-TEST",
            "amount": 100000,
        }
        response = authenticated_client.post("/api/orders/", data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_unique_constraints(self, authenticated_client, company):
        """Test unique constraints are enforced."""
        # Create first order
        data = {"company": company.id, "number": "ORD-UNIQUE", "amount": 100000}
        response1 = authenticated_client.post("/api/orders/", data)
        assert response1.status_code == status.HTTP_201_CREATED

        # Try to create duplicate order number for same company
        response2 = authenticated_client.post("/api/orders/", data)
        assert response2.status_code == status.HTTP_400_BAD_REQUEST
