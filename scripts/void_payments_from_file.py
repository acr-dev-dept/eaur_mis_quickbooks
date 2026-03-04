#!/usr/bin/env python3

import os
import sys
import logging
import pandas as pd

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
from application import create_app
from application.services.payment_sync import PaymentSyncService
from application.models.central_models import QuickBooksConfig


# -------------------------------------------------
# Configuration
# -------------------------------------------------
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
FILE_PATH = os.path.join(
    SCRIPT_DIR,
    "files",
    "UNDEPOSITED_FUNDS_2025.xlsx"
)

TARGET_DEPOSIT_ACCOUNT = "1211"


# -------------------------------------------------
# Core Logic
# -------------------------------------------------
def void_payments_from_excel():
    logger.info("Starting QuickBooks payment void batch from Excel")

    if not os.path.exists(FILE_PATH):
        logger.error("Excel file not found: %s", FILE_PATH)
        return

    app = create_app()

    with app.app_context():

        # -----------------------------------------
        # Validate QB connection once
        # -----------------------------------------
        if not QuickBooksConfig.is_connected():
            logger.error("QuickBooks not connected. Exiting.")
            return

        # -----------------------------------------
        # Load Excel file
        # -----------------------------------------
        df = pd.read_excel(FILE_PATH)

        if "Number" not in df.columns:
            logger.error("Column 'Number' not found in Excel file.")
            return

        doc_numbers = (
            df["Number"]
            .dropna()
            .astype(str)
            .str.strip()
            .unique()
            .tolist()
        )

        total = len(doc_numbers)

        if not total:
            logger.warning("No DocNumbers found in file. Exiting.")
            return

        logger.info("Loaded %s unique DocNumbers", total)

        service = PaymentSyncService()

        voided = skipped = failed = 0

        # -----------------------------------------
        # Process Each DocNumber
        # -----------------------------------------
        for idx, doc_number in enumerate(doc_numbers, start=1):
            try:
                if idx % 25 == 0:
                    logger.info("Processing %s / %s", idx, total)

                query = (
                    "SELECT Id, SyncToken, DocNumber, TotalAmt, "
                    "CustomerRef, DepositToAccountRef, MetaData.CreateTime "
                    f"FROM Payment WHERE DocNumber = '{doc_number}'"
                )

                logger.info("Querying Payment | DocNumber=%s", doc_number)

                result = service.query_payment(query)

                query_response = result.get("QueryResponse")
                if not query_response:
                    logger.warning("No QueryResponse | DocNumber=%s", doc_number)
                    skipped += 1
                    continue

                payments = query_response.get("Payment", [])

                if not payments:
                    logger.warning("Payment not found | DocNumber=%s", doc_number)
                    skipped += 1
                    continue

                payment = payments[0]

                deposit_ref = payment.get("DepositToAccountRef")

                if not (
                    isinstance(deposit_ref, dict)
                    and deposit_ref.get("value") == TARGET_DEPOSIT_ACCOUNT
                ):
                    logger.info(
                        "Skipping DocNumber=%s (Deposit account mismatch)",
                        doc_number,
                    )
                    skipped += 1
                    continue

                payment_id = payment.get("Id")
                sync_token = payment.get("SyncToken")
                total_amt = payment.get("TotalAmt")

                if not payment_id or not sync_token:
                    logger.error(
                        "Missing Id/SyncToken | DocNumber=%s",
                        doc_number,
                    )
                    failed += 1
                    continue
                
                if total_amt == 0:
                    logger.info(
                        "Skipping DocNumber=%s (TotalAmt=0)",
                        doc_number,
                    )
                    skipped += 1
                    continue

                logger.info(
                    "Voiding Payment | DocNumber=%s | Id=%s",
                    doc_number,
                    payment_id,
                )

                void_result = service.void_payment(payment_id, sync_token)

                if not void_result.get("Payment"):
                    logger.error(
                        "Void failed | DocNumber=%s | %s",
                        doc_number,
                        void_result.get("error_message"),
                    )
                    failed += 1
                    continue

                voided += 1

            except Exception:
                failed += 1
                logger.exception(
                    "Unhandled error processing DocNumber=%s",
                    doc_number,
                )

        logger.info(
            "Batch completed | voided=%s skipped=%s failed=%s total=%s",
            voided,
            skipped,
            failed,
            total,
        )


# -------------------------------------------------
# Entrypoint
# -------------------------------------------------
if __name__ == "__main__":
    logger.info("QuickBooks Payment Void Script Started")
    void_payments_from_excel()
    logger.info("QuickBooks Payment Void Script Finished")
