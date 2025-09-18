import logging
from flask import Blueprint, jsonify, request, current_app
from datetime import datetime

from application.services.payment_sync import PaymentSyncService


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
    try:
        payment_sync_service = PaymentSyncService()
        result = payment_sync_service.sync_payment(payment_id)

        return jsonify(result), 200
    except Exception as e:
        logging.error(f"Error syncing payment {payment_id}: {e}")
        return jsonify({'error': 'Internal server error'}), 500
    
@payment_sync_bp.route('/get_unsynced_payments', methods=['GET'])
def get_unsynced_payments():
    try:
        payment_sync_service = PaymentSyncService()
        result = payment_sync_service.get_unsynced_payments()
        current_app.logger.info(f"Retrieved {result} unsynced payments")
        return jsonify(result), 200
    except Exception as e:
        logging.error(f"Error retrieving unsynced payments: {e}")
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