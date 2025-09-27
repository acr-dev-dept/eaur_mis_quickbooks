"""
Bank Sync API endpoints for MIS-QuickBooks integration.

This module provides REST API endpoints for synchronizing bank data from MIS to QuickBooks Chart of Accounts.
"""
import logging
from datetime import datetime
from typing import Dict, Any

from flask import Blueprint, request, jsonify, current_app
from werkzeug.exceptions import BadRequest

from application.services.bank_sync import BankSyncService, BankSyncStatus
from application.models.mis_models import TblBank
from application.models.central_models import QuickBooksConfig
from application.helpers.json_encoder import EnhancedJSONEncoder
from application.helpers.SafeStringify import safe_stringify


# Create blueprint
bank_sync_bp = Blueprint('bank_sync', __name__)

# Set up logging
logger = logging.getLogger(__name__)


def validate_quickbooks_connection():
    """
    Validate that QuickBooks is connected before performing sync operations
    """
    if not QuickBooksConfig.is_connected():
        return jsonify({
            'error': 'QuickBooks is not connected. Please authenticate first.',
            'status': 'error',
            'timestamp': datetime.now().isoformat()
        }), 400
    return None


@bank_sync_bp.route('/sync_bank/<int:bank_id>', methods=['POST'])
def sync_single_bank(bank_id: int):
    """
    Synchronize a single bank to QuickBooks Chart of Accounts
    
    Args:
        bank_id (int): The ID of the bank to synchronize
        
    Returns:
        JSON response with synchronization result
    """
    try:
        # Validate QuickBooks connection
        connection_error = validate_quickbooks_connection()
        if connection_error:
            return connection_error

        current_app.logger.info(f"Starting bank sync for bank ID: {bank_id}")
        
        # Initialize sync service
        sync_service = BankSyncService()
        
        # Get bank details
        bank = sync_service.get_bank_by_id(bank_id)
        if not bank:
            return jsonify({
                'error': f'Bank with ID {bank_id} not found',
                'status': 'error',
                'bank_id': bank_id,
                'timestamp': datetime.now().isoformat()
            }), 404

        # Get force_resync parameter
        force_resync = request.args.get('force', 'false').lower() == 'true'

        # Perform synchronization with duplicate handling
        result = sync_service.sync_single_bank(bank, force_resync=force_resync)

        # Handle different result scenarios
        if result.success:
            current_app.logger.info(f"Bank sync successful for bank ID: {bank_id} - Action: {result.action_taken}")

            # Determine HTTP status code based on action taken
            status_code = 200
            if result.already_synced:
                status_code = 200  # OK - already synced
            elif result.action_taken == 'CREATED_NEW':
                status_code = 201  # Created - new account created

            response_data = {
                'message': result.message,
                'status': 'success',
                'bank_id': bank_id,
                'bank_name': bank.bank_name,
                'quickbooks_id': result.quickbooks_id,
                'duration': result.duration,
                'already_synced': result.already_synced,
                'action_taken': result.action_taken,
                'timestamp': datetime.now().isoformat()
            }

            # Add additional details for already-synced banks
            if result.already_synced and result.details:
                response_data['sync_details'] = {
                    'sync_date': result.details.get('sync_date'),
                    'quickbooks_account_name': result.details.get('quickbooks_account', {}).get('Name') if result.details.get('quickbooks_account') else None
                }

            return jsonify(response_data), status_code

        else:
            # Handle different types of failures
            if result.status == BankSyncStatus.IN_PROGRESS:
                current_app.logger.info(f"Bank sync in progress for bank ID: {bank_id}")
                return jsonify({
                    'message': result.message,
                    'status': 'in_progress',
                    'bank_id': bank_id,
                    'bank_name': bank.bank_name,
                    'action_taken': result.action_taken,
                    'duration': result.duration,
                    'timestamp': datetime.now().isoformat(),
                    'retry_suggestion': 'Try again in a few minutes or use ?force=true to override'
                }), 409  # Conflict - operation in progress
            else:
                current_app.logger.error(f"Bank sync failed for bank ID: {bank_id} - {result.error_message}")
                return jsonify({
                    'error': result.error_message,
                    'message': result.message,
                    'status': 'failed',
                    'bank_id': bank_id,
                    'bank_name': bank.bank_name,
                    'action_taken': result.action_taken,
                    'duration': result.duration,
                    'timestamp': datetime.now().isoformat()
                }), 500

    except Exception as e:
        current_app.logger.error(f"Exception during bank sync for bank {bank_id}: {str(e)}")
        return jsonify({
            'error': f'Internal server error during bank sync: {str(e)}',
            'status': 'error',
            'bank_id': bank_id,
            'timestamp': datetime.now().isoformat()
        }), 500


@bank_sync_bp.route('/get_unsynced_banks', methods=['GET'])
def get_unsynced_banks():
    """
    Get list of banks that haven't been synchronized to QuickBooks
    
    Query Parameters:
        limit (int): Maximum number of banks to return (default: 50)
        offset (int): Number of banks to skip (default: 0)
        
    Returns:
        JSON response with list of unsynchronized banks
    """
    try:
        # Get query parameters
        limit = request.args.get('limit', 50, type=int)
        offset = request.args.get('offset', 0, type=int)
        
        # Validate parameters
        if limit > 100:
            limit = 100  # Cap at 100 for performance
        if offset < 0:
            offset = 0

        current_app.logger.info(f"Getting unsynchronized banks with limit={limit}, offset={offset}")
        
        # Initialize sync service
        sync_service = BankSyncService()
        
        # Get unsynchronized banks
        banks = sync_service.get_unsynchronized_banks(limit=limit, offset=offset)
        
        # Convert to dictionary format
        banks_data = []
        for bank in banks:
            sync_status_enum = sync_service._safe_get_sync_status(bank.status)
            banks_data.append({
                'bank_id': bank.bank_id,
                'bank_code': bank.bank_code,
                'bank_name': bank.bank_name,
                'bank_branch': bank.bank_branch,
                'account_no': bank.account_no,
                'currency': bank.currency,
                'status': bank.status,
                'sync_status': bank.status,
                'sync_status_name': sync_status_enum.name,
                'sync_status_value': sync_status_enum.value,
                'quickbooks_id': bank.qk_id,
                'pushed_by': bank.pushed_by,
                'pushed_date': bank.pushed_date.isoformat() if bank.pushed_date else None
            })

        return jsonify({
            'banks': banks_data,
            'count': len(banks_data),
            'limit': limit,
            'offset': offset,
            'status': 'success',
            'timestamp': datetime.now().isoformat()
        }), 200

    except Exception as e:
        current_app.logger.error(f"Error getting unsynchronized banks: {str(e)}")
        return jsonify({
            'error': f'Error retrieving unsynchronized banks: {str(e)}',
            'status': 'error',
            'timestamp': datetime.now().isoformat()
        }), 500


@bank_sync_bp.route('/get_bank_sync_status/<int:bank_id>', methods=['GET'])
def get_bank_sync_status(bank_id: int):
    """
    Get synchronization status for a specific bank
    
    Args:
        bank_id (int): The ID of the bank to check
        
    Returns:
        JSON response with bank synchronization status
    """
    try:
        current_app.logger.info(f"Getting sync status for bank ID: {bank_id}")
        
        # Initialize sync service
        sync_service = BankSyncService()
        
        # Get bank status
        status_data = sync_service.get_bank_status(bank_id)
        
        if 'error' in status_data:
            return jsonify({
                'error': status_data['error'],
                'status': 'error',
                'bank_id': bank_id,
                'timestamp': datetime.now().isoformat()
            }), 404

        return jsonify({
            'bank_status': status_data,
            'status': 'success',
            'timestamp': datetime.now().isoformat()
        }), 200

    except Exception as e:
        current_app.logger.error(f"Error getting bank sync status for bank {bank_id}: {str(e)}")
        return jsonify({
            'error': f'Error retrieving bank sync status: {str(e)}',
            'status': 'error',
            'bank_id': bank_id,
            'timestamp': datetime.now().isoformat()
        }), 500


@bank_sync_bp.route('/analyze_bank_sync_requirements', methods=['GET'])
def analyze_bank_sync_requirements():
    """
    Get overall bank synchronization statistics and requirements
    
    Returns:
        JSON response with bank sync analysis
    """
    try:
        current_app.logger.info("Analyzing bank sync requirements")
        
        # Initialize sync service
        sync_service = BankSyncService()
        
        # Get sync statistics
        stats = sync_service.analyze_sync_requirements()
        
        # Calculate percentages
        total = stats.total_banks
        sync_percentage = (stats.synced / total * 100) if total > 0 else 0
        
        return jsonify({
            'analysis': {
                'total_banks': stats.total_banks,
                'not_synced': stats.not_synced,
                'synced': stats.synced,
                'failed': stats.failed,
                'in_progress': stats.in_progress,
                'sync_percentage': round(sync_percentage, 2),
                'requires_sync': stats.not_synced + stats.failed,
                'sync_complete': stats.synced == stats.total_banks
            },
            'recommendations': {
                'action_needed': stats.not_synced > 0 or stats.failed > 0,
                'priority_level': 'high' if stats.not_synced > 10 else 'medium' if stats.not_synced > 0 else 'low',
                'estimated_sync_time_minutes': max(1, (stats.not_synced + stats.failed) * 0.5)  # Estimate 30 seconds per bank
            },
            'status': 'success',
            'timestamp': datetime.now().isoformat()
        }), 200

    except Exception as e:
        current_app.logger.error(f"Error analyzing bank sync requirements: {str(e)}")
        return jsonify({
            'error': f'Error analyzing bank sync requirements: {str(e)}',
            'status': 'error',
            'timestamp': datetime.now().isoformat()
        }), 500


@bank_sync_bp.route('/force_resync_bank/<int:bank_id>', methods=['POST'])
def force_resync_bank(bank_id: int):
    """
    Force re-synchronization of a bank, bypassing duplicate checks

    Args:
        bank_id (int): The ID of the bank to force re-sync

    Returns:
        JSON response with synchronization result
    """
    try:
        # Validate QuickBooks connection
        connection_error = validate_quickbooks_connection()
        if connection_error:
            return connection_error

        current_app.logger.info(f"Starting FORCE re-sync for bank ID: {bank_id}")

        # Initialize sync service
        sync_service = BankSyncService()

        # Get bank details
        bank = sync_service.get_bank_by_id(bank_id)
        if not bank:
            return jsonify({
                'error': f'Bank with ID {bank_id} not found',
                'status': 'error',
                'bank_id': bank_id,
                'timestamp': datetime.now().isoformat()
            }), 404

        # Force synchronization (bypass duplicate checks)
        result = sync_service.sync_single_bank(bank, force_resync=True)

        if result.success:
            current_app.logger.info(f"Force re-sync successful for bank ID: {bank_id}")
            return jsonify({
                'message': f'Bank {bank_id} force re-synchronized successfully',
                'status': 'success',
                'bank_id': bank_id,
                'bank_name': bank.bank_name,
                'quickbooks_id': result.quickbooks_id,
                'action_taken': result.action_taken,
                'duration': result.duration,
                'timestamp': datetime.now().isoformat(),
                'warning': 'Force re-sync may create duplicate accounts if the original still exists in QuickBooks'
            }), 201
        else:
            current_app.logger.error(f"Force re-sync failed for bank ID: {bank_id} - {result.error_message}")
            return jsonify({
                'error': result.error_message,
                'message': result.message,
                'status': 'failed',
                'bank_id': bank_id,
                'bank_name': bank.bank_name,
                'action_taken': result.action_taken,
                'duration': result.duration,
                'timestamp': datetime.now().isoformat()
            }), 500

    except Exception as e:
        current_app.logger.error(f"Exception during force re-sync for bank {bank_id}: {str(e)}")
        return jsonify({
            'error': f'Internal server error during force re-sync: {str(e)}',
            'status': 'error',
            'bank_id': bank_id,
            'timestamp': datetime.now().isoformat()
        }), 500


@bank_sync_bp.route('/health', methods=['GET'])
def health_check():
    """
    Health check endpoint for bank sync service

    Returns:
        JSON response with service health status
    """
    try:
        # Check QuickBooks connection
        qb_connected = QuickBooksConfig.is_connected()

        # Initialize sync service to test basic functionality
        sync_service = BankSyncService()

        return jsonify({
            'service': 'Bank Sync API',
            'status': 'healthy',
            'quickbooks_connected': qb_connected,
            'timestamp': datetime.now().isoformat(),
            'version': '2.0.0',  # Updated version with duplicate handling
            'features': [
                'duplicate_detection',
                'force_resync',
                'quickbooks_verification',
                'intelligent_currency_handling'
            ]
        }), 200

    except Exception as e:
        current_app.logger.error(f"Health check failed: {str(e)}")
        return jsonify({
            'service': 'Bank Sync API',
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500
