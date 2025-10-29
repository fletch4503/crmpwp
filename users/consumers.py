import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser
from django.utils import timezone


class NotificationConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer для уведомлений пользователя.
    """

    async def connect(self):
        self.user = self.scope["user"]

        if isinstance(self.user, AnonymousUser):
            await self.close()
            return

        # Создаем группу для пользователя
        self.group_name = f"user_{self.user.id}"

        # Присоединяемся к группе
        await self.channel_layer.group_add(self.group_name, self.channel_name)

        await self.accept()

        # Отправляем приветственное сообщение
        await self.send(
            text_data=json.dumps(
                {
                    "type": "connection_established",
                    "message": f"Connected as {self.user.get_full_name() or self.user.username}",
                    "timestamp": timezone.now().isoformat(),
                }
            )
        )

    async def disconnect(self, close_code):
        # Покидаем группу
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data):
        """
        Обработка входящих сообщений от клиента.
        """
        try:
            data = json.loads(text_data)
            message_type = data.get("type", "")

            if message_type == "ping":
                # Отвечаем на ping
                await self.send(
                    text_data=json.dumps(
                        {"type": "pong", "timestamp": timezone.now().isoformat()}
                    )
                )
            elif message_type == "subscribe":
                # Подписка на дополнительные каналы
                channel = data.get("channel")
                if channel:
                    await self.channel_layer.group_add(channel, self.channel_name)
                    await self.send(
                        text_data=json.dumps(
                            {
                                "type": "subscribed",
                                "channel": channel,
                                "timestamp": timezone.now().isoformat(),
                            }
                        )
                    )

        except json.JSONDecodeError:
            await self.send(
                text_data=json.dumps(
                    {
                        "type": "error",
                        "message": "Invalid JSON format",
                        "timestamp": timezone.now().isoformat(),
                    }
                )
            )

    # Обработчики событий

    async def email_received(self, event):
        """
        Уведомление о новом email.
        """
        await self.send(
            text_data=json.dumps(
                {
                    "type": "email_received",
                    "email_id": event["email_id"],
                    "subject": event["subject"],
                    "sender": event["sender"],
                    "timestamp": event["timestamp"],
                }
            )
        )

    async def project_created(self, event):
        """
        Уведомление о создании проекта.
        """
        await self.send(
            text_data=json.dumps(
                {
                    "type": "project_created",
                    "project_id": event["project_id"],
                    "title": event["title"],
                    "timestamp": event["timestamp"],
                }
            )
        )

    async def contact_created(self, event):
        """
        Уведомление о создании контакта.
        """
        await self.send(
            text_data=json.dumps(
                {
                    "type": "contact_created",
                    "contact_id": event["contact_id"],
                    "name": event["name"],
                    "email": event["email"],
                    "timestamp": event["timestamp"],
                }
            )
        )

    async def task_completed(self, event):
        """
        Уведомление о завершении фоновой задачи.
        """
        await self.send(
            text_data=json.dumps(
                {
                    "type": "task_completed",
                    "task_id": event["task_id"],
                    "task_type": event["task_type"],
                    "status": event["status"],
                    "message": event.get("message", ""),
                    "timestamp": event["timestamp"],
                }
            )
        )

    async def system_notification(self, event):
        """
        Системное уведомление.
        """
        await self.send(
            text_data=json.dumps(
                {
                    "type": "system_notification",
                    "level": event["level"],  # info, warning, error
                    "title": event["title"],
                    "message": event["message"],
                    "timestamp": event["timestamp"],
                }
            )
        )


class ProjectConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer для работы с проектами в реальном времени.
    """

    async def connect(self):
        self.user = self.scope["user"]
        self.project_id = self.scope["url_route"]["kwargs"].get("project_id")

        if isinstance(self.user, AnonymousUser):
            await self.close()
            return

        # Проверяем доступ к проекту
        if not await self.can_access_project():
            await self.close()
            return

        # Создаем группу для проекта
        self.group_name = f"project_{self.project_id}"

        await self.channel_layer.group_add(self.group_name, self.channel_name)

        await self.accept()

        await self.send(
            text_data=json.dumps(
                {
                    "type": "project_connected",
                    "project_id": self.project_id,
                    "timestamp": timezone.now().isoformat(),
                }
            )
        )

    async def disconnect(self, close_code):
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    @database_sync_to_async
    def can_access_project(self):
        """
        Проверяет, имеет ли пользователь доступ к проекту.
        """
        try:
            from projects.models import Project

            return Project.objects.filter(
                id=self.project_id, user=self.user, is_active=True
            ).exists()
        except:
            return False

    async def receive(self, text_data):
        """
        Обработка команд от клиента.
        """
        try:
            data = json.loads(text_data)
            command = data.get("command", "")

            if command == "update_status":
                await self.handle_status_update(data)
            elif command == "add_note":
                await self.handle_add_note(data)
            elif command == "ping":
                await self.send(
                    text_data=json.dumps(
                        {"type": "pong", "timestamp": timezone.now().isoformat()}
                    )
                )

        except json.JSONDecodeError:
            await self.send(
                text_data=json.dumps(
                    {"type": "error", "message": "Invalid JSON format"}
                )
            )

    async def handle_status_update(self, data):
        """
        Обработка обновления статуса проекта.
        """
        new_status = data.get("status")
        reason = data.get("reason", "")

        # Обновляем статус через database_sync_to_async
        success = await self.update_project_status(new_status, reason)

        if success:
            # Отправляем обновление всем в группе
            await self.channel_layer.group_send(
                self.group_name,
                {
                    "type": "status_updated",
                    "user": self.user.get_full_name() or self.user.username,
                    "status": new_status,
                    "reason": reason,
                    "timestamp": timezone.now().isoformat(),
                },
            )
        else:
            await self.send(
                text_data=json.dumps(
                    {"type": "error", "message": "Failed to update project status"}
                )
            )

    async def handle_add_note(self, data):
        """
        Обработка добавления заметки.
        """
        title = data.get("title", "").strip()
        content = data.get("content", "").strip()
        note_type = data.get("note_type", "general")
        is_important = data.get("is_important", False)

        if not title or not content:
            await self.send(
                text_data=json.dumps(
                    {"type": "error", "message": "Title and content are required"}
                )
            )
            return

        # Создаем заметку
        note_data = await self.create_project_note(
            title, content, note_type, is_important
        )

        if note_data:
            # Отправляем обновление всем в группе
            await self.channel_layer.group_send(
                self.group_name,
                {
                    "type": "note_added",
                    "note": note_data,
                    "timestamp": timezone.now().isoformat(),
                },
            )
        else:
            await self.send(
                text_data=json.dumps(
                    {"type": "error", "message": "Failed to create note"}
                )
            )

    @database_sync_to_async
    def update_project_status(self, new_status, reason):
        """
        Обновляет статус проекта.
        """
        try:
            from projects.models import Project, ProjectStatusHistory

            project = Project.objects.get(id=self.project_id, user=self.user)

            old_status = project.status
            project.status = new_status
            project.save()

            # Создаем запись в истории
            ProjectStatusHistory.objects.create(
                project=project,
                user=self.user,
                old_status=old_status,
                new_status=new_status,
                reason=reason,
            )

            return True
        except Exception as e:
            print(f"Error updating project status: {e}")
            return False

    @database_sync_to_async
    def create_project_note(self, title, content, note_type, is_important):
        """
        Создает заметку к проекту.
        """
        try:
            from projects.models import ProjectNote

            note = ProjectNote.objects.create(
                project_id=self.project_id,
                user=self.user,
                title=title,
                content=content,
                note_type=note_type,
                is_important=is_important,
            )

            return {
                "id": str(note.id),
                "title": note.title,
                "content": (
                    note.content[:100] + "..."
                    if len(note.content) > 100
                    else note.content
                ),
                "note_type": note.get_note_type_display(),
                "is_important": note.is_important,
                "user": note.user.get_full_name() or note.user.username,
                "created_at": note.created_at.strftime("%d.%m.%Y %H:%M"),
            }
        except Exception as e:
            print(f"Error creating project note: {e}")
            return None

    # Обработчики событий группы

    async def status_updated(self, event):
        """
        Статус проекта обновлен.
        """
        await self.send(
            text_data=json.dumps(
                {
                    "type": "status_updated",
                    "user": event["user"],
                    "status": event["status"],
                    "reason": event["reason"],
                    "timestamp": event["timestamp"],
                }
            )
        )

    async def note_added(self, event):
        """
        Добавлена новая заметка.
        """
        await self.send(
            text_data=json.dumps(
                {
                    "type": "note_added",
                    "note": event["note"],
                    "timestamp": event["timestamp"],
                }
            )
        )

    async def email_linked(self, event):
        """
        Email привязан к проекту.
        """
        await self.send(
            text_data=json.dumps(
                {
                    "type": "email_linked",
                    "email_id": event["email_id"],
                    "subject": event["subject"],
                    "timestamp": event["timestamp"],
                }
            )
        )


class EmailConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer для работы с email в реальном времени.
    """

    async def connect(self):
        self.user = self.scope["user"]

        if isinstance(self.user, AnonymousUser):
            await self.close()
            return

        # Создаем группу для email пользователя
        self.group_name = f"email_user_{self.user.id}"

        await self.channel_layer.group_add(self.group_name, self.channel_name)

        await self.accept()

        await self.send(
            text_data=json.dumps(
                {"type": "email_connected", "timestamp": timezone.now().isoformat()}
            )
        )

    async def disconnect(self, close_code):
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data):
        """
        Обработка команд от клиента.
        """
        try:
            data = json.loads(text_data)
            command = data.get("command", "")

            if command == "mark_read":
                await self.handle_mark_read(data)
            elif command == "toggle_important":
                await self.handle_toggle_important(data)
            elif command == "ping":
                await self.send(
                    text_data=json.dumps(
                        {"type": "pong", "timestamp": timezone.now().isoformat()}
                    )
                )

        except json.JSONDecodeError:
            await self.send(
                text_data=json.dumps(
                    {"type": "error", "message": "Invalid JSON format"}
                )
            )

    async def handle_mark_read(self, data):
        """
        Обработка пометки email как прочитанного.
        """
        email_id = data.get("email_id")

        if not email_id:
            await self.send(
                text_data=json.dumps(
                    {"type": "error", "message": "Email ID is required"}
                )
            )
            return

        success = await self.mark_email_read(email_id)

        if success:
            await self.send(
                text_data=json.dumps(
                    {
                        "type": "email_updated",
                        "email_id": email_id,
                        "action": "marked_read",
                        "timestamp": timezone.now().isoformat(),
                    }
                )
            )
        else:
            await self.send(
                text_data=json.dumps(
                    {"type": "error", "message": "Failed to mark email as read"}
                )
            )

    async def handle_toggle_important(self, data):
        """
        Обработка переключения важности email.
        """
        email_id = data.get("email_id")

        if not email_id:
            await self.send(
                text_data=json.dumps(
                    {"type": "error", "message": "Email ID is required"}
                )
            )
            return

        success, is_important = await self.toggle_email_important(email_id)

        if success:
            await self.send(
                text_data=json.dumps(
                    {
                        "type": "email_updated",
                        "email_id": email_id,
                        "action": "toggled_important",
                        "is_important": is_important,
                        "timestamp": timezone.now().isoformat(),
                    }
                )
            )
        else:
            await self.send(
                text_data=json.dumps(
                    {"type": "error", "message": "Failed to toggle email importance"}
                )
            )

    @database_sync_to_async
    def mark_email_read(self, email_id):
        """
        Помечает email как прочитанный.
        """
        try:
            from emails.models import EmailMessage

            email = EmailMessage.objects.get(id=email_id, user=self.user)
            email.is_read = True
            email.save()
            return True
        except:
            return False

    @database_sync_to_async
    def toggle_email_important(self, email_id):
        """
        Переключает важность email.
        """
        try:
            from emails.models import EmailMessage

            email = EmailMessage.objects.get(id=email_id, user=self.user)
            email.is_important = not email.is_important
            email.save()
            return True, email.is_important
        except:
            return False, False

    # Обработчики событий группы

    async def email_received(self, event):
        """
        Получен новый email.
        """
        await self.send(
            text_data=json.dumps(
                {
                    "type": "email_received",
                    "email_id": event["email_id"],
                    "subject": event["subject"],
                    "sender": event["sender"],
                    "timestamp": event["timestamp"],
                }
            )
        )

    async def sync_completed(self, event):
        """
        Синхронизация email завершена.
        """
        await self.send(
            text_data=json.dumps(
                {
                    "type": "sync_completed",
                    "emails_processed": event["emails_processed"],
                    "status": event["status"],
                    "timestamp": event["timestamp"],
                }
            )
        )
