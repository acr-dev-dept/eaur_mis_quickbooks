from flask import Blueprint, render_template, request, jsonify
from application.models.central_models import QuickbooksAuditLog

error_logs_bp = Blueprint("error_logs", __name__)

@error_logs_bp.route("/quickbooks/logs")
def logs_page():
    """Render the logs page"""
    return render_template("dashboard/quickbooks_logs.html")

@error_logs_bp.route("/quickbooks/logs/data")
def logs_data():
    """Serve logs data for DataTables"""
    draw = int(request.args.get("draw", 1))
    start = int(request.args.get("start", 0))
    length = int(request.args.get("length", 10))
    search_value = request.args.get("search[value]", "")

    logs, total_records = QuickbooksAuditLog.fetch_paginated_logs(
        start=start, length=length, search=search_value
    )

    data = []
    for log in logs:
        # Map HTTP status to human-readable status
        status_label = {
            200: '<span class="text-green-600 font-semibold">Success</span>',
            400: '<span class="text-yellow-600 font-semibold">Bad Request</span>',
            500: '<span class="text-red-600 font-semibold">Server Error</span>',
        }.get(log.operation_status, f"Unknown ({log.operation_status})")

        data.append([
            log.id,
            log.action_type,
            status_label,
            log.error_message or "-",
            str(log.request_payload)[:50] if log.request_payload else "-",
            str(log.response_payload)[:50] if log.response_payload else "-",
            log.user_id or "-"
        ])

    return jsonify({
        "draw": draw,
        "recordsTotal": total_records,
        "recordsFiltered": total_records,
        "data": data
    })
