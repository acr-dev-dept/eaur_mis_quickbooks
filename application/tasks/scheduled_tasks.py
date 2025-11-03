# scheduled_tasks.py
from application.tasks.quickbooks_sync import celery 
from celery.schedules import crontab


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

    #"sync-items-every-3-sec": {
    #    "task": "application.tasks.quickbooks_sync.bulk_sync_items_task",
    #    "schedule": 3,  # every 3 seconds
    #    "args": (),
    #    "options":{
    #        "expires": 2,  # Task expires in 2 seconds
    #    }
    #},
    #"progressive-invoice-sync-every-5-min": {
    #    "task": "application.tasks.quickbooks_sync.scheduled_invoice_sync_task",
    #    "schedule": crontab(minute='*/5'),  # Every 5 minutes
    #    "options": {
    #        "expires": 240,  # Task expires in 4 minutes (less than schedule interval)
    #    }
    #},
    
    # Optional: Reset offset daily at midnight to start fresh
    #"reset-invoice-sync-offset-daily": {
    #    "task": "application.tasks.quickbooks_sync.reset_invoice_sync_offset",
    #    "schedule": 1200.0,  # every 1200 seconds (20 minutes)
    #},

    "sync-payments-every-5-min": {
        "task": "application.tasks.quickbooks_sync.bulk_sync_payments_task",
        "schedule": crontab(minute='*/6'),  # Every 6 minutes
        "options": {
            "expires": 300,  # Task expires in 5 minutes (less than schedule interval)
        }
    },

}

celery.conf.timezone = "Africa/Kigali"


