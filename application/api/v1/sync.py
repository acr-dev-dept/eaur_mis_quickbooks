"""
Invoice Synchronization API endpoints for EAUR MIS-QuickBooks Integration
Handles bulk synchronization of invoices from MIS to QuickBooks
"""

from flask import Blueprint, request, jsonify, current_app
from application.services.invoice_sync import InvoiceSyncService
from application.models.central_models import QuickBooksConfig
import traceback
from datetime import datetime

sync_bp = Blueprint('sync', __name__)

# Standard response format
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

@sync_bp.route('/analyze', methods=['GET'])
def analyze_sync_requirements():
    """
    Analyze current invoice synchronization requirements
    
    Returns statistics about invoices that need to be synchronized
    """
    try:
        # Validate QuickBooks connection
        is_connected, error_response = validate_quickbooks_connection()
        if not is_connected:
            return error_response

        sync_service = InvoiceSyncService()
        stats = sync_service.analyze_sync_requirements()
        
        current_app.logger.info(f"Sync analysis completed: {stats.to_dict()}")
        
        return create_response(
            success=True,
            data=stats.to_dict(),
            message='Synchronization analysis completed successfully'
        )
        
    except Exception as e:
        current_app.logger.error(f"Error analyzing sync requirements: {e}")
        current_app.logger.error(traceback.format_exc())
        return create_response(
            success=False,
            error='Error analyzing synchronization requirements',
            details=str(e),
            status_code=500
        )

@sync_bp.route('/preview', methods=['GET'])
def preview_unsynchronized_invoices():
    """
    Preview invoices that will be synchronized
    
    Query parameters:
    - limit: Number of invoices to preview (default: 10)
    - offset: Number of invoices to skip (default: 0)
    """
    try:
        # Validate QuickBooks connection
        is_connected, error_response = validate_quickbooks_connection()
        if not is_connected:
            return error_response

        # Get query parameters
        limit = int(request.args.get('limit', 10))
        offset = int(request.args.get('offset', 0))
        
        # Validate parameters
        if limit > 100:
            return create_response(
                success=False,
                error='Limit cannot exceed 100',
                status_code=400
            )

        sync_service = InvoiceSyncService()
        invoices = sync_service.get_unsynchronized_invoices(limit=limit, offset=offset)
        
        # Convert to dictionary format for JSON response
        invoice_data = []
        for invoice in invoices:
            try:
                invoice_dict = invoice.to_dict()
                # Add student details if available
                student_details = sync_service.get_student_details(invoice.reg_no)
                if student_details:
                    invoice_dict['student_details'] = student_details
                invoice_data.append(invoice_dict)
            except Exception as e:
                current_app.logger.warning(f"Error converting invoice {invoice.id} to dict: {e}")
                continue
        
        return create_response(
            success=True,
            data={
                'invoices': invoice_data,
                'count': len(invoice_data),
                'limit': limit,
                'offset': offset
            },
            message=f'Retrieved {len(invoice_data)} unsynchronized invoices'
        )
        
    except Exception as e:
        current_app.logger.error(f"Error previewing unsynchronized invoices: {e}")
        current_app.logger.error(traceback.format_exc())
        return create_response(
            success=False,
            error='Error previewing unsynchronized invoices',
            details=str(e),
            status_code=500
        )

@sync_bp.route('/batch', methods=['POST'])
def sync_batch():
    """
    Synchronize a batch of invoices to QuickBooks
    
    Request body (JSON):
    {
        "batch_size": 50  // Optional, defaults to 50
    }
    """
    try:
        # Validate QuickBooks connection
        is_connected, error_response = validate_quickbooks_connection()
        if not is_connected:
            return error_response

        # Get request data
        request_data = request.get_json() or {}
        batch_size = request_data.get('batch_size', 50)
        
        # Validate batch size
        if batch_size > 100:
            return create_response(
                success=False,
                error='Batch size cannot exceed 100',
                status_code=400
            )

        sync_service = InvoiceSyncService()
        
        current_app.logger.info(f"Starting batch synchronization with batch size: {batch_size}")
        
        results = sync_service.sync_invoices_batch(batch_size=batch_size)
        
        return create_response(
            success=True,
            data=results,
            message=f'Batch synchronization completed: {results["successful"]} successful, {results["failed"]} failed'
        )
        
    except Exception as e:
        current_app.logger.error(f"Error in batch synchronization: {e}")
        current_app.logger.error(traceback.format_exc())
        return create_response(
            success=False,
            error='Error in batch synchronization',
            details=str(e),
            status_code=500
        )

@sync_bp.route('/all', methods=['POST'])
def sync_all():
    """
    Synchronize all unsynchronized invoices to QuickBooks
    
    Request body (JSON):
    {
        "max_batches": 10  // Optional, maximum number of batches to process
    }
    """
    try:
        # Validate QuickBooks connection
        is_connected, error_response = validate_quickbooks_connection()
        if not is_connected:
            return error_response

        # Get request data
        request_data = request.get_json() or {}
        max_batches = request_data.get('max_batches')
        
        sync_service = InvoiceSyncService()
        
        current_app.logger.info(f"Starting full synchronization with max_batches: {max_batches}")
        
        results = sync_service.sync_all_invoices(max_batches=max_batches)
        
        return create_response(
            success=True,
            data=results,
            message=f'Full synchronization completed: {results["total_successful"]} successful, {results["total_failed"]} failed'
        )
        
    except Exception as e:
        current_app.logger.error(f"Error in full synchronization: {e}")
        current_app.logger.error(traceback.format_exc())
        return create_response(
            success=False,
            error='Error in full synchronization',
            details=str(e),
            status_code=500
        )

@sync_bp.route('/single/<int:invoice_id>', methods=['POST'])
def sync_single_invoice(invoice_id):
    """
    Synchronize a single invoice to QuickBooks
    
    Args:
        invoice_id: MIS invoice ID to synchronize
    """
    try:
        # Validate QuickBooks connection
        is_connected, error_response = validate_quickbooks_connection()
        if not is_connected:
            return error_response

        sync_service = InvoiceSyncService()
        
        # Get the invoice
        invoices = sync_service.get_unsynchronized_invoices(limit=1000)  # Get all to find specific one
        invoice = None
        for inv in invoices:
            if inv.id == invoice_id:
                invoice = inv
                break
        
        if not invoice:
            return create_response(
                success=False,
                error='Invoice not found or already synchronized',
                status_code=404
            )
        
        current_app.logger.info(f"Starting synchronization of invoice {invoice_id}")
        
        result = sync_service.sync_single_invoice(invoice)
        
        if result.success:
            return create_response(
                success=True,
                data={
                    'invoice_id': result.invoice_id,
                    'quickbooks_id': result.quickbooks_id
                },
                message=f'Invoice {invoice_id} synchronized successfully'
            )
        else:
            return create_response(
                success=False,
                error=f'Failed to synchronize invoice {invoice_id}',
                details=result.error_message,
                status_code=400
            )
        
    except Exception as e:
        current_app.logger.error(f"Error synchronizing single invoice {invoice_id}: {e}")
        current_app.logger.error(traceback.format_exc())
        return create_response(
            success=False,
            error=f'Error synchronizing invoice {invoice_id}',
            details=str(e),
            status_code=500
        )

@sync_bp.route('/status', methods=['GET'])
def get_sync_status():
    """
    Get current synchronization status and statistics
    """
    try:
        sync_service = InvoiceSyncService()
        stats = sync_service.analyze_sync_requirements()
        
        # Calculate progress percentage
        total = stats.total_invoices
        synced = stats.already_synced
        progress_percentage = (synced / total * 100) if total > 0 else 0
        
        status_data = {
            'statistics': stats.to_dict(),
            'progress_percentage': round(progress_percentage, 2),
            'quickbooks_connected': QuickBooksConfig.is_connected(),
            'last_updated': datetime.now().isoformat()
        }
        
        return create_response(
            success=True,
            data=status_data,
            message='Synchronization status retrieved successfully'
        )
        
    except Exception as e:
        current_app.logger.error(f"Error getting sync status: {e}")
        current_app.logger.error(traceback.format_exc())
        return create_response(
            success=False,
            error='Error getting synchronization status',
            details=str(e),
            status_code=500
        )
