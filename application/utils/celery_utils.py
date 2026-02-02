# application/utils/celery_utils.py
import logging
from celery import Celery
from celery.schedules import crontab
from kombu import Queue

log = logging.getLogger("celery.setup")
if not log.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s'))
    log.addHandler(handler)
    log.setLevel(logging.INFO)

def make_celery(app):
    log.info("make_celery() → Creating Celery instance bound to Flask app")

    celery = Celery(
        app.import_name,
        broker=app.config["broker_url"],
        backend=app.config["RESULT_BACKEND"]
        
    )

    celery.conf.update(app.config, result_expires=3600)

    # All tasks automatically get app context
    class ContextTask(celery.Task):
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)
    celery.Task = ContextTask
    # Critical: Initialize MIS DB connection
    with app.app_context():
        app.logger.info("Initializing DatabaseManager in Celery worker process")
        from application.utils.database import init_database_manager
        init_database_manager(app)
        app.logger.info("DatabaseManager ready — MIS DB works in Celery!")

    # Move all your beat/queues/routes here (or in create_app)
    celery.conf.update(
        timezone='Africa/Kigali',
        enable_utc=True,
        task_queues=(
            Queue("celery"),
            Queue("payment_sync_queue"),
        ),
        task_routes={
            "application.config_files.payment_sync.sync_payment_to_quickbooks_task": {
                "queue": "payment_sync_queue"
            },
            "application.config_files.wallet_sync.sync_wallet_to_quickbooks_task": {
                "queue": "wallet_sync_queue"
            },
            "application.config_files.wallet_sync.update_wallet_to_quickbooks_task": {
                "queue": "wallet_sync_queue"
            },
            "application.tasks.delete_sales_receipt_master.delete_all_wallet_sales_receipts_master": {
                "queue": "wallet_sync_queue"
            },

        },
        beat_schedule={
            "delete sales receipts from logs every 3 minutes": {
                "task": "application.config_files.sales_receipt_deletion_task.scheduled_sales_receipt_deletion_task",
                "schedule": crontab(minute='*/3'),
            },
        }
    )

    log.info("Celery fully configured and ready")
    return celery

"""
"sync_applicants_every_midnight": {
    "task": "application.config_files.tasks.bulk_sync_applicants_task",
    "schedule": crontab(minute='*/6'),
},
"sync_invoices_every_midnight": {
    "task": "application.config_files.sync_invoices_task.scheduled_invoice_sync_task",
    "schedule": crontab(hour=0, minute=20)
},

"sync_payments_every_midnight": {
"task": "application.config_files.sync_payments_task.scheduled_payment_sync_task",
"schedule": crontab(minute='*/6')
},
"sync_sales_receipt_every_midnight": {
"task": "application.config_files.sync_sales_receipt_task.scheduled_sales_receipt_sync_task",
"schedule": crontab(minute='*/2')
}
"sync_students": {
"task": "application.config_files.sync_students_task.bulk_sync_students_task",
"schedule": crontab(hour='18,19,20,1,22,23,0,1,2,3,4,5', minute='6,42'),
},
"""

"""
"sync_students": {
            "task": "application.config_files.sync_students_task.bulk_sync_students_task",
            "schedule": crontab(
                minute='6,42',
                hour='0-23',
                day_of_week='mon,tue,wed,thu,fri'
                )
            },
            "sync_sales_receipt_every_midnight": {
            "task": "application.config_files.sync_sales_receipt_task.scheduled_sales_receipt_sync_task",
            "schedule": crontab(minute='*/10'),
            },
            "sync_invoices_every_midnight": {
            "task": "application.config_files.sync_invoices_task.scheduled_invoice_sync_task",
            "schedule": crontab(minute='12,24,36',
                                hour="0,2,4,6,8,10,12,14,16,18,20,22",
                                day_of_week='mon,tue,wed,thu,fri')
            },
            "update_invoices": {
            "task": "application.config_files.update_invoices_task.scheduled_invoice_update_task",
            "schedule": crontab(
                minute='6,24,30',
                hour='1,3,5,7,9,11,13,15,17,19,21,23',
                day_of_week='mon,tue,wed,thu,fri'
            )
        },



        # WEEKEND SCHEDULES
        "sync_applicants_every_weekend": {
        "task": "application.config_files.tasks.bulk_sync_applicants_task",
        "schedule": crontab(
            minute='6,42',
            hour='0-23',
            day_of_week='sat,sun'
            ),
        },
        "sync_students_every_weekend": {
        "task": "application.config_files.sync_students_task.bulk_sync_students_task",
        "schedule": crontab(
            minute='6,42',
            hour='0-23',
            day_of_week='sat,sun'
            ),
        },
        "sync_invoices_every_weekend": {
        "task": "application.config_files.sync_invoices_task.scheduled_invoice_sync_task",
        "schedule": crontab(
            minute='12,48,24,54',
            hour='0-23',
            day_of_week='sat,sun'
            ),
        },
        "sync_sales_receipt_every_weekend": {
        "task": "application.config_files.sync_sales_receipt_task.scheduled_sales_receipt_sync_task",
        "schedule": crontab(
            minute='18,54',
            hour='0-23',
            day_of_week='sat,sun'
            ),
        },
        "sync_update_invoices_every_weekend": {
        "task": "application.config_files.update_invoices_task.scheduled_invoice_update_task",
        "schedule": crontab(
            minute='6,30,54,24,57',
            hour='0-23',
            day_of_week='sat,sun'
            ),
        },
        "sync_payments_every_weekend": {
        "task": "application.config_files.sync_payments_task.bulk_sync_payments_task",
        "schedule": crontab(
            minute='30,54',
            hour='0-23', 
            day_of_week='sat,sun'
            ),
        },

        },

"""