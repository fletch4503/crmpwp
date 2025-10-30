import re
import logging
from typing import List, Dict, Optional, Any

logger = logging.getLogger(__name__)


class EmailParser:
    """
    Утилита для парсинга email сообщений.
    """

    # Регулярные выражения для поиска ИНН
    INN_PATTERNS = [
        r"\b\d{10}\b",  # 10 цифр
        r"\b\d{12}\b",  # 12 цифр
        r"ИНН[:\s]*(\d{10,12})",  # ИНН: 1234567890
        r"inn[:\s]*(\d{10,12})",  # inn: 1234567890
        r"ИНН\s*организации[:\s]*(\d{10,12})",  # ИНН организации: 1234567890
    ]

    # Регулярные выражения для поиска номеров проектов
    PROJECT_NUMBER_PATTERNS = [
        r"\b(?:проект|project|пр)\s*[№#]?\s*([A-Z0-9\-]+)\b",
        r"\b([A-Z]{2,}\-\d{2,})\b",  # Формат типа PR-001
        r"\b(\d{4}\-[A-Z]{2,}\-\d{2,})\b",  # Формат типа 2024-PR-01
        r"номер\s*проекта[:\s]*([A-Z0-9\-]+)",
        r"project\s*number[:\s]*([A-Z0-9\-]+)",
    ]

    # Регулярные выражения для поиска контактов
    CONTACT_PATTERNS = [
        r"([A-Za-zА-Яа-яЁё\s]+)\s*<([^>]+)>",  # Имя <email>
        r"([A-Za-zА-Яа-яЁё\s]+)\s*\(([^)]+)\)",  # Имя (email)
        r"email[:\s]*([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})",
        r"телефон[:\s]*([\+\d\s\-\(\)]+)",
        r"phone[:\s]*([\+\d\s\-\(\)]+)",
    ]

    def extract_inn(self, text: str) -> Optional[str]:
        """
        Извлекает ИНН из текста.
        """
        if not text:
            return None

        for pattern in self.INN_PATTERNS:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                inn = match if isinstance(match, str) else match
                if self._validate_inn(inn):
                    return inn

        return None
        """
        Извлекает ИНН из текста.
        """
        if not text:
            return None

        for pattern in self.INN_PATTERNS:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                inn = match if isinstance(match, str) else match
                if self._validate_inn(inn):
                    return inn

        return None

    def extract_project_number(self, subject: str, body: str) -> Optional[str]:
        """
        Извлекает номер проекта из темы и тела письма.
        """
        text = f"{subject} {body}"

        for pattern in self.PROJECT_NUMBER_PATTERNS:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                # Возвращаем первый найденный номер
                return str(matches[0])

        return None

    def extract_contacts(self, text: str) -> List[Dict[str, str]]:
        """
        Извлекает контактную информацию из текста.
        """
        contacts = []

        # Ищем email адреса
        email_pattern = r"\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b"
        emails = re.findall(email_pattern, text)

        # Ищем телефонные номера
        phone_pattern = r"[\+\d\s\-\(\)]{7,}"
        phones = re.findall(phone_pattern, text)

        # Ищем имена
        name_pattern = r"\b([A-ZА-Я][a-zа-яё]+(?:\s+[A-ZА-Я][a-zа-яё]+)*)\b"
        re.findall(name_pattern, text)

        # Создаем контакты на основе найденных данных
        for email in emails:
            contact = {"email": email}

            # Пытаемся найти имя для этого email
            # Ищем паттерны типа "Имя <email>" или "Имя (email)"
            name_email_pattern = (
                rf"([A-Za-zА-Яа-яЁё\s]+)\s*[<(]\s*{re.escape(email)}\s*[>)]"
            )
            name_match = re.search(name_email_pattern, text, re.IGNORECASE)
            if name_match:
                full_name = name_match.group(1).strip()
                name_parts = full_name.split()
                if len(name_parts) >= 2:
                    contact["first_name"] = name_parts[0]
                    contact["last_name"] = " ".join(name_parts[1:])
                else:
                    contact["first_name"] = full_name

            contacts.append(contact)

        # Добавляем контакты без email, но с телефонами
        for phone in phones:
            phone_clean = re.sub(r"[^\+\d]", "", phone)
            if len(phone_clean) >= 7:
                # Проверяем, не добавлен ли уже этот контакт
                existing = next(
                    (c for c in contacts if c.get("phone") == phone_clean), None
                )
                if not existing:
                    contact = {"phone": phone_clean}

                    # Пытаемся найти имя для этого телефона
                    phone_name_pattern = (
                        rf"([A-Za-zА-Яа-яЁё\s]+)\s*[:\-]?\s*{re.escape(phone)}"
                    )
                    name_match = re.search(phone_name_pattern, text, re.IGNORECASE)
                    if name_match:
                        full_name = name_match.group(1).strip()
                        name_parts = full_name.split()
                        if len(name_parts) >= 2:
                            contact["first_name"] = name_parts[0]
                            contact["last_name"] = " ".join(name_parts[1:])
                        else:
                            contact["first_name"] = full_name

                    contacts.append(contact)

        return contacts

    def _validate_inn(self, inn: str) -> bool:
        """
        Проверяет корректность ИНН.
        """
        if not inn or not inn.isdigit():
            return False

        length = len(inn)
        if length not in [10, 12]:
            return False

        # Простая проверка контрольных цифр
        try:
            digits = [int(d) for d in inn]

            if length == 10:  # Для юридических лиц
                weights = [2, 4, 10, 3, 5, 9, 4, 6, 8]
                control_sum = sum(d * w for d, w in zip(digits[:9], weights))
                control_digit = control_sum % 11 % 10
                return control_digit == digits[9]

            elif length == 12:  # Для физических лиц
                # Проверка первой контрольной цифры
                weights1 = [7, 2, 4, 10, 3, 5, 9, 4, 6, 8]
                control_sum1 = sum(d * w for d, w in zip(digits[:10], weights1))
                control_digit1 = control_sum1 % 11 % 10
                if control_digit1 != digits[10]:
                    return False

                # Проверка второй контрольной цифры
                weights2 = [3, 7, 2, 4, 10, 3, 5, 9, 4, 6, 8]
                control_sum2 = sum(d * w for d, w in zip(digits[:11], weights2))
                control_digit2 = control_sum2 % 11 % 10
                return control_digit2 == digits[11]

        except (ValueError, IndexError):
            return False

        return True


class EmailProcessor:
    """
    Процессор для обработки email сообщений.
    """

    def __init__(self):
        self.parser = EmailParser()

    def process_email(self, email_message: Any) -> Dict[str, Any]:
        """
        Обрабатывает email сообщение и возвращает результаты парсинга.
        """
        results: Dict[str, object] = {
            "parsed_inn": None,
            "parsed_project_number": None,
            "parsed_contacts": [],
            "suggested_company": None,
            "suggested_project": None,
            "processing_errors": [],
        }

        try:
            # Парсим ИНН
            full_text = f"{email_message.subject} {email_message.body_text} {email_message.body_html}"
            results["parsed_inn"] = self.parser.extract_inn(full_text)

            # Парсим номер проекта
            results["parsed_project_number"] = self.parser.extract_project_number(
                email_message.subject,
                f"{email_message.body_text} {email_message.body_html}",
            )

            # Парсим контакты
            results["parsed_contacts"] = self.parser.extract_contacts(full_text)

            # Предлагаем компанию на основе ИНН
            if results["parsed_inn"]:
                from companies.models import Company

                company = Company.objects.filter(
                    inn=results["parsed_inn"], is_active=True
                ).first()
                if company:
                    results["suggested_company"] = company

            # Предлагаем проект на основе номера
            if results["parsed_project_number"]:
                from projects.models import Project

                project = Project.objects.filter(
                    project_number=results["parsed_project_number"], is_active=True
                ).first()
                if project:
                    results["suggested_project"] = project

        except Exception as e:
            logger.error(
                f"Error processing email {getattr(email_message, 'id', 'unknown')}: {e}"
            )
            processing_errors = results["processing_errors"]
            if isinstance(processing_errors, list):
                processing_errors.append(str(e))

        return results

    def create_project_from_email(self, email_message: Any, user: Any) -> Optional[Any]:
        """
        Создает проект на основе email сообщения.
        """
        try:
            from projects.models import Project

            # Проверяем, не существует ли уже проект
            existing = Project.objects.filter(
                user=user, source_email_id=email_message.message_id
            ).first()

            if existing:
                return existing

            # Создаем проект
            project = Project.objects.create(
                user=user,
                title=email_message.subject,
                description=f"Проект создан из email от {email_message.sender}",
                inn=email_message.parsed_inn,
                project_number=email_message.parsed_project_number,
                source_email_id=email_message.message_id,
                tags=["email_auto"],
            )

            return project

        except Exception as e:
            logger.error(f"Error creating project from email: {e}")
            return None
        """
        Создает проект на основе email сообщения.
        """
        try:
            from projects.models import Project

            # Проверяем, не существует ли уже проект
            existing = Project.objects.filter(
                user=user, source_email_id=email_message.message_id
            ).first()

            if existing:
                return existing

            # Создаем проект
            project = Project.objects.create(
                user=user,
                title=email_message.subject,
                description=f"Проект создан из email от {email_message.sender}",
                inn=email_message.parsed_inn,
                project_number=email_message.parsed_project_number,
                source_email_id=email_message.message_id,
                tags=["email_auto"],
            )

            return project

        except Exception as e:
            logger.error(f"Error creating project from email: {e}")
            return None

    def create_contacts_from_email(self, email_message: Any, user: Any) -> List[Any]:
        """
        Создает контакты на основе email сообщения.
        """
        created_contacts = []

        try:
            from contacts.models import Contact

            for contact_data in email_message.parsed_contacts:
                # Проверяем, существует ли контакт
                existing = Contact.objects.filter(
                    user=user, email=contact_data.get("email", "")
                ).first()

                if existing:
                    continue

                # Создаем контакт
                contact = Contact.objects.create(
                    user=user,
                    first_name=contact_data.get("first_name", ""),
                    last_name=contact_data.get("last_name", ""),
                    email=contact_data.get("email", ""),
                    phone=contact_data.get("phone", ""),
                    tags=["email_auto"],
                )

                created_contacts.append(contact)

        except Exception as e:
            logger.error(f"Error creating contacts from email: {e}")

        return created_contacts
        """
        Создает контакты на основе email сообщения.
        """
        created_contacts = []

        try:
            from contacts.models import Contact

            for contact_data in email_message.parsed_contacts:
                # Проверяем, существует ли контакт
                existing = Contact.objects.filter(
                    user=user, email=contact_data.get("email", "")
                ).first()

                if existing:
                    continue

                # Создаем контакт
                contact = Contact.objects.create(
                    user=user,
                    first_name=contact_data.get("first_name", ""),
                    last_name=contact_data.get("last_name", ""),
                    email=contact_data.get("email", ""),
                    phone=contact_data.get("phone", ""),
                    tags=["email_auto"],
                )

                created_contacts.append(contact)

        except Exception as e:
            logger.error(f"Error creating contacts from email: {e}")

        return created_contacts
