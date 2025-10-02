from flask import Blueprint, render_template, request, jsonify
from application.models.mis_models import Payment

payments_route = Blueprint('payments_rte', __name__)
@payments_route.route('/get_payments', methods=['GET'])
def get_payments():
    """Server-side endpoint for DataTables pagination of payments"""
    try:
        draw = int(request.args.get('draw', 1))
        start = int(request.args.get('start', 0))
        length = int(request.args.get('length', 50))
        search_value = request.args.get('search', None)

        total_records, filtered_records, payments = Payment.fetch_paginated_payments(
            start=start, length=length, search=search_value
        )

        return jsonify({
            "draw": draw,
            "recordsTotal": total_records,
            "recordsFiltered": filtered_records,
            "data": payments
        })

    except Exception as e:
        from flask import current_app
        current_app.logger.error(f"Error in get_payments: {str(e)}")
        return jsonify({
            "draw": request.args.get('draw', 1),
            "recordsTotal": 0,
            "recordsFiltered": 0,
            "data": []
        })

# HTML page route
@payments_route.route('/', methods=['GET'])
def payments_page():
    """Render the payments page with empty table skeleton"""
    return render_template("dashboard/payments.html")