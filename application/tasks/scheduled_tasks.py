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
    "sync-payments-every-150-sec": {
        "task": "application.tasks.quickbooks_sync.sync_payments",
       "schedule": 150.0,  # every 150 seconds
       "args": (),
         "options":{
                "expires": 140,  # Task expires in 140 seconds
         }
    },
    

    "sync-applicants-every-300-sec": {
        "task": "application.tasks.quickbooks_sync.bulk_sync_applicants_task",
        "schedule": 300.0,  # every 300 seconds
        "args": (),
        "options":{
            "expires": 290,  # Task expires in 290 seconds
        }

    },

    #"sync-students-every-15-sec": {
    #    "task": "application.tasks.quickbooks_sync.bulk_sync_students_task",
    #    "schedule": 15.0,  # every 15 seconds
    #    "args": (),
    #},
}

celery.conf.timezone = "Africa/Kigali"


