from celery import shared_task
from application.services.payment_sync import PaymentSyncService

@shared_task(
    name='application.config_files.payment_sync.sync_payment_to_quickbooks_task',
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=60, # retry after 1 minute
    retry_kwargs={"max_retries": 5},
    retry_jitter=True)

def sync_payment_to_quickbooks_task(self, payment_id: int):
    service = PaymentSyncService()
    return service.sync_single_payment_async(payment_id)