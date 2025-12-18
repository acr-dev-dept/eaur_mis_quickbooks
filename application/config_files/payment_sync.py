# from shared_task
# from celery import shared_task
from flask import app
from application.config_files.celery import celery
from application.services.payment_sync import PaymentSyncService

@celery.task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=60,  # retry after 1 minute
    retry_kwargs={"max_retries": 5},
    retry_jitter=True,
    name="application.config_files.payment_sync.sync_payment_to_quickbooks_task"  # explicit name
)
def sync_payment_to_quickbooks_task(self, payment_id: int):
    with app.app_context():
        service = PaymentSyncService()
        return service.sync_single_payment_async(payment_id)