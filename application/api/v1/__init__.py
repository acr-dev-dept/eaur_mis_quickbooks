"""
API v1 Blueprint for EAUR MIS-QuickBooks Integration
"""

from flask import Blueprint

# Create the main API v1 blueprint
api_v1_bp = Blueprint('api_v1', __name__)

# Import and register sub-blueprints
from .quickbooks import quickbooks_bp
from .mis_data import mis_data_bp

# Register sub-blueprints
api_v1_bp.register_blueprint(quickbooks_bp, url_prefix='/quickbooks')
api_v1_bp.register_blueprint(mis_data_bp, url_prefix='/mis')