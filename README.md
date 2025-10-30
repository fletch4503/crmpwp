# CRM Pro - Корпоративная CRM система

[![CI/CD Pipeline](https://github.com/your-username/crmpwp/actions/workflows/ci-cd.yml/badge.svg)](https://github.com/your-username/crmpwp/actions/workflows/ci-cd.yml)
[![Code Coverage](https://codecov.io/gh/your-username/crmpwp/branch/main/graph/badge.svg)](https://codecov.io/gh/your-username/crmpwp)
[![Docker Image](https://img.shields.io/badge/docker-ready-blue.svg)](https://hub.docker.com)
[![Python 3.13](https://img.shields.io/badge/python-3.13-blue.svg)](https://www.python.org/)
[![Django 5.2](https://img.shields.io/badge/django-5.2-green.svg)](https://www.djangoproject.com/)

Полнофункциональная CRM система на Django с современным стеком технологий для управления контактами, компаниями, проектами и email интеграцией.

## 🚀 Возможности

### ✅ Основной функционал

- **Система аутентификации** на базе allauth (регистрация, логин, логаут, профиль, мягкое удаление)
- **Расширенная модель пользователя** (фото, дата рождения, телефон, IP, верификация)
- **RBAC система прав** (роли + объектные разрешения + токены доступа)
- **CRUD операции** для всех бизнес-объектов
- **API на DRF** для всех приложений
- **Django Admin** для администраторов
- **Фронтенд** с DaisyUI, HTMX и Bootstrap
- **WebSockets** для real-time обновлений
- **Celery** для фоновых задач

### 📊 Бизнес-объекты

- **Контакты** - управление контактами клиентов и поставщиков
- **Компании** - карточки компаний с ИНН и финансовыми данными
- **Проекты** - управление проектными запросами с историей переписок
- **Email интеграция** - синхронизация с Exchange и автоматический парсинг

## 🛠 Технологии

### Бэкенд

- **Python 3.13**
- **Django 5.2** с Django REST Framework
- **PostgreSQL** - основная база данных
- **Redis** - кеш и сессии
- **RabbitMQ** - брокер сообщений для Celery
- **Channels** - WebSockets
- **Celery** - фоновые задачи

### Фронтенд

- **DaisyUI** - компоненты UI
- **HTMX** - динамические обновления
- **Bootstrap** - базовые стили

### DevOps & Качество

- **Docker & Docker Compose** - контейнеризация
- **uv** - менеджер зависимостей
- **GitHub Actions** - CI/CD
- **pytest** - тестирование
- **Black, isort, flake8, mypy** - качество кода

## 📋 Предварительные требования

- Docker и Docker Compose
- Python 3.13+ (для локальной разработки)
- uv package manager

## 🚀 Быстрый старт

### 1. Клонирование репозитория

```bash
git clone https://github.com/fletch4503/crmpwp.git
cd crmpwp
```

### 2. Запуск с Docker Compose

```bash
# Сборка и запуск всех сервисов
docker-compose up --build

# Или в фоне
docker-compose up -d --build
```

### 3. Инициализация данных

```bash
# Войти в контейнер приложения
docker-compose exec web bash

# Создать миграции
python manage.py migrate

# Сгенерировать тестовые данные
python manage.py generate_test_data

# Создать суперпользователя
python manage.py createsuperuser
```

### 4. Доступ к приложению

- **Веб-интерфейс**: http://localhost:8000
- **Django Admin**: http://localhost:8000/admin/
- **API документация**: http://localhost:8000/api/
- **RabbitMQ**: http://localhost:15672 (guest/guest)
- **Health check**: http://localhost:8000/health/

## 🔧 Локальная разработка

### Установка зависимостей
```bash
# Установка uv (если не установлен)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Синхронизация зависимостей
uv sync

# Активация виртуального окружения
source .venv/bin/activate  # Linux/Mac
# или
.venv\Scripts\activate     # Windows
```

### Настройка переменных окружения
Создайте файл `.env` в корне проекта:
```env
SECRET_KEY=your-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Database
DB_NAME=crm_db
DB_USER=crm_user
DB_PASSWORD=crm_password
DB_HOST=localhost
DB_PORT=5432

# Redis
REDIS_URL=redis://localhost:6379/0

# Celery
CELERY_BROKER_URL=amqp://guest:guest@localhost:5672//
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# Email (для Exchange интеграции)
EMAIL_HOST=your-exchange-server.com
EMAIL_PORT=993
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@company.com
EMAIL_HOST_PASSWORD=your-password
```

### Запуск сервисов
```bash
# В отдельных терминалах:

# 1. PostgreSQL и Redis (через Docker)
docker run -d -p 5432:5432 -e POSTGRES_DB=crm_db -e POSTGRES_USER=crm_user -e POSTGRES_PASSWORD=crm_password postgres:15
docker run -d -p 6379:6379 redis:7-alpine
docker run -d -p 5672:5672 -p 15672:15672 rabbitmq:3-management-alpine

# 2. Django сервер
uv run python manage.py runserver

# 3. Celery worker
uv run celery -A crm worker --loglevel=info

# 4. Celery beat (опционально)
uv run celery -A crm beat --loglevel=info --scheduler django_celery_beat.schedulers:DatabaseScheduler
```

## 🧪 Тестирование

### Запуск тестов
```bash
# Все тесты
uv run pytest

# С покрытием
uv run pytest --cov=crm --cov-report=html

# Конкретное приложение
uv run pytest tests/test_users.py

# С verbose выводом
uv run pytest -v
```

### Генерация тестовых данных
```bash
# По умолчанию (10 пользователей, 20 компаний, 50 контактов, 30 проектов, 100 email)
python manage.py generate_test_data

# Кастомные количества
python manage.py generate_test_data --users 5 --companies 10 --contacts 25 --projects 15 --emails 50
```

## 📚 API Документация

### Использование Postman коллекции
1. Импортируйте `postman_collection.json` в Postman
2. Настройте переменную `base_url` (по умолчанию `http://localhost:8000`)
3. Выполняйте запросы последовательно, начиная с аутентификации

### Основные API endpoints

#### Аутентификация
- `POST /api/auth/login/` - Вход в систему
- `POST /api/auth/logout/` - Выход из системы
- `GET /api/auth/me/` - Информация о текущем пользователе

#### Пользователи
- `GET /api/users/` - Список пользователей
- `POST /api/users/` - Создание пользователя
- `GET /api/users/{id}/` - Детали пользователя
- `PATCH /api/users/{id}/` - Обновление пользователя

#### Контакты
- `GET /api/contacts/` - Список контактов
- `POST /api/contacts/` - Создание контакта
- `GET /api/contacts/{id}/` - Детали контакта
- `PUT /api/contacts/{id}/` - Обновление контакта
- `DELETE /api/contacts/{id}/` - Удаление контакта

#### Компании
- `GET /api/companies/` - Список компаний
- `POST /api/companies/` - Создание компании
- `GET /api/companies/{id}/` - Детали компании

#### Проекты
- `GET /api/projects/` - Список проектов
- `POST /api/projects/` - Создание проекта
- `GET /api/projects/{id}/` - Детали проекта

#### Email
- `GET /api/emails/messages/` - Список email сообщений
- `POST /api/emails/credentials/` - Настройка email учетных данных
- `POST /api/emails/sync/` - Синхронизация email

## 🏗 Архитектура

### Структура проекта
```
crmpwp/
├── crm/                    # Основной проект Django
│   ├── settings.py        # Настройки
│   ├── urls.py           # Маршруты
│   ├── asgi.py           # ASGI конфигурация
│   └── celery.py         # Celery конфигурация
├── users/                 # Приложение пользователей
├── contacts/              # Приложение контактов
├── companies/             # Приложение компаний
├── projects/              # Приложение проектов
├── emails/                # Приложение email интеграции
├── tests/                 # Тесты
├── static/                # Статические файлы
├── media/                 # Медиа файлы
├── templates/             # Шаблоны
├── docker-compose.yml     # Docker Compose
├── Dockerfile            # Docker образ
└── pyproject.toml        # Зависимости (uv)
```

### База данных
См. [db_readme.md](db_readme.md) для детального описания схемы БД и ER-диаграммы.

## 🔒 Безопасность

- **RBAC система** с объектными разрешениями
- **Верификация email и телефона**
- **Ограниченные токены доступа**
- **CORS защита**
- **SQL инъекции** - предотвращены Django ORM
- **XSS защита** - встроена в Django templates
- **CSRF защита** - включена по умолчанию

## 📈 Мониторинг

### Health Checks
- `GET /health/` - Общий health check
- Статус БД, Redis, RabbitMQ

### Логирование
- Структурированные логи в JSON формате
- Ротация логов
- Мониторинг ошибок

## 🚀 Развертывание

### Production окружение
```bash
# Сборка production образа
docker build -t crmpwp:latest .

# Запуск через docker-compose
docker-compose -f docker-compose.prod.yml up -d

# Или через Kubernetes
kubectl apply -f k8s/
```

### Переменные окружения для production
```env
DEBUG=False
SECRET_KEY=your-production-secret-key
ALLOWED_HOSTS=your-domain.com,www.your-domain.com
DATABASE_URL=postgresql://user:pass@host:5432/db
REDIS_URL=redis://host:6379/0
CELERY_BROKER_URL=amqp://user:pass@host:5672//
```

## 🤝 Вклад в проект

1. Fork проект
2. Создайте feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit изменения (`git commit -m 'Add some AmazingFeature'`)
4. Push в branch (`git push origin feature/AmazingFeature`)
5. Создайте Pull Request

## 📝 Лицензия

Этот проект лицензирован под MIT License - см. файл [LICENSE](LICENSE) для деталей.

## 📞 Поддержка

- **Issues**: [GitHub Issues](https://github.com/your-username/crmpwp/issues)
- **Discussions**: [GitHub Discussions](https://github.com/your-username/crmpwp/discussions)
- **Email**: support@crmpro.com

## 🙏 Благодарности

- Django community за отличный фреймворк
- Всех контрибьюторов и пользователей
- Open source сообщество

---

**CRM Pro** - мощная и гибкая CRM система для современных бизнесов! 🚀