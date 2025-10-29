import os
import json
from datetime import datetime, timedelta
from django.core.management import call_command
from django.utils import timezone
from django.contrib.auth import get_user_model
from celery import shared_task
from django.db.models import Count, Q

from emails.models import EmailMessage, EmailSyncLog
from projects.models import Project
from companies.models import Company
from contacts.models import Contact

User = get_user_model()


@shared_task(bind=True)
def generate_daily_reports(self):
    """
    Генерация ежедневных отчетов для пользователей.
    """
    yesterday = timezone.now().date() - timedelta(days=1)

    # Получаем всех активных пользователей
    users = User.objects.filter(is_active=True)

    for user in users:
        try:
            # Статистика за вчера
            emails_yesterday = EmailMessage.objects.filter(
                user=user, received_at__date=yesterday
            )

            projects_created = Project.objects.filter(
                user=user, created_at__date=yesterday
            )

            companies_created = Company.objects.filter(
                user=user, created_at__date=yesterday
            )

            contacts_created = Contact.objects.filter(
                user=user, created_at__date=yesterday
            )

            # Формируем отчет
            report_data = {
                "date": yesterday.isoformat(),
                "emails_received": emails_yesterday.count(),
                "projects_created": projects_created.count(),
                "companies_created": companies_created.count(),
                "contacts_created": contacts_created.count(),
                "emails_with_inn": emails_yesterday.exclude(
                    parsed_inn__isnull=True
                ).count(),
                "emails_processed": emails_yesterday.filter(is_processed=True).count(),
            }

            # Отправляем уведомление пользователю
            from users.signals import send_realtime_notification

            send_realtime_notification(
                user.id,
                "system_notification",
                {
                    "level": "info",
                    "title": "Ежедневный отчет",
                    "message": f'За {yesterday}: {report_data["emails_received"]} email, '
                    f'{report_data["projects_created"]} проектов, '
                    f'{report_data["companies_created"]} компаний, '
                    f'{report_data["contacts_created"]} контактов.',
                },
            )

        except Exception as e:
            print(f"Error generating report for user {user.id}: {e}")

    return "Daily reports generated"


@shared_task(bind=True)
def backup_database(self):
    """
    Создание резервной копии базы данных.
    """
    try:
        # Создаем директорию для бэкапов
        backup_dir = "/app/backups"
        os.makedirs(backup_dir, exist_ok=True)

        # Генерируем имя файла
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = f"{backup_dir}/crm_backup_{timestamp}.sql"

        # Используем pg_dump через shell
        import subprocess

        result = subprocess.run(
            [
                "pg_dump",
                "-h",
                os.getenv("DB_HOST", "db"),
                "-U",
                os.getenv("DB_USER", "crm_user"),
                "-d",
                os.getenv("DB_NAME", "crm_db"),
                "-f",
                backup_file,
                "--no-password",
                "--format=custom",
            ],
            env={"PGPASSWORD": os.getenv("DB_PASSWORD", "crm_password")},
            capture_output=True,
            text=True,
        )

        if result.returncode == 0:
            # Уведомляем администраторов
            admin_users = User.objects.filter(is_superuser=True)

            for admin in admin_users:
                from users.signals import send_realtime_notification

                send_realtime_notification(
                    admin.id,
                    "system_notification",
                    {
                        "level": "info",
                        "title": "Резервная копия создана",
                        "message": f"База данных успешно сохранена: {backup_file}",
                    },
                )

            # Очищаем старые бэкапы (оставляем последние 7)
            cleanup_old_backups.delay(backup_dir, 7)

            return f"Backup created: {backup_file}"
        else:
            raise Exception(f"pg_dump failed: {result.stderr}")

    except Exception as e:
        # Уведомляем администраторов об ошибке
        admin_users = User.objects.filter(is_superuser=True)

        for admin in admin_users:
            from users.signals import send_realtime_notification

            send_realtime_notification(
                admin.id,
                "system_notification",
                {
                    "level": "error",
                    "title": "Ошибка резервного копирования",
                    "message": f"Не удалось создать резервную копию: {str(e)}",
                },
            )

        raise e


@shared_task(bind=True)
def cleanup_old_backups(self, backup_dir, keep_count=7):
    """
    Очистка старых резервных копий.
    """
    try:
        if not os.path.exists(backup_dir):
            return "Backup directory does not exist"

        # Получаем список файлов бэкапа
        backup_files = [
            f
            for f in os.listdir(backup_dir)
            if f.startswith("crm_backup_") and f.endswith(".sql")
        ]

        if len(backup_files) <= keep_count:
            return f"Only {len(backup_files)} backups found, no cleanup needed"

        # Сортируем по дате (новые сначала)
        backup_files.sort(reverse=True)

        # Удаляем старые файлы
        files_to_delete = backup_files[keep_count:]
        deleted_count = 0

        for filename in files_to_delete:
            file_path = os.path.join(backup_dir, filename)
            try:
                os.remove(file_path)
                deleted_count += 1
            except OSError as e:
                print(f"Error deleting {file_path}: {e}")

        return f"Deleted {deleted_count} old backup files"

    except Exception as e:
        print(f"Error cleaning up backups: {e}")
        return f"Cleanup failed: {e}"


@shared_task(bind=True)
def send_weekly_summary(self):
    """
    Отправка еженедельной сводки пользователям.
    """
    week_ago = timezone.now() - timedelta(days=7)

    users = User.objects.filter(is_active=True)

    for user in users:
        try:
            # Статистика за неделю
            weekly_stats = {
                "emails_total": EmailMessage.objects.filter(
                    user=user, received_at__gte=week_ago
                ).count(),
                "projects_total": Project.objects.filter(
                    user=user, created_at__gte=week_ago
                ).count(),
                "companies_total": Company.objects.filter(
                    user=user, created_at__gte=week_ago
                ).count(),
                "contacts_total": Contact.objects.filter(
                    user=user, created_at__gte=week_ago
                ).count(),
                "emails_processed": EmailMessage.objects.filter(
                    user=user, received_at__gte=week_ago, is_processed=True
                ).count(),
                "sync_logs": EmailSyncLog.objects.filter(
                    credentials__user=user, started_at__gte=week_ago
                ).aggregate(
                    total=Count("id"),
                    successful=Count("id", filter=Q(status="success")),
                    failed=Count("id", filter=Q(status="failed")),
                ),
            }

            # Отправляем сводку
            from users.signals import send_realtime_notification

            send_realtime_notification(
                user.id,
                "system_notification",
                {
                    "level": "info",
                    "title": "Еженедельная сводка",
                    "message": f'За неделю: {weekly_stats["emails_total"]} email получено, '
                    f'{weekly_stats["projects_total"]} проектов создано, '
                    f'{weekly_stats["sync_logs"]["successful"]}/{weekly_stats["sync_logs"]["total"]} успешных синхронизаций.',
                },
            )

        except Exception as e:
            print(f"Error sending weekly summary to user {user.id}: {e}")

    return "Weekly summaries sent"


@shared_task(bind=True)
def health_check(self):
    """
    Проверка здоровья системы.
    """
    results = {
        "database": False,
        "redis": False,
        "email_sync": False,
        "timestamp": timezone.now().isoformat(),
    }

    # Проверка базы данных
    try:
        User.objects.count()
        results["database"] = True
    except Exception as e:
        results["database_error"] = str(e)

    # Проверка Redis
    try:
        from django.core.cache import cache

        cache.set("health_check", "ok", 10)
        if cache.get("health_check") == "ok":
            results["redis"] = True
    except Exception as e:
        results["redis_error"] = str(e)

    # Проверка последней синхронизации email
    try:
        last_sync = (
            EmailSyncLog.objects.filter(
                started_at__gte=timezone.now() - timedelta(hours=1)
            )
            .order_by("-started_at")
            .first()
        )

        if last_sync and last_sync.status == "success":
            results["email_sync"] = True
        else:
            results["email_sync"] = False
            results["last_sync_status"] = (
                last_sync.status if last_sync else "no_recent_sync"
            )
    except Exception as e:
        results["email_sync_error"] = str(e)

    # Уведомляем администраторов если есть проблемы
    if not all([results["database"], results["redis"], results["email_sync"]]):
        admin_users = User.objects.filter(is_superuser=True)

        for admin in admin_users:
            from users.signals import send_realtime_notification

            send_realtime_notification(
                admin.id,
                "system_notification",
                {
                    "level": "warning",
                    "title": "Проблемы со здоровьем системы",
                    "message": f'Проверьте статус системы. Database: {results["database"]}, Redis: {results["redis"]}, Email sync: {results["email_sync"]}',
                },
            )

    return results
