from celery import Celery
from application.tasks.quickbooks_sync import celery as payment_celery
from celery.schedules import crontab

# Pick one Celery instance to configure beat (usually the main one)
celery = payment_celery  # you can also make a dedicated celery instance if you prefer

celery.conf.beat_schedule = {
    "sync-payments-every-2-min": {
        "task": "application.tasks.quickbooks_sync.sync_payments",
        "schedule": 120.0,  # every 2 minutes
        "args": (),
    },
    #"sync-customers-every-4-min": {
        #"task": "application.tasks.quickbooks_sync.sync_applicants",
        #"schedule": 240.0,  # every 4 minutes
        #"args": (),
    #},
    "sync-invoices-every-2-min": {
        "task": "application.tasks.quickbooks_sync.sync_invoices",
        "schedule": 120.0,  # every 2 minutes
        "args": (),
    }
}

celery.conf.timezone = "Africa/Kigali"


