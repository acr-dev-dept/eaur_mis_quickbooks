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
        },
        beat_schedule={
            "sync_payments_every_midnight": {
            "task": "application.config_files.sync_payments_task.scheduled_payment_sync_task",
            "schedule": crontab(hour='18,19,20,1,22,23,0,1,2,3,4,5', minute='6,42')
            },
            "sync_sales_receipt_every_midnight": {
            "task": "application.config_files.sync_sales_receipt_task.scheduled_sales_receipt_sync_task",
            "schedule": crontab(hour="18,19,20,1,22,23,0,1,2,3,4,5", minute='12,48'),
        },
            "sync_invoices_every_midnight": {
            "task": "application.config_files.sync_invoices_task.scheduled_invoice_sync_task",
            "schedule": crontab(hour="18,19,20,1,22,23,0,1,2,3,4,5", minute='24,54'),
        },
            "update_invoices": {
            "task": "application.config_files.update_invoices_task.scheduled_invoice_update_task",
            "schedule": crontab(hour="18,19,20,1,22,23,0,1,2,3,4,5", minute='30,57'),
        },
        },
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