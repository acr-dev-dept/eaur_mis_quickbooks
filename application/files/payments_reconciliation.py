#!/usr/bin/env python3
"""
Wallet reconciliation CLI importer

Usage:
    ./wallet_reconciliation_import.py /path/to/file.json
"""

import sys
import json
from pathlib import Path

# ----------------------------------------
# Flask app bootstrap
# ----------------------------------------
from application import create_app, db
from application.models.mis_models import TblStudentWallet


def import_wallet_transactions(json_path: str):

    with open(json_path, "r") as f:
        data = json.load(f)

    per_payer_code = data.get("per_payer_code", {})

    results = {
        "updated": [],
        "created": [],
        "failed": []
    }

    for payer_code, payer_data in per_payer_code.items():

        transactions = payer_data.get("transactions", [])

        if not transactions:
            continue

        try:
            wallet = TblStudentWallet.query.filter_by(
                reg_no=payer_code
            ).first()

            total_amount = 0

            # -------------------------------
            # EXISTING WALLET
            # -------------------------------
            if wallet:
                wallet.dept = 0
                db.session.flush()

                for txn in transactions:
                    transaction_id = str(txn.get("transaction_reference"))
                    amount = float(txn.get("paid_amount", 0))

                    total_amount += amount

                    TblStudentWallet.topup_wallet(
                        payer_code=payer_code,
                        external_transaction_id=transaction_id,
                        amount=amount,
                        slip_no=txn.get("slip_no", None)
                    )

                wallet.dept = total_amount

                results["updated"].append({
                    "payer_code": payer_code,
                    "total_amount": total_amount,
                    "transactions": len(transactions)
                })

            # -------------------------------
            # CREATE WALLET
            # -------------------------------
            else:
                wallet = TblStudentWallet(
                    reg_no=payer_code,
                    dept=0,
                    is_paid="Yes"
                )

                db.session.add(wallet)
                db.session.flush()

                for txn in transactions:
                    transaction_id = str(txn.get("transaction_reference"))
                    amount = float(txn.get("paid_amount", 0))

                    total_amount += amount

                    TblStudentWallet.topup_wallet(
                        payer_code=payer_code,
                        external_transaction_id=transaction_id,
                        amount=amount
                    )

                wallet.dept = total_amount

                results["created"].append({
                    "payer_code": payer_code,
                    "total_amount": total_amount,
                    "transactions": len(transactions)
                })

            db.session.commit()

        except Exception as e:
            db.session.rollback()

            results["failed"].append({
                "payer_code": payer_code,
                "error": str(e)
            })

    return results


def main():
    if len(sys.argv) != 2:
        print("Usage:")
        print("  ./wallet_reconciliation_import.py <reconciliation.json>")
        sys.exit(1)

    json_file = Path(sys.argv[1])

    if not json_file.exists():
        print(f"File not found: {json_file}")
        sys.exit(1)

    app = create_app()

    with app.app_context():
        results = import_wallet_transactions(json_file)

    print(json.dumps(results, indent=4))


if __name__ == "__main__":
    main()
