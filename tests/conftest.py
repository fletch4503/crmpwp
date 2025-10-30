import os
import sys
import django
from django.conf import settings

# Configure Django settings before importing anything else
if not settings.configured:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "crm.settings")
    # Temporarily remove crm from sys.modules to avoid celery import
    if "crm" in sys.modules:
        del sys.modules["crm"]
    if "crm.celery" in sys.modules:
        del sys.modules["crm.celery"]
    # Set minimal settings to avoid missing dependencies
    settings.configure(
        DEBUG=True,
        SECRET_KEY="test-secret-key",
        INSTALLED_APPS=[
            "django.contrib.auth",
            "django.contrib.contenttypes",
            "rest_framework",
            "phonenumber_field",
            "users",
            "contacts",
            "companies",
            "projects",
            "emails",
        ],
        DATABASES={
            "default": {
                "ENGINE": "django.db.backends.sqlite3",
                "NAME": ":memory:",
            }
        },
        USE_TZ=True,
    )
    django.setup()

import pytest  # type: ignore
from django.contrib.auth import get_user_model
from django.test import Client
from rest_framework.test import APIClient
from model_bakery import baker

from users.models import Role, Permission, UserRole, RolePermission, AccessToken
from contacts.models import Contact
from companies.models import Company, Order, Payment
from projects.models import Project
from emails.models import EmailCredentials, EmailMessage

User = get_user_model()


@pytest.fixture
def client():
    """Django test client."""
    return Client()


@pytest.fixture
def api_client():
    """DRF API client."""
    return APIClient()


@pytest.fixture
def user():
    """Create a test user."""
    return baker.make(User, email="test@example.com", username="testuser")


@pytest.fixture
def admin_user():
    """Create an admin user."""
    return baker.make(
        User,
        email="admin@example.com",
        username="admin",
        is_staff=True,
        is_superuser=True,
    )


@pytest.fixture
def authenticated_client(api_client, user):
    """API client authenticated as regular user."""
    api_client.force_authenticate(user=user)
    return api_client


@pytest.fixture
def admin_client(api_client, admin_user):
    """API client authenticated as admin user."""
    api_client.force_authenticate(user=admin_user)
    return api_client


@pytest.fixture
def role():
    """Create a test role."""
    return baker.make(Role, name="Test Role", description="Test role description")


@pytest.fixture
def permission():
    """Create a test permission."""
    return baker.make(Permission, name="Test Permission", codename="test_perm")


@pytest.fixture
def user_role(user, role):
    """Create a user-role relationship."""
    return baker.make(UserRole, user=user, role=role)


@pytest.fixture
def role_permission(role, permission):
    """Create a role-permission relationship."""
    return baker.make(RolePermission, role=role, permission=permission)


@pytest.fixture
def access_token(user):
    """Create an access token for user."""
    return baker.make(AccessToken, user=user, is_active=True)


@pytest.fixture
def contact(user):
    """Create a test contact."""
    return baker.make(Contact, user=user)


@pytest.fixture
def company(user):
    """Create a test company."""
    return baker.make(Company, user=user, inn="1234567890")


@pytest.fixture
def order(company):
    """Create a test order."""
    return baker.make(Order, company=company)


@pytest.fixture
def payment(company, order):
    """Create a test payment."""
    return baker.make(Payment, company=company, order=order)


@pytest.fixture
def project(user, company):
    """Create a test project."""
    return baker.make(Project, user=user, inn=company.inn if company else None)


@pytest.fixture
def email_credentials(user):
    """Create email credentials."""
    return baker.make(EmailCredentials, user=user, is_active=True)


@pytest.fixture
def email_message(user, email_credentials, project, company):
    """Create a test email message."""
    return baker.make(
        EmailMessage,
        user=user,
        credentials=email_credentials,
        related_project=project,
        related_company=company,
    )


@pytest.fixture
def system_roles():
    """Create system roles (Admin, Manager, User)."""
    admin_role = baker.make(
        Role,
        name="Администратор",
        description="Полный доступ ко всем функциям",
        is_system_role=True,
    )
    manager_role = baker.make(
        Role,
        name="Менеджер",
        description="Управление проектами и контактами",
        is_system_role=True,
    )
    user_role = baker.make(
        Role, name="Пользователь", description="Базовый доступ", is_system_role=True
    )
    return {"admin": admin_role, "manager": manager_role, "user": user_role}


@pytest.fixture
def system_permissions():
    """Create system permissions."""
    permissions = {}
    permission_data = [
        ("view_users", "Просмотр пользователей"),
        ("add_users", "Создание пользователей"),
        ("change_users", "Изменение пользователей"),
        ("delete_users", "Удаление пользователей"),
        ("view_projects", "Просмотр проектов"),
        ("add_projects", "Создание проектов"),
        ("change_projects", "Изменение проектов"),
        ("delete_projects", "Удаление проектов"),
        ("manage_roles", "Управление ролями"),
        ("manage_permissions", "Управление разрешениями"),
    ]

    for codename, name in permission_data:
        permissions[codename] = baker.make(
            Permission, name=name, codename=codename, is_system_permission=True
        )

    return permissions
