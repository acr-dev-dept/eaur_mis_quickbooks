from flask import Blueprint, request, jsonify, current_app
from application.services.customer_sync import CustomerSyncService
from application.models.central_models import QuickBooksConfig, QuickbooksAuditLog
import traceback
from datetime import datetime
from application.models.mis_models import TblIncomeCategory
from application.services.income_sync import IncomeSyncService
from application.utils.database import db_manager

income_sync_api = Blueprint('income_sync_api', __name__)

def create_response(success=True, data=None, message="", error=None, details=None, status_code=200):
    """Create standardized API response"""
    response = {
        'success': success,
        'message': message,
        'timestamp': datetime.now().isoformat()
    }
    
    if success:
        response['data'] = data
    else:
        response['error'] = error
        if details:
            response['details'] = details
    
    return jsonify(response), status_code

def validate_quickbooks_connection():
    """Validate QuickBooks connection"""
    if not QuickBooksConfig.is_connected():
        return False, create_response(
            success=False,
            error='QuickBooks not connected',
            message='Please authenticate with QuickBooks first',
            status_code=400
        )
    return True, None


@income_sync_api.route('/sync_income_category', methods=['POST'])
def sync_income_category():
    """API endpoint to trigger income category synchronization with QuickBooks.
    Expects JSON payload with income category details.
    {
        "id": 1
    }
    
    """

    try:
        # validate QuickBooks connection
        is_connected, error_response = validate_quickbooks_connection()
        if not is_connected:
            return error_response
        
        sync_service = IncomeSyncService()
        category_data = request.json
        if not category_data or 'id' not in category_data:
            return jsonify({
                'success': False,
                'error': 'Invalid payload',
                'message': 'Income category ID is required',
            }), 400

        category = TblIncomeCategory.get_category_by_id(category_data['id'])
        if not category:
            return jsonify({
                'success': False,
                'error': 'Not Found',
                'message': f'Income category with ID {category_data["id"]} not found',
            }), 404
        if category.income_account_qb:
            return jsonify({
                'success': False,
                'error':'Duplication error',
                'message': f'Income category with ID {category_data["id"]} is already synced to QuickBooks',
            }), 400
        result = sync_service.sync_income_category(category=category)
        
        return jsonify({
            'success': True,
            'data': {'synced': result.to_dict() if hasattr(result, "to_dict") else str(result)},
            'message': 'Income category synchronization completed'
        }), 200

    except Exception as e:
        current_app.logger.error(f"Exception in sync_income_category API: {str(e)}")
        traceback_str = traceback.format_exc()
        current_app.logger.error(traceback_str)
        return jsonify({
            'success': False,
            'error': 'Internal Server Error',
            'message': 'An error occurred during income category synchronization',
            'details': str(e)
        }), 500