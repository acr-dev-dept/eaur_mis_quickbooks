#!/usr/bin/env python3

import os
import sys
import logging
import pandas as pd
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
    "undeposited_funds_2024_test_v2.xlsx"
)
DEPOSIT_ACCOUNT_ID = "1211"
PAYMENT_METHOD_ID = "2"


# -------------------------------------------------
# Core Logic
# -------------------------------------------------
def create_payments_from_excel():
    logger.info("Starting QuickBooks Payment Creation Batch")

    if not os.path.exists(FILE_PATH):
        logger.error("Excel file not found: %s", FILE_PATH)
        return

    app = create_app()

    with app.app_context():

        if not QuickBooksConfig.is_connected():
            logger.error("QuickBooks not connected. Exiting.")
            return

        df = pd.read_excel(FILE_PATH)

        required_columns = [
            "Transaction date",
            "Number",
            "Name",
            "Amount",
        ]

        for col in required_columns:
            if col not in df.columns:
                logger.error("Missing required column: %s", col)
                return

        total = len(df)
        logger.info("Loaded %s rows from Excel", total)

        service = PaymentSyncService()

        created = skipped = failed = 0

        for idx, row in df.iterrows():
            try:
                if idx % 25 == 0:
                    logger.info("Processing %s / %s", idx, total)

                if pd.isna(row["Name"]) or pd.isna(row["Amount"]) or pd.isna(row["Transaction date"]):
                    logger.warning("Skipping row %s (missing data)", idx)
                    skipped += 1
                    continue
                #query the payment first to see if it exists and skip
                query = (
                    "SELECT Id, SyncToken, DocNumber, TotalAmt, "
                    "CustomerRef, DepositToAccountRef, MetaData.CreateTime "
                    f"FROM Payment WHERE DocNumber = '{row['Number']}'"
                )
                result = service.query_payment(query)
                # Check if payment exists
                payments = result.get("Payment", [])
                payment_exists = False
                for payment in payments:
                    if payment.get("DepositToAccountRef", {}).get("value") == DEPOSIT_ACCOUNT_ID:
                        logger.warning("Payment already exists | DocNumber=%s", row["Number"])
                        skipped += 1
                        payment_exists = True
                        break  # Stop checking further

                if payment_exists:
                    continue  # Skip the current row entirely

                # Format date
                txn_date = pd.to_datetime(row["Transaction date"], errors="coerce")
                txn_date = txn_date.strftime("%Y-%m-%d")

                payment_data = {
                    "id": str(idx + 1),
                    "trans_code": str(row["Number"]),
                    "customer_ref_id": str(row["Name"]).strip(),
                    "deposit_account_id": DEPOSIT_ACCOUNT_ID,
                    "payment_method_id": PAYMENT_METHOD_ID,
                    "amount": float(row["Amount"]),
                    "date": txn_date,
                }

                logger.info(
                    "Creating Payment | DocNumber=%s | Customer=%s | Amount=%s",
                    payment_data["trans_code"],
                    payment_data["customer_ref_id"],
                    payment_data["amount"],
                )

                result = service.create_payment(payment_data)

                # Robust response validation
                if "Fault" in result:
                    logger.error(
                        "Creation failed | DocNumber=%s | %s",
                        payment_data["trans_code"],
                        result["Fault"],
                    )
                    failed += 1
                    continue

                if not result.get("Payment"):
                    logger.error(
                        "Unexpected response | DocNumber=%s | %s",
                        payment_data["trans_code"],
                        result,
                    )
                    failed += 1
                    continue

                created += 1

            except Exception:
                failed += 1
                logger.exception("Unhandled error at row %s", idx)

        logger.info(
            "Batch completed | created=%s skipped=%s failed=%s total=%s",
            created,
            skipped,
            failed,
            total,
        )


# -------------------------------------------------
# Entrypoint
# -------------------------------------------------
if __name__ == "__main__":
    logger.info("QuickBooks Payment Creation Script Started")
    create_payments_from_excel()
    logger.info("QuickBooks Payment Creation Script Finished")
