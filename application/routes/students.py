from flask import Blueprint, render_template, request, jsonify
from application.models.mis_models import TblPersonalUg

students_route = Blueprint('students_rte', __name__)
@students_route.route('/get_students', methods=['GET'])
def get_students():
    """Server-side endpoint for DataTables pagination of students"""
    try:
        draw = int(request.args.get('draw', 1))
        start = int(request.args.get('start', 0))
        length = int(request.args.get('length', 50))
        search_value = request.args.get('search[value]', None)

        total_records, filtered_records, students = TblPersonalUg.fetch_paginated_students(
            start=start, length=length, search=search_value
        )

        return jsonify({
            "draw": draw,
            "recordsTotal": total_records,
            "recordsFiltered": filtered_records,
            "data": students
        })

    except Exception as e:
        from flask import current_app
        current_app.logger.error(f"Error in get_students: {str(e)}")
        return jsonify({
            "draw": request.args.get('draw', 1),
            "recordsTotal": 0,
            "recordsFiltered": 0,
            "data": []
        })

# HTML page route
@students_route.route('/', methods=['GET'])
def students_page():
    """Render the students page with empty table skeleton"""
    return render_template("dashboard/students.html")