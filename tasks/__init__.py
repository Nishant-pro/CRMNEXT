from celery import Celery
from config import Config

celery = Celery(__name__,
                broker=Config.CELERY_BROKER_URL,
                backend=Config.CELERY_RESULT_BACKEND)
celery.conf.update(task_serializer='json',
                   result_serializer='json',
                   accept_content=['json'],
                   timezone='Europe/London',
                   enable_utc=True)
