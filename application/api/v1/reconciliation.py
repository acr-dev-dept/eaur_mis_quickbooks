import json
from decimal import Decimal
from flask import Blueprint, jsonify, current_app
from application import db
from application.models.central_models import IntegrationLog
from application.models.mis_models import TblStudentWallet
reconciliation_bp = Blueprint("reconciliation", __name__)
from sqlalchemy import func


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
