#!/usr/bin/env python3

import sys
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

from application import create_app, db
from application.models.mis_models import (
    TblStudentWalletLedger,
    TblStudentWalletHistory,
)

def migrate_wallet_history_to_ledger():
    app = create_app()
    with app.app_context():
        from sqlalchemy.orm import Session
        session: Session = db.session

        history_rows = (
            session.query(TblStudentWalletHistory)
            .order_by(TblStudentWalletHistory.created_at.asc())
            .all()
        )

        migrated = skipped = 0

        for h in history_rows:
            exists_q = session.query(TblStudentWalletLedger).filter(
                TblStudentWalletLedger.trans_code == h.external_transaction_id
            ).first()

            if exists_q:
                skipped += 1
                continue

            # direction & source
            if h.transaction_type == "TOPUP":
                direction = "credit"
                amount = h.amount
                source = "sales_receipt"

            elif h.transaction_type == "REFUND":
                direction = "credit"
                amount = h.amount
                source = "refund"

            elif h.transaction_type == "DEBIT":
                direction = "debit"
                amount = -h.amount
                source = "invoice"

            elif h.transaction_type == "ADJUSTMENT":
                direction = "credit" if h.amount >= 0 else "debit"
                amount = h.amount
                source = "adjustment"

            else:
                skipped += 1
                continue

            ledger = TblStudentWalletLedger(
                student_id=h.reg_no,  
                direction=direction,
                original_amount=abs(h.amount),
                amount=amount,
                trans_code=h.external_transaction_id or h.trans_code,
                payment_chanel=h.payment_chanel,
                bank_id=h.bank_id,
                source=source,
                created_at=h.created_at,
            )

            session.add(ledger)
            migrated += 1

        session.commit()
        print({"migrated": migrated, "skipped": skipped})

if __name__ == "__main__":
    migrate_wallet_history_to_ledger()
