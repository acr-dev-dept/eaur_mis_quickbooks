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
from application.models.central_models import QuickbooksAuditLog

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

@invoices_bp.route('/sync_single_invoice', methods=['POST'])
def sync_single_invoice():
    """Sync a single invoice from MIS to QuickBooks.
    JSON Payload:
        {
            "invoice_id": <int>
        }
    """
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

@invoices_bp.route('/update/<int:invoice_id>', methods=['POST'])
def update_invoice_qb(invoice_id):
    """Update an existing invoice in QuickBooks by ID from MIS."""
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

        current_app.logger.info(f'Updating invoice in QuickBooks with ID: {invoice_id}')
        invoice_sync_service = InvoiceSyncService()
        invoice_data = TblImvoice.get_invoice_by_id(invoice_id)
        current_app.logger.info(f'Fetched invoice data: {invoice_data} and the type is {type(invoice_data)}')


        result = invoice_sync_service.update_single_invoice(invoice=invoice_data)

        current_app.logger.info(f'Update result test: {result}')

        if not result.success:
            QuickbooksAuditLog.add_audit_log(
                action_type="Update single invoice",
                operation_status=400,
                error_message=result.error_message or "Failed to update invoice",
            )
            return create_response(
                success=False,
                error='Failed to update invoice',
                details=result.error_message or 'Unknown error',
                status_code=400
            )

        current_app.logger.info("Invoice updated successfully")
        QuickbooksAuditLog.add_audit_log(
            action_type="Update single invoice",
            operation_status=200,
            error_message=None,
        )
        return create_response(
            success=True,
            data=result.details or {},
            message='Invoice updated successfully'
        )

    except Exception as e:
        current_app.logger.error(f"Error updating invoice: {e}")
        current_app.logger.error(traceback.format_exc())
        QuickbooksAuditLog.add_audit_log(
            action_type="Update single invoice",
            operation_status=500,
            error_message=str(e),
        )
        return create_response(
            success=False,
            error='Error updating invoice',
            details=str(e),
            status_code=500
        )

@invoices_bp.route('/delete/<int:invoice_id>', methods=['DELETE'])
def delete_invoice_qb(invoice_id):
    """Delete an existing invoice in QuickBooks by ID from MIS."""

    try:
        # Validate QuickBooks connection
        is_connected, error_response = validate_quickbooks_connection()
        if not is_connected:
            return error_response
        
        invoice_data = TblImvoice.get_invoice_by_id(invoice_id)

        if not invoice_data:
            current_app.logger.error(f"Invoice with ID {invoice_id} not found")
            return create_response(
                success=False,
                error='Invoice not found',
                message='Invoice not found',
                status_code=404
            )
        
        if invoice_data.is_prepayment:
            current_app.logger.info("Skip wallet based invoice deletion")
            return create_response(
                success=False,
                error='Wallet based invoice deletion is not supported',
                message='Wallet based invoice deletion is not supported',
                status_code=400
            )
        
        if invoice_data.get('balance') is not None:
            current_app.logger.info("Skip balance based invoice deletion because it is linked with a payment")
            return create_response(
                success=False,
                error='Balance based invoice deletion is not supported',
                message='Balance based invoice deletion is not supported',
                status_code=400
            )
        current_app.logger.info(f'Deleting invoice in QuickBooks with ID: {invoice_id}')
        invoice_sync_service = InvoiceSyncService()
        result = invoice_sync_service.delete_invoice_from_quickbooks(invoice_data)

        if not result.success:
            QuickbooksAuditLog.add_audit_log(
                action_type="Delete single invoice",
                operation_status=400,
                error_message=result.error_message or "Failed to delete invoice",
            )
            return create_response(
                success=False,
                error=result.error_message or 'Unknown error',
                status_code=400
            )

        current_app.logger.info("Invoice deleted successfully")
        QuickbooksAuditLog.add_audit_log(
            action_type=f"Delete single invoice {invoice_id}",
            operation_status=200,
            error_message=None,
        )
        # Update the invoice record
        update_invoice = TblImvoice.update_invoice_quickbooks_row(invoice_id)

        if not update_invoice:
            current_app.logger.info("Failed to update invoice record")
        else:
            current_app.logger.info("Invoice record updated successfully")

            
        return create_response(
            success=True,
            data=result.details or {},
            message='Invoice deleted successfully'
        )

    except Exception as e:
        current_app.logger.error(f"Error deleting invoice: {e}")
        current_app.logger.error(traceback.format_exc,)
        QuickbooksAuditLog.add_audit_log(
            action_type="Delete single invoice",
            operation_status=500,
            error_message=str(e),
        )
        return create_response(
            success=False,
            error=f'Error deleting invoice {e}',
            status_code=500
        )


        
