import logging
from celery import shared_task, group

from application import create_app, db
from application.models.mis_models import TblStudentWallet
from application.models.central_models import QuickBooksConfig


logger = logging.getLogger(__name__)


@shared_task
def delete_all_wallet_sales_receipts_master():
    logger.info("Starting master sales receipt deletion task")

    app = create_app()

    with app.app_context():
        if not QuickBooksConfig.is_connected():
            logger.error("QuickBooks not connected — aborting")
            return "aborted"

        wallet_ids = [
            wid for (wid,) in db.session.query(TblStudentWallet.id)
            .filter(TblStudentWallet.quickbooks_id.isnot(None))
            .all()
        ]

        logger.info("Dispatching %s deletion tasks", len(wallet_ids))
        from application.tasks.delete_sales_receipt_single import (
            delete_single_wallet_sales_receipt,
        )
        job = group(
            delete_single_wallet_sales_receipt.s(wallet_id)
            for wallet_id in wallet_ids
        )

        job.apply_async()
        return "dispatched"
