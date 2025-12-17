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
        'schedule': crontab(minute='*/1'),
    }
}

celery.conf.task_routes = {
    'application.config_files.payment_sync.sync_payment_to_quickbooks_task': {'queue': 'payment_sync_queue'},
}
def make_celery(app):
    celery.conf.update(app.config)

    class ContextTask(celery.Task):
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)

    celery.Task = ContextTask
    return celery
