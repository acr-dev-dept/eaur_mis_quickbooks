from flask import Blueprint, request, jsonify, current_app
from application.models.central_models import QuickBooksConfig
import traceback
from datetime import datetime
from application.models.mis_models import TblStudentWallet
from application.services.sales_receipt_sync import SalesReceiptSyncService


sales_receipt_api = Blueprint('sales_receipt_api', __name__)

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

@sales_receipt_api.route('/create', methods=['POST'])
def create_sales_receipt():
    """
        API endpoint to create a sales receipt in QuickBooks.
        Expects JSON payload with a payment_id only.
        {
            "id": 123 
        }
    """

    try:
        # validate QuickBooks connection
        is_connected, error_response = validate_quickbooks_connection()
        if not is_connected:
            return error_response
        
        sales_data_id = request.json
        sales_data = TblStudentWallet.get_sales_data(sales_data_id['id'])
        sync_service = SalesReceiptSyncService()

        if not sales_data or not sales_data.id:
            return jsonify({
                'success': False,
                'error': 'Invalid input',
                'message': 'id is required',
                'timestamp': datetime.now().isoformat()
            }), 400
        if sales_data.is_paid.lower() != "yes":
            current_app.logger.info(f"Wallet data is not paid:")
            return jsonify({
                'success': False,
                'message': 'Wallet data is not paid',
                'timestamp': datetime.now().isoformat()
            }), 400
        
        result = sync_service.sync_single_sales_receipt(sales_data)
        if not result.success:
            return jsonify({
                'success': False,
                'error': 'Failed to create sales receipt',
                'details': result.error_message,
                'timestamp': datetime.now().isoformat()
            }), 500

        return jsonify({
            'success': True,
            'data': {'synced': result.to_dict() if hasattr(result, "to_dict") else str(result)},
            'message': 'Sales receipt created successfully'
        }), 200
    
    except Exception as e:
        current_app.logger.error(f"Error creating sales receipt: {str(e)}")
        traceback_str = traceback.format_exc()
        return jsonify({
            'success': False,
            'error': 'Failed to create sales receipt',
            'details': traceback_str,
            'timestamp': datetime.now().isoformat()
        }), 500
