import random
from datetime import datetime, timedelta
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from faker import Faker

from users.models import Role, Permission, UserRole, RolePermission, AccessToken
from contacts.models import Contact
from companies.models import Company, Order, Payment
from projects.models import Project
from emails.models import EmailCredentials, EmailMessage, EmailSyncLog

User = get_user_model()
fake = Faker("ru_RU")


class Command(BaseCommand):
    help = "Generate test data for CRM system"

    def add_arguments(self, parser):
        parser.add_argument(
            "--users", type=int, default=10, help="Number of users to create"
        )
        parser.add_argument(
            "--companies", type=int, default=20, help="Number of companies to create"
        )
        parser.add_argument(
            "--contacts", type=int, default=50, help="Number of contacts to create"
        )
        parser.add_argument(
            "--projects", type=int, default=30, help="Number of projects to create"
        )
        parser.add_argument(
            "--emails", type=int, default=100, help="Number of email messages to create"
        )

    def handle(self, *args, **options):
        self.stdout.write("Starting test data generation...")

        # Create system roles and permissions
        self.create_system_roles_permissions()

        # Create users
        users = self.create_users(options["users"])

        # Create companies
        companies = self.create_companies(options["companies"], users)

        # Create contacts
        self.create_contacts(options["contacts"], users, companies)

        # Create projects
        projects = self.create_projects(options["projects"], users, companies)

        # Create orders and payments
        self.create_orders_payments(companies)

        # Create email credentials and messages
        self.create_emails(options["emails"], users, projects, companies)

        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully generated test data:\n"
                f"- {len(users)} users\n"
                f"- {len(companies)} companies\n"
                f'- {options["contacts"]} contacts\n'
                f"- {len(projects)} projects\n"
                f'- {options["emails"]} email messages'
            )
        )

    def create_system_roles_permissions(self):
        """Create system roles and permissions."""
        self.stdout.write("Creating system roles and permissions...")

        # Create permissions
        permissions_data = [
            ("view_users", "Просмотр пользователей"),
            ("add_users", "Создание пользователей"),
            ("change_users", "Изменение пользователей"),
            ("delete_users", "Удаление пользователей"),
            ("view_contacts", "Просмотр контактов"),
            ("add_contacts", "Создание контактов"),
            ("change_contacts", "Изменение контактов"),
            ("delete_contacts", "Удаление контактов"),
            ("view_companies", "Просмотр компаний"),
            ("add_companies", "Создание компаний"),
            ("change_companies", "Изменение компаний"),
            ("delete_companies", "Удаление компаний"),
            ("view_projects", "Просмотр проектов"),
            ("add_projects", "Создание проектов"),
            ("change_projects", "Изменение проектов"),
            ("delete_projects", "Удаление проектов"),
            ("view_emails", "Просмотр email"),
            ("manage_roles", "Управление ролями"),
            ("manage_permissions", "Управление разрешениями"),
        ]

        permissions = {}
        for codename, name in permissions_data:
            perm, created = Permission.objects.get_or_create(
                codename=codename, defaults={"name": name, "is_system_permission": True}
            )
            permissions[codename] = perm

        # Create roles
        roles_data = [
            (
                "Администратор",
                "Полный доступ ко всем функциям системы",
                [
                    "view_users",
                    "add_users",
                    "change_users",
                    "delete_users",
                    "view_contacts",
                    "add_contacts",
                    "change_contacts",
                    "delete_contacts",
                    "view_companies",
                    "add_companies",
                    "change_companies",
                    "delete_companies",
                    "view_projects",
                    "add_projects",
                    "change_projects",
                    "delete_projects",
                    "view_emails",
                    "manage_roles",
                    "manage_permissions",
                ],
            ),
            (
                "Менеджер",
                "Управление проектами и контактами",
                [
                    "view_contacts",
                    "add_contacts",
                    "change_contacts",
                    "view_companies",
                    "add_companies",
                    "change_companies",
                    "view_projects",
                    "add_projects",
                    "change_projects",
                    "delete_projects",
                    "view_emails",
                ],
            ),
            (
                "Пользователь",
                "Базовый доступ к системе",
                ["view_contacts", "view_companies", "view_projects", "view_emails"],
            ),
        ]

        roles = {}
        for role_name, description, perm_codenames in roles_data:
            role, created = Role.objects.get_or_create(
                name=role_name,
                defaults={"description": description, "is_system_role": True},
            )
            roles[role_name] = role

            # Assign permissions to role
            for codename in perm_codenames:
                if codename in permissions:
                    RolePermission.objects.get_or_create(
                        role=role, permission=permissions[codename]
                    )

        return roles

    def create_users(self, count):
        """Create test users."""
        self.stdout.write(f"Creating {count} users...")

        users = []

        # Create admin user
        admin_user, created = User.objects.get_or_create(
            email="admin@example.com",
            defaults={
                "username": "admin",
                "first_name": "Администратор",
                "last_name": "Системы",
                "is_staff": True,
                "is_superuser": True,
                "is_email_verified": True,
            },
        )
        if created:
            admin_user.set_password("admin123")
            admin_user.save()

            # Assign admin role
            admin_role = Role.objects.get(name="Администратор")
            UserRole.objects.get_or_create(user=admin_user, role=admin_role)

        users.append(admin_user)

        # Create regular users
        for i in range(count - 1):
            email = fake.email()
            user, created = User.objects.get_or_create(
                email=email,
                defaults={
                    "username": fake.user_name(),
                    "first_name": fake.first_name(),
                    "last_name": fake.last_name(),
                    "phone": fake.phone_number(),
                    "date_of_birth": fake.date_of_birth(minimum_age=18, maximum_age=65),
                    "is_email_verified": fake.boolean(chance_of_getting_true=70),
                    "is_phone_verified": fake.boolean(chance_of_getting_true=50),
                },
            )
            if created:
                user.set_password("password123")
                user.save()

                # Assign random role
                roles = list(Role.objects.all())
                if roles:
                    random_role = random.choice(roles)
                    UserRole.objects.get_or_create(user=user, role=random_role)

            users.append(user)

        return users

    def create_companies(self, count, users):
        """Create test companies."""
        self.stdout.write(f"Creating {count} companies...")

        companies = []

        for i in range(count):
            # Generate unique INN (10 digits)
            inn = "".join([str(random.randint(0, 9)) for _ in range(10)])

            company, created = Company.objects.get_or_create(
                inn=inn,
                defaults={
                    "name": fake.company(),
                    "address": fake.address(),
                    "user": random.choice(users),
                },
            )
            companies.append(company)

        return companies

    def create_contacts(self, count, users, companies):
        """Create test contacts."""
        self.stdout.write(f"Creating {count} contacts...")

        for i in range(count):
            Contact.objects.create(
                user=random.choice(users),
                first_name=fake.first_name(),
                last_name=fake.last_name(),
                email=fake.email(),
                phone=fake.phone_number(),
                company=fake.company() if random.choice([True, False]) else "",
                is_email_verified=fake.boolean(chance_of_getting_true=60),
                is_phone_verified=fake.boolean(chance_of_getting_true=40),
            )

    def create_projects(self, count, users, companies):
        """Create test projects."""
        self.stdout.write(f"Creating {count} projects...")

        projects = []
        statuses = ["draft", "active", "completed", "on_hold", "cancelled"]
        priorities = ["low", "medium", "high", "urgent"]

        project_titles = [
            "Разработка веб-приложения",
            "Мобильное приложение",
            "Интеграция с внешними системами",
            "Оптимизация производительности",
            "Миграция на новую платформу",
            "Автоматизация бизнес-процессов",
            "Анализ данных",
            "Создание API",
            "Тестирование системы",
            "Документирование проекта",
        ]

        for i in range(count):
            # Randomly assign INN from existing companies
            inn = None
            if companies and random.choice([True, False]):
                inn = random.choice(companies).inn

            project = Project.objects.create(
                user=random.choice(users),
                title=random.choice(project_titles),
                description=fake.text(max_nb_chars=200),
                status=random.choice(statuses),
                priority=random.choice(priorities),
                inn=inn,
            )
            projects.append(project)

        return projects

    def create_orders_payments(self, companies):
        """Create orders and payments for companies."""
        self.stdout.write("Creating orders and payments...")

        for company in companies:
            # Create 1-3 orders per company
            num_orders = random.randint(1, 3)

            for i in range(num_orders):
                order_amount = random.randint(50000, 500000)
                order = Order.objects.create(
                    company=company,
                    number=f"ORD-{company.id}-{i+1:03d}",
                    amount=order_amount,
                )

                # Create 0-2 payments per order
                num_payments = random.randint(0, 2)
                remaining_amount = order_amount

                for j in range(num_payments):
                    if remaining_amount <= 0:
                        break

                    payment_amount = random.randint(10000, remaining_amount)
                    Payment.objects.create(
                        company=company,
                        order=order,
                        amount=payment_amount,
                    )
                    remaining_amount -= payment_amount

    def create_emails(self, count, users, projects, companies):
        """Create email credentials and messages."""
        self.stdout.write(f"Creating {count} email messages...")

        # Create email credentials for some users
        email_credentials = []
        servers = ["mail.company.com", "exchange.company.ru", "smtp.gmail.com"]

        for user in random.sample(
            users, min(len(users), 5)
        ):  # Up to 5 users with email
            credentials = EmailCredentials.objects.create(
                user=user,
                email=fake.email(),
                server=random.choice(servers),
                use_ssl=True,
                is_active=True,
            )
            email_credentials.append(credentials)

        # Create email messages
        subjects = [
            "Запрос на сотрудничество",
            "Коммерческое предложение",
            "Вопрос по проекту",
            "Отчет о проделанной работе",
            "Запрос информации",
            "Подтверждение заказа",
            "Техническая поддержка",
            "Обновление статуса проекта",
        ]

        for i in range(count):
            credentials = (
                random.choice(email_credentials) if email_credentials else None
            )
            if not credentials:
                continue

            # Randomly link to project or company
            related_project = (
                random.choice(projects)
                if projects and random.choice([True, False])
                else None
            )
            related_company = (
                random.choice(companies)
                if companies and random.choice([True, False])
                else None
            )

            # Generate INN in email body if company is linked
            body = fake.text(max_nb_chars=300)
            if related_company:
                body += f"\n\nИНН компании: {related_company.inn}"

            EmailMessage.objects.create(
                user=credentials.user,
                credentials=credentials,
                subject=random.choice(subjects),
                body=body,
                sender=fake.email(),
                recipients_to=fake.email(),
                is_read=fake.boolean(chance_of_getting_true=60),
                is_important=fake.boolean(chance_of_getting_true=20),
                has_attachments=fake.boolean(chance_of_getting_true=30),
                is_processed=fake.boolean(chance_of_getting_true=80),
                parsed_inn=related_company.inn if related_company else None,
                related_project=related_project,
                related_company=related_company,
                received_at=fake.date_time_between(
                    start_date="-30d",
                    end_date="now",
                    tzinfo=timezone.get_current_timezone(),
                ),
            )

        # Create sync logs
        for credentials in email_credentials:
            for i in range(random.randint(1, 5)):
                EmailSyncLog.objects.create(
                    credentials=credentials,
                    status=random.choice(["success", "failed", "running"]),
                    messages_processed=random.randint(0, 20),
                    error_message=(
                        fake.text(max_nb_chars=100)
                        if random.choice([True, False])
                        else ""
                    ),
                    started_at=fake.date_time_between(
                        start_date="-7d",
                        end_date="now",
                        tzinfo=timezone.get_current_timezone(),
                    ),
                    finished_at=(
                        fake.date_time_between(
                            start_date="-7d",
                            end_date="now",
                            tzinfo=timezone.get_current_timezone(),
                        )
                        if random.choice([True, False])
                        else None
                    ),
                )
