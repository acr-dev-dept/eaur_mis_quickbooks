from celery import Celery
from celery.schedules import crontab
import os
from dotenv import load_dotenv

load_dotenv()

celery = Celery(
    'my_app',
    broker=os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/0'),
    backend=os.getenv('CELERY_RESULT_BACKEND', 'redis://localhost:6379/1'),
    include=['application.config_files.tasks']
)

# Autodiscover tasks
celery.autodiscover_tasks([
    'application',
    'application.config_files'
])

celery.conf.beat_schedule = {
    'sync_applicants_every_5_minutes': {
        'task': 'application.config_files.tasks.bulk_sync_applicants_task',
        'schedule': crontab(minute='*/1'), # at 00
    }
}

def make_celery(app):
    celery.conf.update(app.config)
    return celery
