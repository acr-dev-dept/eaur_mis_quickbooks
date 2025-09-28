from flask  import Blueprint, render_template

dashboard_route = Blueprint('dashboard', __name__)
@dashboard_route.route('/', methods=['GET'])
def dashboard_page():
    """Render the main dashboard page"""
    return render_template("dashboard/index.html")