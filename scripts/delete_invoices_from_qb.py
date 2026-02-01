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
PUSHED_FROM_DATE = datetime(2026, 1, 30)


def delete_qb_invoices():
    logger.info("Starting QuickBooks invoice deletion job")
    logger.info("Filter: pushed_by >= %s", PUSHED_FROM_DATE.date())

    app = create_app()

    with app.app_context():
        session = db.session

        # Validate QB connection once
        if not QuickBooksConfig.is_connected():
            logger.error("QuickBooks not connected. Exiting.")
            return

        invoices = (
            session.query(TblImvoice)
            .filter(TblImvoice.pushed_by >= PUSHED_FROM_DATE)
            .order_by(TblImvoice.pushed_by.asc())
            .all()
        )

        logger.info("Fetched %s invoices for deletion", len(invoices))

        if not invoices:
            logger.warning("No invoices found — exiting")
            return

        service = InvoiceSyncService()

        deleted = skipped = failed = 0

        for idx, invoice in enumerate(invoices, start=1):
            try:
                logger.info("Processing %s / %s | invoice_id=%s", idx, len(invoices), invoice.id)

                # Skip rules
                if invoice.is_prepayment:
                    skipped += 1
                    logger.info("Skipped prepayment invoice %s", invoice.id)
                    continue

                if invoice.balance is not None:
                    skipped += 1
                    logger.info("Skipped balance-linked invoice %s", invoice.id)
                    continue

                result = service.delete_invoice_from_quickbooks(invoice)

                if not result.success:
                    failed += 1
                    logger.error(
                        "QB delete failed for invoice %s: %s",
                        invoice.id,
                        result.error_message,
                    )
                    QuickbooksAuditLog.add_audit_log(
                        action_type="Batch delete invoice",
                        operation_status=400,
                        error_message=result.error_message,
                    )
                    continue

                # Update MIS record
                TblImvoice.update_invoice_quickbooks_row(invoice.id)

                QuickbooksAuditLog.add_audit_log(
                    action_type=f"Batch delete invoice {invoice.id}",
                    operation_status=200,
                    error_message=None,
                )

                deleted += 1

                # Commit every 50 records
                if idx % 50 == 0:
                    session.commit()
                    logger.info("Committed batch at record %s", idx)

            except Exception:
                session.rollback()
                failed += 1
                logger.exception("Error deleting invoice_id=%s", invoice.id)

        session.commit()

        logger.info(
            "Deletion complete | deleted=%s skipped=%s failed=%s total=%s",
            deleted,
            skipped,
            failed,
            len(invoices),
        )


if __name__ == "__main__":
    delete_qb_invoices()
    logger.info("QuickBooks invoice deletion script finished")
