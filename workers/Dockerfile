# Dedicated Chromium runtime. Keep this Playwright image version aligned
# with backend/requirements.txt.
FROM mcr.microsoft.com/playwright/python:v1.41.0-jammy

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app

WORKDIR /app

COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/app ./app

CMD ["celery", "-A", "app.worker.celery_app:celery_app", "worker", "--loglevel=INFO", "--concurrency=1", "--prefetch-multiplier=1"]
