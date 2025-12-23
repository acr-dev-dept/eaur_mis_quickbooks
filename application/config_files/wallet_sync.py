from application.config_files.celery_app import celery
from application.services.sales_receipt_sync import SalesReceiptSyncService


@celery.task(
    bind=True,
    name="application.config_files.wallet_sync.sync_wallet_to_quickbooks_task",
    autoretry_for=(Exception,),
    retry_backoff=60,
    retry_kwargs={"max_retries": 5},
    retry_jitter=True,
)
def sync_wallet_to_quickbooks_task(self, wallet_id: int):
    # No need to create app or push context — it's automatic!
    service = SalesReceiptSyncService()
    return service.sync_single_sales_receipt_async(wallet_id)