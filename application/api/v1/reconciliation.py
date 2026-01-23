import json
from decimal import Decimal
from flask import Blueprint, jsonify, current_app, request
from application import db
from application.models.central_models import IntegrationLog
from application.models.mis_models import TblStudentWallet, TblStudentWalletHistory
reconciliation_bp = Blueprint("reconciliation", __name__)
from sqlalchemy import func
import pandas as pd
import os
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
    - Only Txn Status = SUCCESSFUL is included
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
        # Filter SUCCESSFUL transactions only
        # ------------------------------------
        df["Txn Status"] = df["Txn Status"].astype(str).str.strip().str.upper()
        df = df[df["Txn Status"] == "SUCCESSFUL"]

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
    Full bidirectional reconciliation between:

    - Cloud payments JSON (source of truth)
    - Wallet ledger history (internal accounting)

    Detects:
    - missing credits
    - ghost credits
    - partial credits
    - duplicates
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

        # ------------------------------------------------------------------
        # STEP 1 — LOAD CLOUD PAYMENTS JSON
        # ------------------------------------------------------------------

        with open(file_path, "r") as f:
            cloud_json = json.load(f)

        payer_blocks = cloud_json.get("per_payer_code", {})

        cloud_map = {}

        for payer_code, block in payer_blocks.items():
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

        # ------------------------------------------------------------------
        # STEP 2 — WALLET LEDGER TOTALS
        # ------------------------------------------------------------------

        wallet_rows = (
            db.session.query(
                TblStudentWalletHistory.external_transaction_id.label("trx_id"),
                func.count(TblStudentWalletHistory.id).label("entries"),
                func.sum(TblStudentWalletHistory.amount).label("wallet_total")
            )
            .filter(TblStudentWalletHistory.external_transaction_id.isnot(None))
            .group_by(TblStudentWalletHistory.external_transaction_id)
            .all()
        )

        wallet_map = {
            str(row.trx_id): {
                "wallet_total": float(row.wallet_total or 0),
                "wallet_entries": int(row.entries)
            }
            for row in wallet_rows
        }

        # ------------------------------------------------------------------
        # STEP 3 — FULL BIDIRECTIONAL RECONCILIATION
        # ------------------------------------------------------------------

        matched = []
        mismatches = {
            "missing_in_wallet": [],
            "missing_in_cloud": [],
            "amount_mismatch": [],
            "duplicate_wallet_entries": [],
            "orphan_wallet_transactions": []
        }

        all_refs = set(wallet_map.keys()) | set(cloud_map.keys())

        for trx_ref in all_refs:

            wallet = wallet_map.get(trx_ref)
            cloud = cloud_map.get(trx_ref)

            # --------------------------------------------------------------
            # Cloud exists but wallet missing
            # --------------------------------------------------------------
            if cloud and not wallet:
                mismatches["missing_in_wallet"].append({
                    "transaction_reference": trx_ref,
                    "cloud_total": cloud["cloud_total"],
                    "cloud_transactions": cloud["transactions"]
                })
                continue

            # --------------------------------------------------------------
            # Wallet exists but cloud missing
            # --------------------------------------------------------------
            if wallet and not cloud:
                mismatches["missing_in_cloud"].append({
                    "transaction_reference": trx_ref,
                    "wallet_total": wallet["wallet_total"],
                    "wallet_entries": wallet["wallet_entries"]
                })

                mismatches["orphan_wallet_transactions"].append({
                    "transaction_reference": trx_ref,
                    "wallet_total": wallet["wallet_total"],
                    "wallet_entries": wallet["wallet_entries"]
                })
                continue

            wallet_total = wallet["wallet_total"]
            cloud_total = cloud["cloud_total"]

            # --------------------------------------------------------------
            # Duplicate wallet entries
            # --------------------------------------------------------------
            if wallet["wallet_entries"] > 1:
                mismatches["duplicate_wallet_entries"].append({
                    "transaction_reference": trx_ref,
                    "wallet_entries": wallet["wallet_entries"],
                    "wallet_total": wallet_total
                })

            # --------------------------------------------------------------
            # Amount mismatch
            # --------------------------------------------------------------
            if round(wallet_total, 2) != round(cloud_total, 2):
                mismatches["amount_mismatch"].append({
                    "transaction_reference": trx_ref,
                    "wallet_total": wallet_total,
                    "cloud_total": cloud_total,
                    "difference": round(wallet_total - cloud_total, 2)
                })
            else:
                matched.append({
                    "transaction_reference": trx_ref,
                    "amount": wallet_total
                })

        # ------------------------------------------------------------------
        # RESPONSE
        # ------------------------------------------------------------------

        return jsonify({
            "status": "success",
            "summary": {
                "wallet_transaction_refs": len(wallet_map),
                "cloud_transaction_refs": len(cloud_map),
                "matched": len(matched),
                "missing_in_wallet": len(mismatches["missing_in_wallet"]),
                "missing_in_cloud": len(mismatches["missing_in_cloud"]),
                "orphan_wallet_transactions": len(mismatches["orphan_wallet_transactions"]),
                "amount_mismatch": len(mismatches["amount_mismatch"]),
                "duplicate_wallet_entries": len(mismatches["duplicate_wallet_entries"])
            },
            "mismatches": mismatches,
            "matched": matched
        }), 200

    except Exception as e:
        current_app.logger.exception("Wallet–Cloud reconciliation failed")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500
