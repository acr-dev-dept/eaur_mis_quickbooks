#!/usr/bin/env python3

import logging
from decimal import Decimal
import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

from application.models.mis_models import (
    TblStudentWalletLedger,
    TblStudentWalletHistory,
)




# -------------------------------------------------
# Logging config
# -------------------------------------------------


logger = logging.getLogger(__name__)



def migrate_wallet_history_to_ledger():
    logger.info("Starting wallet history → ledger migration")

    from application import create_app, db

    app = create_app()

    with app.app_context():
        session = db.session

        history_rows = (
            session.query(TblStudentWalletHistory)
            .filter(TblStudentWalletHistory.amount != 0)
            .order_by(TblStudentWalletHistory.created_at.asc())
            .all()
        )
        logger.info("Fetched %s wallet history records", len(history_rows))

        if not history_rows:
            logger.warning("No history records found — exiting")
            return

        migrated = skipped = errors = 0

        for idx, h in enumerate(history_rows, start=1):
            try:
                if idx % 100 == 0:
                    logger.info("Processing record %s / %s", idx, len(history_rows))

                # Deduplication
                if h.external_transaction_id:
                    exists_q = (
                        session.query(TblStudentWalletLedger.id)
                        .filter(
                            TblStudentWalletLedger.trans_code
                            == h.external_transaction_id
                        )
                        .first()
                    )
                    if exists_q:
                        skipped += 1
                        continue

                # Direction & source
                if h.transaction_type == "TOPUP":
                    direction = "credit"
                    amount = Decimal(h.amount)
                    source = "sales_receipt"

                elif h.transaction_type == "REFUND":
                    direction = "credit"
                    amount = Decimal(h.amount)
                    source = "refund"

                elif h.transaction_type == "DEBIT":
                    direction = "debit"
                    amount = Decimal(h.amount) * Decimal("-1")
                    source = "invoice"

                elif h.transaction_type == "ADJUSTMENT":
                    direction = "credit" if h.amount >= 0 else "debit"
                    amount = Decimal(h.amount)
                    source = "adjustment"

                else:
                    logger.warning(
                        "Skipping unknown transaction type: %s (id=%s)",
                        h.transaction_type,
                        h.id,
                    )
                    skipped += 1
                    continue

                ledger = TblStudentWalletLedger(
                    student_id=h.reg_no,
                    direction=direction,
                    original_amount=abs(Decimal(h.amount)),
                    amount=amount,
                    trans_code=h.external_transaction_id or h.trans_code,
                    payment_chanel=h.payment_chanel,
                    bank_id=h.bank_id,
                    source=source,
                    created_at=h.created_at,
                )

                session.add(ledger)
                session.flush()  # <-- forces DB validation early
                migrated += 1

            except Exception as e:
                session.rollback()
                errors += 1
                logger.exception(
                    "Failed processing history_id=%s reg_no=%s",
                    h.id,
                    h.reg_no,
                )

        try:
            session.commit()
        except Exception:
            session.rollback()
            logger.exception("Final commit failed")
            raise

        logger.info(
            "Migration complete | migrated=%s skipped=%s errors=%s total=%s",
            migrated,
            skipped,
            errors,
            len(history_rows),
        )


if __name__ == "__main__":
    migrate_wallet_history_to_ledger()
    logger.info("Wallet history migration script finished execution")