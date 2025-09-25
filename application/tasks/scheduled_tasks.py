from celery import Celery
from application.tasks.quickbooks_sync import celery as payment_celery
from celery.schedules import crontab

# Pick one Celery instance to configure beat (usually the main one)
celery = payment_celery  # you can also make a dedicated celery instance if you prefer

celery.conf.beat_schedule = {
    "sync-payments-every-5-min": {
        "task": "application.tasks.quickbooks_sync.sync_payments",
        "schedule": 300.0,  # every 5 minutes
        "args": (),
    }
}

celery.conf.timezone = "Africa/Kigali"
