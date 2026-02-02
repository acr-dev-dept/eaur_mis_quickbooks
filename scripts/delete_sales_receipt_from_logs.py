#!/usr/bin/env python3

import os
import sys
import logging
import re
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

# -------------------------------------------------
# Logging configuration
# -------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

logger = logging.getLogger(__name__)

# -------------------------------------------------
# Imports
# -------------------------------------------------
from application import create_app, db
from application.services.sales_receipt_sync import SalesReceiptSyncService
from application.models.central_models import QuickBooksConfig, QuickbooksAuditLog



# -------------------------------------------------
# Helpers
# -------------------------------------------------
QB_ID_REGEX = re.compile(r"ID:\s*(\d+)")


def extract_quickbooks_id(message: str) -> str | None:
    """Extract QuickBooks ID from audit log message."""
    if not message:
        return None
    match = QB_ID_REGEX.search(message)
    return match.group(1) if match else None


def get_current_sync_token_from_qb(qb_id: str) -> str:
    """
    Placeholder: fetch SalesReceipt from QuickBooks
    and return its current SyncToken.
    """
    
    service = SalesReceiptSyncService()
    try:
        sales_receipt = service.get_sales_receipt_from_quickbooks(qb_id)
        logger.info("Fetched SalesReceipt: %s", sales_receipt)
        return sales_receipt['details']['SalesReceipt']['SyncToken']
    except Exception as e:
        logger.error("Error fetching SalesReceipt qb_id=%s: %s", qb_id, str(e))
        raise e


# -------------------------------------------------
# Main deletion logic
# -------------------------------------------------
def delete_all_wallet_sales_receipts(batch_size: int = 50):
    logger.info("Starting batch deletion using audit logs")

    app = create_app()

    with app.app_context():
        session = db.session

        if not QuickBooksConfig.is_connected():
            logger.error("QuickBooks not connected. Exiting.")
            return

        # -------------------------------------------------
        # Fetch audit log rows
        # -------------------------------------------------
        logs = (
            session.query(QuickbooksAuditLog)
            .filter(
                QuickbooksAuditLog.action_type == "sales_receipt",
                QuickbooksAuditLog.operation_status == "SUCCESS",
            )
            .order_by(QuickbooksAuditLog.created_at.asc())
            .all()
        )

        total = len(logs)
        logger.info("Fetched %s successful sales_receipt audit records", total)

        if not logs:
            return

        service = SalesReceiptSyncService()

        deleted = skipped = failed = 0

        for idx, log in enumerate(logs, start=1):
            try:
                if idx % 25 == 0:
                    logger.info("Processing %s / %s", idx, total)

                qb_id = extract_quickbooks_id(log.error_message)

                if not qb_id:
                    logger.warning("Skipping audit_log_id=%s (no QB ID)", log.id)
                    skipped += 1
                    continue

                # -----------------------------------------
                # SyncToken logic
                # -----------------------------------------
                sync_token = "0"

                if log.error_message.startswith("Updated"):
                    
                    logger.info(
                        "Fetching SyncToken for updated SalesReceipt qb_id=%s",
                        qb_id,
                    )
                    sync_token = get_current_sync_token_from_qb(qb_id)
                    if sync_token is None:
                        logger.info("SalesReceipt deleted already, skipping qb_id=%s", qb_id)
                        skipped += 1
                        QuickbooksAuditLog.update_log_status(
                            log.id,
                            "SKIPPED",
                            f"SalesReceipt ID: {qb_id} deleted already.",
                        )
                        continue
                logger.info(
                    "Deleting SalesReceipt qb_id=%s sync_token=%s",
                    qb_id,
                    sync_token,
                )

                result = service.delete_sales_receipt_in_quickbooks(
                    qb_id,
                    sync_token
                )

                if not result.get("success"):
                    failed += 1
                    logger.error(
                        "Failed deleting qb_id=%s | %s",
                        qb_id,
                        result.get("error_message"),
                    )
                    
                    continue

                deleted += 1
                QuickbooksAuditLog.update_log_status(
                    log.id,
                    "DELETED",
                    f"SalesReceipt ID: {qb_id} deleted successfully.",
                )
                if idx % batch_size == 0:
                    session.commit()
                    logger.info("Committed batch at %s records", idx)

            except NotImplementedError:
                failed += 1
                logger.error("SyncToken fetch not implemented for qb_id=%s", qb_id)

            except Exception:
                session.rollback()
                failed += 1
                logger.exception(
                    "Unhandled error processing audit_log_id=%s", log.id
                )

        session.commit()

        logger.info(
            "Batch deletion completed | deleted=%s skipped=%s failed=%s total=%s",
            deleted,
            skipped,
            failed,
            total,
        )


# -------------------------------------------------
# Entrypoint
# -------------------------------------------------
if __name__ == "__main__":
    logger.info("SalesReceipt deletion script started")
    delete_all_wallet_sales_receipts()
    logger.info("SalesReceipt deletion script finished")
