import logging
from datetime import datetime, timedelta
from django.utils import timezone
from celery import shared_task
from exchangelib import Credentials, Account, Configuration, DELEGATE
from exchangelib.errors import ErrorNonExistentMailbox, ErrorAccessDenied

from .models import EmailCredentials, EmailMessage, EmailAttachment, EmailSyncLog
from .utils import EmailParser

logger = logging.getLogger(__name__)


@shared_task(bind=True)
def sync_user_emails(self, user_id, credentials_id):
    """
    Синхронизация email для пользователя.
    """
    try:
        credentials = EmailCredentials.objects.get(
            id=credentials_id, user_id=user_id, is_active=True
        )
    except EmailCredentials.DoesNotExist:
        logger.error(f"Credentials not found: {credentials_id}")
        return

    # Создаем лог синхронизации
    sync_log = EmailSyncLog.objects.create(
        credentials=credentials, started_at=timezone.now()
    )

    try:
        # Подключаемся к Exchange
        creds = Credentials(
            username=credentials.username, password=credentials.password
        )

        config = Configuration(server=credentials.server, credentials=creds)

        account = Account(
            primary_smtp_address=credentials.email,
            config=config,
            autodiscover=False,
            access_type=DELEGATE,
        )

        # Получаем непрочитанные сообщения за последний период
        since_date = credentials.last_sync or (timezone.now() - timedelta(days=30))

        # Фильтруем по дате
        messages = account.inbox.filter(datetime_received__gte=since_date).order_by(
            "-datetime_received"
        )[
            :100
        ]  # Ограничение для производительности

        emails_processed = 0
        emails_skipped = 0
        attachments_downloaded = 0

        for message in messages:
            try:
                # Проверяем, не обрабатывали ли уже это сообщение
                existing_email = EmailMessage.objects.filter(
                    user=credentials.user, message_id=message.message_id
                ).first()

                if existing_email:
                    emails_skipped += 1
                    continue

                # Создаем EmailMessage
                email_obj = EmailMessage.objects.create(
                    user=credentials.user,
                    credentials=credentials,
                    message_id=message.message_id,
                    uid=getattr(message, "uid", ""),
                    subject=message.subject or "",
                    sender=str(message.sender.email_address),
                    recipients_to=[str(r.email_address) for r in message.to_recipients],
                    recipients_cc=[str(r.email_address) for r in message.cc_recipients],
                    recipients_bcc=[
                        str(r.email_address) for r in message.bcc_recipients
                    ],
                    body_text=message.text_body or "",
                    body_html=message.body or "",
                    received_at=message.datetime_received,
                    sent_at=getattr(message, "datetime_sent", None),
                    size=getattr(message, "size", 0),
                    is_read=getattr(message, "is_read", False),
                    has_attachments=len(message.attachments) > 0,
                )

                # Обрабатываем вложения
                for attachment in message.attachments:
                    try:
                        # Скачиваем вложение
                        attachment_content = attachment.content

                        # Сохраняем в файл (упрощенная версия)
                        # В реальном проекте нужно сохранить в MEDIA_ROOT
                        file_path = f"emails/{credentials.user.id}/{email_obj.id}/{attachment.name}"

                        # Создаем EmailAttachment
                        EmailAttachment.objects.create(
                            email=email_obj,
                            filename=attachment.name,
                            content_type=getattr(
                                attachment, "content_type", "application/octet-stream"
                            ),
                            size=len(attachment_content) if attachment_content else 0,
                            file_path=file_path,
                            content_id=getattr(attachment, "content_id", ""),
                            is_inline=getattr(attachment, "is_inline", False),
                            is_downloaded=True,
                        )

                        attachments_downloaded += 1

                    except Exception as e:
                        logger.error(
                            f"Error downloading attachment {attachment.name}: {e}"
                        )
                        EmailAttachment.objects.create(
                            email=email_obj,
                            filename=attachment.name,
                            content_type=getattr(
                                attachment, "content_type", "application/octet-stream"
                            ),
                            size=0,
                            file_path="",
                            download_errors=str(e),
                        )

                # Обрабатываем email (парсинг, создание проектов и т.д.)
                process_email_message.delay(email_obj.id)

                emails_processed += 1

            except Exception as e:
                logger.error(f"Error processing message {message.message_id}: {e}")
                sync_log.errors.append(f"Message {message.message_id}: {str(e)}")
                continue

        # Обновляем статистику
        sync_log.emails_fetched = len(messages)
        sync_log.emails_processed = emails_processed
        sync_log.emails_skipped = emails_skipped
        sync_log.attachments_downloaded = attachments_downloaded
        sync_log.status = "success" if emails_processed > 0 else "partial"
        sync_log.completed_at = timezone.now()
        sync_log.duration_seconds = (
            sync_log.completed_at - sync_log.started_at
        ).seconds
        sync_log.save()

        # Обновляем время последней синхронизации
        credentials.last_sync = timezone.now()
        credentials.total_emails_processed += emails_processed
        credentials.save()

        logger.info(
            f"Email sync completed for {credentials.email}: {emails_processed} processed"
        )

    except (ErrorNonExistentMailbox, ErrorAccessDenied) as e:
        error_msg = f"Exchange connection error: {e}"
        logger.error(error_msg)
        sync_log.status = "failed"
        sync_log.errors.append(error_msg)
        sync_log.completed_at = timezone.now()
        sync_log.save()

        # Обновляем статус учетных данных
        credentials.last_error = error_msg
        credentials.last_error_time = timezone.now()
        credentials.save()

    except Exception as e:
        error_msg = f"Unexpected error during email sync: {e}"
        logger.error(error_msg)
        sync_log.status = "failed"
        sync_log.errors.append(error_msg)
        sync_log.completed_at = timezone.now()
        sync_log.save()


@shared_task(bind=True)
def process_email_message(self, email_id):
    """
    Обработка отдельного email сообщения.
    """
    try:
        email = EmailMessage.objects.get(id=email_id)
    except EmailMessage.DoesNotExist:
        logger.error(f"Email not found: {email_id}")
        return

    try:
        parser = EmailParser()

        # Парсим ИНН
        inn = parser.extract_inn(email.body_text + " " + email.body_html)
        if inn:
            email.parsed_inn = inn

        # Парсим номер проекта
        project_number = parser.extract_project_number(
            email.subject, email.body_text + " " + email.body_html
        )
        if project_number:
            email.parsed_project_number = project_number

        # Парсим контакты
        contacts = parser.extract_contacts(email.body_text + " " + email.body_html)
        if contacts:
            email.parsed_contacts = contacts

        # Ищем или создаем связанные объекты
        if email.parsed_inn:
            # Ищем компанию по ИНН
            from companies.models import Company

            company = Company.objects.filter(
                user=email.user, inn=email.parsed_inn, is_active=True
            ).first()
            if company:
                email.related_company = company

        # Проверяем правила обработки
        from .models import EmailProcessingRule

        rules = EmailProcessingRule.objects.filter(
            user=email.user, is_active=True
        ).order_by("priority")

        for rule in rules:
            if rule.matches_email(email):
                # Применяем действия правила
                if rule.auto_create_project:
                    create_project_from_email.delay(email.id)

                if rule.auto_create_contact and email.parsed_contacts:
                    create_contacts_from_email.delay(email.id, email.parsed_contacts)

                if rule.mark_as_important:
                    email.is_important = True

                break  # Применяем только первое подходящее правило

        email.is_processed = True
        email.save()

        logger.info(f"Email processed: {email.subject}")

    except Exception as e:
        logger.error(f"Error processing email {email_id}: {e}")
        email.processing_errors.append(str(e))
        email.save()


@shared_task(bind=True)
def create_project_from_email(self, email_id):
    """
    Создание проекта из email.
    """
    try:
        email = EmailMessage.objects.get(id=email_id)
    except EmailMessage.DoesNotExist:
        logger.error(f"Email not found: {email_id}")
        return

    try:
        from projects.models import Project

        # Проверяем, не создан ли уже проект для этого email
        existing_project = Project.objects.filter(
            user=email.user, source_email_id=email.message_id
        ).first()

        if existing_project:
            logger.info(f"Project already exists for email {email_id}")
            return

        # Создаем проект
        project = Project.objects.create(
            user=email.user,
            title=email.subject,
            description=f"Проект создан из email от {email.sender}\n\n{email.body_preview}",
            inn=email.parsed_inn,
            project_number=email.parsed_project_number,
            source_email_id=email.message_id,
            tags=["email_auto"],
        )

        # Связываем с компанией
        if email.related_company:
            project.company = email.related_company
            project.save()

        # Создаем запись в истории email проекта
        from projects.models import ProjectEmail

        ProjectEmail.objects.create(
            project=project,
            message_id=email.message_id,
            subject=email.subject,
            sender=email.sender,
            recipients=email.all_recipients,
            body=email.body_text or email.body_html,
            received_at=email.received_at,
            has_attachments=email.has_attachments,
            attachments_count=email.attachments.count(),
            parsed_inn=email.parsed_inn,
            parsed_project_number=email.parsed_project_number,
            parsed_contacts=email.parsed_contacts,
        )

        # Связываем email с проектом
        email.related_project = project
        email.save()

        logger.info(f"Project created from email: {project.title}")

    except Exception as e:
        logger.error(f"Error creating project from email {email_id}: {e}")


@shared_task(bind=True)
def create_contacts_from_email(self, email_id, contacts_data):
    """
    Создание контактов из email.
    """
    try:
        email = EmailMessage.objects.get(id=email_id)
    except EmailMessage.DoesNotExist:
        logger.error(f"Email not found: {email_id}")
        return

    try:
        from contacts.models import Contact

        for contact_data in contacts_data:
            # Проверяем, существует ли уже контакт
            existing_contact = Contact.objects.filter(
                user=email.user, email=contact_data.get("email", "")
            ).first()

            if existing_contact:
                continue

            # Создаем контакт
            Contact.objects.create(
                user=email.user,
                first_name=contact_data.get("first_name", ""),
                last_name=contact_data.get("last_name", ""),
                email=contact_data.get("email", ""),
                phone=contact_data.get("phone", ""),
                tags=["email_auto"],
            )

        logger.info(f"Contacts created from email {email_id}")

    except Exception as e:
        logger.error(f"Error creating contacts from email {email_id}: {e}")


@shared_task(bind=True)
def sync_all_user_emails(self):
    """
    Синхронизация email для всех активных пользователей.
    """
    active_credentials = EmailCredentials.objects.filter(is_active=True)

    for credentials in active_credentials:
        # Проверяем, не пора ли синхронизировать
        if credentials.last_sync:
            time_diff = timezone.now() - credentials.last_sync
            if time_diff.total_seconds() < (credentials.sync_interval * 60):
                continue  # Еще не время

        # Запускаем синхронизацию
        sync_user_emails.delay(credentials.user.id, credentials.id)

    logger.info(f"Email sync scheduled for {active_credentials.count()} users")
