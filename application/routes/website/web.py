from flask  import Blueprint, render_template

web_route = Blueprint('web', __name__, url_prefix='/web')

@web_route.route('/', methods=['GET'])
def web_page():
    """Render the main web page"""
    return render_template("website/index.html")

@web_route.route('/privacy_policy', methods=['GET'])
def privacy_policy_page():
    """Render the privacy policy page"""
    return render_template("website/privacy_policy.html")

@web_route.route('/terms_of_use', methods=['GET'])
def terms_of_use_page():
    """Render the Terms of Use page"""
    return render_template("website/terms_of_use.html")