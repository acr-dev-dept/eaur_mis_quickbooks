import json
from decimal import Decimal
from flask import Blueprint, jsonify, current_app
from application import db
from application.models.central_models import IntegrationLog
reconciliation_bp = Blueprint("reconciliation", __name__)


@reconciliation_bp.route("/api/v1/reconciliation/valid-payments/total", methods=["GET"])
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
