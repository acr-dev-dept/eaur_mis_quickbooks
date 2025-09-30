"""
Invoice API endpoints for EAUR MIS-QuickBooks Integration
Handles all invoice-related operations with consistent response format
"""

from flask import Blueprint, request, jsonify, current_app, Response
from application.services.quickbooks import QuickBooks
from application.models.central_models import QuickBooksConfig
import traceback
from application.services.invoice_sync import InvoiceSyncService
from datetime import datetime
from application.models.mis_models import TblImvoice
from flask import render_template
from application.models.central import QuickbooksAuditLog

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


@invoices_bp.route('/<invoice_id>', methods=['PUT'])
def update_invoice(invoice_id):
    """Update an existing invoice."""
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

        update_data = request_data
        update_type = request.args.get('type', 'sparse')  # sparse or full
        
        qb = QuickBooks()
        current_app.logger.info(f'Updating invoice {invoice_id} with {update_type} update')
        
        if update_type.lower() == 'full':
            result = qb.full_update_invoice(qb.realm_id, invoice_id, update_data)
        else:
            result = qb.sparse_invoice_update(qb.realm_id, invoice_id, update_data)
        
        # Check for errors in the response
        if 'Fault' in result:
            return create_response(
                success=False,
                error='Failed to update invoice',
                details=result['Fault']['Error'][0]['Message'] if result['Fault']['Error'] else 'Unknown error',
                status_code=400
            )
        
        current_app.logger.info("Invoice updated successfully")
        return create_response(
            success=True,
            data=result,
            message='Invoice updated successfully'
        )
        
    except Exception as e:
        current_app.logger.error(f"Error updating invoice: {e}")
        current_app.logger.error(traceback.format_exc())
        return create_response(
            success=False,
            error='Error updating invoice',
            details=str(e),
            status_code=500
        )

@invoices_bp.route('/<invoice_id>', methods=['DELETE'])
def delete_invoice(invoice_id):
    """Delete an invoice."""
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
        current_app.logger.info(f'Deleting invoice with ID: {invoice_id}')
        
        result = qb.delete_invoice(qb.realm_id, invoice_id)
        
        # Check for errors in the response
        if 'Fault' in result:
            return create_response(
                success=False,
                error='Failed to delete invoice',
                details=result['Fault']['Error'][0]['Message'] if result['Fault']['Error'] else 'Unknown error',
                status_code=400
            )
        
        current_app.logger.info("Invoice deleted successfully")
        return create_response(
            success=True,
            data=result,
            message='Invoice deleted successfully'
        )
        
    except Exception as e:
        current_app.logger.error(f"Error deleting invoice: {e}")
        current_app.logger.error(traceback.format_exc())
        return create_response(
            success=False,
            error='Error deleting invoice',
            details=str(e),
            status_code=500
        )


@invoices_bp.route('/<invoice_id>/void', methods=['POST'])
def void_invoice(invoice_id):
    """Void an invoice."""
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
        current_app.logger.info(f'Voiding invoice with ID: {invoice_id}')

        result = qb.void_invoice(qb.realm_id, invoice_id)

        # Check for errors in the response
        if 'Fault' in result:
            return create_response(
                success=False,
                error='Failed to void invoice',
                details=result['Fault']['Error'][0]['Message'] if result['Fault']['Error'] else 'Unknown error',
                status_code=400
            )

        current_app.logger.info("Invoice voided successfully")
        return create_response(
            success=True,
            data=result,
            message='Invoice voided successfully'
        )

    except Exception as e:
        current_app.logger.error(f"Error voiding invoice: {e}")
        current_app.logger.error(traceback.format_exc())
        return create_response(
            success=False,
            error='Error voiding invoice',
            details=str(e),
            status_code=500
        )


@invoices_bp.route('/<invoice_id>/pdf', methods=['GET'])
def get_invoice_pdf(invoice_id):
    """Get invoice as PDF."""
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
        current_app.logger.info(f'Getting PDF for invoice with ID: {invoice_id}')

        result = qb.get_invoice_as_pdf(qb.realm_id, invoice_id)

        # Check for errors in the response
        if isinstance(result, dict) and 'Fault' in result:
            return create_response(
                success=False,
                error='Failed to get invoice PDF',
                details=result['Fault']['Error'][0]['Message'] if result['Fault']['Error'] else 'Unknown error',
                status_code=400
            )

        current_app.logger.info("Invoice PDF retrieved successfully")
        # For PDF content, return binary data with appropriate headers
        return Response(
            result,
            mimetype='application/pdf',
            headers={
                'Content-Disposition': f'attachment; filename=invoice_{invoice_id}.pdf',
                'Content-Type': 'application/pdf'
            }
        )

    except Exception as e:
        current_app.logger.error(f"Error getting invoice PDF: {e}")
        current_app.logger.error(traceback.format_exc())
        return create_response(
            success=False,
            error='Error getting invoice PDF',
            details=str(e),
            status_code=500
        )

@invoices_bp.route('/<invoice_id>/send', methods=['POST'])
def send_invoice(invoice_id):
    """Send invoice via email."""
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

        # Check if email is provided in request body
        email = None
        try:
            request_data = request.get_json()
            if request_data and 'email' in request_data:
                email = request_data['email']
        except Exception:
            # If JSON parsing fails, continue without email
            pass
            if not email or '@' not in email:
                return create_response(
                    success=False,
                    error='Invalid email address',
                    message='Please provide a valid email address',
                    status_code=400
                )

        qb = QuickBooks()
        current_app.logger.info(f'Sending invoice {invoice_id} via email')

        if email:
            # Send to specific email
            result = qb.send_invoice_to_a_given_email(qb.realm_id, invoice_id, email)
        else:
            # Send to email in invoice
            result = qb.send_invoice_to_supplied_email(qb.realm_id, invoice_id)

        # Check for errors in the response
        if 'Fault' in result:
            return create_response(
                success=False,
                error='Failed to send invoice',
                details=result['Fault']['Error'][0]['Message'] if result['Fault']['Error'] else 'Unknown error',
                status_code=400
            )

        current_app.logger.info("Invoice sent successfully")
        return create_response(
            success=True,
            data=result,
            message=f'Invoice sent successfully{" to " + email if email else ""}'
        )

    except Exception as e:
        current_app.logger.error(f"Error sending invoice: {e}")
        current_app.logger.error(traceback.format_exc())
        return create_response(
            success=False,
            error='Error sending invoice',
            details=str(e),
            status_code=500
        )
@invoices_bp.route('/sync_single_invoice', methods=['POST'])
def sync_single_invoice():
    """Sync a single invoice from MIS to QuickBooks."""
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

        if not request_data or 'invoice_id' not in request_data:
            return create_response(
                success=False,
                error='No invoice_id provided',
                message='Please provide invoice_id in JSON data',
                status_code=400
            )

        invoice_id = request_data['invoice_id']
        if not isinstance(invoice_id, int):
            return create_response(
                success=False,
                error='Invalid invoice_id',
                message='invoice_id must be an integer',
                status_code=400
            )

        current_app.logger.info(f'Syncing single invoice with ID: {invoice_id}')

        invoice_sync_service = InvoiceSyncService()
        invoice_data = invoice_sync_service.fetch_invoice_data(invoice_id)
        
        result = invoice_sync_service.sync_single_invoice(invoice_data)
        
        current_app.logger.info(f'Sync result: {result}')

        if not result.success:
            return create_response(
                success=False,
                error='Failed to sync invoice',
                details=result.error_message or 'Unknown error',
                status_code=400
            )

        current_app.logger.info("Invoice synced successfully")
        # update quickbooks_id in MIS database
        qb_id = result.quickbooks_id

        current_app.logger.info(f"Updating MIS invoice {invoice_id} with QuickBooks ID {qb_id}")
        update_invoice = TblImvoice.update_invoice_quickbooks_status(
            quickbooks_id=qb_id,
            pushed_by="InvoiceSyncService",
            pushed_date=datetime.now(),
            QuickBk_Status=1,
            invoice_id=invoice_id
        )

        if not update_invoice:
            current_app.logger.error(f"Failed to update MIS invoice {invoice_id} with QuickBooks ID")
            return create_response(
                success=False,
                error='Failed to update MIS invoice with QuickBooks ID',
                status_code=500
            )
        return create_response(
            success=True,
            data=result.details or {},
            message='Invoice synced successfully'
        )

    except Exception as e:
        current_app.logger.error(f"Error syncing invoice: {e}")
        current_app.logger.error(traceback.format_exc())
        return create_response(
            success=False,
            error='Error syncing invoice',
            details=str(e),
            status_code=500
        )
    
@invoices_bp.route('/sync/<int:invoice_id>', methods=['GET'])
def sync_invoice(invoice_id):
    """Sync a single invoice by ID from MIS to QuickBooks."""
    try:
        # Validate QuickBooks connection
        is_connected, error_response = validate_quickbooks_connection()
        if not is_connected:
            QuickbooksAuditLog.add_audit_log(
                action_type="Validate QuickBooks connection",
                operation_status=500,
                error_message="QuickBooks not connected",
            )
            return error_response

        if not invoice_id:
            QuickbooksAuditLog.add_audit_log(
                action_type="Validate invoice_id",
                operation_status=400,
                error_message="Invoice ID is required",
            )
            return create_response(
                success=False,
                error='Invoice ID is required',
                message='Please provide a valid invoice ID',
                status_code=400
            )

        current_app.logger.info(f'Syncing invoice with ID: {invoice_id}')

        invoice_sync_service = InvoiceSyncService()
        invoice_data = invoice_sync_service.fetch_invoice_data(invoice_id)
        
        result = invoice_sync_service.sync_single_invoice(invoice_data)
        
        current_app.logger.info(f'Sync result: {result}')

        if not result.success:
            QuickbooksAuditLog.add_audit_log(
                action_type="Sync single invoice",
                operation_status=400,
                error_message=result.error_message or "Failed to sync invoice",
            )
            return create_response(
                success=False,
                error='Failed to sync invoice',
                details=result.error_message or 'Unknown error',
                status_code=400
            )

        current_app.logger.info("Invoice synced successfully")
        # update quickbooks_id in MIS database
        qb_id = result.quickbooks_id
        current_app.logger.info(f"Updating MIS invoice {invoice_id} with QuickBooks ID {qb_id}")
        update_invoice = TblImvoice.update_invoice_quickbooks_status(
            quickbooks_id=qb_id,
            pushed_by="InvoiceSyncService",
            pushed_date=datetime.now(),
            QuickBk_Status=1,
            invoice_id=invoice_id
        )

        if not update_invoice:
            current_app.logger.error(f"Failed to update MIS invoice {invoice_id} with QuickBooks ID")
            QuickbooksAuditLog.add_audit_log(
                action_type="Update MIS invoice with QuickBooks ID",
                operation_status=500,
                error_message="Failed to update MIS invoice with QuickBooks ID",
            )
            return create_response(
                success=False,
                error='Failed to update MIS invoice with QuickBooks ID',
                status_code=500
            )
        QuickbooksAuditLog.add_audit_log(
            action_type="Sync single invoice",
            operation_status=200,
            error_message=None,
        )
        return create_response(
            success=True,
            data=result.details or {},
            message='Invoice synced successfully'
        )

    except Exception as e:
        current_app.logger.error(f"Error syncing invoice: {e}")
        current_app.logger.error(traceback.format_exc())
        QuickbooksAuditLog.add_audit_log(
            action_type="Sync single invoice",
            operation_status=500,
            error_message=str(e),
        )
        return create_response(
            success=False,
            error='Error syncing invoice',
            details=str(e),
            status_code=500
        )

