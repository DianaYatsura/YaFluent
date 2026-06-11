from celery import Celery

from core.config import settings

celery_app = Celery("tasks", broker=settings.REDIS_URL, backend=settings.REDIS_URL)


@celery_app.task
def send_morning_reminder():
    pass
