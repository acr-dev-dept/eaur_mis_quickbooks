from application.config_files.celery_app import celery
from application.services.payment_sync import PaymentSyncService


@celery.task(
    bind=True,
    name="payments.sync_to_quickbooks",
    autoretry_for=(Exception,),
    retry_backoff=60,
    retry_kwargs={"max_retries": 5},
    retry_jitter=True,
)
def sync_payment_to_quickbooks_task(self, payment_id: int):
    # No need to create app or push context — it's automatic!
    service = PaymentSyncService()
    return service.sync_single_payment_async(payment_id)