import logging
from celery import shared_task

from application import create_app, db
from application.models.mis_models import TblStudentWallet
from application.services.sales_receipt_sync import SalesReceiptSyncService

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_kwargs={"max_retries": 3, "countdown": 30},
    retry_backoff=True,
    retry_jitter=True,
)
def delete_single_wallet_sales_receipt(self, wallet_id: int):
    app = create_app()

    with app.app_context():
        session = db.session

        sales_data = TblStudentWallet.get_sales_data(wallet_id)

        if not sales_data or not sales_data.quickbooks_id:
            logger.info(
                "Skipping wallet_id=%s (no QB sales receipt)",
                wallet_id,
            )
            return "skipped"

        service = SalesReceiptSyncService()

        logger.info(
            "Deleting Sales Receipt | wallet_id=%s qb_id=%s",
            wallet_id,
            sales_data.quickbooks_id,
        )

        result = service.delete_sales_receipt_in_quickbooks(
            sales_data.quickbooks_id,
            sales_data.sync_token,
            sales_data.id,
        )

        if not result.get("success"):
            raise Exception(result.get("error_message"))

        session.commit()
        return "deleted"
