import json
from application import db
from application.models.mis_models import TblStudentWallet


JSON_FILE_PATH = "/home/eaur/eaur_mis_quickbooks/application/files/payments_13_20.json"


def import_wallet_transactions():
    """
    Updates tbl_student_wallet using reconciliation JSON file
    """

    with open(JSON_FILE_PATH, "r") as f:
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

            # ----------------------------------
            # Existing wallet
            # ----------------------------------
            if wallet:
                # clear dept first
                wallet.dept = 0
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
                db.session.add(wallet)

                results["updated"].append({
                    "payer_code": payer_code,
                    "total_amount": total_amount,
                    "transactions": len(transactions)
                })

            # ----------------------------------
            # Create new wallet
            # ----------------------------------
            else:
                wallet = TblStudentWallet(
                    reg_no=payer_code,
                    dept=0,
                    is_paid="Yes"
                )

                db.session.add(wallet)
                db.session.flush()  # get ID

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
