# ==============================================
# Dockerfile для AI диетолога 3.0
# Многоступенчатая сборка для Amvera
# ==============================================

# Этап 1: Базовый образ для сборки
FROM python:3.11-slim-bookworm as builder

# Установка системных зависимостей
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Создание виртуального окружения
RUN python -m venv /opt/venv

# Активация виртуального окружения
ENV PATH="/opt/venv/bin:$PATH"

# Копирование и установка зависимостей
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ==============================================
# Этап 2: Финальный образ
# ==============================================
FROM python:3.11-slim-bookworm as runtime

# Установка системных зависимостей для runtime
RUN apt-get update && apt-get install -y \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Создание пользователя и группы для безопасности
RUN groupadd -r aibot && useradd -r -g aibot aibot

# Создание рабочей директории
WORKDIR /app

# Копирование виртуального окружения из builder
COPY --from=builder /opt/venv /opt/venv

# Копирование исходного кода
COPY . .

# Настройка прав доступа
RUN chown -R aibot:aibot /app && \
    chmod -R 755 /app

# Переключение на непривилегированного пользователя
USER aibot

# Активация виртуального окружения
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONPATH="/app" \
    PYTHONUNBUFFERED="1" \
    PYTHONDONTWRITEBYTECODE="1"

# Переменные окружения по умолчанию
ENV ENVIRONMENT="production" \
    PORT="8080"

# Открытие порта для вебхуков
EXPOSE 8080

# Команда запуска приложения
CMD ["python", "main.py"]

# ==============================================
# МЕТКИ ДЛЯ Amvera
# ==============================================
LABEL org.opencontainers.image.title="AI Diet Bot 3.0" \
      org.opencontainers.image.description="Telegram bot for personalized meal plans generation" \
      org.opencontainers.image.version="3.0.0" \
      org.opencontainers.image.vendor="Your Company" \
      org.opencontainers.image.licenses="MIT" \
      org.opencontainers.image.source="https://github.com/your-username/ai-diet-bot"

# ==============================================
# HEALTHCHECK (опционально для Amvera)
# ==============================================
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1