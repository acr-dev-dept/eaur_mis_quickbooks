from celery import Celery
from celery.schedules import crontab
import os
from pathlib import Path
from dotenv import load_dotenv

# CRITICAL FIX: Load .env from the correct path
# Get the directory where celery.py is located
basedir = Path(__file__).resolve().parent
env_path = basedir / '.env'

print(f"Looking for .env at: {env_path}")
print(f".env exists: {env_path.exists()}")

# Load the .env file
load_dotenv(dotenv_path=env_path)

# Get the broker URL
broker_url = os.getenv('CELERY_BROKER_URL')
result_backend = os.getenv('CELERY_RESULT_BACKEND')

print(f"CELERY_BROKER_URL from env: {broker_url}")
print(f"CELERY_RESULT_BACKEND from env: {result_backend}")

# Fallback to Redis if not set
if not broker_url:
    broker_url = 'redis://localhost:6379/0'
    print(f"WARNING: CELERY_BROKER_URL not found in .env, using default: {broker_url}")

if not result_backend:
    result_backend = 'redis://localhost:6379/1'
    print(f"WARNING: CELERY_RESULT_BACKEND not found in .env, using default: {result_backend}")

# Create Celery instance with explicit broker
celery = Celery('my_app')

# CRITICAL: Set broker AFTER creating instance
celery.conf.broker_url = broker_url
celery.conf.result_backend = result_backend

# Additional configuration
celery.conf.update(
    broker_connection_retry_on_startup=True,
    task_track_started=True,
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='Africa/Kigali',
    enable_utc=True,
    task_always_eager=False,
    worker_prefetch_multiplier=1,
    task_acks_late=True,
)

# Autodiscover tasks
celery.autodiscover_tasks([
    'application',
    'application.config_files',
])

celery.conf.beat_schedule = {
    'sync_applicants_every_5_minutes': {
        'task': 'application.config_files.tasks.bulk_sync_applicants_task',
        'schedule': crontab(minute='*/1'),
    }
}

def make_celery(app):
    celery.conf.update(app.config)
    
    class ContextTask(celery.Task):
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)
    
    celery.Task = ContextTask
    return celery
