from celery import Celery
from application.tasks.quickbooks_sync import celery as payment_celery
from celery.schedules import crontab

# Pick one Celery instance to configure beat (usually the main one)
celery = payment_celery  # you can also make a dedicated celery instance if you prefer

celery.conf.beat_schedule = {
    #"sync-payments-every-15-sec": {
        #"task": "application.tasks.quickbooks_sync.sync_payments",
        #"schedule": 15.0,  # every 15 seconds
       # "args": (),
    #},
    "sync-invoices-every-15-sec": {
        "task": "application.tasks.quickbooks_sync.sync_invoices",
        "schedule": 15.0,  # every 15 seconds
        "args": (),
    },
    "sync-payments-every-15-sec": {
        "task": "application.tasks.quickbooks_sync.sync_payments",
        "schedule": 15.0,  # every 15 seconds
        "args": (),
    },
    "sync-applicants-every-15-sec": {
        "task": "application.tasks.quickbooks_sync.sync_applicants",
        "schedule": 15.0,  # every 15 seconds
        "args": (),
    },
    "sync-students-every-15-sec": {
        "task": "application.tasks.quickbooks_sync.sync_students",
        "schedule": 15.0,  # every 15 seconds
        "args": (),
    },
}

celery.conf.timezone = "Africa/Kigali"


