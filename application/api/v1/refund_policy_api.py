from flask import Blueprint, request, jsonify, current_app
from application.services.refund_receipt import RefundReceiptService
from application.models.central_models import QuickBooksConfig
from application.models.mis_models import Payment
import traceback
from datetime import datetime

refund_policy_api = Blueprint('refund_policy_api', __name__)

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

@refund_policy_api.route('/create_refund_receipt', methods=['POST'])
def create_refund_receipt():
    """API endpoint to create a refund receipt in QuickBooks.
    Expects JSON payload with a payment_id only.
    {
        "payment_id": 123 
    }
    """
    
    try:
        # validate QuickBooks connection
        is_connected, error_response = validate_quickbooks_connection()
        if not is_connected:
            return error_response
        
        refund_data_id = request.json
        refund_data = Payment.get_refund_data(refund_data_id['payment_id'])
        if not refund_data or 'payment_id' not in refund_data:
            return jsonify({
                'success': False,
                'error': 'Invalid input',
                'message': 'payment_id is required',
                'timestamp': datetime.now().isoformat()
            }), 400
        
        refund_service = RefundReceiptService()
        mapped_data = refund_service.map_refund_receipt_data(refund_data)
        qb_response = refund_service.create_refund_receipt(mapped_data)
        
        return create_response(
            success=True,
            data=qb_response,
            message='Refund receipt created successfully'
        )
    
    except Exception as e:
        current_app.logger.error(f"Error creating refund receipt: {str(e)}")
        traceback_str = traceback.format_exc()
        return create_response(
            success=False,
            error='Failed to create refund receipt',
            details=traceback_str,
            status_code=500
        )