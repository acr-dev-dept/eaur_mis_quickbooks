import json
from decimal import Decimal
from flask import Blueprint, jsonify, current_app, request
from application import db
from application.models.central_models import IntegrationLog
from application.models.mis_models import TblStudentWallet, TblStudentWalletHistory, TblPersonalUg, TblOnlineApplication, TblStudentWalletLedger, Payment
from sqlalchemy import func
import pandas as pd
import os
from datetime import datetime, timedelta
from application.models.central_models import IntegrationLog
from sqlalchemy.exc import IntegrityError
from datetime import date
from application.utils.database import db_manager
from application.services.opening_balance import OpeningBalanceSyncService



reconciliation_bp = Blueprint("reconciliation", __name__)

@reconciliation_bp.route("/valid-payments/total", methods=["GET"])
def get_total_valid_payments():
    """
    Returns the total amount and count of VALID payments from IntegrationLogs.
    """

    try:
        logs = (
            db.session.query(IntegrationLog)
            .filter(IntegrationLog.response_data.like('%VALID%'))
            .all()
        )

        total_amount = Decimal("0.00")
        valid_count = 0

        for log in logs:
            try:
                if isinstance(log.response_data, dict):
                    response = log.response_data
                elif isinstance(log.response_data, str):
                    response = json.loads(log.response_data)
                else:
                    current_app.logger.warning(
                        f"Unsupported response_data type in IntegrationLogs id={log.id}"
                    )
                    continue

            except json.JSONDecodeError:
                current_app.logger.warning(
                    f"Invalid JSON in IntegrationLogs id={log.id}"
                )
                continue

            if response.get("transaction_status") != "VALID":
                continue

            amount = response.get("amount")
            if not amount:
                continue

            try:
                total_amount += Decimal(str(amount))
                valid_count += 1
            except Exception:
                current_app.logger.warning(
                    f"Invalid amount format in IntegrationLogs id={log.id}: {amount}"
                )

        return jsonify({
            "status": "success",
            "data": {
                "total_valid_transactions": valid_count,
                "total_amount": str(total_amount),
                "currency": "RWF"
            }
        }), 200

    except Exception as e:
        current_app.logger.exception("Failed to aggregate VALID payments")
        return jsonify({
            "status": "error",
            "message": "Internal server error"
        }), 500


"""
@reconciliation_bp.route("/clean-duplicate-logs", methods=["POST"])
def clean_duplicate_integration_logs():
    
    #Removes duplicate IntegrationLog records based on external_transaction_id.
    #Keeps the oldest record and deletes the rest.
    

    try:
        # Step 1: find transaction_ids with duplicates
        duplicates = (
            db.session.query(
                IntegrationLog.external_transaction_id,
                func.count(IntegrationLog.id).label("cnt")
            )
            .group_by(IntegrationLog.external_transaction_id)
            .having(func.count(IntegrationLog.id) > 1)
            .all()
        )

        total_deleted = 0
        for txn_id, count in duplicates:
            # Step 2: fetch all logs for this transaction_id ordered by id (oldest first)
            logs = (
                db.session.query(IntegrationLog)
                .filter_by(external_transaction_id=txn_id)
                .order_by(IntegrationLog.id.asc())
                .all()
            )

            # Keep the first one, delete the rest
            for duplicate_log in logs[1:]:
                db.session.delete(duplicate_log)
                total_deleted += 1

            current_app.logger.info(f"Cleaned {count - 1} duplicate logs for transaction {txn_id}")

        db.session.commit()

        return jsonify({
            "status": "success",
            "total_duplicates_removed": total_deleted,
            "total_transactions_checked": len(duplicates)
        }), 200

    except Exception as e:
        current_app.logger.exception("Failed to clean duplicate integration logs")
        db.session.rollback()
        return jsonify({
            "status": "error",
            "message": "Internal server error",
            "error": str(e)
        }), 500

"""
@reconciliation_bp.route("/duplicate-wallets", methods=["GET"])
def get_duplicate_external_transaction_ids():
    """
    Returns wallet records that have duplicate external_transaction_id
    """

    # Step 1: find duplicated external_transaction_ids
    duplicate_ids_subquery = (
        db.session.query(
            TblStudentWallet.external_transaction_id
        )
        .filter(TblStudentWallet.external_transaction_id.isnot(None))
        .group_by(TblStudentWallet.external_transaction_id)
        .having(func.count(TblStudentWallet.id) > 1)
        .subquery()
    )

    # Step 2: fetch all records with those duplicated IDs
    duplicate_records = (
        db.session.query(TblStudentWallet)
        .filter(
            TblStudentWallet.external_transaction_id.in_(
                duplicate_ids_subquery
            )
        )
        .order_by(
            TblStudentWallet.external_transaction_id,
            TblStudentWallet.date.asc()
        )
        .all()
    )

    results = []

    for record in duplicate_records:
        results.append({
            
            record.external_transaction_id: {
                "id": record.id,
                "payer_code": record.reg_no,
                "amount": str(record.dept),
                "date": record.payment_date.isoformat() if record.payment_date else None,
            }
        })

    return jsonify({
        "status": "success",
        "duplicate_count": len(results),
        "records": results
    }), 200


@reconciliation_bp.route("/analyze-transactions", methods=["POST"])
def analyze_transactions_file():
    """
    Receives a file path and returns transaction statistics
    grouped by payer code with transaction-level details.

    Assumes:
    - First row is header
    - Only Txn Status = SUCCESSFUL or PENDING_SETTLEMENT is included
    """

    data = request.get_json(silent=True)

    if not data or "file_path" not in data:
        return jsonify({
            "status": "error",
            "message": "file_path is required"
        }), 400

    file_path = data["file_path"]

    if not os.path.exists(file_path):
        return jsonify({
            "status": "error",
            "message": "File not found",
            "file_path": file_path
        }), 404

    try:
        # Explicitly tell pandas first row is header
        df = pd.read_csv(
            file_path,
            header=0,
            skip_blank_lines=True
        )

        # Normalize column names (important for bank files)
        df.columns = df.columns.str.strip()

        required_columns = {
            "Payer Code",
            "Paid Amount",
            "Txn Status",
            "Int. Txn Ref."
        }

        missing = required_columns - set(df.columns)

        if missing:
            return jsonify({
                "status": "error",
                "message": "Missing required columns",
                "missing_columns": list(missing)
            }), 400

        # ------------------------------------
        # Filter SUCCESSFUL transactions and PENDING_SETTLEMENT transactions
        # ------------------------------------
        df = df[
            (df["Txn Status"] == "SUCCESSFUL") |
            (df["Txn Status"] == "PENDING_SETTLEMENT")
        ]


        # ------------------------------------
        # Convert paid amount safely
        # ------------------------------------
        df["Paid Amount"] = (
            df["Paid Amount"]
            .astype(str)
            .str.replace(",", "", regex=False)
        )

        df["Paid Amount"] = pd.to_numeric(
            df["Paid Amount"],
            errors="coerce"
        ).fillna(0)

        # ------------------------------------
        # Overall summary
        # ------------------------------------
        total_transactions = int(len(df))
        total_amount = float(df["Paid Amount"].sum())

        # ------------------------------------
        # Group per payer code
        # ------------------------------------
        per_payer_code = {}

        for payer_code, group in df.groupby("Payer Code"):
            transactions = []

            for _, row in group.iterrows():
                transactions.append({
                    "transaction_reference": row["Int. Txn Ref."],
                    "paid_amount": float(row["Paid Amount"]),
                    "slip_no": row.get("Bank Slip", None)
                })

            per_payer_code[str(payer_code)] = {
                "transaction_count": int(len(group)),
                "total_paid_amount": float(group["Paid Amount"].sum()),
                "transactions": transactions
            }

        return jsonify({
            "status": "success",
            "file_path": file_path,
            "summary": {
                "total_transactions": total_transactions,
                "total_paid_amount": round(total_amount, 2)
            },
            "per_payer_code": per_payer_code
        }), 200

    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


@reconciliation_bp.route("/wallet_hist_vs_cloud_pyts", methods=["POST"])
def wallet_hist_vs_cloud_pyts():
    """
    Wallet ↔ Cloud reconciliation with date-range filtering.

    Payload:
    {
        "file_path": ".../payments.json",
        "date_from": "YYYY-MM-DD",
        "date_to": "YYYY-MM-DD"
    }

    payments.json structure:
    {
        "per_payer_code": {
            "PAYER001": {
                "transactions": [
                    {
                        "transaction_reference": "TRX123",
                        "paid_amount": 1000.00,
                        "slip_no": "SLIP001"
                    },
                    ...
                ]
            },
            ...
        }
    """

    try:
        payload = request.get_json()

        required = ["file_path", "date_from", "date_to"]
        if not payload or not all(k in payload for k in required):
            return jsonify({
                "status": "error",
                "message": "file_path, date_from and date_to are required"
            }), 400

        # ---------------------------------------------------------------
        # Date handling
        # ---------------------------------------------------------------

        date_from = datetime.strptime(payload["date_from"], "%Y-%m-%d")
        date_to = datetime.strptime(payload["date_to"], "%Y-%m-%d") + timedelta(days=1)

        file_path = payload["file_path"]

        if not os.path.exists(file_path):
            return jsonify({
                "status": "error",
                "message": f"JSON file not found: {file_path}"
            }), 404

        # ---------------------------------------------------------------
        # STEP 1 — LOAD CLOUD PAYMENTS JSON
        # ---------------------------------------------------------------

        with open(file_path, "r") as f:
            cloud_json = json.load(f)

        cloud_map = {}

        for payer_code, block in cloud_json.get("per_payer_code", {}).items():
            for trx in block.get("transactions", []):

                trx_ref = str(trx.get("transaction_reference"))
                amount = float(trx.get("paid_amount", 0))

                if trx_ref not in cloud_map:
                    cloud_map[trx_ref] = {
                        "cloud_total": 0.0,
                        "transactions": []
                    }

                cloud_map[trx_ref]["cloud_total"] += amount
                cloud_map[trx_ref]["transactions"].append({
                    "payer_code": payer_code,
                    "paid_amount": amount,
                    "slip_no": trx.get("slip_no")
                })

        # ---------------------------------------------------------------
        # STEP 2 — WALLET HISTORY FILTERED BY DATE
        # ---------------------------------------------------------------

        wallet_rows = (
            db.session.query(
                TblStudentWalletHistory.external_transaction_id.label("trx_id"),
                func.count(TblStudentWalletHistory.id).label("entries"),
                func.sum(TblStudentWalletHistory.amount).label("wallet_total"),
                func.min(TblStudentWalletHistory.created_at).label("first_posted"),
                func.max(TblStudentWalletHistory.created_at).label("last_posted")
            )
            .filter(
                TblStudentWalletHistory.external_transaction_id.isnot(None),
                TblStudentWalletHistory.created_at >= date_from,
                TblStudentWalletHistory.created_at < date_to
            )
            .group_by(TblStudentWalletHistory.external_transaction_id)
            .all()
        )

        wallet_map = {
            str(row.trx_id): {
                "wallet_total": float(row.wallet_total or 0),
                "wallet_entries": int(row.entries),
                "first_posted": row.first_posted,
                "last_posted": row.last_posted
            }
            for row in wallet_rows
        }

        # ---------------------------------------------------------------
        # STEP 3 — BIDIRECTIONAL RECONCILIATION
        # ---------------------------------------------------------------

        matched = []

        absent = {
            "absent_in_wallet": [],
            "absent_in_cloud": []
        }

        mismatches = {
            "amount_mismatch": [],
            "duplicate_wallet_entries": []
        }

        all_refs = set(wallet_map.keys()) | set(cloud_map.keys())

        for trx_ref in all_refs:

            wallet = wallet_map.get(trx_ref)
            cloud = cloud_map.get(trx_ref)

            # -----------------------------------------------------------
            # Absent in wallet
            # -----------------------------------------------------------
            if cloud and not wallet:
                absent["absent_in_wallet"].append({
                    "transaction_reference": trx_ref,
                    "cloud_total": cloud["cloud_total"],
                    "cloud_transactions": cloud["transactions"]
                })
                continue

            # -----------------------------------------------------------
            # Absent in cloud
            # -----------------------------------------------------------
            if wallet and not cloud:
                absent["absent_in_cloud"].append({
                    "transaction_reference": trx_ref,
                    "wallet_total": wallet["wallet_total"],
                    "wallet_entries": wallet["wallet_entries"],
                    "first_posted": wallet["first_posted"],
                    "last_posted": wallet["last_posted"]
                })
                continue

            # -----------------------------------------------------------
            # Duplicate wallet posting
            # -----------------------------------------------------------
            if wallet["wallet_entries"] > 1:
                mismatches["duplicate_wallet_entries"].append({
                    "transaction_reference": trx_ref,
                    "wallet_entries": wallet["wallet_entries"],
                    "wallet_total": wallet["wallet_total"]
                })

            # -----------------------------------------------------------
            # Amount mismatch
            # -----------------------------------------------------------
            if round(wallet["wallet_total"], 2) != round(cloud["cloud_total"], 2):
                mismatches["amount_mismatch"].append({
                    "transaction_reference": trx_ref,
                    "wallet_total": wallet["wallet_total"],
                    "cloud_total": cloud["cloud_total"],
                    "difference": round(
                        wallet["wallet_total"] - cloud["cloud_total"], 2
                    )
                })
            else:
                matched.append({
                    "transaction_reference": trx_ref,
                    "amount": wallet["wallet_total"]
                })

        # ---------------------------------------------------------------
        # RESPONSE
        # ---------------------------------------------------------------

        return jsonify({
            "status": "success",
            "date_range": {
                "from": payload["date_from"],
                "to": payload["date_to"]
            },
            "summary": {
                "wallet_refs": len(wallet_map),
                "cloud_refs": len(cloud_map),
                "matched": len(matched),
                "absent_in_wallet": len(absent["absent_in_wallet"]),
                "absent_in_cloud": len(absent["absent_in_cloud"]),
                "amount_mismatch": len(mismatches["amount_mismatch"]),
                "duplicate_wallet_entries": len(mismatches["duplicate_wallet_entries"])
            },
            "absent": absent,
            "mismatches": mismatches,
            "matched": matched
        }), 200

    except Exception as e:
        current_app.logger.exception("Date-range reconciliation failed")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


@reconciliation_bp.route("/import_wallet_history_from_json", methods=["POST"])
def import_wallet_history_from_json():
    """
    Imports cloud payment JSON into tbl_student_wallet_history.

    BALANCE RULE:
    - balance_before starts at 0 per payer_code
    - balances are computed ONLY from cloud data
    - existing wallet data is NOT read
    """

    try:
        payload = request.get_json()

        if not payload or "file_path" not in payload:
            return jsonify({
                "status": "error",
                "message": "file_path is required"
            }), 400

        file_path = payload["file_path"]

        if not os.path.exists(file_path):
            return jsonify({
                "status": "error",
                "message": f"File not found: {file_path}"
            }), 404

        # ------------------------------------------------------------
        # LOAD CLOUD JSON
        # ------------------------------------------------------------

        with open(file_path, "r") as f:
            cloud_json = json.load(f)

        payer_blocks = cloud_json.get("per_payer_code", {})

        inserted = []
        skipped_duplicates = []
        failed = []

        # ------------------------------------------------------------
        # PROCESS PER PAYER (ISOLATED BALANCES)
        # ------------------------------------------------------------

        for payer_code, block in payer_blocks.items():

            running_balance = 0.0

            transactions = block.get("transactions", [])

            # Optional but recommended ordering
            transactions.sort(
                key=lambda x: str(x.get("transaction_reference"))
            )

            for trx in transactions:

                try:
                    trx_ref = str(trx.get("transaction_reference"))
                    amount = float(trx.get("paid_amount", 0))
                    slip_no = trx.get("slip_no")

                    if not trx_ref:
                        continue

                    # ------------------------------------------------
                    # IDEMPOTENCY
                    # ------------------------------------------------

                    exists = (
                        db.session.query(TblStudentWalletHistory.id)
                        .filter(
                            TblStudentWalletHistory.external_transaction_id == trx_ref
                        )
                        .first()
                    )

                    if exists:
                        skipped_duplicates.append({
                            "transaction_reference": trx_ref,
                            "payer_code": payer_code
                        })
                        continue

                    balance_before = running_balance
                    balance_after = running_balance + amount

                    wallet_entry = TblStudentWalletHistory(
                        wallet_id=None,
                        reg_no=payer_code,
                        reference_number=slip_no,
                        transaction_type="TOPUP",
                        amount=amount,
                        balance_before=balance_before,
                        balance_after=balance_after,
                        trans_code=slip_no,
                        external_transaction_id=trx_ref,
                        payment_chanel="CLOUD_JSON_IMPORT",
                        slip_no=slip_no,
                        comment="Imported from cloud JSON (cloud-based balance)",
                        created_by="system_reconciliation"
                    )

                    db.session.add(wallet_entry)

                    running_balance = balance_after

                    inserted.append({
                        "transaction_reference": trx_ref,
                        "payer_code": payer_code,
                        "amount": amount,
                        "balance_after": balance_after
                    })

                except Exception as row_error:
                    failed.append({
                        "transaction_reference": trx.get("transaction_reference"),
                        "payer_code": payer_code,
                        "error": str(row_error)
                    })

        db.session.commit()

        # ------------------------------------------------------------
        # RESPONSE
        # ------------------------------------------------------------

        return jsonify({
            "status": "success",
            "summary": {
                "inserted": len(inserted),
                "skipped_duplicates": len(skipped_duplicates),
                "failed": len(failed)
            },
            "inserted": inserted,
            "skipped_duplicates": skipped_duplicates,
            "failed": failed
        }), 200

    except Exception as e:
        db.session.rollback()
        current_app.logger.exception("Cloud-based wallet import failed")

        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@reconciliation_bp.route("/sync-absent-wallet-payments", methods=["POST"])
def sync_absent_wallet_payments():
    """
    Syncs wallet payments that are absent in the wallet system
    based on the provided JSON payload.

    Payload:
     {
        "absent_in_wallet": [
            {
                "cloud_total": 20000.0,
                "cloud_transactions": [
                    {
                        "paid_amount": 20000.0,
                        "payer_code": "25100683",
                        "slip_no": "FT26026KKTMK"
                    }
                ],
                "transaction_reference": "11202601252123066871"
            },
            ...
        ]
    }
    """
    payload = request.get_json()

    if not payload or "absent_in_wallet" not in payload:
        return jsonify({
            "status": 400,
            "message": "Invalid payload structure"
        }), 400

    results = []

    for record in payload["absent_in_wallet"]:

        transaction_reference = record.get("transaction_reference")
        cloud_total = float(record.get("cloud_total", 0))
        transactions = record.get("cloud_transactions", [])

        if not transactions:
            continue

        for tx in transactions:

            payer_code = tx.get("payer_code")
            slip_no = tx.get("slip_no")
            amount = float(tx.get("paid_amount", 0))
            payment_channel = "MOMO"
            transaction_status = "SUCCESS"
            started_at = datetime.now()

            # check if transaction already exists
            existing_tx = TblStudentWalletHistory.get_by_transaction_id(transaction_reference)

            if existing_tx:
                current_app.logger.info(
                    f"Duplicate transaction ignored: {transaction_reference}"
                )
                results.append({
                    "payer_code": payer_code,
                    "transaction_reference": transaction_reference,
                    "status": "DUPLICATE"
                })
                continue
            # ────────────────────────────────────────────────
            # Resolve payer
            # ────────────────────────────────────────────────
            student = TblPersonalUg.get_student_data(payer_code)
            applicant = None

            if not student:
                applicant = TblOnlineApplication.get_applicant_data(payer_code)

            if not student and not applicant:
                current_app.logger.error(f"Payer not found: {payer_code}")
                results.append({
                    "payer_code": payer_code,
                    "status": "FAILED",
                    "reason": "Payer not found"
                })
                continue

            reg_no = student.reg_no if student else applicant.tracking_id



            # ────────────────────────────────────────────────
            # Wallet lookup
            # ────────────────────────────────────────────────

            with TblStudentWalletHistory.get_session() as session:
                wallet = TblStudentWallet.get_by_reg_no(session, reg_no)

                try:
                    balance_before = wallet.dept if wallet else 0.0
                    balance_after = balance_before + amount

                    
                    
                    # Wallet history (IDEMPOTENT)
                    # UNIQUE(external_transaction_id)
                    
                    history = TblStudentWalletHistory(
                        wallet_id=wallet.id if wallet else None,
                        reg_no=reg_no,
                        reference_number=wallet.reference_number or None
                        if wallet else f"{int(datetime.now().strftime('%Y%m%d%H%M%S'))}_{reg_no}",
                        transaction_type="TOPUP",
                        slip_no=slip_no,
                        amount=amount,
                        balance_before=balance_before,
                        balance_after=balance_after,
                        trans_code=transaction_reference,
                        external_transaction_id=transaction_reference,
                        payment_chanel=payment_channel,
                        bank_id=wallet.bank_id if wallet else 2,
                        created_at=datetime(2026, 1, 25, 22, 0, 0),
                        comment="Wallet top-up",
                        created_by="SYSTEM"
                    )

                    session.add(history)
                    session.flush()
                    # check if transaction existed in ledger
                    existing_ledger_tx = TblStudentWalletLedger.get_by_transaction_id(transaction_reference)
                    if existing_ledger_tx:
                        continue

                    # Create ledger entry

                    if amount >= 0:
                        ledger_entry = TblStudentWalletLedger(
                            student_id=reg_no,
                            direction="credit",
                            original_amount=abs(Decimal(amount)),
                            amount=amount,
                            trans_code=transaction_reference,
                            payment_chanel=payment_channel,
                            bank_id=2,
                            source="sales_receipt",
                            slip_no=slip_no,
                            created_at=datetime.now()
                    )
                        session.add(ledger_entry)
                        session.flush()

                except IntegrityError:
                    session.rollback()
                    current_app.logger.info(
                        f"Duplicate wallet transaction ignored: {transaction_reference}"
                    )

                    results.append({
                        "payer_code": payer_code,
                        "transaction_reference": transaction_reference,
                        "status": "DUPLICATE"
                    })
                    continue

                # ────────────────────────────────────────────────
                # Update or create wallet
                # ────────────────────────────────────────────────
                if wallet:
                    wallet.dept = balance_after
                    wallet.external_transaction_id = transaction_reference
                    wallet.trans_code = transaction_reference
                    wallet.payment_date = datetime.now()
                    session.add(wallet)
                    session.flush()
                else:
                    created_wallet = TblStudentWallet(
                        reg_prg_id=int(datetime.now().strftime("%Y%m%d%H%M%S")),
                        reg_no=reg_no,
                        reference_number=f"{int(datetime.now().strftime('%Y%m%d%H%M%S'))}_{reg_no}",
                        trans_code=transaction_reference,
                        external_transaction_id=transaction_reference,
                        payment_chanel=payment_channel,
                        payment_date=date.today(),
                        is_paid="Yes",
                        dept=amount,
                        fee_category=128,
                        bank_id=2,
                        slip_no=slip_no if slip_no else "N/A"
                    )
                    
                    session.add(created_wallet)
                    session.flush()


                # ────────────────────────────────────────────────
                # Integration log
                # ────────────────────────────────────────────────
                IntegrationLog.log_integration_operation(
                    system_name="UrubutoPay",
                    operation="Wallet Payment",
                    status=transaction_status,
                    external_transaction_id=transaction_reference,
                    payer_code=payer_code,
                    response_data=tx,
                    started_at=started_at,
                    completed_at=datetime.now()
                )

                results.append({
                    "payer_code": payer_code,
                    "reg_no": reg_no,
                    "amount": amount,
                    "transaction_reference": transaction_reference,
                    "status": "SUCCESS"
                })

    return jsonify({
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "status": 200,
        "processed": len(results),
        "results": results
    }), 200


@reconciliation_bp.route("/translate_to_json", methods=["POST"])
def translate_to_json():

    data = request.get_json()
    absent_in_wallet = []

    for payer_code, info in data.get("per_payer_code", {}).items():
        total_paid = info.get("total_paid_amount", 0)
        transactions = info.get("transactions", [])

        cloud_transactions = []
        for tx in transactions:
            cloud_transactions.append({
                "paid_amount": tx.get("paid_amount"),
                "payer_code": payer_code,
                "slip_no": tx.get("slip_no")  # can be None
            })

        absent_in_wallet.append({
            "cloud_total": total_paid,
            "transaction_reference": str(transactions[0]["transaction_reference"]) if transactions else None,
            "cloud_transactions": cloud_transactions
        })

    result = {
        "absent_in_wallet": absent_in_wallet
    }

    return jsonify(result), 200

from datetime import datetime
from flask import jsonify
from sqlalchemy import func

# Assuming these are already imported in your file:
# from your_app import reconciliation_bp, db_manager
# from your_models import IntegrationLog


@reconciliation_bp.route("/payments-before-cutoff", methods=["GET"])
def payments_before_cutoff_report():
    CUTOFF_DATETIME = datetime(2026, 1, 13, 0, 0, 0)

    # Define JSON paths (adjust these if your actual keys are different!)
    JSON_PATH_AMOUNT = "$.amount"
    JSON_PATH_PAYER_CODE = "$.payer_code"
    JSON_PATH_PAYMENT_DATETIME = "$.payment_date_time"   # ← confirm this key!

    # Critical: match this EXACTLY to the format in your JSON string
    # Run the SQL query I suggested to check examples and adjust
    DATETIME_FORMAT = '%Y-%m-%d %H:%i:%s'   # ← CHANGE THIS BASED ON YOUR DATA

    with db_manager.get_mis_session() as session:
        try:
            # ---- Aggregates ----
            aggregates = (
                session.query(
                    func.count(IntegrationLog.id).label("count"),
                    func.coalesce(
                        func.sum(
                            func.cast(
                                func.JSON_UNQUOTE(
                                    func.JSON_EXTRACT(IntegrationLog.response_data, JSON_PATH_AMOUNT)
                                ),
                                "DECIMAL(18,2)"
                            )
                        ), 0
                    ).label("total_amount"),
                    func.min(
                        func.STR_TO_DATE(
                            func.JSON_UNQUOTE(
                                func.JSON_EXTRACT(IntegrationLog.response_data, JSON_PATH_PAYMENT_DATETIME)
                            ),
                            DATETIME_FORMAT
                        )
                    ).label("from_payment_time"),
                    func.max(
                        func.STR_TO_DATE(
                            func.JSON_UNQUOTE(
                                func.JSON_EXTRACT(IntegrationLog.response_data, JSON_PATH_PAYMENT_DATETIME)
                            ),
                            DATETIME_FORMAT
                        )
                    ).label("to_payment_time")
                )
                .filter(
                    func.STR_TO_DATE(
                        func.JSON_UNQUOTE(
                            func.JSON_EXTRACT(IntegrationLog.response_data, JSON_PATH_PAYMENT_DATETIME)
                        ),
                        DATETIME_FORMAT
                    ) < CUTOFF_DATETIME,
                    func.JSON_EXTRACT(IntegrationLog.response_data, JSON_PATH_PAYMENT_DATETIME).isnot(None),
                    func.STR_TO_DATE(
                        func.JSON_UNQUOTE(
                            func.JSON_EXTRACT(IntegrationLog.response_data, JSON_PATH_PAYMENT_DATETIME)
                        ),
                        DATETIME_FORMAT
                    ).isnot(None)
                )
                .one()
            )

            # ---- Records ----
            records = (
                session.query(
                    IntegrationLog.id,
                    func.JSON_UNQUOTE(
                        func.JSON_EXTRACT(IntegrationLog.response_data, JSON_PATH_PAYER_CODE)
                    ).label("payer_code"),
                    func.cast(
                        func.JSON_UNQUOTE(
                            func.JSON_EXTRACT(IntegrationLog.response_data, JSON_PATH_AMOUNT)
                        ),
                        "DECIMAL(18,2)"
                    ).label("amount")
                )
                .filter(
                    func.STR_TO_DATE(
                        func.JSON_UNQUOTE(
                            func.JSON_EXTRACT(IntegrationLog.response_data, JSON_PATH_PAYMENT_DATETIME)
                        ),
                        DATETIME_FORMAT
                    ) < CUTOFF_DATETIME,
                    func.JSON_EXTRACT(IntegrationLog.response_data, JSON_PATH_PAYMENT_DATETIME).isnot(None),
                    func.STR_TO_DATE(
                        func.JSON_UNQUOTE(
                            func.JSON_EXTRACT(IntegrationLog.response_data, JSON_PATH_PAYMENT_DATETIME)
                        ),
                        DATETIME_FORMAT
                    ).isnot(None)
                )
                .order_by(
                    func.STR_TO_DATE(
                        func.JSON_UNQUOTE(
                            func.JSON_EXTRACT(IntegrationLog.response_data, JSON_PATH_PAYMENT_DATETIME)
                        ),
                        DATETIME_FORMAT
                    ).asc()
                )
                .all()
            )

            data = [
                {
                    "id": r.id,
                    "payer_code": r.payer_code,
                    "amount": float(r.amount)
                }
                for r in records
            ]

            return jsonify({
                "timestamp": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
                "status": 200,
                "cutoff_date": CUTOFF_DATETIME.strftime("%Y-%m-%d %H:%M:%S"),
                "summary": {
                    "count": aggregates.count,
                    "total_amount": float(aggregates.total_amount or 0),
                    "from_payment_time": (
                        aggregates.from_payment_time.strftime("%Y-%m-%d %H:%M:%S")
                        if aggregates.from_payment_time else None
                    ),
                    "to_payment_time": (
                        aggregates.to_payment_time.strftime("%Y-%m-%d %H:%M:%S")
                        if aggregates.to_payment_time else None
                    )
                },
                "data": data
            }), 200

        except Exception as e:
            session.rollback()
            return jsonify({
                "timestamp": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
                "status": 500,
                "message": "Failed to generate payments report",
                "error": str(e)
            }), 500

from sqlalchemy import and_

import json
from flask import jsonify
from datetime import datetime, timedelta
from sqlalchemy import and_

@reconciliation_bp.route("/integration-logs/feb-04", methods=["GET"])
def get_feb_04_integration_logs():
    """
    Fetch integration logs created on 4th February.
    Returns response_data as JSON, payer_code, external_transaction_id.
    """

    # Define date range for Feb 4 (00:00:00 → 23:59:59)
    start_date = datetime(2026, 2, 4, 0, 0, 0)
    end_date = start_date + timedelta(days=1)

    logs = (
        db.session.query(
            IntegrationLog.response_data,
            IntegrationLog.payer_code,
            IntegrationLog.external_transaction_id,
        )
        .filter(
            and_(
                IntegrationLog.created_at >= start_date,
                IntegrationLog.created_at < end_date,
            )
        )
        .order_by(IntegrationLog.created_at.asc())
        .all()
    )

    result = []
    for log in logs:
        # Convert string to JSON/dict
        try:
            response_json = json.loads(log.response_data)
        except json.JSONDecodeError:
            response_json = log.response_data  # fallback if it's not valid JSON
        result.append({
            "response_data": response_json,
            "payer_code": log.payer_code,
            "external_transaction_id": log.external_transaction_id,
        })

    return jsonify({
        "date": "2026-02-04",
        "record_count": len(result),
        "records": result,
    }), 200


from flask import request, jsonify
from datetime import datetime

@reconciliation_bp.route("/filter-before-jan-13", methods=["POST"])
def filter_before_jan_13():
    """
    Accepts JSON payload in the same structure as /integration-logs/feb-04,
    returns only response_data where payment_date_time < 2026-01-13,
    and includes the total amount.
    """

    payload = request.get_json()
    if not payload or "records" not in payload:
        return jsonify({"error": "Invalid payload"}), 400

    cutoff_date = datetime(2026, 1, 13, 0, 0, 0)

    filtered_response_data = []
    total_amount = 0.0

    for record in payload["records"]:
        response_data = record.get("response_data")
        if not response_data:
            continue

        payment_date_str = response_data.get("payment_date_time")
        if not payment_date_str:
            continue

        try:
            payment_date = datetime.strptime(payment_date_str, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            continue  # skip invalid date formats

        if payment_date < cutoff_date:
            filtered_response_data.append(response_data)
            amount = response_data.get("amount", 0)
            try:
                total_amount += float(amount)
            except (TypeError, ValueError):
                continue  # skip if amount is invalid

    return jsonify({
        "cutoff_date": "2026-01-13",
        "filtered_count": len(filtered_response_data),
        "total_amount": total_amount,
        "records": filtered_response_data
    }), 200


from flask import request, jsonify
from sqlalchemy.exc import SQLAlchemyError

@reconciliation_bp.route("/delete-and-update-wallet-bulk", methods=["POST"])
def delete_and_update_wallet_bulk():
    """
    Optimized bulk deletion and wallet update.
    Accepts JSON payload like /filter-before-jan-13 output.
    Reports success, failures, and total amount handled.
    """
    payload = request.get_json()
    if not payload or "records" not in payload:
        return jsonify({"error": "Invalid payload"}), 400

    transaction_ids = [r.get("transaction_id") or r.get("external_transaction_id") for r in payload["records"]]
    payer_codes = [r.get("payer_code") for r in payload["records"]]

    success = {
        "ledger_deleted": [],
        "history_deleted": [],
        "wallet_updated": []
    }
    failed = {
        "ledger_skipped": [],
        "history_skipped": [],
        "wallet_skipped": []
    }

    total_amount_handled = 0.0

    try:
        # ---------------------------
        # Bulk fetch Ledger entries
        # ---------------------------
        ledgers = db.session.query(TblStudentWalletLedger)\
            .filter(TblStudentWalletLedger.trans_code.in_(transaction_ids)).all()
        ledger_map = {l.trans_code: l for l in ledgers}

        # Bulk fetch History entries
        histories = db.session.query(TblStudentWalletHistory)\
            .filter(TblStudentWalletHistory.external_transaction_id.in_(transaction_ids)).all()
        history_map = {h.external_transaction_id: h for h in histories}

        # Bulk fetch Wallet entries
        wallets = db.session.query(TblStudentWallet)\
            .filter(TblStudentWallet.reg_no.in_(payer_codes)).all()
        wallet_map = {w.reg_no: w for w in wallets}

        # ---------------------------
        # Process each record
        # ---------------------------
        for record in payload["records"]:
            transaction_id = record.get("transaction_id") or record.get("external_transaction_id")
            payer_code = record.get("payer_code")
            amount = float(record.get("amount", 0))

            # Ledger deletion
            ledger_entry = ledger_map.get(transaction_id)
            if ledger_entry:
                if not ledger_entry.quickbooks_id:
                    db.session.delete(ledger_entry)
                    success["ledger_deleted"].append(transaction_id)
                    total_amount_handled += amount
                else:
                    failed["ledger_skipped"].append({
                        "transaction_id": transaction_id,
                        "reason": "Ledger has quickbooks_id"
                    })

            # History deletion
            history_entry = history_map.get(transaction_id)
            if history_entry:
                db.session.delete(history_entry)
                success["history_deleted"].append(transaction_id)
                total_amount_handled += amount
            else:
                failed["history_skipped"].append({
                    "transaction_id": transaction_id,
                    "reason": "Not found in history"
                })

            # Wallet update
            wallet_entry = wallet_map.get(payer_code)
            if wallet_entry:
                current_dept = float(wallet_entry.dept or 0)
                new_dept = current_dept - amount
                if new_dept >= 0:
                    wallet_entry.dept = new_dept
                    db.session.add(wallet_entry)
                    success["wallet_updated"].append({
                        "reg_no": payer_code,
                        "old_dept": current_dept,
                        "new_dept": new_dept
                    })
                    total_amount_handled += amount
                else:
                    failed["wallet_skipped"].append({
                        "reg_no": payer_code,
                        "reason": f"Dept would become negative ({current_dept} - {amount})"
                    })
            else:
                failed["wallet_skipped"].append({
                    "reg_no": payer_code,
                    "reason": "Wallet entry not found"
                })

        db.session.commit()
    except SQLAlchemyError as e:
        db.session.rollback()
        return jsonify({
            "error": "Database error",
            "message": str(e)
        }), 500

    return jsonify({
        "status": "completed",
        "total_amount_handled": total_amount_handled,
        "success": success,
        "failed": failed
    }), 200


import re
from flask import request, jsonify

@reconciliation_bp.route("/wallet-reference-lookup", methods=["POST"])
def wallet_reference_lookup():
    """
    For each skipped wallet entry:
    - Lookup TblStudentWallet by reg_no
    - Return reference_number
    - Extract amount from reason
    """

    payload = request.get_json()
    if not payload or "wallet_skipped" not in payload:
        return jsonify({"error": "Invalid payload"}), 400

    reg_nos = [w.get("reg_no") for w in payload["wallet_skipped"] if w.get("reg_no")]

    # Bulk fetch wallets
    wallets = (
        db.session.query(TblStudentWallet)
        .filter(TblStudentWallet.reg_no.in_(reg_nos))
        .all()
    )
    wallet_map = {w.reg_no: w for w in wallets}

    results = []

    for item in payload["wallet_skipped"]:
        reg_no = item.get("reg_no")
        reason = item.get("reason", "")

        # Extract amount from reason: (X - AMOUNT)
        amount = None
        match = re.search(r"-\s*([\d\.]+)\)", reason)
        if match:
            amount = float(match.group(1))

        wallet = wallet_map.get(reg_no)

        results.append({
            "reg_no": reg_no,
            "reference_number": wallet.reference_number if wallet else None,
            "amount": amount,
            "reason": reason,
            "wallet_found": bool(wallet)
        })

    return jsonify({
        "record_count": len(results),
        "records": results
    }), 200



from datetime import date
from flask import request, jsonify
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import func

@reconciliation_bp.route("/apply-wallet-deductions", methods=["POST"])
def apply_wallet_deductions():
    """
    Deduct amounts from Payment.amount
    ONLY for payments recorded on 2026-02-04
    """

    payload = request.get_json()
    if not payload or "records" not in payload:
        return jsonify({"error": "Invalid payload"}), 400

    success = []
    failed = []

    total_requested = 0.0
    total_deducted = 0.0

    TARGET_DATE = date(2026, 2, 4)

    try:
        for item in payload["records"]:
            reg_no = item.get("reg_no")
            wallet_ref = item.get("reference_number")
            remaining = float(item.get("amount", 0))

            total_requested += remaining

            if not wallet_ref or remaining <= 0:
                failed.append({
                    "reg_no": reg_no,
                    "reference_number": wallet_ref,
                    "reason": "Invalid reference number or amount"
                })
                continue

            payments = (
                db.session.query(Payment)
                .filter(
                    Payment.student_wallet_ref == wallet_ref,
                    func.date(Payment.recorded_date) == TARGET_DATE
                )
                .order_by(Payment.recorded_date.asc())
                .with_for_update()
                .all()
            )

            if not payments:
                failed.append({
                    "reg_no": reg_no,
                    "reference_number": wallet_ref,
                    "amount_requested": remaining,
                    "reason": "No payments found on 2026-02-04"
                })
                continue

            deductions = []

            for payment in payments:
                if remaining <= 0:
                    break

                if payment.amount is None or payment.amount <= 0:
                    continue

                before = float(payment.amount)
                deduct = min(before, remaining)

                payment.amount -= deduct
                remaining -= deduct
                total_deducted += deduct

                deductions.append({
                    "payment_id": payment.id,
                    "before": before,
                    "deducted": deduct,
                    "after": payment.amount,
                    "recorded_date": payment.recorded_date.isoformat()
                })

                db.session.add(payment)

            if remaining == 0:
                success.append({
                    "reg_no": reg_no,
                    "reference_number": wallet_ref,
                    "amount_requested": item["amount"],
                    "amount_deducted": item["amount"],
                    "deductions": deductions,
                    "status": "fully_applied"
                })
            else:
                failed.append({
                    "reg_no": reg_no,
                    "reference_number": wallet_ref,
                    "amount_requested": item["amount"],
                    "amount_deducted": item["amount"] - remaining,
                    "amount_remaining": remaining,
                    "deductions": deductions,
                    "reason": "Insufficient balance on 2026-02-04"
                })

        db.session.commit()

    except SQLAlchemyError as e:
        db.session.rollback()
        return jsonify({
            "error": "Database error",
            "message": str(e)
        }), 500

    return jsonify({
        "status": "completed",
        "summary": {
            "total_records": len(payload["records"]),
            "total_amount_requested": total_requested,
            "total_amount_deducted": total_deducted
        },
        "success_count": len(success),
        "failed_count": len(failed),
        "success": success,
        "failed": failed
    }), 200



from flask import request, jsonify
from sqlalchemy.exc import SQLAlchemyError

@reconciliation_bp.route("/revert-wallet-deductions", methods=["POST"])
def revert_wallet_deductions():
    """
    Revert wallet deductions by restoring payment.amount
    to its ORIGINAL 'before' value.
    """

    payload = request.get_json()
    if not payload or "records" not in payload:
        return jsonify({"error": "Invalid payload"}), 400

    reverted = []
    failed = []

    total_reverted = 0.0
    total_payments = 0

    try:
        for record in payload["records"]:
            reg_no = record.get("reg_no")
            wallet_ref = record.get("reference_number")

            for d in record.get("deductions", []):
                payment_id = d.get("payment_id")
                before_amount = d.get("before")

                total_payments += 1

                if payment_id is None or before_amount is None:
                    failed.append({
                        "reg_no": reg_no,
                        "reference_number": wallet_ref,
                        "payment_id": payment_id,
                        "reason": "Missing payment_id or before amount"
                    })
                    continue

                payment = (
                    db.session.query(Payment)
                    .filter(Payment.id == payment_id)
                    .with_for_update()
                    .first()
                )

                if not payment:
                    failed.append({
                        "reg_no": reg_no,
                        "reference_number": wallet_ref,
                        "payment_id": payment_id,
                        "reason": "Payment not found"
                    })
                    continue

                old_amount = float(payment.amount or 0)
                restored_amount = float(before_amount)

                payment.amount = restored_amount
                total_reverted += restored_amount

                db.session.add(payment)

                reverted.append({
                    "payment_id": payment.id,
                    "trans_code": payment.trans_code,
                    "reg_no": reg_no,
                    "reference_number": wallet_ref,
                    "before_deduction": restored_amount,
                    "previous_db_value": old_amount,
                    "restored_to": restored_amount
                })

        db.session.commit()

    except SQLAlchemyError as e:
        db.session.rollback()
        return jsonify({
            "error": "Database error",
            "message": str(e)
        }), 500

    return jsonify({
        "status": "completed",
        "summary": {
            "total_records": len(payload["records"]),
            "total_payments_processed": total_payments,
            "total_restored_amount": total_reverted,
            "reverted_count": len(reverted),
            "failed_count": len(failed)
        },
        "reverted": reverted,
        "failed": failed
    }), 200


from flask import Blueprint, request, jsonify
from datetime import datetime, timedelta
from sqlalchemy import and_, not_


@reconciliation_bp.route("/payments/trace-unexpected-zero", methods=["POST"])
def trace_unexpected_zero_payments():
    """
    Traces payments with amount = 0 between Feb 4–6, 2026
    that are NOT present in the provided JSON reference list.
    """

    payload = request.get_json(silent=True) or {}
    records = payload.get("records", [])

    # Extract reference numbers from provided JSON
    provided_refs = {
        r.get("reference_number")
        for r in records
        if r.get("reference_number")
    }

    # Date window: Feb 4 → Feb 7 (exclusive)
    start_date = datetime(2026, 2, 4, 0, 0, 0)
    end_date = datetime(2026, 2, 7, 0, 0, 0)

    query = (
        db.session.query(
            Payment.student_wallet_ref,
            Payment.amount,
            Payment.recorded_date,
        )
        .filter(
            and_(
                Payment.recorded_date >= start_date,
                Payment.recorded_date < end_date,
                Payment.amount == 0,
            )
        )
    )

    # Exclude known reference numbers
    if provided_refs:
        query = query.filter(
            not_(Payment.student_wallet_ref.in_(provided_refs))
        )

    results = query.order_by(Payment.recorded_date.asc()).all()

    response = [
        {
            "reference_number": r.student_wallet_ref,
            "amount": float(r.amount),
            "recorded_date": r.recorded_date.strftime("%Y-%m-%d %H:%M:%S"),
            "issue": "ZERO_AMOUNT_NOT_IN_INPUT_JSON",
        }
        for r in results
    ]

    return jsonify({
        "date_window": "2026-02-04 → 2026-02-06",
        "provided_reference_count": len(provided_refs),
        "unexpected_zero_payments": len(response),
        "records": response,
    }), 200

@reconciliation_bp.route("/outstanding-balance", methods=["GET"])
def get_outstanding_balance():
    """
    API Endpoint to fetch the 2024 invoice total, payment total,
    and outstanding balance for a given student reg_no.
    Example request: 
    payload : {
        "reg_no": "REG12345"}
    """
    reg_no = request.json.get("reg_no")
    if not reg_no:
        return {"error": "Missing 'reg_no' query parameter"}, 400

    service = OpeningBalanceSyncService()
    return service.get_outstanding_balance(reg_no)

from flask import Blueprint, jsonify
from sqlalchemy import text


@reconciliation_bp.route("/wallet-payments-summary", methods=["GET"])
def wallet_payments_summary():
    """
    Fetch payments and wallet history for each student_wallet record.
    Show totals, matched histories without duplicates, and highlight mismatches.
    """
    query = text("""
        SELECT
            w.reg_no,
            w.reference_number,
            p.id AS payment_id,
            p.amount AS payment_amount,
            p.recorded_date AS payment_date,
            h.id AS history_id,
            h.amount AS history_amount,
            h.created_at AS history_created_at
        FROM tbl_student_wallet w
        LEFT JOIN payment p
            ON p.student_wallet_ref = w.reference_number
        LEFT JOIN tbl_student_wallet_history h
            ON h.reg_no = w.reg_no
        ORDER BY w.reg_no, p.recorded_date
    """)

    result = db.session.execute(query).fetchall()

    wallets = {}

    for row in result:
        key = (row.reg_no, row.reference_number)

        if key not in wallets:
            wallets[key] = {
                "reg_no": row.reg_no,
                "reference_number": row.reference_number,
                "payments": [],
                "payment_count": 0,
                "payment_total": 0.0,
                "matched_histories": [],
                "history_match_count": 0,
                "wallet_history_total": 0.0,
                "mismatches": False  # new field
            }

        # Add unique payments
        if row.payment_id and row.payment_id not in [p["payment_id"] for p in wallets[key]["payments"]]:
            amount = float(row.payment_amount) if row.payment_amount is not None else 0.0
            wallets[key]["payments"].append({
                "payment_id": row.payment_id,
                "amount": amount,
                "recorded_date": row.payment_date.isoformat() if row.payment_date else None
            })
            wallets[key]["payment_count"] += 1
            wallets[key]["payment_total"] += amount

        # Add unique histories
        if row.history_id and row.history_id not in [h["history_id"] for h in wallets[key]["matched_histories"]]:
            amount = float(row.history_amount) if row.history_amount is not None else 0.0
            wallets[key]["matched_histories"].append({
                "history_id": row.history_id,
                "amount": amount,
                "created_at": row.history_created_at.isoformat() if row.history_created_at else None
            })
            wallets[key]["history_match_count"] += 1
            wallets[key]["wallet_history_total"] += amount

    # Update mismatches after processing all rows
    for key, record in wallets.items():
        record["mismatches"] = record["payment_total"] != record["wallet_history_total"]

    filtered_results = [
        record for record in wallets.values()
        if record["payment_count"] > 0
    ]

    return jsonify({
        "status": "success",
        "results": filtered_results
    }), 200


from flask import jsonify
from sqlalchemy import text
import json
from datetime import datetime

from flask import request, jsonify
from sqlalchemy import text
import json
from datetime import datetime

@reconciliation_bp.route(
    "/reconcile-integration-vs-wallet-history",
    methods=["GET"]
)
def reconcile_integration_vs_wallet_history():
    """
    FAST reconciliation between integration_logs and tbl_student_wallet_history
    - status = VALID
    - payment_date_time > 2026-01-12
    - Detect missing & amount mismatches
    """

    cutoff_date = "2026-01-12 00:00:00"
    include_details = request.args.get("details", "false").lower() == "true"

    # 1️⃣ Fetch integration logs ONLY ONCE (filtered in SQL)
    integration_rows = db.session.execute(text("""
        SELECT
            external_transaction_id,
            response_data
        FROM integration_logs
        WHERE status = 'VALID'
          AND response_data IS NOT NULL
          AND JSON_EXTRACT(response_data, '$.payment_date_time') > :cutoff
    """), {"cutoff": cutoff_date}).fetchall()

    if not integration_rows:
        return jsonify({
            "status": "success",
            "summary": {
                "total_checked": 0,
                "missing_count": 0,
                "mismatched_count": 0
            }
        }), 200

    # 2️⃣ Parse integration data (memory-efficient)
    integration_map = {}
    transaction_ids = set()

    for row in integration_rows:
        try:
            data = json.loads(row.response_data)
        except Exception:
            continue

        tx_id = data.get("transaction_id")
        amount = data.get("amount")

        if not tx_id or amount is None:
            continue

        integration_map[tx_id] = {
            "amount": float(amount),
            "payer_code": data.get("payer_code"),
            "observation": data.get("observation"),
            "payment_date_time": data.get("payment_date_time")
        }
        transaction_ids.add(tx_id)

    if not transaction_ids:
        return jsonify({
            "status": "success",
            "summary": {
                "total_checked": 0,
                "missing_count": 0,
                "mismatched_count": 0
            }
        }), 200

    # 3️⃣ Fetch wallet history IN BULK
    history_rows = db.session.execute(text("""
        SELECT
            external_transaction_id,
            amount
        FROM tbl_student_wallet_history
        WHERE external_transaction_id IN :tx_ids
    """), {"tx_ids": tuple(transaction_ids)}).fetchall()

    history_map = {
        row.external_transaction_id: float(row.amount)
        for row in history_rows
        if row.external_transaction_id is not None
    }

    # 4️⃣ Reconcile (O(n))
    missing = []
    mismatched = []

    for tx_id, integ in integration_map.items():
        hist_amount = history_map.get(tx_id)

        # ❌ Missing
        if hist_amount is None:
            if include_details:
                missing.append({
                    "external_transaction_id": tx_id,
                    "payer_code": integ["payer_code"],
                    "amount": integ["amount"],
                    "observation": integ["observation"],
                    "payment_date_time": integ["payment_date_time"],
                    "reason": "Not found in wallet history"
                })
            continue

        # ⚠️ Mismatch
        if hist_amount != integ["amount"]:
            if include_details:
                mismatched.append({
                    "external_transaction_id": tx_id,
                    "payer_code": integ["payer_code"],
                    "integration_amount": integ["amount"],
                    "wallet_history_amount": hist_amount,
                    "observation": integ["observation"],
                    "payment_date_time": integ["payment_date_time"],
                    "reason": "Amount mismatch"
                })

    # 5️⃣ Fast response (summary first)
    response = {
        "status": "success",
        "cutoff_date": "2026-01-12",
        "summary": {
            "total_checked": len(integration_map),
            "missing_count": sum(
                1 for tx in integration_map if tx not in history_map
            ),
            "mismatched_count": sum(
                1 for tx, integ in integration_map.items()
                if tx in history_map and history_map[tx] != integ["amount"]
            )
        }
    }

    if include_details:
        response["missing_transactions"] = missing
        response["amount_mismatches"] = mismatched

    return jsonify(response), 200


from flask import request, jsonify
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime

@reconciliation_bp.route(
    "/insert-missing-wallet-history",
    methods=["POST"]
)
def insert_missing_wallet_history():
    """
    Insert missing transactions into tbl_student_wallet_history
    from reconciliation payload.
    """

    payload = request.get_json()
    if not payload or "missing_transactions" not in payload:
        return jsonify({
            "status": "error",
            "message": "Invalid payload"
        }), 400

    inserted = []
    skipped = []
    failed = []

    total_amount_inserted = 0.0

    try:
        for item in payload["missing_transactions"]:
            tx_id = item.get("external_transaction_id")
            amount = item.get("amount")
            reg_no = item.get("payer_code")
            comment = item.get("observation")
            payment_date_time = item.get("payment_date_time")

            if not tx_id or amount is None or not reg_no:
                failed.append({
                    "external_transaction_id": tx_id,
                    "reason": "Missing required fields"
                })
                continue

            # Safety check: do not double insert
            exists = (
                db.session.query(TblStudentWalletHistory.id)
                .filter(
                    TblStudentWalletHistory.external_transaction_id == tx_id
                )
                .first()
            )

            if exists:
                skipped.append({
                    "external_transaction_id": tx_id,
                    "reason": "Already exists in wallet history"
                })
                continue

            # Parse datetime safely
            try:
                created_at = datetime.strptime(
                    payment_date_time,
                    "%Y-%m-%d %H:%M:%S"
                ) if payment_date_time else datetime.utcnow()
            except ValueError:
                created_at = datetime.utcnow()

            history = TblStudentWalletHistory(
                reg_no=reg_no,
                reference_number=tx_id,
                transaction_type="TOPUP",
                amount=float(amount),
                balance_before=0.0,
                balance_after=float(amount),
                external_transaction_id=tx_id,
                comment=comment,
                created_by="reconciliation",
                created_at=created_at
            )

            db.session.add(history)

            inserted.append({
                "external_transaction_id": tx_id,
                "reg_no": reg_no,
                "amount": float(amount)
            })
            total_amount_inserted += float(amount)

        db.session.commit()

    except SQLAlchemyError as e:
        db.session.rollback()
        return jsonify({
            "status": "error",
            "message": "Database error",
            "details": str(e)
        }), 500

    return jsonify({
        "status": "completed",
        "summary": {
            "total_missing_received": len(payload["missing_transactions"]),
            "inserted_count": len(inserted),
            "skipped_count": len(skipped),
            "failed_count": len(failed),
            "total_amount_inserted": total_amount_inserted
        },
        "inserted": inserted,
        "skipped": skipped,
        "failed": failed
    }), 200

@reconciliation_bp.route(
    "/wallet-payment-exceeds-history",
    methods=["GET"]
)
def wallet_payment_exceeds_history():
    """
    Return wallet records where:
    - reference_number matches YYYYMMDDHHMMSS_REGNO
    - payment_total > wallet_history_total
    - wallet_history_total > 0
    - mismatches = True
    """

    query = text("""
        SELECT
            w.reg_no,
            w.reference_number,
            p.id AS payment_id,
            p.amount AS payment_amount,
            p.recorded_date AS payment_date,
            h.id AS history_id,
            h.amount AS history_amount,
            h.created_at AS history_created_at
        FROM tbl_student_wallet w
        LEFT JOIN payment p
            ON p.student_wallet_ref = w.reference_number
        LEFT JOIN tbl_student_wallet_history h
            ON h.reg_no = w.reg_no
        WHERE w.reference_number REGEXP '^[0-9]{14}_[0-9]+$'
        ORDER BY w.reg_no, p.recorded_date
    """)

    rows = db.session.execute(query).fetchall()

    wallets = {}

    for row in rows:
        key = (row.reg_no, row.reference_number)

        if key not in wallets:
            wallets[key] = {
                "reg_no": row.reg_no,
                "reference_number": row.reference_number,
                "payments": [],
                "payment_total": 0.0,
                "payment_count": 0,
                "matched_histories": [],
                "wallet_history_total": 0.0,
                "history_match_count": 0,
                "mismatches": False
            }

        # Add unique payments
        if row.payment_id and row.payment_id not in {
            p["payment_id"] for p in wallets[key]["payments"]
        }:
            amount = float(row.payment_amount or 0)
            wallets[key]["payments"].append({
                "payment_id": row.payment_id,
                "amount": amount,
                "recorded_date": (
                    row.payment_date.isoformat()
                    if row.payment_date else None
                )
            })
            wallets[key]["payment_total"] += amount
            wallets[key]["payment_count"] += 1

        # Add unique wallet histories
        if row.history_id and row.history_id not in {
            h["history_id"] for h in wallets[key]["matched_histories"]
        }:
            amount = float(row.history_amount or 0)
            wallets[key]["matched_histories"].append({
                "history_id": row.history_id,
                "amount": amount,
                "created_at": (
                    row.history_created_at.isoformat()
                    if row.history_created_at else None
                )
            })
            wallets[key]["wallet_history_total"] += amount
            wallets[key]["history_match_count"] += 1

    # Final reconciliation filter
    results = []
    for record in wallets.values():
        record["mismatches"] = (
            record["payment_total"] != record["wallet_history_total"]
        )

        if (
            record["mismatches"]
            and record["payment_total"] > record["wallet_history_total"]
            and record["wallet_history_total"] > 0
        ):
            record["difference"] = (
                record["payment_total"] - record["wallet_history_total"]
            )
            results.append(record)

    return jsonify({
        "status": "success",
        "count": len(results),
        "results": results
    }), 200
