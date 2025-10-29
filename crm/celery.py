import os
from celery import Celery
from celery.schedules import crontab

# Set the default Django settings module
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "crm.settings")

app = Celery("crm")

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
app.config_from_object("django.conf:settings", namespace="CELERY")

# Load task modules from all registered Django apps.
app.autodiscover_tasks()

# Configure periodic tasks
app.conf.beat_schedule = {
    "sync-emails-every-15-minutes": {
        "task": "emails.tasks.sync_all_user_emails",
        "schedule": crontab(minute="*/15"),
    },
    "cleanup-expired-tokens-daily": {
        "task": "users.tasks.cleanup_expired_tokens",
        "schedule": crontab(hour=2, minute=0),  # Every day at 2:00 AM
    },
    "generate-daily-reports": {
        "task": "crm.tasks.generate_daily_reports",
        "schedule": crontab(hour=6, minute=0),  # Every day at 6:00 AM
    },
    "backup-database-weekly": {
        "task": "crm.tasks.backup_database",
        "schedule": crontab(day_of_week=0, hour=3, minute=0),  # Every Sunday at 3:00 AM
    },
}

app.conf.timezone = "Europe/Moscow"


@app.task(bind=True)
def debug_task(self):
    print(f"Request: {self.request!r}")
