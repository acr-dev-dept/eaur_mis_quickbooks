# scheduled_tasks.py
from application.tasks.quickbooks_sync import celery 
from celery.schedules import crontab


celery.conf.beat_schedule = {

    """A"""
    #"sync-applicants-every-300-sec": {
    #    "task": "application.tasks.quickbooks_sync.bulk_sync_applicants_task",
    #    "schedule": 300.0,  # every 300 seconds
    #    "args": (),
    #    "options":{
    #        "expires": 290,  # Task expires in 290 seconds
    #    }
    #},


    """B"""
    #"sync-students-every-15-sec": {
    #    "task": "application.tasks.quickbooks_sync.bulk_sync_students_task",
    #    "schedule": 15.0,  # every 15 seconds
    #    "args": (),
    #},

    """C"""
    #"sync-income-categories-every-300-sec": {
    #    "task": "application.tasks.quickbooks_sync.bulk_sync_income_categories_task",
    #    "schedule": 30.0,  # every 300 seconds
    #    "args": (),
    #    "options":{
    #        "expires": 29,  # Task expires in 290 seconds
    #    }
    #},

    """D"""

    "sync-items-every-3-sec": {
        "task": "application.tasks.quickbooks_sync.bulk_sync_items_task",
        "schedule": 3,  # every 3 seconds
        "args": (),
        "options":{
            "expires": 2,  # Task expires in 2 seconds
        }
    },

    """E"""
    #"progressive-invoice-sync-every-7-min": {
    #    "task": "application.tasks.quickbooks_sync.scheduled_invoice_sync_task",
    #    "schedule": crontab(minute='*/7'),  # Every 7 minutes
    #    "args": (),
    #    "options": {
    #        "expires": 360,  # Task expires in 6 minutes (less than schedule interval)
    #    }
    #},

    
    # Optional: Reset offset daily at midnight to start fresh
    "reset-invoice-sync-offset-daily": {
        "task": "application.tasks.quickbooks_sync.reset_invoice_sync_offset",
        "schedule": crontab(hour=0, minute=0),  # Every day at midnight
    },


    #"sync-payments-every-5-min": {
    #    "task": "application.tasks.quickbooks_sync.bulk_sync_payments_task",
    #    "schedule": crontab(minute='*/6'),  # Every 6 minutes
    #    "options": {
    #        "expires": 300,  # Task expires in 5 minutes (less than schedule interval)
    #    }
    #},

}

celery.conf.timezone = "Africa/Kigali"


