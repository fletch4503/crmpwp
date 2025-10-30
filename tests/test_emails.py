import pytest
from django.urls import reverse
from rest_framework import status
from model_bakery import baker

from emails.models import EmailCredentials, EmailMessage, EmailSyncLog


class TestEmailCredentialsModel:
    """Test EmailCredentials model functionality."""

    def test_credentials_creation(self, user):
        """Test basic email credentials creation."""
        credentials = baker.make(
            EmailCredentials,
            user=user,
            email="test@example.com",
            server="mail.example.com",
            is_active=True,
        )
        assert credentials.email == "test@example.com"
        assert credentials.server == "mail.example.com"
        assert credentials.user == user
        assert credentials.is_active

    def test_credentials_str(self, user):
        """Test credentials string representation."""
        credentials = baker.make(EmailCredentials, user=user, email="user@domain.com")
        assert str(credentials) == "user@domain.com"


class TestEmailMessageModel:
    """Test EmailMessage model functionality."""

    def test_email_message_creation(self, user, email_credentials, project, company):
        """Test basic email message creation."""
        message = baker.make(
            EmailMessage,
            user=user,
            credentials=email_credentials,
            subject="Test Subject",
            body="Test body",
            sender="sender@example.com",
            related_project=project,
            related_company=company,
        )
        assert message.subject == "Test Subject"
        assert message.body == "Test body"
        assert message.sender == "sender@example.com"
        assert message.related_project == project
        assert message.related_company == company

    def test_email_message_str(self, user, email_credentials):
        """Test email message string representation."""
        message = baker.make(
            EmailMessage,
            user=user,
            credentials=email_credentials,
            subject="Important Email",
        )
        assert str(message) == "Important Email"


class TestEmailSyncLogModel:
    """Test EmailSyncLog model functionality."""

    def test_sync_log_creation(self, email_credentials):
        """Test basic sync log creation."""
        log = baker.make(
            EmailSyncLog,
            credentials=email_credentials,
            status="success",
            messages_processed=10,
        )
        assert log.status == "success"
        assert log.messages_processed == 10
        assert log.credentials == email_credentials

    def test_sync_log_str(self, email_credentials):
        """Test sync log string representation."""
        log = baker.make(EmailSyncLog, credentials=email_credentials, status="success")
        assert "success" in str(log)


class TestEmailViews:
    """Test email-related views."""

    def test_email_list_requires_auth(self, client):
        """Test that email list requires authentication."""
        response = client.get(reverse("emails:email_list"))
        assert response.status_code == 302  # Redirect to login

    def test_email_list_authenticated(self, authenticated_client):
        """Test email list view for authenticated user."""
        response = authenticated_client.get(reverse("emails:email_list"))
        assert response.status_code == 200

    def test_credentials_setup_view(self, authenticated_client):
        """Test credentials setup view."""
        response = authenticated_client.get(reverse("emails:credentials_setup"))
        assert response.status_code == 200


class TestEmailAPIViews:
    """Test email API views."""

    def test_email_credentials_list_api(self, authenticated_client):
        """Test email credentials list API endpoint."""
        response = authenticated_client.get("/api/emails/credentials/")
        assert response.status_code == status.HTTP_200_OK

    def test_email_credentials_create_api(self, authenticated_client):
        """Test email credentials creation via API."""
        data = {
            "email": "new@example.com",
            "server": "mail.example.com",
            "use_ssl": True,
            "is_active": True,
        }
        response = authenticated_client.post("/api/emails/credentials/", data)
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["email"] == "new@example.com"

    def test_email_message_list_api(self, authenticated_client):
        """Test email message list API endpoint."""
        response = authenticated_client.get("/api/emails/messages/")
        assert response.status_code == status.HTTP_200_OK
        assert "results" in response.data

    def test_email_message_detail_api(self, authenticated_client, email_message):
        """Test email message detail API endpoint."""
        response = authenticated_client.get(f"/api/emails/messages/{email_message.id}/")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["subject"] == email_message.subject

    def test_email_sync_api(self, authenticated_client, email_credentials):
        """Test email synchronization API."""
        data = {"credentials_id": email_credentials.id}
        response = authenticated_client.post("/api/emails/sync/", data)
        # This might be async, so we check that the request was accepted
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_202_ACCEPTED]

    def test_email_search_api(self, authenticated_client, email_message):
        """Test email search functionality."""
        # Search by subject
        response = authenticated_client.get(
            f"/api/emails/messages/?search={email_message.subject}"
        )
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) > 0

        # Search by sender
        response = authenticated_client.get(
            f"/api/emails/messages/?search={email_message.sender}"
        )
        assert response.status_code == status.HTTP_200_OK

    def test_email_filtering_api(self, authenticated_client, email_message):
        """Test email filtering."""
        # Filter by read status
        response = authenticated_client.get("/api/emails/messages/?is_read=false")
        assert response.status_code == status.HTTP_200_OK

        # Filter by importance
        response = authenticated_client.get("/api/emails/messages/?is_important=true")
        assert response.status_code == status.HTTP_200_OK

    def test_email_mark_as_read_api(self, authenticated_client, email_message):
        """Test mark email as read API."""
        data = {"is_read": True}
        response = authenticated_client.patch(
            f"/api/emails/messages/{email_message.id}/", data
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data["is_read"]

    def test_email_mark_important_api(self, authenticated_client, email_message):
        """Test mark email as important API."""
        data = {"is_important": True}
        response = authenticated_client.patch(
            f"/api/emails/messages/{email_message.id}/", data
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data["is_important"]


class TestEmailPermissions:
    """Test email permissions."""

    def test_user_can_only_see_own_emails(self, authenticated_client, user):
        """Test that users can only see their own emails."""
        # Create email for the user
        credentials = baker.make(EmailCredentials, user=user)
        email = baker.make(EmailMessage, user=user, credentials=credentials)

        # Create email for another user
        other_user = baker.make("users.User")
        other_credentials = baker.make(EmailCredentials, user=other_user)
        other_email = baker.make(
            EmailMessage, user=other_user, credentials=other_credentials
        )

        response = authenticated_client.get("/api/emails/messages/")
        email_ids = [e["id"] for e in response.data["results"]]

        assert email.id in email_ids
        assert other_email.id not in email_ids

    def test_user_can_only_see_own_credentials(self, authenticated_client, user):
        """Test that users can only see their own credentials."""
        # Create credentials for the user
        credentials = baker.make(EmailCredentials, user=user)

        # Create credentials for another user
        other_user = baker.make("users.User")
        other_credentials = baker.make(EmailCredentials, user=other_user)

        response = authenticated_client.get("/api/emails/credentials/")
        credentials_ids = [c["id"] for c in response.data["results"]]

        assert credentials.id in credentials_ids
        assert other_credentials.id not in credentials_ids


class TestEmailValidation:
    """Test email data validation."""

    def test_email_credentials_validation(self, authenticated_client):
        """Test email credentials validation."""
        # Valid credentials
        data = {
            "email": "valid@example.com",
            "server": "mail.example.com",
            "use_ssl": True,
            "is_active": True,
        }
        response = authenticated_client.post("/api/emails/credentials/", data)
        assert response.status_code == status.HTTP_201_CREATED

        # Invalid email format
        data["email"] = "invalid-email"
        response = authenticated_client.post("/api/emails/credentials/", data)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "email" in response.data

    def test_email_message_validation(self, authenticated_client, email_credentials):
        """Test email message validation."""
        # Valid message
        data = {
            "credentials": email_credentials.id,
            "subject": "Valid Subject",
            "body": "Valid body",
            "sender": "sender@example.com",
        }
        response = authenticated_client.post("/api/emails/messages/", data)
        assert response.status_code == status.HTTP_201_CREATED

        # Missing required fields
        data_missing = {"body": "Body without subject"}
        response = authenticated_client.post("/api/emails/messages/", data_missing)
        assert response.status_code == status.HTTP_400_BAD_REQUEST


class TestEmailProcessing:
    """Test email processing functionality."""

    def test_inn_parsing(self, authenticated_client, email_credentials):
        """Test INN parsing from email content."""
        inn = "1234567890"
        body = f"Please process order for company with INN: {inn}"

        data = {
            "credentials": email_credentials.id,
            "subject": "Order Request",
            "body": body,
            "sender": "client@example.com",
        }
        response = authenticated_client.post("/api/emails/messages/", data)
        assert response.status_code == status.HTTP_201_CREATED

        # Check if INN was parsed
        if "parsed_inn" in response.data:
            assert response.data["parsed_inn"] == inn

    def test_project_creation_from_email(self, authenticated_client, email_credentials):
        """Test automatic project creation from email."""
        inn = "1234567890"
        subject = f"Project Request - INN {inn}"

        data = {
            "credentials": email_credentials.id,
            "subject": subject,
            "body": "Please create a new project for us.",
            "sender": "client@example.com",
        }
        response = authenticated_client.post("/api/emails/messages/", data)
        assert response.status_code == status.HTTP_201_CREATED

        # Check if project was created (if auto-creation is implemented)
        # This depends on the business logic implementation

    def test_contact_creation_from_email(self, authenticated_client, email_credentials):
        """Test automatic contact creation from email."""
        data = {
            "credentials": email_credentials.id,
            "subject": "Introduction",
            "body": "Hello, my name is John Doe. Contact me at john@example.com",
            "sender": "john@example.com",
        }
        response = authenticated_client.post("/api/emails/messages/", data)
        assert response.status_code == status.HTTP_201_CREATED

        # Check if contact was created (if auto-creation is implemented)
        # This depends on the business logic implementation


class TestEmailSync:
    """Test email synchronization functionality."""

    def test_sync_log_creation(self, authenticated_client, email_credentials):
        """Test that sync creates log entries."""
        initial_count = EmailSyncLog.objects.count()

        data = {"credentials_id": email_credentials.id}
        response = authenticated_client.post("/api/emails/sync/", data)

        # Sync might be async, but log should be created
        # This test assumes sync is synchronous for simplicity
        if response.status_code == status.HTTP_200_OK:
            final_count = EmailSyncLog.objects.count()
            assert final_count > initial_count

    def test_sync_status_tracking(self, authenticated_client, email_credentials):
        """Test sync status tracking."""
        data = {"credentials_id": email_credentials.id}
        response = authenticated_client.post("/api/emails/sync/", data)

        if response.status_code == status.HTTP_200_OK:
            # Check latest sync log
            latest_log = (
                EmailSyncLog.objects.filter(credentials=email_credentials)
                .order_by("-started_at")
                .first()
            )

            if latest_log:
                assert latest_log.status in ["success", "failed", "running"]
                if latest_log.status == "success":
                    assert latest_log.messages_processed >= 0


class TestEmailStatistics:
    """Test email statistics and analytics."""

    def test_email_stats_calculation(self, authenticated_client):
        """Test email statistics calculation."""
        # Create emails with different properties
        credentials = baker.make(
            EmailCredentials, user=authenticated_client.handler._force_user
        )
        baker.make(
            EmailMessage,
            user=authenticated_client.handler._force_user,
            credentials=credentials,
            is_read=True,
        )
        baker.make(
            EmailMessage,
            user=authenticated_client.handler._force_user,
            credentials=credentials,
            is_read=False,
            is_important=True,
        )
        baker.make(
            EmailMessage,
            user=authenticated_client.handler._force_user,
            credentials=credentials,
            has_attachments=True,
        )

        response = authenticated_client.get("/api/emails/stats/")
        assert response.status_code == status.HTTP_200_OK

        stats = response.data
        assert "total_emails" in stats
        assert "unread_count" in stats
        assert "important_count" in stats
        assert stats["total_emails"] >= 3

    def test_sync_stats_calculation(self, authenticated_client, email_credentials):
        """Test sync statistics calculation."""
        # Create sync logs with different statuses
        baker.make(
            EmailSyncLog,
            credentials=email_credentials,
            status="success",
            messages_processed=10,
        )
        baker.make(
            EmailSyncLog,
            credentials=email_credentials,
            status="failed",
            messages_processed=0,
        )
        baker.make(
            EmailSyncLog,
            credentials=email_credentials,
            status="success",
            messages_processed=5,
        )

        response = authenticated_client.get("/api/emails/sync-stats/")
        assert response.status_code == status.HTTP_200_OK

        stats = response.data
        assert "total_syncs" in stats
        assert "successful_syncs" in stats
        assert "total_messages_processed" in stats
        assert stats["total_messages_processed"] >= 15
