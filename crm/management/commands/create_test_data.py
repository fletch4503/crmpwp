import os
import random
from datetime import datetime, timedelta
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
from faker import Faker

from users.models import Role, UserRole
from contacts.models import Contact
from companies.models import Company, Order, Payment
from projects.models import Project
from emails.models import EmailCredentials, EmailMessage

User = get_user_model()
fake = Faker("ru_RU")


class Command(BaseCommand):
    help = "Create test data for development and testing"

    def add_arguments(self, parser):
        parser.add_argument(
            "--users",
            type=int,
            default=5,
            help="Number of test users to create",
        )
        parser.add_argument(
            "--contacts",
            type=int,
            default=20,
            help="Number of test contacts to create",
        )
        parser.add_argument(
            "--companies",
            type=int,
            default=10,
            help="Number of test companies to create",
        )
        parser.add_argument(
            "--projects",
            type=int,
            default=15,
            help="Number of test projects to create",
        )
        parser.add_argument(
            "--emails",
            type=int,
            default=50,
            help="Number of test emails to create",
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("🎲 Создаем тестовые данные..."))

        try:
            with transaction.atomic():
                # Получаем роли
                admin_role = Role.objects.get(name="Администратор")
                manager_role = Role.objects.get(name="Менеджер")
                user_role = Role.objects.get(name="Пользователь")

                # Создаем тестовых пользователей
                users = self.create_test_users(
                    options["users"], admin_role, manager_role, user_role
                )

                # Создаем тестовые компании
                companies = self.create_test_companies(options["companies"], users)

                # Создаем тестовые контакты
                contacts = self.create_test_contacts(
                    options["contacts"], users, companies
                )

                # Создаем тестовые проекты
                projects = self.create_test_projects(
                    options["projects"], users, companies
                )

                # Создаем тестовые email
                self.create_test_emails(
                    options["emails"], users, contacts, projects, companies
                )

            self.stdout.write(self.style.SUCCESS("✅ Тестовые данные созданы успешно!"))

            self.stdout.write(self.style.WARNING("\n📊 Созданы:"))
            self.stdout.write(f'  👥 Пользователи: {options["users"]}')
            self.stdout.write(f'  🏢 Компании: {options["companies"]}')
            self.stdout.write(f'  👤 Контакты: {options["contacts"]}')
            self.stdout.write(f'  📋 Проекты: {options["projects"]}')
            self.stdout.write(f'  📧 Email: {options["emails"]}')

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"❌ Ошибка создания тестовых данных: {str(e)}")
            )
            raise

    def create_test_users(self, count, admin_role, manager_role, user_role):
        """Создает тестовых пользователей."""
        self.stdout.write(f"👥 Создаем {count} тестовых пользователей...")

        users = []
        roles = [manager_role, user_role]

        for i in range(count):
            # Генерируем данные
            first_name = fake.first_name()
            last_name = fake.last_name()
            email = f"user{i+1}@test.com"
            username = f"user{i+1}"

            # Создаем пользователя
            user = User.objects.create_user(
                email=email,
                username=username,
                password="password123",
                first_name=first_name,
                last_name=last_name,
                phone=fake.phone_number(),
                date_of_birth=fake.date_of_birth(minimum_age=18, maximum_age=65),
                is_email_verified=random.choice([True, False]),
                is_phone_verified=random.choice([True, False]),
            )

            # Назначаем случайную роль
            role = random.choice(roles)
            UserRole.objects.create(
                user=user,
                role=role,
                assigned_by=None,
            )

            users.append(user)
            self.stdout.write(f"  ✓ Создан пользователь: {user.email} ({role.name})")

        return users

    def create_test_companies(self, count, users):
        """Создает тестовые компании."""
        self.stdout.write(f"🏢 Создаем {count} тестовых компаний...")

        companies = []

        for i in range(count):
            # Генерируем данные компании
            company = Company.objects.create(
                user=random.choice(users),
                name=fake.company(),
                inn=self.generate_inn(),
                address=fake.address(),
            )

            # Создаем заказы и оплаты для некоторых компаний
            if random.choice([True, False]):
                self.create_orders_and_payments(company)

            companies.append(company)
            self.stdout.write(
                f"  ✓ Создана компания: {company.name} (ИНН: {company.inn})"
            )

        return companies

    def create_orders_and_payments(self, company):
        """Создает заказы и оплаты для компании."""
        order_count = random.randint(1, 5)

        for _ in range(order_count):
            # Создаем заказ
            order = Order.objects.create(
                company=company,
                number=f"ORD-{random.randint(1000, 9999)}",
                amount=random.randint(10000, 500000),
            )

            # Создаем оплату для некоторых заказов
            if random.choice([True, False]):
                Payment.objects.create(
                    company=company,
                    order=order,
                    amount=order.amount,
                    paid_at=timezone.now() - timedelta(days=random.randint(1, 30)),
                )

    def create_test_contacts(self, count, users, companies):
        """Создает тестовые контакты."""
        self.stdout.write(f"👤 Создаем {count} тестовых контактов...")

        contacts = []

        for i in range(count):
            # Выбираем случайную компанию или None
            company = random.choice(companies) if random.choice([True, False]) else None

            contact = Contact.objects.create(
                user=random.choice(users),
                first_name=fake.first_name(),
                last_name=fake.last_name(),
                email=fake.email(),
                phone=fake.phone_number(),
                company=company.name if company else fake.company(),
                is_email_verified=random.choice([True, False]),
                is_phone_verified=random.choice([True, False]),
            )

            contacts.append(contact)
            self.stdout.write(f"  ✓ Создан контакт: {contact.get_full_name()}")

        return contacts

    def create_test_projects(self, count, users, companies):
        """Создает тестовые проекты."""
        self.stdout.write(f"📋 Создаем {count} тестовых проектов...")

        projects = []
        statuses = ["draft", "active", "completed", "on_hold", "cancelled"]

        for i in range(count):
            # Выбираем случайную компанию
            company = random.choice(companies) if companies else None

            project = Project.objects.create(
                user=random.choice(users),
                title=fake.sentence(nb_words=4)[:-1],  # Убираем точку
                description=fake.paragraph(nb_sentences=3),
                status=random.choice(statuses),
                priority=random.choice(["low", "medium", "high", "urgent"]),
                inn=company.inn if company else None,
            )

            projects.append(project)
            self.stdout.write(
                f"  ✓ Создан проект: {project.title} ({project.get_status_display()})"
            )

        return projects

    def create_test_emails(self, count, users, contacts, projects, companies):
        """Создает тестовые email сообщения."""
        self.stdout.write(f"📧 Создаем {count} тестовых email...")

        # Получаем credentials для пользователей
        credentials = {}
        for user in users:
            cred = EmailCredentials.objects.filter(user=user).first()
            if cred:
                credentials[user.id] = cred

        for i in range(count):
            # Выбираем пользователя с credentials
            user_with_creds = [u for u in users if u.id in credentials]
            if not user_with_creds:
                continue

            user = random.choice(user_with_creds)
            cred = credentials[user.id]

            # Выбираем случайные связанные объекты
            # related_contact = (
            #     random.choice(contacts)
            #     if contacts and random.choice([True, False])
            #     else None
            # )
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

            # Генерируем email
            email = EmailMessage.objects.create(
                user=user,
                credentials=cred,
                subject=fake.sentence(nb_words=6)[:-1],
                body=fake.paragraph(nb_sentences=5),
                sender=fake.email(),
                recipients_to=[fake.email() for _ in range(random.randint(1, 3))],
                received_at=timezone.now()
                - timedelta(
                    days=random.randint(0, 30),
                    hours=random.randint(0, 23),
                    minutes=random.randint(0, 59),
                ),
                is_read=random.choice([True, False]),
                is_important=random.choice([True, False]),
                has_attachments=random.choice([True, False]),
                parsed_inn=(
                    related_company.inn
                    if related_company and random.choice([True, False])
                    else None
                ),
                related_company=related_company,
                related_project=related_project,
                is_processed=random.choice([True, False]),
            )

            self.stdout.write(f"  ✓ Создан email: {email.subject[:30]}...")

    def generate_inn(self):
        """Генерирует случайный ИНН."""
        # Простая генерация 10-значного ИНН
        inn = "".join([str(random.randint(0, 9)) for _ in range(10)])

        # Проверяем, не существует ли уже такой ИНН
        while Company.objects.filter(inn=inn).exists():
            inn = "".join([str(random.randint(0, 9)) for _ in range(10)])

        return inn
