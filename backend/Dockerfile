FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Сначала зависимости: этот слой кешируется, пока requirements.txt не менялся
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Приложение и миграции
COPY alembic.ini .
COPY alembic ./alembic
COPY app ./app

# Запускаем не от root
RUN useradd --system --uid 10001 --no-create-home appuser
USER appuser

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
