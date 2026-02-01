#!/usr/bin/env python3

import logging
import os
import sys
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

from application import create_app, db
from application.models.mis_models import TblImvoice
from application.services.invoice_sync import InvoiceSyncService
from application.models.central_models import QuickbooksAuditLog, QuickBooksConfig

# -------------------------------------------------
# Logging
# -------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)


# -------------------------------------------------
# Config
# -------------------------------------------------
PUSHED_FROM_DATE = datetime(2026, 1, 1)


def delete_qb_invoices():
    logger.info("Starting QuickBooks invoice deletion job")
    logger.info("Filter: date >= %s", PUSHED_FROM_DATE.date())

    app = create_app()

    with app.app_context():
        session = db.session

        # Validate QB connection once
        if not QuickBooksConfig.is_connected():
            logger.error("QuickBooks not connected. Exiting.")
            return

        invoice_ids = [
            i for (i,) in session.query(TblImvoice.id)
            .filter(TblImvoice.pushed_date >= PUSHED_FROM_DATE, TblImvoice.quickbooks_id.isnot(None), TblImvoice.reference_number.isnot(None))
            .order_by(TblImvoice.pushed_date.asc())

            .all()
        ]

        invoice_ids = invoice_ids # Limit for testing purposes
        logger.info("Fetched %s invoices for deletion", len(invoice_ids))

        if not invoice_ids:
            logger.warning("No invoices found — exiting")
            return
        logger.info("Proceeding to delete invoices from QuickBooks, ids: %s", invoice_ids)
        service = InvoiceSyncService()

        deleted = skipped = failed = 0

        for idx, invoice_id in enumerate(invoice_ids, start=1):
            try:
                logger.info("Processing %s / %s | invoice_id=%s", idx, len(invoice_ids), invoice_id)

                # Fetch invoice object only when needed
                invoice = TblImvoice.get_invoice_by_id(invoice_id)

                if not invoice:
                    logger.warning("Invoice ID %s not found, skipping", invoice_id)
                    continue
                logger.info("Deleting invoice : %s", invoice)
                # Delete in QuickBooks
                result = service.delete_invoice_from_quickbooks(invoice)

                if result.success:
                    TblImvoice.update_invoice_quickbooks_row(invoice_id)
                    logger.info("Deleted invoice %s successfully", invoice_id)
                else:
                    logger.error(
                        "Failed to delete invoice %s: %s", invoice_id, result.error_message
                    )

                # Commit every 50 invoices to make progress visible
                if idx % 50 == 0:
                    session.commit()
                    logger.info("Committed batch at invoice %s", idx)

            except Exception:
                session.rollback()
                logger.exception("Error processing invoice_id=%s", invoice_id)

        # Final commit
        session.commit()
        logger.info("QuickBooks invoice deletion job completed")


if __name__ == "__main__":
    delete_qb_invoices()
    logger.info("QuickBooks invoice deletion script finished")
