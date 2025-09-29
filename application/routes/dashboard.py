from flask  import Blueprint, render_template
from application.models.mis_models import TblIncomeCategory

dashboard_route = Blueprint('dashboard', __name__)
@dashboard_route.route('/', methods=['GET'])
def dashboard_page():
    """Render the main dashboard page"""
    numbers = {}
    active_categories_count = TblIncomeCategory.count_active_categories()
    total_students = TblPersonalUg.count_students()

    numbers['active_categories'] = active_categories_count
    numbers['total_students'] = total_students

    return render_template("dashboard/index.html", numbers=numbers)