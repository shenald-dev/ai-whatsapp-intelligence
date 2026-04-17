import os
from celery import Celery

REDIS_URL = os.getenv("REDIS_URL")
if not REDIS_URL:
    raise ValueError("REDIS_URL environment variable is not set")

celery_app = Celery(
    "whatsapp_workers",
    broker=REDIS_URL,
    backend=REDIS_URL,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)

# This will be called by FastAPI ingest endpoint
@celery_app.task(name="enrich_message", bind=True, max_retries=3)
def enrich_message_task(self, message_id: str):
    from .tasks import process_message
    try:
        return process_message(message_id)
    except Exception as exc:
        raise self.retry(exc=exc, countdown=2 ** self.request.retries)
