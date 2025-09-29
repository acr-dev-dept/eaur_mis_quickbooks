from flask  import Blueprint, render_template
from application.models.mis_models.TblIncomeCategory import TblIncomeCategory

dashboard_route = Blueprint('dashboard', __name__)
@dashboard_route.route('/', methods=['GET'])
def dashboard_page():
    """Render the main dashboard page"""
    active_categories_count = TblIncomeCategory.count_active_categories()
    return render_template("dashboard/index.html", cat_no=active_categories_count)