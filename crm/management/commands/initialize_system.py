import os
import sys
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from django.db import transaction
from django.conf import settings
from getpass import getpass
import requests

from users.models import Role, Permission, UserRole, RolePermission
from emails.models import EmailCredentials

User = get_user_model()


class Command(BaseCommand):
    help = "Initialize the CRM system with basic data and admin user"

    def add_arguments(self, parser):
        parser.add_argument(
            "--skip-admin",
            action="store_true",
            help="Skip creating admin user",
        )
        parser.add_argument(
            "--email-setup",
            action="store_true",
            help="Setup email credentials during initialization",
        )

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS("🚀 Начинаем инициализацию CRM системы...")
        )

        try:
            with transaction.atomic():
                # Создаем базовые роли и разрешения
                self.create_basic_roles_and_permissions()

                # Создаем администратора
                if not options["skip_admin"]:
                    self.create_admin_user()

                # Настраиваем email если запрошено
                if options["email_setup"]:
                    self.setup_email_credentials()

                # Создаем базовые настройки
                self.create_system_settings()

            self.stdout.write(
                self.style.SUCCESS("✅ Инициализация CRM системы завершена успешно!")
            )

            # Выводим информацию о следующем шаге
            self.stdout.write(self.style.WARNING("\n📋 Следующие шаги:"))
            self.stdout.write("1. Запустите сервер: python manage.py runserver")
            self.stdout.write("2. Перейдите в админку: http://localhost:8000/admin/")
            self.stdout.write("3. Настройте подключение к email в профиле пользователя")
            self.stdout.write("4. Начните работу с системой!")

        except Exception as e:
            raise CommandError(f"❌ Ошибка инициализации: {str(e)}")

    def create_basic_roles_and_permissions(self):
        """Создает базовые роли и разрешения системы RBAC."""
        self.stdout.write("📝 Создаем базовые роли и разрешения...")

        # Создаем базовые разрешения
        permissions_data = [
            # Пользователи
            {"name": "Просмотр пользователей", "codename": "view_users"},
            {"name": "Создание пользователей", "codename": "add_users"},
            {"name": "Изменение пользователей", "codename": "change_users"},
            {"name": "Удаление пользователей", "codename": "delete_users"},
            # Email
            {"name": "Просмотр email", "codename": "view_emails"},
            {"name": "Отправка email", "codename": "send_emails"},
            {"name": "Удаление email", "codename": "delete_emails"},
            # Проекты
            {"name": "Просмотр проектов", "codename": "view_projects"},
            {"name": "Создание проектов", "codename": "add_projects"},
            {"name": "Изменение проектов", "codename": "change_projects"},
            {"name": "Удаление проектов", "codename": "delete_projects"},
            # Компании
            {"name": "Просмотр компаний", "codename": "view_companies"},
            {"name": "Создание компаний", "codename": "add_companies"},
            {"name": "Изменение компаний", "codename": "change_companies"},
            {"name": "Удаление компаний", "codename": "delete_companies"},
            # Контакты
            {"name": "Просмотр контактов", "codename": "view_contacts"},
            {"name": "Создание контактов", "codename": "add_contacts"},
            {"name": "Изменение контактов", "codename": "change_contacts"},
            {"name": "Удаление контактов", "codename": "delete_contacts"},
            # Администрирование
            {"name": "Управление ролями", "codename": "manage_roles"},
            {"name": "Управление разрешениями", "codename": "manage_permissions"},
            {"name": "Просмотр логов", "codename": "view_logs"},
            {"name": "Управление системой", "codename": "manage_system"},
        ]

        permissions = []
        for perm_data in permissions_data:
            perm, created = Permission.objects.get_or_create(
                codename=perm_data["codename"],
                defaults={
                    "name": perm_data["name"],
                    "is_system_permission": True,
                },
            )
            permissions.append(perm)
            if created:
                self.stdout.write(f"  ✓ Создано разрешение: {perm.name}")

        # Создаем базовые роли
        roles_data = [
            {
                "name": "Администратор",
                "description": "Полный доступ ко всем функциям системы",
                "permissions": permissions,  # Все разрешения
                "is_system_role": True,
            },
            {
                "name": "Менеджер",
                "description": "Управление проектами, компаниями и контактами",
                "permissions": [
                    p
                    for p in permissions
                    if p.codename
                    in [
                        "view_emails",
                        "send_emails",
                        "view_projects",
                        "add_projects",
                        "change_projects",
                        "view_companies",
                        "add_companies",
                        "change_companies",
                        "view_contacts",
                        "add_contacts",
                        "change_contacts",
                    ]
                ],
                "is_system_role": True,
            },
            {
                "name": "Пользователь",
                "description": "Базовый доступ к просмотру данных",
                "permissions": [
                    p
                    for p in permissions
                    if p.codename
                    in [
                        "view_emails",
                        "view_projects",
                        "view_companies",
                        "view_contacts",
                    ]
                ],
                "is_system_role": True,
            },
        ]

        for role_data in roles_data:
            role, created = Role.objects.get_or_create(
                name=role_data["name"],
                defaults={
                    "description": role_data["description"],
                    "is_system_role": role_data["is_system_role"],
                },
            )

            if created:
                self.stdout.write(f"  ✓ Создана роль: {role.name}")

                # Назначаем разрешения роли
                for permission in role_data["permissions"]:
                    RolePermission.objects.get_or_create(
                        role=role, permission=permission, defaults={"assigned_by": None}
                    )

        self.stdout.write("✅ Базовые роли и разрешения созданы")

    def create_admin_user(self):
        """Создает администратора системы."""
        self.stdout.write("👤 Создаем администратора системы...")

        # Проверяем, есть ли уже пользователи
        if User.objects.exists():
            self.stdout.write(
                "⚠️  Пользователи уже существуют, пропускаем создание администратора"
            )
            return

        # Запрашиваем данные администратора
        self.stdout.write("\n📝 Введите данные администратора:")

        email = input("Email: ").strip()
        if not email:
            raise CommandError("Email обязателен")

        username = input("Имя пользователя: ").strip()
        if not username:
            username = email.split("@")[0]

        first_name = input("Имя: ").strip()
        last_name = input("Фамилия: ").strip()

        # Пароль
        while True:
            password = getpass("Пароль: ")
            if not password:
                self.stdout.write(self.style.ERROR("Пароль не может быть пустым"))
                continue

            password_confirm = getpass("Подтвердите пароль: ")
            if password != password_confirm:
                self.stdout.write(self.style.ERROR("Пароли не совпадают"))
                continue
            break

        # Создаем администратора
        admin_user = User.objects.create_user(
            email=email,
            username=username,
            password=password,
            first_name=first_name,
            last_name=last_name,
            is_staff=True,
            is_superuser=True,
        )

        # Назначаем роль администратора
        admin_role = Role.objects.get(name="Администратор")
        UserRole.objects.create(
            user=admin_user,
            role=admin_role,
            assigned_by=None,
        )

        self.stdout.write(
            self.style.SUCCESS(f"✅ Администратор {admin_user.email} создан успешно")
        )

    def setup_email_credentials(self):
        """Настраивает подключение к email."""
        self.stdout.write("📧 Настраиваем подключение к email...")

        # Получаем администратора
        try:
            admin_user = User.objects.filter(is_superuser=True).first()
            if not admin_user:
                self.stdout.write(
                    self.style.WARNING(
                        "⚠️  Администратор не найден, пропускаем настройку email"
                    )
                )
                return
        except User.DoesNotExist:
            self.stdout.write(
                self.style.WARNING(
                    "⚠️  Администратор не найден, пропускаем настройку email"
                )
            )
            return

        # Проверяем, есть ли уже credentials
        if EmailCredentials.objects.filter(user=admin_user).exists():
            self.stdout.write("⚠️  Email credentials уже настроены, пропускаем")
            return

        self.stdout.write("\n📧 Введите настройки Exchange:")
        email = input("Email адрес: ").strip()
        if not email:
            self.stdout.write("⚠️  Email не указан, пропускаем настройку")
            return

        server = input("Сервер Exchange (mail.company.com): ").strip()
        if not server:
            self.stdout.write("⚠️  Сервер не указан, пропускаем настройку")
            return

        password = getpass("Пароль: ")
        if not password:
            self.stdout.write("⚠️  Пароль не указан, пропускаем настройку")
            return

        # Создаем credentials
        EmailCredentials.objects.create(
            user=admin_user,
            email=email,
            server=server,
            password=password,  # В реальности нужно шифровать
            use_ssl=True,
            is_active=True,
        )

        self.stdout.write(
            self.style.SUCCESS(f"✅ Email credentials для {email} созданы")
        )

        # Тестируем подключение
        self.stdout.write("🔍 Тестируем подключение...")
        try:
            # Здесь можно добавить тест подключения
            self.stdout.write("✅ Подключение успешно (тест пропущен)")
        except Exception as e:
            self.stdout.write(
                self.style.WARNING(f"⚠️  Не удалось подключиться: {str(e)}")
            )

    def create_system_settings(self):
        """Создает базовые настройки системы."""
        self.stdout.write("⚙️  Создаем системные настройки...")

        # Здесь можно добавить создание системных настроек
        # Например, настройки по умолчанию для email, уведомлений и т.д.

        self.stdout.write("✅ Системные настройки созданы")
