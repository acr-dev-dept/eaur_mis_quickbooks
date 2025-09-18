import logging
from flask import Blueprint, jsonify, request
from flask_restx import Namespace, Resource, fields
from datetime import datetime

from application.services.payment_sync import PaymentSyncService
from application.helpers.decorator import token_required
from application.exceptions import ClientError, ServerError

payment_sync_bp = Blueprint('payment_sync_bp', __name__)
payment_sync_ns = Namespace('payment_sync', description='Payment Synchronization Operations')

# Logger
logger = logging.getLogger(__name__)

# Models for API serialization
sync_status_model = payment_sync_ns.model('SyncStatus', {
    'total_payments': fields.Integer(required=True, description='Total payments found in MIS'),
    'not_synced': fields.Integer(required=True, description='Number of payments not yet synced'),
    'synced': fields.Integer(required=True, description='Number of payments successfully synced'),
    'failed': fields.Integer(required=True, description='Number of payments that failed to sync'),
    'in_progress': fields.Integer(required=True, description='Number of payments currently in progress of syncing')
})

sync_result_item_model = payment_sync_ns.model('SyncResultItem', {
    'status': fields.String(required=True, description='Synchronization status (SYNCED, FAILED, IN_PROGRESS)'),
    'message': fields.String(required=True, description='Descriptive message for the sync result'),
    'success': fields.Boolean(required=True, description='True if the synchronization was successful, False otherwise'),
    'quickbooks_id': fields.String(description='QuickBooks ID if successfully synced'),
    'details': fields.Raw(description='Additional details from the QuickBooks API response'),
    'error_message': fields.String(description='Error message if an error occurred'),
    'traceback': fields.String(description='Full traceback if an error occurred'),
    'duration': fields.Float(description='Duration of the sync operation in seconds')
})

sync_batch_result_model = payment_sync_ns.model('SyncBatchResult', {
    'total_processed': fields.Integer(required=True, description='Total payments processed in the batch'),
    'successful': fields.Integer(required=True, description='Number of payments successfully synced in the batch'),
    'failed': fields.Integer(required=True, description='Number of payments that failed in the batch'),
    'results': fields.List(fields.Nested(sync_result_item_model), description='Detailed results for each payment in the batch')
})

overall_sync_results_model = payment_sync_ns.model('OverallSyncResults', {
    'batches_processed': fields.Integer(required=True, description='Total batches processed'),
    'total_processed': fields.Integer(required=True, description='Total payments processed across all batches'),
    'total_successful': fields.Integer(required=True, description='Number of payments successfully synced overall'),
    'total_failed': fields.Integer(required=True, description='Number of payments that failed overall'),
    'batch_results': fields.List(fields.Nested(sync_batch_result_model), description='Results of each batch synchronization'),
    'start_time': fields.DateTime(dt_format='iso8601', description='Start time of the overall synchronization process'),
    'end_time': fields.DateTime(dt_format='iso8601', description='End time of the overall synchronization process')
})

@payment_sync_ns.route('/status')
class PaymentSyncStatusResource(Resource):
    @token_required
    @payment_sync_ns.marshal_with(sync_status_model)
    @payment_sync_ns.doc(security='apikey')
    def get(self):
        """Get current payment synchronization status"""
        try:
            service = PaymentSyncService()
            status = service.analyze_sync_requirements()
            return status.to_dict(), 200 # Return the dictionary representation
        except ClientError as e:
            logger.warning(f"Client error in payment sync status: {e.message}")
            payment_sync_ns.abort(e.status_code, message=e.message)
        except ServerError as e:
            logger.error(f"Server error in payment sync status: {e.message}")
            payment_sync_ns.abort(e.status_code, message=e.message)
        except Exception as e:
            logger.exception("Unexpected error getting payment sync status")
            payment_sync_ns.abort(500, message=f"Internal server error: {e}")

@payment_sync_ns.route('/sync-batch')
class PaymentSyncBatchResource(Resource):
    @token_required
    @payment_sync_ns.doc(
        security='apikey',
        params={'batch_size': {'description': 'Number of payments to sync in this batch', 'type': 'integer', 'default': 50}}
    )
    @payment_sync_ns.marshal_with(sync_batch_result_model)
    def post(self):
        """Trigger synchronization for a batch of payments to QuickBooks"""
        try:
            batch_size = request.args.get('batch_size', type=int)
            service = PaymentSyncService()
            result = service.sync_payments_batch(batch_size=batch_size)
            return result, 200
        except ClientError as e:
            logger.warning(f"Client error in payment batch sync: {e.message}")
            payment_sync_ns.abort(e.status_code, message=e.message)
        except ServerError as e:
            logger.error(f"Server error in payment batch sync: {e.message}")
            payment_sync_ns.abort(e.status_code, message=e.message)
        except Exception as e:
            logger.exception("Unexpected error during payment batch sync")
            payment_sync_ns.abort(500, message=f"Internal server error: {e}")

@payment_sync_ns.route('/sync-all')
class PaymentSyncAllResource(Resource):
    @token_required
    @payment_sync_ns.doc(
        security='apikey',
        params={'max_batches': {'description': 'Maximum number of batches to process', 'type': 'integer', 'default': 0}}
    )
    @payment_sync_ns.marshal_with(overall_sync_results_model)
    def post(self):
        """Trigger synchronization for all unsynchronized payments to QuickBooks"""
        try:
            max_batches = request.args.get('max_batches', type=int)
            service = PaymentSyncService()
            result = service.sync_all_payments(max_batches=max_batches if max_batches > 0 else None)
            return result, 200
        except ClientError as e:
            logger.warning(f"Client error in overall payment sync: {e.message}")
            payment_sync_ns.abort(e.status_code, message=e.message)
        except ServerError as e:
            logger.error(f"Server error in overall payment sync: {e.message}")
            payment_sync_ns.abort(e.status_code, message=e.message)
        except Exception as e:
            logger.exception("Unexpected error during overall payment sync")
            payment_sync_ns.abort(500, message=f"Internal server error: {e}")

# Register namespace with blueprint
payment_sync_bp.add_url_rule('/<path:path>', endpoint='payment_sync_ns', view_func=payment_sync_ns.as_view('payment_sync_ns'))
