"""
Invoice API endpoints for EAUR MIS-QuickBooks Integration
Handles all invoice-related operations with consistent response format
"""

from flask import Blueprint, request, jsonify, current_app, Response
from application.services.quickbooks import QuickBooks
from application.models.central_models import QuickBooksConfig
import traceback

invoices_bp = Blueprint('invoices', __name__)

# Standard response format
def create_response(success=True, data=None, message="", error=None, details=None, status_code=200):
    """
    Create standardized API response
    
    Args:
        success (bool): Success status
        data: Response data
        message (str): Success message
        error (str): Error message
        details (str): Error details
        status_code (int): HTTP status code
        
    Returns:
        tuple: (response_dict, status_code)
    """
    response = {
        'success': success,
        'message': message
    }
    
    if success:
        response['data'] = data
    else:
        response['error'] = error
        if details:
            response['details'] = details
    
    return jsonify(response), status_code

def validate_quickbooks_connection():
    """
    Validate QuickBooks connection
    
    Returns:
        tuple: (is_connected, error_response)
    """
    if not QuickBooksConfig.is_connected():
        return False, create_response(
            success=False,
            error='QuickBooks not connected',
            message='Please connect to QuickBooks first',
            status_code=400
        )
    return True, None

@invoices_bp.route('/', methods=['GET'])
def get_invoices():
    """Get all invoices with optional filtering."""
    try:
        # Validate QuickBooks connection
        is_connected, error_response = validate_quickbooks_connection()
        if not is_connected:
            return error_response

        qb = QuickBooks()
        current_app.logger.info('Getting invoices')
        
        # Get query parameters for filtering
        params = {}
        if request.args.get('customer_id'):
            params['customerref'] = request.args.get('customer_id')
        if request.args.get('doc_number'):
            params['docnumber'] = request.args.get('doc_number')
        if request.args.get('active'):
            params['active'] = request.args.get('active').lower() == 'true'
        
        invoices = qb.get_invoices(qb.realm_id, params if params else None)
        current_app.logger.info("Invoices retrieved successfully")
        
        # Check for errors in the response
        if 'error' in invoices:
            return create_response(
                success=False,
                error=invoices['error'],
                details=invoices.get('details', ''),
                status_code=500
            )
        
        return create_response(
            success=True,
            data=invoices,
            message='Invoices retrieved successfully'
        )
        
    except Exception as e:
        current_app.logger.error(f"Error getting invoices: {e}")
        current_app.logger.error(traceback.format_exc())
        return create_response(
            success=False,
            error='Error getting invoices',
            details=str(e),
            status_code=500
        )

@invoices_bp.route('/<invoice_id>', methods=['GET'])
def get_invoice(invoice_id):
    """Get a specific invoice by ID."""
    try:
        # Validate QuickBooks connection
        is_connected, error_response = validate_quickbooks_connection()
        if not is_connected:
            return error_response

        if not invoice_id:
            return create_response(
                success=False,
                error='Invoice ID is required',
                message='Please provide a valid invoice ID',
                status_code=400
            )

        qb = QuickBooks()
        current_app.logger.info(f'Getting invoice with ID: {invoice_id}')
        
        invoice = qb.get_invoice(qb.realm_id, invoice_id)
        
        # Check for errors in the response
        if 'Fault' in invoice:
            return create_response(
                success=False,
                error='Invoice not found or error occurred',
                details=invoice['Fault']['Error'][0]['Message'] if invoice['Fault']['Error'] else 'Unknown error',
                status_code=404
            )
        
        current_app.logger.info("Invoice retrieved successfully")
        return create_response(
            success=True,
            data=invoice,
            message='Invoice retrieved successfully'
        )
        
    except Exception as e:
        current_app.logger.error(f"Error getting invoice: {e}")
        current_app.logger.error(traceback.format_exc())
        return create_response(
            success=False,
            error='Error getting invoice',
            details=str(e),
            status_code=500
        )


@invoices_bp.route('/', methods=['POST'])
def create_invoice():
    """Create a new invoice."""
    try:
        # Validate QuickBooks connection
        is_connected, error_response = validate_quickbooks_connection()
        if not is_connected:
            return error_response

        # Validate request data
        try:
            request_data = request.get_json()
        except Exception:
            return create_response(
                success=False,
                error='Invalid JSON data',
                message='Please provide valid JSON data',
                status_code=400
            )

        if not request_data:
            return create_response(
                success=False,
                error='No data provided',
                message='Please provide invoice data in JSON format',
                status_code=400
            )

        invoice_data = request_data
        
        # Basic validation for required fields
        if 'Line' not in invoice_data:
            return create_response(
                success=False,
                error='Missing required field: Line',
                message='Invoice must contain at least one line item',
                status_code=400
            )

        if 'CustomerRef' not in invoice_data:
            return create_response(
                success=False,
                error='Missing required field: CustomerRef',
                message='Invoice must have a customer reference',
                status_code=400
            )

        qb = QuickBooks()
        current_app.logger.info('Creating new invoice')
        
        result = qb.create_invoice(qb.realm_id, invoice_data)
        
        # Check for errors in the response
        if 'Fault' in result:
            return create_response(
                success=False,
                error='Failed to create invoice',
                details=result['Fault']['Error'][0]['Message'] if result['Fault']['Error'] else 'Unknown error',
                status_code=400
            )
        
        current_app.logger.info("Invoice created successfully")
        return create_response(
            success=True,
            data=result,
            message='Invoice created successfully',
            status_code=201
        )
        
    except Exception as e:
        current_app.logger.error(f"Error creating invoice: {e}")
        current_app.logger.error(traceback.format_exc())
        return create_response(
            success=False,
            error='Error creating invoice',
            details=str(e),
            status_code=500
        )
