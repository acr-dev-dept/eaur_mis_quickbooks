#!/usr/bin/env python3

import os
import sys
import logging
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

# -------------------------------------------------
# Logging configuration (MANDATORY)
# -------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

logger = logging.getLogger(__name__)

# -------------------------------------------------
# Imports after sys.path fix
# -------------------------------------------------
from application import create_app, db
from application.models.mis_models import TblStudentWallet
from application.services.sales_receipt_sync import (
    SalesReceiptSyncService,
)
from application.models.central_models import QuickBooksConfig


# -------------------------------------------------
# Main batch deletion logic
# -------------------------------------------------
def delete_all_wallet_sales_receipts(batch_size: int = 50):
    logger.info("Starting batch deletion of QuickBooks sales receipts")

    app = create_app()

    with app.app_context():
        session = db.session

        # -------------------------------------------------
        # Validate QB connection ONCE
        # -------------------------------------------------
        # Validate QB connection once
        if not QuickBooksConfig.is_connected():
            logger.error("QuickBooks not connected. Exiting.")
            return
        # -------------------------------------------------
        # Fetch wallet IDs ONLY (lightweight)
        # -------------------------------------------------
        wallet_ids = [
            wid for (wid,) in session.query(TblStudentWallet.id)
            .filter(TblStudentWallet.quickbooks_id.isnot(None))
            .order_by(TblStudentWallet.id.asc())
            .all()
        ]

        total = len(wallet_ids)
        logger.info("Fetched %s wallet records with QuickBooks IDs", total)

        if not wallet_ids:
            logger.warning("No wallet records found — exiting")
            return

        service = SalesReceiptSyncService()

        deleted = skipped = failed = 0

        for idx, wallet_id in enumerate(wallet_ids, start=1):
            try:
                if idx % 25 == 0:
                    logger.info("Processing %s / %s", idx, total)

                sales_data = TblStudentWallet.get_sales_data(wallet_id)

                if not sales_data or not sales_data.quickbooks_id:
                    logger.warning(
                        "Skipping wallet_id=%s (not synced or missing QB ID)",
                        wallet_id,
                    )
                    skipped += 1
                    continue

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
                    failed += 1
                    logger.error(
                        "Failed deleting wallet_id=%s | %s",
                        wallet_id,
                        result.get("error_message"),
                    )
                    continue

                deleted += 1

                # Commit periodically for visibility & safety
                if idx % batch_size == 0:
                    session.commit()
                    logger.info("Committed batch at %s records", idx)

            except Exception:
                session.rollback()
                failed += 1
                logger.exception(
                    "Unhandled error processing wallet_id=%s", wallet_id
                )

        # Final commit
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
    logger.info("Sales Receipt batch deletion script started")
    delete_all_wallet_sales_receipts()
    logger.info("Sales Receipt batch deletion script finished")
