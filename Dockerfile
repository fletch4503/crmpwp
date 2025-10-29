FROM python:3.13-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Копируем файлы зависимостей
COPY pyproject.toml ./

# Устанавливаем uv для управления зависимостями
RUN pip install uv

# Устанавливаем зависимости глобально (без виртуального окружения)
RUN uv pip install --system -r pyproject.toml

# Copy project
COPY . .

# Открываем порт 8000 для Django
EXPOSE 8000

# Activate virtual environment and run the application
CMD ["bash", "-c", "source .venv/bin/activate && python manage.py runserver 0.0.0.0:8000"]