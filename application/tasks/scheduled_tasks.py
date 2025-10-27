from celery import Celery
from application.tasks.quickbooks_sync import celery as payment_celery
from application.tasks.applicant_sync import celery as applicant_celery
from celery.schedules import crontab

celery = Celery('scheduled_tasks')
celery.conf.beat_schedule = {
    #"sync-payments-every-15-sec": {
        #"task": "application.tasks.quickbooks_sync.sync_payments",
        #"schedule": 15.0,  # every 15 seconds
       # "args": (),
    #},
    #"""
    #"sync-invoices-every-15-sec": {
    #    "task": "application.tasks.quickbooks_sync.sync_invoices",
    #    "schedule": 15.0,  # every 15 seconds
    #    "args": (),
    #},
    #"sync-payments-every-15-sec": {
    #    "task": "application.tasks.quickbooks_sync.sync_payments",
    #   "schedule": 15.0,  # every 15 seconds
    #   "args": (),
    #},
    #"""

    "sync-applicants-every-5-sec": {
        "task": "application.tasks.quickbooks_sync.bulk_sync_applicants_task",
        "schedule": 5.0,  # every 5 seconds
        "args": (),
    },
    "sync-students-every-15-sec": {
        "task": "application.tasks.quickbooks_sync.bulk_sync_students_task",
        "schedule": 15.0,  # every 15 seconds
        "args": (),
    },
}

celery.conf.timezone = "Africa/Kigali"


