import logging
from flask import Blueprint, jsonify, request, current_app
from datetime import datetime

from application.services.payment_sync import PaymentSyncService
from application.models.mis_models import Payment


payment_sync_bp = Blueprint('payment_sync_bp', __name__)


@payment_sync_bp.route('/sync_payments', methods=['POST'])
def sync_payments():
    try:
        data = request.get_json()
        start_date = data.get('start_date')
        end_date = data.get('end_date')

        if not start_date or not end_date:
            return jsonify({'error': 'start_date and end_date are required'}), 400

        payment_sync_service = PaymentSyncService()
        result = payment_sync_service.sync_payments(start_date, end_date)

        return jsonify(result), 200
    except Exception as e:
        logging.error(f"Error syncing payments: {e}")
        return jsonify({'error': 'Internal server error'}), 500
    
@payment_sync_bp.route('/sync_payment/<int:payment_id>', methods=['POST'])
def sync_payment(payment_id):
    """Sync a single payment by its ID."""
    try:
        current_app.logger.info(f"Starting sync for payment ID: {payment_id}")
        # get the payment object given the payment_id
        payment = Payment.get_payment_by_id(payment_id)
        payment_date = datetime.strptime(payment.date.strip(), '%Y/%m/%d').date()

        if payment_date < datetime(2025, 1, 1):
            return jsonify({'error': 'Payment date is before 2025-01-01'}), 400

        if not payment:
            return jsonify({'error': 'Payment not found'}), 404

        payment_dict = payment.to_dict() if payment else {}
        current_app.logger.info(f"Attempting to sync payment: {payment_dict}")
        
    except Exception as e:
        current_app.logger.error(f"Error retrieving payment {payment_id}: {e}")
        return jsonify({'error': 'Internal server error'}), 500
        

    try:
        payment_sync_service = PaymentSyncService()
        result = payment_sync_service.sync_single_payment(payment)
        current_app.logger.info(f"Sync result for payment {payment_id}: {result}")

        return result, 200
    except Exception as e:
        logging.error(f"Error syncing payment {payment_id}: {e}")
        return jsonify({'error': 'Internal server error'}), 500
    
@payment_sync_bp.route('/get_unsynced_payments', methods=['GET'])
def get_unsynced_payments():
    try:
        # Get limit and offset from request query parameters
        limit = request.args.get('limit', type=int, default=50) # default to 50
        offset = request.args.get('offset', type=int, default=0) # default to 0
        
        # Ensure limit is not excessively large
        if limit > 200:
            limit = 200 # Set a max limit to prevent misuse

        payment_sync_service = PaymentSyncService()
        result = payment_sync_service.get_unsynchronized_payments(limit=limit, offset=offset)
        
        current_app.logger.info(f"Retrieved {len(result)} unsynchronized payments")
        
        dict_payments = [payment.to_dict() for payment in result]
        
        return jsonify(
            {
                "status": "success",
                "number_of_records": len(dict_payments),
                "payments": dict_payments
            }
        ), 200
    except Exception as e:
        current_app.logger.error(f"Error retrieving unsynchronized payments: {e}")
        return jsonify({'error': 'Internal server error'}), 500
    
@payment_sync_bp.route('/get_payment_status/<int:payment_id>', methods=['GET'])
def get_payment_status(payment_id):
    try:
        payment_sync_service = PaymentSyncService()
        result = payment_sync_service.get_payment_status(payment_id)

        return jsonify(result), 200
    except Exception as e:
        logging.error(f"Error retrieving payment status for {payment_id}: {e}")
        return jsonify({'error': 'Internal server error'}), 500
    
@payment_sync_bp.route('/resync_payment/<int:payment_id>', methods=['POST'])
def resync_payment(payment_id):
    try:
        payment_sync_service = PaymentSyncService()
        result = payment_sync_service.resync_payment(payment_id)

        return jsonify(result), 200
    except Exception as e:
        logging.error(f"Error resyncing payment {payment_id}: {e}")
        return jsonify({'error': 'Internal server error'}), 500
    
@payment_sync_bp.route('/get_sync_audit_logs', methods=['GET'])
def get_sync_audit_logs():
    try:
        payment_sync_service = PaymentSyncService()
        result = payment_sync_service.get_sync_audit_logs()

        return jsonify(result), 200
    except Exception as e:
        logging.error(f"Error retrieving sync audit logs: {e}")
        return jsonify({'error': 'Internal server error'}), 500
    
@payment_sync_bp.route('/get_quickbooks_config', methods=['GET'])
def get_quickbooks_config():
    try:
        payment_sync_service = PaymentSyncService()
        result = payment_sync_service.get_quickbooks_config()

        return jsonify(result), 200
    except Exception as e:
        logging.error(f"Error retrieving QuickBooks config: {e}")
        return jsonify({'error': 'Internal server error'}), 500
    
@payment_sync_bp.route('/update_quickbooks_config', methods=['POST'])
def update_quickbooks_config():
    try:
        data = request.get_json()
        payment_sync_service = PaymentSyncService()
        result = payment_sync_service.update_quickbooks_config(data)

        return jsonify(result), 200
    except Exception as e:
        logging.error(f"Error updating QuickBooks config: {e}")
        return jsonify({'error': 'Internal server error'}), 500
    
@payment_sync_bp.route('/analyze_sync_requirements', methods=['get'])
def analyze_sync_requirements():
    """Analyze and report on payment sync requirements."""
    try:
        payment_sync_service = PaymentSyncService()
        result = payment_sync_service.analyze_sync_requirements()

        return jsonify(result), 200
    except Exception as e:
        logging.error(f"Error analyzing sync requirements: {e}")
        return jsonify({'error': 'Internal server error'}), 500