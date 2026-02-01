from flask import Blueprint, jsonify, current_app



qb_admin_bp = Blueprint("qb_admin", __name__, url_prefix="/api/admin/qb")


@qb_admin_bp.route("/delete-sales-receipts", methods=["POST"])
def trigger_sales_receipt_deletion():
    """
    Triggers async deletion of all QuickBooks Sales Receipts
    linked to wallet records.
    """

    try:
        current_app.logger.warning(
            "ADMIN ACTION: Triggering QuickBooks Sales Receipt deletion task"
        )
        from application.tasks.delete_sales_receipt_master import (
            delete_all_wallet_sales_receipts_master,
        )
        task = delete_all_wallet_sales_receipts_master.delay()


        return jsonify({
            "success": True,
            "message": "Sales receipt deletion task started",
            "task_id": task.id,
        }), 202

    except Exception as e:
        current_app.logger.exception(
            "Failed to trigger sales receipt deletion task"
        )

        return jsonify({
            "success": False,
            "error": "Failed to start deletion task",
            "details": str(e),
        }), 500
