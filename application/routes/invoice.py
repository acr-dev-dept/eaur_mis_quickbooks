from flask import Blueprint, render_template, request, jsonify
from application.models.mis_models import TblImvoice


invoices_route = Blueprint('invoices_rte', __name__)

@invoices_route.route('/get_mis_invoices', methods=['GET'])
def get_mis_invoices():
    """Server-side endpoint for DataTables pagination"""
    try:
        draw = int(request.args.get('draw', 1))
        start = int(request.args.get('start', 0))
        length = int(request.args.get('length', 50))
        search_value = request.args.get('search_value', '').strip()
        status_filter = request.args.get('status_filter', '').strip().lower()

        total_records, filtered_records, invoices = TblImvoice.fetch_paginated_invoices(
            start=start, length=length, search=search_value, status=status_filter       
        )

        return jsonify({
            "draw": draw,
            "recordsTotal": total_records,
            "recordsFiltered": filtered_records,
            "data": invoices
        })

    except Exception as e:
        from flask import current_app
        current_app.logger.error(f"Error in get_mis_invoices: {str(e)}")
        return jsonify({
            "draw": request.args.get('draw', 1),
            "recordsTotal": 0,
            "recordsFiltered": 0,
            "data": []
        })

# HTML page route
@invoices_route.route('/', methods=['GET'])
def invoices_page():
    """Render the invoices page with empty table skeleton"""
    return render_template("dashboard/invoices.html")