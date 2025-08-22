from flask import Blueprint, request, jsonify, current_app, session, flash, redirect, url_for
from application.services.quickbooks import QuickBooks
from application.helpers.quickbooks_helpers import QuickBooksHelper
from application.models.central_models import QuickBooksConfig, QuickbooksAuditLog
import os
import logging
import traceback
from decimal import Decimal
from dotenv import load_dotenv

load_dotenv()

quickbooks_bp = Blueprint('quickbooks', __name__)


@quickbooks_bp.route('/get_company_info', methods=['GET'])
def get_company_info():
    """Get company info."""
    try:
        # Check if QuickBooks is configured
        if not QuickBooksConfig.is_connected():
            return jsonify({'error': 'QuickBooks not connected'}), 400

        qb = QuickBooks()
        current_app.logger.info('Getting company info')
        company_info = qb.get_company_info(qb.realm_id)
        current_app.logger.info(f"Company info: {company_info}")
        return jsonify(company_info), 200
    except Exception as e:
        current_app.logger.error(f"Error getting company info: {e}")
        return jsonify({'error': 'Error getting company info'}), 500

@quickbooks_bp.route('/get_accounts', methods=['GET'])
def get_accounts():
    """Get accounts."""
    try:
        # Check if QuickBooks is configured
        if not QuickBooksConfig.is_connected():
            return jsonify({'error': 'QuickBooks not connected'}), 400

        qb = QuickBooks()
        current_app.logger.info('Getting accounts')
        accounts = qb.get_accounts(qb.realm_id)
        current_app.logger.info(f"Accounts retrieved successfully")
        return jsonify(accounts), 200
    except Exception as e:
        current_app.logger.error(f"Error getting accounts: {e}")
        return jsonify({'error': 'Error getting accounts'}), 500

@quickbooks_bp.route('/get_vendors', methods=['GET'])
def get_vendors():
    """Get vendors."""
    try:
        # Check if QuickBooks is configured
        if not QuickBooksConfig.is_connected():
            return jsonify({'error': 'QuickBooks not connected'}), 400

        qb = QuickBooks()
        current_app.logger.info('Getting vendors')
        vendors = qb.get_vendors(qb.realm_id)
        current_app.logger.info(f"Vendors retrieved successfully")
        return jsonify(vendors), 200
    except Exception as e:
        current_app.logger.error(f"Error getting vendors: {e}")
        return jsonify({'error': 'Error getting vendors'}), 500

@quickbooks_bp.route('/get_auth_url', methods=['GET'])
def get_auth_url():
    """Get the QuickBooks OAuth2 authorization URL."""
    try:
        qb = QuickBooks()
        current_app.logger.info("QuickBooks client initialized")

        auth_url = qb.get_authorization_url()
        current_app.logger.info(f"Authorization URL generated")

        # TODO: Add audit logging after database models are implemented

        return redirect(auth_url)
    except Exception as e:
        current_app.logger.error(f"Error getting authorization URL: {e}")
        return jsonify({'error': 'Error getting authorization URL'}), 400

@quickbooks_bp.route('/disconnect', methods=['GET'])
def disconnect():
    """Disconnect from QuickBooks."""
    try:
        # Check if QuickBooks is configured
        if not QuickBooksConfig.is_connected():
            return jsonify({'error': 'QuickBooks not connected'}), 400

        qb = QuickBooks()
        current_app.logger.info("QuickBooks client initialized")

        qb.disconnect_app()
        message = "QuickBooks integration disconnected successfully!"
        return jsonify({'success': True, 'message': message}), 200
    except Exception as e:
        current_app.logger.error(f"Error disconnecting from QuickBooks: {e}")
        message = "Error disconnecting from QuickBooks"
        return jsonify({'success': False, 'message': message}), 500

@quickbooks_bp.route('/webhook', methods=['GET'])
def webhook():
    """Callback route for QuickBooks OAuth2."""
    try:
        code = request.args.get('code')
        state = request.args.get('state')
        error = request.args.get('error')
        realm_id = request.args.get('realmId')

        current_app.logger.info(f"Callback - realm_id: {realm_id}, state: {state}, error: {error}")

        if error:
            current_app.logger.error(f"Error in callback: {error}")
            return jsonify({'error': 'Error in callback'}), 400

        if not code:
            current_app.logger.error("No code provided in callback")
            return jsonify({'error': 'No code provided'}), 400

        if not realm_id:
            current_app.logger.error("No realm ID provided in callback")
            return jsonify({'error': 'No realm ID provided'}), 400

        qb = QuickBooks()
        tokens = qb.get_quickbooks_access_token(code)

        current_app.logger.info("Access tokens retrieved successfully")

        # Update QuickBooks configuration
        try:
            config = QuickBooksConfig.update_config(
                access_token=QuickBooksHelper.encrypt(tokens['access_token']),
                refresh_token=QuickBooksHelper.encrypt(tokens['refresh_token']),
                authorization_code=QuickBooksHelper.encrypt(code),
                realm_id=realm_id,
                is_active=True
            )
            current_app.logger.info("Updated QuickBooks configuration successfully")
            return jsonify({'success': True, 'message': 'QuickBooks integration successful'}), 200
        except Exception as e:
            current_app.logger.error(f"Failed to update QuickBooks configuration: {e}")
            return jsonify({'error': 'Failed to update QuickBooks configuration'}), 400

    except Exception as e:
        current_app.logger.error(f"Error in webhook: {e}")
        return jsonify({'error': 'Error processing callback'}), 500


# Invoice Endpoints
@quickbooks_bp.route('/invoices', methods=['GET'])
def get_invoices():
    """Get all invoices with optional filtering."""
    try:
        # Check if QuickBooks is configured
        if not QuickBooksConfig.is_connected():
            return jsonify({
                'success': False,
                'error': 'QuickBooks not connected',
                'message': 'Please connect to QuickBooks first'
            }), 400

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
            return jsonify({
                'success': False,
                'error': invoices['error'],
                'details': invoices.get('details', '')
            }), 500

        return jsonify({
            'success': True,
            'data': invoices,
            'message': 'Invoices retrieved successfully'
        }), 200

    except Exception as e:
        current_app.logger.error(f"Error getting invoices: {e}")
        return jsonify({
            'success': False,
            'error': 'Error getting invoices',
            'details': str(e)
        }), 500


@quickbooks_bp.route('/invoices/<invoice_id>', methods=['GET'])
def get_invoice(invoice_id):
    """Get a specific invoice by ID."""
    try:
        # Check if QuickBooks is configured
        if not QuickBooksConfig.is_connected():
            return jsonify({
                'success': False,
                'error': 'QuickBooks not connected',
                'message': 'Please connect to QuickBooks first'
            }), 400

        if not invoice_id:
            return jsonify({
                'success': False,
                'error': 'Invoice ID is required',
                'message': 'Please provide a valid invoice ID'
            }), 400

        qb = QuickBooks()
        current_app.logger.info(f'Getting invoice with ID: {invoice_id}')

        invoice = qb.get_invoice(qb.realm_id, invoice_id)

        # Check for errors in the response
        if 'Fault' in invoice:
            return jsonify({
                'success': False,
                'error': 'Invoice not found or error occurred',
                'details': invoice['Fault']['Error'][0]['Message'] if invoice['Fault']['Error'] else 'Unknown error'
            }), 404

        current_app.logger.info("Invoice retrieved successfully")
        return jsonify({
            'success': True,
            'data': invoice,
            'message': 'Invoice retrieved successfully'
        }), 200

    except Exception as e:
        current_app.logger.error(f"Error getting invoice: {e}")
        return jsonify({
            'success': False,
            'error': 'Error getting invoice',
            'details': str(e)
        }), 500


@quickbooks_bp.route('/invoices', methods=['POST'])
def create_invoice():
    """Create a new invoice."""
    try:
        # Check if QuickBooks is configured
        if not QuickBooksConfig.is_connected():
            return jsonify({
                'success': False,
                'error': 'QuickBooks not connected',
                'message': 'Please connect to QuickBooks first'
            }), 400

        # Validate request data
        if not request.json:
            return jsonify({
                'success': False,
                'error': 'No data provided',
                'message': 'Please provide invoice data in JSON format'
            }), 400

        invoice_data = request.json

        # Basic validation for required fields
        if 'Line' not in invoice_data:
            return jsonify({
                'success': False,
                'error': 'Missing required field: Line',
                'message': 'Invoice must contain at least one line item'
            }), 400

        if 'CustomerRef' not in invoice_data:
            return jsonify({
                'success': False,
                'error': 'Missing required field: CustomerRef',
                'message': 'Invoice must have a customer reference'
            }), 400

        qb = QuickBooks()
        current_app.logger.info('Creating new invoice')

        result = qb.create_invoice(qb.realm_id, invoice_data)

        # Check for errors in the response
        if 'Fault' in result:
            return jsonify({
                'success': False,
                'error': 'Failed to create invoice',
                'details': result['Fault']['Error'][0]['Message'] if result['Fault']['Error'] else 'Unknown error'
            }), 400

        current_app.logger.info("Invoice created successfully")
        return jsonify({
            'success': True,
            'data': result,
            'message': 'Invoice created successfully'
        }), 201

    except Exception as e:
        current_app.logger.error(f"Error creating invoice: {e}")
        return jsonify({
            'success': False,
            'error': 'Error creating invoice',
            'details': str(e)
        }), 500