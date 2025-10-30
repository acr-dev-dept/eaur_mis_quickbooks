from celery import Celery
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

    #"sync-applicants-every-300-sec": {
    #    "task": "application.tasks.quickbooks_sync.bulk_sync_applicants_task",
    #    "schedule": 300.0,  # every 300 seconds
    #    "args": (),
    #    "options":{
    #        "expires": 290,  # Task expires in 290 seconds
    #    }
    #},



    #"sync-students-every-15-sec": {
    #    "task": "application.tasks.quickbooks_sync.bulk_sync_students_task",
    #    "schedule": 15.0,  # every 15 seconds
    #    "args": (),
    #},

    #"sync-income-categories-every-300-sec": {
    #    "task": "application.tasks.quickbooks_sync.bulk_sync_income_categories_task",
    #    "schedule": 300.0,  # every 300 seconds
    #    "args": (),
    #    "options":{
    #        "expires": 290,  # Task expires in 290 seconds
    #    }
    #},

    "sync-items-every-30-sec": {
        "task": "application.tasks.quickbooks_sync.bulk_sync_items_task",
        "schedule": 30.0,  # every 30 seconds
        "args": (),
        "options":{
            "expires": 29,  # Task expires in 29 seconds
        }
    },
}

celery.conf.timezone = "Africa/Kigali"


