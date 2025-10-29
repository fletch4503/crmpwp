import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from model_bakery import baker

from users.models import Role, Permission, UserRole, RolePermission, AccessToken

User = get_user_model()


class TestUserModel:
    """Test User model functionality."""

    def test_user_creation(self):
        """Test basic user creation."""
        user = baker.make(User, email="test@example.com", username="testuser")
        assert user.email == "test@example.com"
        assert user.username == "testuser"
        assert not user.is_email_verified
        assert not user.is_phone_verified

    def test_user_full_name(self):
        """Test user full name property."""
        user = baker.make(User, first_name="John", last_name="Doe", username="johndoe")
        assert user.get_full_name() == "John Doe"

    def test_user_is_admin(self):
        """Test admin status check."""
        regular_user = baker.make(User, is_staff=False, is_superuser=False)
        admin_user = baker.make(User, is_staff=True, is_superuser=True)

        assert not regular_user.is_admin
        assert admin_user.is_admin

    def test_user_has_verified_contact(self):
        """Test verified contact check."""
        unverified_user = baker.make(
            User, is_email_verified=False, is_phone_verified=False
        )
        email_verified_user = baker.make(
            User, is_email_verified=True, is_phone_verified=False
        )
        phone_verified_user = baker.make(
            User, is_email_verified=False, is_phone_verified=True
        )

        assert not unverified_user.has_verified_contact
        assert email_verified_user.has_verified_contact
        assert phone_verified_user.has_verified_contact


class TestRoleModel:
    """Test Role model functionality."""

    def test_role_creation(self):
        """Test basic role creation."""
        role = baker.make(Role, name="Test Role", description="Test description")
        assert role.name == "Test Role"
        assert role.description == "Test description"
        assert not role.is_system_role

    def test_role_str(self):
        """Test role string representation."""
        role = baker.make(Role, name="Manager")
        assert str(role) == "Manager"


class TestPermissionModel:
    """Test Permission model functionality."""

    def test_permission_creation(self):
        """Test basic permission creation."""
        permission = baker.make(
            Permission, name="Test Permission", codename="test_perm"
        )
        assert permission.name == "Test Permission"
        assert permission.codename == "test_perm"
        assert not permission.is_system_permission

    def test_permission_str(self):
        """Test permission string representation."""
        permission = baker.make(Permission, name="View Users", codename="view_users")
        assert str(permission) == "View Users (view_users)"


class TestUserRoleModel:
    """Test UserRole model functionality."""

    def test_user_role_creation(self, user, role):
        """Test user-role relationship creation."""
        user_role = baker.make(UserRole, user=user, role=role)
        assert user_role.user == user
        assert user_role.role == role

    def test_user_role_str(self, user, role):
        """Test user-role string representation."""
        user_role = baker.make(UserRole, user=user, role=role)
        assert str(user_role) == f"{user.email} - {role.name}"


class TestAccessTokenModel:
    """Test AccessToken model functionality."""

    def test_token_creation(self, user):
        """Test access token creation."""
        token = baker.make(AccessToken, user=user, is_active=True)
        assert token.user == user
        assert token.is_active
        assert not token.is_expired

    def test_token_str(self, user):
        """Test token string representation."""
        token = baker.make(AccessToken, user=user, token="abc123")
        assert str(token) == f"{user.email} - abc123..."


class TestUserViews:
    """Test user-related views."""

    def test_dashboard_view_requires_auth(self, client):
        """Test that dashboard requires authentication."""
        response = client.get(reverse("users:dashboard"))
        assert response.status_code == 302  # Redirect to login

    def test_dashboard_view_authenticated(self, authenticated_client):
        """Test dashboard view for authenticated user."""
        response = authenticated_client.get(reverse("users:dashboard"))
        assert response.status_code == 200


class TestUserAPIViews:
    """Test user API views."""

    def test_user_list_api(self, admin_client):
        """Test user list API endpoint."""
        response = admin_client.get("/api/users/")
        assert response.status_code == status.HTTP_200_OK
        assert "results" in response.data

    def test_user_create_api(self, admin_client):
        """Test user creation via API."""
        data = {
            "email": "newuser@example.com",
            "username": "newuser",
            "password": "password123",
            "first_name": "New",
            "last_name": "User",
        }
        response = admin_client.post("/api/users/", data)
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["email"] == "newuser@example.com"

    def test_user_detail_api(self, admin_client, user):
        """Test user detail API endpoint."""
        response = admin_client.get(f"/api/users/{user.id}/")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["email"] == user.email

    def test_role_list_api(self, admin_client):
        """Test role list API endpoint."""
        response = admin_client.get("/api/roles/")
        assert response.status_code == status.HTTP_200_OK

    def test_permission_list_api(self, admin_client):
        """Test permission list API endpoint."""
        response = admin_client.get("/api/permissions/")
        assert response.status_code == status.HTTP_200_OK

    def test_login_api(self, api_client, user):
        """Test login API endpoint."""
        data = {
            "email": user.email,
            "password": "password123",  # Default password from conftest
        }
        response = api_client.post("/api/auth/login/", data)
        assert response.status_code == status.HTTP_200_OK
        assert "token" in response.data
        assert "user" in response.data

    def test_current_user_api(self, authenticated_client, user):
        """Test current user API endpoint."""
        response = authenticated_client.get("/api/auth/me/")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["email"] == user.email

    def test_change_password_api(self, authenticated_client, user):
        """Test password change API endpoint."""
        data = {
            "old_password": "password123",
            "new_password": "newpassword123",
            "new_password_confirm": "newpassword123",
        }
        response = authenticated_client.post("/api/auth/change-password/", data)
        assert response.status_code == status.HTTP_200_OK

        # Verify password was changed
        user.refresh_from_db()
        assert user.check_password("newpassword123")

    def test_bulk_assign_role_api(self, admin_client, user, role):
        """Test bulk role assignment API."""
        data = {"user_ids": [user.id], "role_id": role.id}
        response = admin_client.post("/api/users/bulk-assign-role/", data)
        assert response.status_code == status.HTTP_200_OK

        # Verify role was assigned
        assert UserRole.objects.filter(user=user, role=role).exists()

    def test_user_stats_api(self, admin_client):
        """Test user statistics API."""
        response = admin_client.get("/api/users/stats/")
        assert response.status_code == status.HTTP_200_OK
        assert "total_users" in response.data
        assert "active_users" in response.data

    def test_role_stats_api(self, admin_client):
        """Test role statistics API."""
        response = admin_client.get("/api/roles/stats/")
        assert response.status_code == status.HTTP_200_OK
        assert "total_roles" in response.data
        assert "system_roles" in response.data


class TestPermissions:
    """Test permission system."""

    def test_admin_has_all_permissions(self, admin_client):
        """Test that admin has access to all endpoints."""
        endpoints = [
            "/api/users/",
            "/api/roles/",
            "/api/permissions/",
            "/api/users/stats/",
            "/api/roles/stats/",
        ]

        for endpoint in endpoints:
            response = admin_client.get(endpoint)
            assert response.status_code == status.HTTP_200_OK, f"Failed for {endpoint}"

    def test_regular_user_limited_access(self, authenticated_client):
        """Test that regular user has limited access."""
        # Should be able to access own profile
        response = authenticated_client.get("/api/auth/me/")
        assert response.status_code == status.HTTP_200_OK

        # Should not be able to access user management
        response = authenticated_client.get("/api/users/")
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_unauthenticated_access(self, api_client):
        """Test that unauthenticated users are blocked."""
        response = api_client.get("/api/users/")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
