from celery import Celery

from app.core.config import settings

# Sender-only Celery instance – no workers run in the backend process.
# Tasks are dispatched by name via send_task() so there is no import
# dependency on the worker package.
celery = Celery(
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
)
