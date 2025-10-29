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

# Устанавливаем зависимости в систему (без виртуального окружения)
RUN uv pip install --system -r pyproject.toml

# Copy project
COPY . .

# Create logs directory
RUN mkdir -p /app/logs

# Открываем порт 8000 для Django
EXPOSE 8000

# Использовать uv run для запуска без активации venv
CMD ["uv", "run", "python", "manage.py", "runserver", "0.0.0.0:8000"]