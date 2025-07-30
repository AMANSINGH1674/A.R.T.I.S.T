"""
Celery worker configuration for the ARTIST application.
"""

from celery import Celery
import os

from artist.config import settings

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "artist.config.settings")

celery_app = Celery(
    "artist",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["artist.worker.tasks"]
)

celery_app.conf.update(
    task_track_started=True,
    result_expires=3600,  # 1 hour
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)

if __name__ == "__main__":
    celery_app.start()
