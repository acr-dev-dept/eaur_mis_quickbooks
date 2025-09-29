from flask import Blueprint, render_template, request, jsonify
from application.models.mis_models import TblIncomeCategory

items_route = Blueprint('items_rte', __name__)
@items_route.route('/get_items', methods=['GET'])
def get_items():
    """Server-side endpoint for DataTables pagination of items"""
    try:
        draw = int(request.args.get('draw', 1))
        start = int(request.args.get('start', 0))
        length = int(request.args.get('length', 50))
        search_value = request.args.get('search[value]', None)

        total_records, filtered_records, items = TblIncomeCategory.fetch_paginated_items(
            start=start, length=length, search=search_value
        )

        return jsonify({
            "draw": draw,
            "recordsTotal": total_records,
            "recordsFiltered": filtered_records,
            "data": items
        })

    except Exception as e:
        from flask import current_app
        current_app.logger.error(f"Error in get_items: {str(e)}")
        return jsonify({
            "draw": request.args.get('draw', 1),
            "recordsTotal": 0,
            "recordsFiltered": 0,
            "data": []
        })

# HTML page route
@items_route.route('/', methods=['GET'])
def items_page():
    """Render the items page with empty table skeleton"""
    return render_template("dashboard/items.html")