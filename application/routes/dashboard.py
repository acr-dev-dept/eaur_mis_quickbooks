from flask  import Blueprint, render_template
from application.models.mis_models import TblIncomeCategory, TblPersonalUg, TblOnlineApplication, TblImvoice, Payment

dashboard_route = Blueprint('dashboard', __name__)
@dashboard_route.route('/', methods=['GET'])
def dashboard_page():
    """Render the main dashboard page"""
    numbers = {}
    active_categories_count = TblIncomeCategory.count_active_categories()
    total_students = TblPersonalUg.count_students()

    numbers['active_categories'] = active_categories_count
    numbers['total_students'] = total_students
    numbers['total_applicants'] = TblOnlineApplication.count_applicants()
    numbers['total_invoices'] = TblImvoice.count_invoices()
    numbers['total_payments'] = Payment.count_payments()
    numbers['synced_categories'] = TblIncomeCategory.count_synced_categories()
    numbers['synced_payments'] = Payment.count_synced_payments()

    return render_template("dashboard/index.html", numbers=numbers)