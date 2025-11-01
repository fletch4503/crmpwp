import pytest
from django.urls import reverse
from rest_framework import status
from model_bakery import baker

from contacts.models import Contact


class TestContactModel:
    """Test Contact model functionality."""

    def test_contact_creation(self, user):
        """Test basic contact creation."""
        contact = baker.make(
            Contact,
            user=user,
            first_name="John",
            last_name="Doe",
            email="john@example.com",
        )
        assert contact.first_name == "John"
        assert contact.last_name == "Doe"
        assert contact.email == "john@example.com"
        assert contact.user == user
        assert not contact.is_email_verified
        assert not contact.is_phone_verified

    def test_contact_full_name(self, user):
        """Test contact full name property."""
        contact = baker.make(Contact, user=user, first_name="Jane", last_name="Smith")
        assert contact.get_full_name() == "Jane Smith"

    def test_contact_str(self, user):
        """Test contact string representation."""
        contact = baker.make(Contact, user=user, first_name="Bob", last_name="Johnson")
        assert str(contact) == "Bob Johnson"


class TestContactViews:
    """Test contact-related views."""

    def test_contact_list_requires_auth(self, client):
        """Test that contact list requires authentication."""
        response = client.get(reverse("contacts:contact_list"))
        assert response.status_code == 302  # Redirect to login

    def test_contact_list_authenticated(self, authenticated_client):
        """Test contact list view for authenticated user."""
        response = authenticated_client.get(reverse("contacts:contact_list"))
        assert response.status_code == 200

    def test_contact_create_view(self, authenticated_client):
        """Test contact creation view."""
        response = authenticated_client.get(reverse("contacts:contact_create"))
        assert response.status_code == 200

    def test_contact_detail_view(self, authenticated_client, contact):
        """Test contact detail view."""
        response = authenticated_client.get(
            reverse("contacts:contact_detail", kwargs={"pk": contact.pk})
        )
        assert response.status_code == 200


class TestContactAPIViews:
    """Test contact API views."""

    def test_contact_list_api(self, authenticated_client):
        """Test contact list API endpoint."""
        response = authenticated_client.get("/api/contacts/")
        assert response.status_code == status.HTTP_200_OK
        assert "results" in response.data

    def test_contact_create_api(self, authenticated_client):
        """Test contact creation via API."""
        data = {
            "first_name": "Alice",
            "last_name": "Wonder",
            "email": "alice@example.com",
            "phone": "+7 (999) 123-45-67",
            "company": "Wonder Corp",
        }
        response = authenticated_client.post("/api/contacts/", data)
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["first_name"] == "Alice"
        assert response.data["email"] == "alice@example.com"

    def test_contact_detail_api(self, authenticated_client, contact):
        """Test contact detail API endpoint."""
        response = authenticated_client.get(f"/api/contacts/{contact.id}/")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["email"] == contact.email

    def test_contact_update_api(self, authenticated_client, contact):
        """Test contact update via API."""
        data = {"first_name": "Updated Name"}
        response = authenticated_client.patch(f"/api/contacts/{contact.id}/", data)
        assert response.status_code == status.HTTP_200_OK
        assert response.data["first_name"] == "Updated Name"

    def test_contact_delete_api(self, authenticated_client, contact):
        """Test contact deletion via API."""
        response = authenticated_client.delete(f"/api/contacts/{contact.id}/")
        assert response.status_code == status.HTTP_204_NO_CONTENT

        # Verify contact was deleted
        response = authenticated_client.get(f"/api/contacts/{contact.id}/")
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_contact_search_api(self, authenticated_client, contact):
        """Test contact search functionality."""
        # Search by email
        response = authenticated_client.get(f"/api/contacts/?search={contact.email}")
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) > 0

        # Search by name
        response = authenticated_client.get(
            f"/api/contacts/?search={contact.first_name}"
        )
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) > 0

    def test_contact_filtering_api(self, authenticated_client, contact):
        """Test contact filtering."""
        # Filter by verification status
        response = authenticated_client.get("/api/contacts/?is_email_verified=true")
        assert response.status_code == status.HTTP_200_OK

        response = authenticated_client.get("/api/contacts/?is_phone_verified=false")
        assert response.status_code == status.HTTP_200_OK

    def test_contact_bulk_operations_api(self, authenticated_client):
        """Test bulk operations on contacts."""
        # Create multiple contacts
        contacts_data = [
            {
                "first_name": f"Contact{i}",
                "last_name": "Test",
                "email": f"contact{i}@example.com",
            }
            for i in range(3)
        ]

        created_contacts = []
        for contact_data in contacts_data:
            response = authenticated_client.post("/api/contacts/", contact_data)
            assert response.status_code == status.HTTP_201_CREATED
            created_contacts.append(response.data["id"])

        # Bulk mark as verified
        bulk_data = {"contacts": created_contacts, "action": "verify_email"}
        response = authenticated_client.post("/api/contacts/bulk/", bulk_data)
        assert response.status_code == status.HTTP_200_OK

    def test_contact_export_api(self, authenticated_client):
        """Test contact export functionality."""
        response = authenticated_client.get("/api/contacts/export/")
        assert response.status_code == status.HTTP_200_OK
        assert "attachment" in response.get("Content-Disposition", "")


class TestContactPermissions:
    """Test contact permissions."""

    def test_user_can_only_see_own_contacts(self, authenticated_client, user):
        """Test that users can only see their own contacts."""
        # Create contact for the user
        contact = baker.make(Contact, user=user)

        # Create contact for another user
        other_user = baker.make("users.User")
        other_contact = baker.make(Contact, user=other_user)

        response = authenticated_client.get("/api/contacts/")
        contact_ids = [c["id"] for c in response.data["results"]]

        assert contact.id in contact_ids
        assert other_contact.id not in contact_ids

    def test_user_can_modify_own_contacts(self, authenticated_client, contact):
        """Test that users can modify their own contacts."""
        data = {"first_name": "Modified"}
        response = authenticated_client.patch(f"/api/contacts/{contact.id}/", data)
        assert response.status_code == status.HTTP_200_OK
        assert response.data["first_name"] == "Modified"

    def test_user_cannot_modify_others_contacts(self, authenticated_client):
        """Test that users cannot modify others' contacts."""
        other_user = baker.make("users.User")
        other_contact = baker.make(Contact, user=other_user)

        data = {"first_name": "Modified"}
        response = authenticated_client.patch(
            f"/api/contacts/{other_contact.id}/", data
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestContactValidation:
    """Test contact data validation."""

    def test_email_uniqueness_per_user(self, authenticated_client, contact):
        """Test that email must be unique per user."""
        data = {
            "first_name": "Duplicate",
            "last_name": "Email",
            "email": contact.email,  # Same email as existing contact
        }
        response = authenticated_client.post("/api/contacts/", data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "email" in response.data

    def test_phone_format_validation(self, authenticated_client):
        """Test phone number format validation."""
        data = {
            "first_name": "Test",
            "last_name": "User",
            "email": "test@example.com",
            "phone": "invalid-phone",
        }
        response = authenticated_client.post("/api/contacts/", data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "phone" in response.data

    def test_valid_phone_format(self, authenticated_client):
        """Test valid phone number formats."""
        valid_phones = ["+7 (999) 123-45-67", "+7 999 123 45 67", "+79991234567"]

        for phone in valid_phones:
            data = {
                "first_name": "Test",
                "last_name": "User",
                "email": f"test{phone.replace(' ', '')}@example.com",
                "phone": phone,
            }
            response = authenticated_client.post("/api/contacts/", data)
            assert (
                response.status_code == status.HTTP_201_CREATED
            ), f"Failed for phone: {phone}"


class TestContactStatistics:
    """Test contact statistics and analytics."""

    def test_contact_stats_calculation(self, authenticated_client):
        """Test contact statistics calculation."""
        # Create contacts with different verification statuses
        baker.make(
            Contact,
            user=authenticated_client.handler._force_user,
            is_email_verified=True,
        )
        baker.make(
            Contact,
            user=authenticated_client.handler._force_user,
            is_phone_verified=True,
        )
        baker.make(
            Contact,
            user=authenticated_client.handler._force_user,
            is_email_verified=True,
            is_phone_verified=True,
        )

        response = authenticated_client.get("/api/contacts/stats/")
        assert response.status_code == status.HTTP_200_OK

        stats = response.data
        assert "total_contacts" in stats
        assert "verified_emails" in stats
        assert "verified_phones" in stats
        assert stats["verified_emails"] >= 2
        assert stats["verified_phones"] >= 1
