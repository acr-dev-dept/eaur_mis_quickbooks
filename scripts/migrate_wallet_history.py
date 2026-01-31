#!/usr/bin/env python3
"""
One-time migration script:
tbl_student_wallet_history -> tbl_student_wallet_ledger
"""

from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import exists

from application.models.mis_models import TblStudentWalletLedger, TblStudentWalletHistory

def migrate_wallet_history_to_ledger(db_session: Session):
    """
    One-time migration:
    tbl_student_wallet_history -> tbl_student_wallet_ledger
    """

    history_rows = db_session.query(TblStudentWalletHistory).order_by(
        TblStudentWalletHistory.created_at.asc()
    ).all()

    migrated = 0
    skipped = 0

    for h in history_rows:
        # -------------------------------------------------
        # Deduplication safeguard
        # -------------------------------------------------
        if h.external_transaction_id:
            already_exists = db_session.query(
                exists().where(
                    TblStudentWalletLedger.trans_code == h.external_transaction_id
                )
            ).scalar()

            if already_exists:
                skipped += 1
                continue

        # -------------------------------------------------
        # Direction & accounting sign
        # -------------------------------------------------
        if h.transaction_type in ("TOPUP", "REFUND"):
            direction = "credit"
            signed_amount = Decimal(h.amount)
            source = "sales_receipt" if h.transaction_type == "TOPUP" else "refund"

        elif h.transaction_type == "DEBIT":
            direction = "debit"
            signed_amount = Decimal(h.amount) * Decimal("-1")
            source = "invoice"

        elif h.transaction_type == "ADJUSTMENT":
            if h.amount >= 0:
                direction = "credit"
                signed_amount = Decimal(h.amount)
            else:
                direction = "debit"
                signed_amount = Decimal(h.amount)
            source = "adjustment"

        else:
            # Unknown transaction type → skip safely
            skipped += 1
            continue

        # -------------------------------------------------
        # Build ledger entry
        # -------------------------------------------------
        ledger_row = TblStudentWalletLedger(
            student_id=h.reg_no,
            direction=direction,
            original_amount=Decimal(abs(h.amount)),
            amount=signed_amount,
            trans_code=h.external_transaction_id or h.trans_code,
            payment_chanel=h.payment_chanel,
            bank_id=h.bank_id,
            source=source,
            created_at=h.created_at,
        )

        db_session.add(ledger_row)
        migrated += 1

    db_session.commit()

    return {
        "migrated": migrated,
        "skipped": skipped,
        "total_history": len(history_rows),
    }
