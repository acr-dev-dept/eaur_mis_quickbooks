from flask import Blueprint, request, jsonify, current_app, session, flash, redirect, url_for
from application.services.quickbooks import QuickBooks
from application.helpers.quickbooks_helpers import QuickBooksHelper
from application.models.central_models import QuickBooksConfig, QuickbooksAuditLog
import os
import logging
import traceback
from decimal import Decimal
from dotenv import load_dotenv
from application.models.mis_models import TblIncomeCategory
from datetime import datetime



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


@quickbooks_bp.route('/invoices/<invoice_id>', methods=['PUT'])
def update_invoice(invoice_id):
    """Update an existing invoice."""
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

        # Validate request data
        if not request.json:
            return jsonify({
                'success': False,
                'error': 'No data provided',
                'message': 'Please provide invoice data in JSON format'
            }), 400

        update_data = request.json
        update_type = request.args.get('type', 'sparse')  # sparse or full

        qb = QuickBooks()
        current_app.logger.info(f'Updating invoice {invoice_id} with {update_type} update')

        if update_type.lower() == 'full':
            result = qb.full_update_invoice(qb.realm_id, invoice_id, update_data)
        else:
            result = qb.sparse_invoice_update(qb.realm_id, invoice_id, update_data)

        # Check for errors in the response
        if 'Fault' in result:
            return jsonify({
                'success': False,
                'error': 'Failed to update invoice',
                'details': result['Fault']['Error'][0]['Message'] if result['Fault']['Error'] else 'Unknown error'
            }), 400

        current_app.logger.info("Invoice updated successfully")
        return jsonify({
            'success': True,
            'data': result,
            'message': 'Invoice updated successfully'
        }), 200

    except Exception as e:
        current_app.logger.error(f"Error updating invoice: {e}")
        return jsonify({
            'success': False,
            'error': 'Error updating invoice',
            'details': str(e)
        }), 500


@quickbooks_bp.route('/invoices/<invoice_id>', methods=['DELETE'])
def delete_invoice(invoice_id):
    """Delete an invoice."""
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
        current_app.logger.info(f'Deleting invoice with ID: {invoice_id}')

        result = qb.delete_invoice(qb.realm_id, invoice_id)

        # Check for errors in the response
        if 'Fault' in result:
            return jsonify({
                'success': False,
                'error': 'Failed to delete invoice',
                'details': result['Fault']['Error'][0]['Message'] if result['Fault']['Error'] else 'Unknown error'
            }), 400

        current_app.logger.info("Invoice deleted successfully")
        return jsonify({
            'success': True,
            'data': result,
            'message': 'Invoice deleted successfully'
        }), 200

    except Exception as e:
        current_app.logger.error(f"Error deleting invoice: {e}")
        return jsonify({
            'success': False,
            'error': 'Error deleting invoice',
            'details': str(e)
        }), 500


@quickbooks_bp.route('/invoices/<invoice_id>/void', methods=['POST'])
def void_invoice(invoice_id):
    """Void an invoice."""
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
        current_app.logger.info(f'Voiding invoice with ID: {invoice_id}')

        result = qb.void_invoice(qb.realm_id, invoice_id)

        # Check for errors in the response
        if 'Fault' in result:
            return jsonify({
                'success': False,
                'error': 'Failed to void invoice',
                'details': result['Fault']['Error'][0]['Message'] if result['Fault']['Error'] else 'Unknown error'
            }), 400

        current_app.logger.info("Invoice voided successfully")
        return jsonify({
            'success': True,
            'data': result,
            'message': 'Invoice voided successfully'
        }), 200

    except Exception as e:
        current_app.logger.error(f"Error voiding invoice: {e}")
        return jsonify({
            'success': False,
            'error': 'Error voiding invoice',
            'details': str(e)
        }), 500


@quickbooks_bp.route('/invoices/<invoice_id>/pdf', methods=['GET'])
def get_invoice_pdf(invoice_id):
    """Get invoice as PDF."""
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
        current_app.logger.info(f'Getting PDF for invoice with ID: {invoice_id}')

        result = qb.get_invoice_as_pdf(qb.realm_id, invoice_id)

        # Check for errors in the response
        if isinstance(result, dict) and 'Fault' in result:
            return jsonify({
                'success': False,
                'error': 'Failed to get invoice PDF',
                'details': result['Fault']['Error'][0]['Message'] if result['Fault']['Error'] else 'Unknown error'
            }), 400

        current_app.logger.info("Invoice PDF retrieved successfully")
        # For PDF content, we should return the binary data with appropriate headers
        from flask import Response
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
        return jsonify({
            'success': False,
            'error': 'Error getting invoice PDF',
            'details': str(e)
        }), 500


@quickbooks_bp.route('/invoices/<invoice_id>/send', methods=['POST'])
def send_invoice(invoice_id):
    """Send invoice via email."""
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

        # Check if email is provided in request body
        email = None
        if request.json and 'email' in request.json:
            email = request.json['email']
            if not email or '@' not in email:
                return jsonify({
                    'success': False,
                    'error': 'Invalid email address',
                    'message': 'Please provide a valid email address'
                }), 400

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
            return jsonify({
                'success': False,
                'error': 'Failed to send invoice',
                'details': result['Fault']['Error'][0]['Message'] if result['Fault']['Error'] else 'Unknown error'
            }), 400

        current_app.logger.info("Invoice sent successfully")
        return jsonify({
            'success': True,
            'data': result,
            'message': f'Invoice sent successfully{" to " + email if email else ""}'
        }), 200

    except Exception as e:
        current_app.logger.error(f"Error sending invoice: {e}")
        return jsonify({
            'success': False,
            'error': 'Error sending invoice',
            'details': str(e)
        }), 500


# Payment Endpoints
@quickbooks_bp.route('/payments', methods=['GET'])
def get_payments():
    """Get all payments with optional filtering."""
    try:
        # Check if QuickBooks is configured
        if not QuickBooksConfig.is_connected():
            return jsonify({
                'success': False,
                'error': 'QuickBooks not connected',
                'message': 'Please connect to QuickBooks first'
            }), 400

        qb = QuickBooks()
        current_app.logger.info('Getting payments')

        # Get query parameters for filtering
        params = {}
        if request.args.get('customer_id'):
            params['customerref'] = request.args.get('customer_id')
        if request.args.get('txn_date'):
            params['txndate'] = request.args.get('txn_date')
        if request.args.get('active'):
            params['active'] = request.args.get('active').lower() == 'true'

        payments = qb.get_payments(qb.realm_id, params if params else None)
        current_app.logger.info("Payments retrieved successfully")

        # Check for errors in the response
        if 'error' in payments:
            return jsonify({
                'success': False,
                'error': payments['error'],
                'details': payments.get('details', '')
            }), 500

        return jsonify({
            'success': True,
            'data': payments,
            'message': 'Payments retrieved successfully'
        }), 200

    except Exception as e:
        current_app.logger.error(f"Error getting payments: {e}")
        return jsonify({
            'success': False,
            'error': 'Error getting payments',
            'details': str(e)
        }), 500


@quickbooks_bp.route('/payments/<payment_id>', methods=['GET'])
def get_payment(payment_id):
    """Get a specific payment by ID."""
    try:
        # Check if QuickBooks is configured
        if not QuickBooksConfig.is_connected():
            return jsonify({
                'success': False,
                'error': 'QuickBooks not connected',
                'message': 'Please connect to QuickBooks first'
            }), 400

        if not payment_id:
            return jsonify({
                'success': False,
                'error': 'Payment ID is required',
                'message': 'Please provide a valid payment ID'
            }), 400

        qb = QuickBooks()
        current_app.logger.info(f'Getting payment with ID: {payment_id}')

        payment = qb.get_payment(qb.realm_id, payment_id)

        # Check for errors in the response
        if 'Fault' in payment:
            return jsonify({
                'success': False,
                'error': 'Payment not found or error occurred',
                'details': payment['Fault']['Error'][0]['Message'] if payment['Fault']['Error'] else 'Unknown error'
            }), 404

        current_app.logger.info("Payment retrieved successfully")
        return jsonify({
            'success': True,
            'data': payment,
            'message': 'Payment retrieved successfully'
        }), 200

    except Exception as e:
        current_app.logger.error(f"Error getting payment: {e}")
        return jsonify({
            'success': False,
            'error': 'Error getting payment',
            'details': str(e)
        }), 500


@quickbooks_bp.route('/payments', methods=['POST'])
def create_payment():
    """Create a new payment."""
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
                'message': 'Please provide payment data in JSON format'
            }), 400

        payment_data = request.json

        # Basic validation for required fields
        if 'CustomerRef' not in payment_data:
            return jsonify({
                'success': False,
                'error': 'Missing required field: CustomerRef',
                'message': 'Payment must have a customer reference'
            }), 400

        if 'TotalAmt' not in payment_data:
            return jsonify({
                'success': False,
                'error': 'Missing required field: TotalAmt',
                'message': 'Payment must have a total amount'
            }), 400

        qb = QuickBooks()
        current_app.logger.info('Creating new payment')

        result = qb.create_payment(qb.realm_id, payment_data)

        # Check for errors in the response
        if 'Fault' in result:
            return jsonify({
                'success': False,
                'error': 'Failed to create payment',
                'details': result['Fault']['Error'][0]['Message'] if result['Fault']['Error'] else 'Unknown error'
            }), 400

        current_app.logger.info("Payment created successfully")
        return jsonify({
            'success': True,
            'data': result,
            'message': 'Payment created successfully'
        }), 201

    except Exception as e:
        current_app.logger.error(f"Error creating payment: {e}")
        return jsonify({
            'success': False,
            'error': 'Error creating payment',
            'details': str(e)
        }), 500


@quickbooks_bp.route('/payments/<payment_id>', methods=['PUT'])
def update_payment(payment_id):
    """Update an existing payment."""
    try:
        # Check if QuickBooks is configured
        if not QuickBooksConfig.is_connected():
            return jsonify({
                'success': False,
                'error': 'QuickBooks not connected',
                'message': 'Please connect to QuickBooks first'
            }), 400

        if not payment_id:
            return jsonify({
                'success': False,
                'error': 'Payment ID is required',
                'message': 'Please provide a valid payment ID'
            }), 400

        # Validate request data
        if not request.json:
            return jsonify({
                'success': False,
                'error': 'No data provided',
                'message': 'Please provide payment data in JSON format'
            }), 400

        update_data = request.json

        qb = QuickBooks()
        current_app.logger.info(f'Updating payment {payment_id}')

        result = qb.update_payment(qb.realm_id, payment_id, update_data)

        # Check for errors in the response
        if 'Fault' in result:
            return jsonify({
                'success': False,
                'error': 'Failed to update payment',
                'details': result['Fault']['Error'][0]['Message'] if result['Fault']['Error'] else 'Unknown error'
            }), 400

        current_app.logger.info("Payment updated successfully")
        return jsonify({
            'success': True,
            'data': result,
            'message': 'Payment updated successfully'
        }), 200

    except Exception as e:
        current_app.logger.error(f"Error updating payment: {e}")
        return jsonify({
            'success': False,
            'error': 'Error updating payment',
            'details': str(e)
        }), 500


@quickbooks_bp.route('/payments/<payment_id>', methods=['DELETE'])
def delete_payment(payment_id):
    """Delete a payment."""
    try:
        # Check if QuickBooks is configured
        if not QuickBooksConfig.is_connected():
            return jsonify({
                'success': False,
                'error': 'QuickBooks not connected',
                'message': 'Please connect to QuickBooks first'
            }), 400

        if not payment_id:
            return jsonify({
                'success': False,
                'error': 'Payment ID is required',
                'message': 'Please provide a valid payment ID'
            }), 400

        qb = QuickBooks()
        current_app.logger.info(f'Deleting payment with ID: {payment_id}')

        result = qb.delete_payment(qb.realm_id, payment_id)

        # Check for errors in the response
        if 'Fault' in result:
            return jsonify({
                'success': False,
                'error': 'Failed to delete payment',
                'details': result['Fault']['Error'][0]['Message'] if result['Fault']['Error'] else 'Unknown error'
            }), 400

        current_app.logger.info("Payment deleted successfully")
        return jsonify({
            'success': True,
            'data': result,
            'message': 'Payment deleted successfully'
        }), 200

    except Exception as e:
        current_app.logger.error(f"Error deleting payment: {e}")
        return jsonify({
            'success': False,
            'error': 'Error deleting payment',
            'details': str(e)
        }), 500


@quickbooks_bp.route('/payments/<payment_id>/void', methods=['POST'])
def void_payment(payment_id):
    """Void a payment."""
    try:
        # Check if QuickBooks is configured
        if not QuickBooksConfig.is_connected():
            return jsonify({
                'success': False,
                'error': 'QuickBooks not connected',
                'message': 'Please connect to QuickBooks first'
            }), 400

        if not payment_id:
            return jsonify({
                'success': False,
                'error': 'Payment ID is required',
                'message': 'Please provide a valid payment ID'
            }), 400

        qb = QuickBooks()
        current_app.logger.info(f'Voiding payment with ID: {payment_id}')

        result = qb.void_payment(qb.realm_id, payment_id)

        # Check for errors in the response
        if 'Fault' in result:
            return jsonify({
                'success': False,
                'error': 'Failed to void payment',
                'details': result['Fault']['Error'][0]['Message'] if result['Fault']['Error'] else 'Unknown error'
            }), 400

        current_app.logger.info("Payment voided successfully")
        return jsonify({
            'success': True,
            'data': result,
            'message': 'Payment voided successfully'
        }), 200

    except Exception as e:
        current_app.logger.error(f"Error voiding payment: {e}")
        return jsonify({
            'success': False,
            'error': 'Error voiding payment',
            'details': str(e)
        }), 500


@quickbooks_bp.route('/payments/<payment_id>/pdf', methods=['GET'])
def get_payment_pdf(payment_id):
    """Get payment as PDF."""
    try:
        # Check if QuickBooks is configured
        if not QuickBooksConfig.is_connected():
            return jsonify({
                'success': False,
                'error': 'QuickBooks not connected',
                'message': 'Please connect to QuickBooks first'
            }), 400

        if not payment_id:
            return jsonify({
                'success': False,
                'error': 'Payment ID is required',
                'message': 'Please provide a valid payment ID'
            }), 400

        qb = QuickBooks()
        current_app.logger.info(f'Getting PDF for payment with ID: {payment_id}')

        result = qb.get_payment_as_pdf(qb.realm_id, payment_id)

        # Check for errors in the response
        if isinstance(result, dict) and 'Fault' in result:
            return jsonify({
                'success': False,
                'error': 'Failed to get payment PDF',
                'details': result['Fault']['Error'][0]['Message'] if result['Fault']['Error'] else 'Unknown error'
            }), 400

        current_app.logger.info("Payment PDF retrieved successfully")
        # For PDF content, we should return the binary data with appropriate headers
        from flask import Response
        return Response(
            result,
            mimetype='application/pdf',
            headers={
                'Content-Disposition': f'attachment; filename=payment_{payment_id}.pdf',
                'Content-Type': 'application/pdf'
            }
        )

    except Exception as e:
        current_app.logger.error(f"Error getting payment PDF: {e}")
        return jsonify({
            'success': False,
            'error': 'Error getting payment PDF',
            'details': str(e)
        }), 500


@quickbooks_bp.route('/payments/<payment_id>/send', methods=['POST'])
def send_payment(payment_id):
    """Send payment via email."""
    try:
        # Check if QuickBooks is configured
        if not QuickBooksConfig.is_connected():
            return jsonify({
                'success': False,
                'error': 'QuickBooks not connected',
                'message': 'Please connect to QuickBooks first'
            }), 400

        if not payment_id:
            return jsonify({
                'success': False,
                'error': 'Payment ID is required',
                'message': 'Please provide a valid payment ID'
            }), 400

        # Email is required for payment sending
        if not request.json or 'email' not in request.json:
            return jsonify({
                'success': False,
                'error': 'Email address is required',
                'message': 'Please provide an email address in the request body'
            }), 400

        email = request.json['email']
        if not email or '@' not in email:
            return jsonify({
                'success': False,
                'error': 'Invalid email address',
                'message': 'Please provide a valid email address'
            }), 400

        qb = QuickBooks()
        current_app.logger.info(f'Sending payment {payment_id} to email: {email}')

        result = qb.send_payment(qb.realm_id, payment_id, email)

        # Check for errors in the response
        if 'Fault' in result:
            return jsonify({
                'success': False,
                'error': 'Failed to send payment',
                'details': result['Fault']['Error'][0]['Message'] if result['Fault']['Error'] else 'Unknown error'
            }), 400

        current_app.logger.info("Payment sent successfully")
        return jsonify({
            'success': True,
            'data': result,
            'message': f'Payment sent successfully to {email}'
        }), 200

    except Exception as e:
        current_app.logger.error(f"Error sending payment: {e}")
        return jsonify({
            'success': False,
            'error': 'Error sending payment',
            'details': str(e)
        }), 500
@quickbooks_bp.route('/item/get_items', methods=['GET'])
def get_item():
    """Get all items."""
    try:
        # Check if QuickBooks is configured
        if not QuickBooksConfig.is_connected():
            return jsonify({
                'success': False,
                'error': 'QuickBooks not connected',
                'message': 'Please connect to QuickBooks first'
            }), 400

        qb = QuickBooks()
        current_app.logger.info('Getting items')

        items = qb.get_items(qb.realm_id)
        current_app.logger.info("Items retrieved successfully")

        # Check for errors in the response
        if 'error' in items:
            return jsonify({
                'success': False,
                'error': items['error'],
                'details': items.get('details', '')
            }), 500

        return jsonify({
            'success': True,
            'number_of_items': len(items) if isinstance(items, list) else 0,
            'data': items,
            'message': 'Items retrieved successfully'
        }), 200

    except Exception as e:
        current_app.logger.error(f"Error getting items: {e}")
        return jsonify({
            'success': False,
            'error': 'Error getting items',
            'details': str(e)
        }), 500
    
@quickbooks_bp.route('/item/get_items/<string:item_type>', methods=['GET'])
def get_items(item_type):
    """Get items by type."""
    try:
        # Check if QuickBooks is configured
        if not QuickBooksConfig.is_connected():
            return jsonify({
                'success': False,
                'error': 'QuickBooks not connected',
                'message': 'Please connect to QuickBooks first'
            }), 400

        if item_type.lower() not in ['service', 'inventory', 'non-inventory', 'bundle']:
            return jsonify({
                'success': False,
                'error': 'Invalid item type',
                'message': 'Item type must be one of: service, inventory, non-inventory, bundle'
            }), 400

        qb = QuickBooks()
        current_app.logger.info(f'Getting items of type: {item_type}')

        items = qb.get_items_by_type(qb.realm_id, item_type.lower())
        current_app.logger.info("Items retrieved successfully")

        # Check for errors in the response
        if 'error' in items:
            return jsonify({
                'success': False,
                'error': items['error'],
                'details': items.get('details', '')
            }), 500

        return jsonify({
            'success': True,
            'number_of_items': len(items) if isinstance(items, list) else 0,
            'data': items,
            'message': f'Items of type {item_type} retrieved successfully'
        }), 200

    except Exception as e:
        current_app.logger.error(f"Error getting items: {e}")
        return jsonify({
            'success': False,
            'error': 'Error getting items',
            'details': str(e)
        }), 500
    
@quickbooks_bp.route('/item/create_item', methods=['POST'])
def create_item():
    """Create a new item.
    
    Example:
    {
        "Name": "Sample Item",
        "Type": "Service",
        "IncomeAccountRef": {
            "value": "79",
            "name": "Sales of Product Income"
        },
        "Description": "This is a sample item",
        "UnitPrice": 100.00,
        "Taxable": false
        }
    """
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
                'message': 'Please provide item data in JSON format'
            }), 400
        required_item_types = ['Service', 'Inventory', 'NonInventory', 'Bundle']

        item_data = request.json

        if item_data.get('Type') not in required_item_types:
            current_app.logger.error(f"Invalid item type: {item_data.get('Type')}")
            return jsonify({
                'success': False,
                'error': 'Invalid item type',
                'message': f"Item type must be one of: {', '.join(required_item_types)}"
            }), 400


        # Basic validation for required fields
        if 'Name' not in item_data:
            return jsonify({
                'success': False,
                'error': 'Missing required field: Name',
                'message': 'Item must have a name'
            }), 400

        if 'Type' not in item_data:
            return jsonify({
                'success': False,
                'error': 'Invalid or missing required field: Type',
                'message': 'Item type must be one of: service, inventory, non-inventory, bundle'
            }), 400

        if 'IncomeAccountRef' not in item_data:
            return jsonify({
                'success': False,
                'error': 'Missing required field: IncomeAccountRef',
                'message': 'Item must have an income account reference'
            }), 400

        qb = QuickBooks()
        current_app.logger.info('Creating new item')

        result = qb.create_item(qb.realm_id, item_data)

        # Check for errors in the response
        if 'Fault' in result:
            return jsonify({
                'success': False,
                'error': 'Failed to create item',
                'details': result['Fault']['Error'][0]['Message'] if result['Fault']['Error'] else 'Unknown error'
            }), 400

        current_app.logger.info("Item created successfully")
        return jsonify({
            'success': True,
            'data': result,
            'message': 'Item created successfully'
        }), 201

    except Exception as e:
        current_app.logger.error(f"Error creating item: {e}")
        return jsonify({
            'success': False,
            'error': 'Error creating item',
            'details': str(e)
        }), 500
    
@quickbooks_bp.route('/item/sync_items', methods=['POST'])
def sync_single_item():
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
                'message': 'Please provide item data in JSON format'
            }), 400
        required_item_types = ['Service', 'Inventory', 'NonInventory', 'Bundle']
        payload = request.json

        income_category = TblIncomeCategory.get_category_by_id(payload.get('income_category_id'))

        if not income_category:
            return jsonify({
                'success': False,
                'error': 'Invalid income category ID',
                'message': 'Please provide a valid income category ID'
            }), 400
        if income_category['status_Id'] != 1:
            return jsonify({
                'success': False,
                'error': 'Income category is inactive',
                'message': 'Please provide an active income category'
            }), 400
        
        if income_category['Quickbk_Status'] == 1:
            return jsonify({
                'success': False,
                'error': 'Income category already synced',
                'message': 'This income category has already been synced with QuickBooks'
            }), 400

        item_data = {
            "Name": income_category['name'],
            "Type": "Service",
            "IncomeAccountRef": {
                "value": "79",
            },
            "Description": income_category['description'] or "No description",
            "UnitPrice": float(income_category['amount']) if income_category['amount'] else 0.0,
        }
        qb = QuickBooks()
        current_app.logger.info('Syncing single item')
        result = qb.create_item(qb.realm_id, item_data)
        current_app.logger.info(f"QuickBooks response: {result}")
        if 'Fault' in result:
            return jsonify({
                'success': False,
                'error': 'Failed to sync item',
                'details': result['Fault']['Error'][0]['Message'] if result['Fault']['Error'] else 'Unknown error'
            }), 400
        current_app.logger.info("Item synced successfully")
        # update qb status
        current_app.logger.info(f"QuickBooks response: {result}")
        current_app.logger.info(f"data from result: {result.get('data', {})}")
        current_app.logger.info(f"Item from data: {result.get('data', {}).get('Item', {})}")

        item_id = result.get("data", {}).get("Item", {}).get("Id")
        current_app.logger.info(f"Item ID from QuickBooks: {item_id}")
        if not item_id:
            return jsonify({
                'success': False,
                'error': 'Failed to retrieve Item ID from QuickBooks response',
                'details': 'Item ID is missing in the response data'
            }), 500
        update_status = TblIncomeCategory.update_quickbooks_status(category_id=income_category['id'], quickbooks_id=item_id, pushed_by="ItemSyncService")
        current_app.logger.info(f"QuickBooks status updated: {update_status}")
        if not update_status:
            current_app.logger.error("Failed to update QuickBooks status in local database")
        return jsonify({
            'success': True,
            'data': result,
            'message': 'Item synced successfully'
        }), 201
    except Exception as e:
        current_app.logger.error(f"Error syncing item: {e}")
        return jsonify({
            'success': False,
            'error': 'Error syncing item',
            'details': str(e)
        }), 500

        


@quickbooks_bp.route('/get_customers', methods=['GET'])
def get_customers():
    """Get all customers."""
    try:
        # Check if QuickBooks is configured
        if not QuickBooksConfig.is_connected():
            return jsonify({
                'success': False,
                'error': 'QuickBooks not connected',
                'message': 'Please connect to QuickBooks first'
            }), 400

        qb = QuickBooks()
        current_app.logger.info('Getting customers')

        customers = qb.get_customers(qb.realm_id)
        current_app.logger.info("Customers retrieved successfully")

        # Check for errors in the response
        if 'error' in customers:
            return jsonify({
                'success': False,
                'error': customers['error'],
                'details': customers.get('details', '')
            }), 500

        return jsonify({
            'success': True,
            'number_of_customers': len(customers) if isinstance(customers, list) else 0,
            'data': customers,
            'message': 'Customers retrieved successfully'
        }), 200

    except Exception as e:
        current_app.logger.error(f"Error getting customers: {e}")
        return jsonify({
            'success': False,
            'error': 'Error getting customers',
            'details': str(e)
        }), 500

@quickbooks_bp.route('/get_items', methods=['GET'])
def get_all_items():
    """Get all items."""
    try:
        # Check if QuickBooks is configured
        if not QuickBooksConfig.is_connected():
            return jsonify({
                'success': False,
                'error': 'QuickBooks not connected',
                'message': 'Please connect to QuickBooks first'
            }), 400

        qb = QuickBooks()
        current_app.logger.info('Getting items')

        items = qb.get_items(qb.realm_id)
        current_app.logger.info("Items retrieved successfully")

        # Check for errors in the response
        if 'error' in items:
            return jsonify({
                'success': False,
                'error': items['error'],
                'details': items.get('details', '')
            }), 500

        return jsonify({
            'success': True,
            'number_of_items': len(items) if isinstance(items, list) else 0,
            'data': items,
            'message': 'Items retrieved successfully'
        }), 200

    except Exception as e:
        current_app.logger.error(f"Error getting items: {e}")
        return jsonify({
            'success': False,
            'error': 'Error getting items',
            'details': str(e)
        }), 500

@quickbooks_bp.route('/get_customer', methods=['GET'])
def get_customer():
    """Get a specific customer by ID."""
    try:
        # Check if QuickBooks is configured
        if not QuickBooksConfig.is_connected():
            return jsonify({
                'success': False,
                'error': 'QuickBooks not connected',
                'message': 'Please connect to QuickBooks first'
            }), 400

        customer_id = request.args.get('customer_id')
        if not customer_id:
            return jsonify({
                'success': False,
                'error': 'Customer ID is required',
                'message': 'Please provide a valid customer ID as a query parameter'
            }), 400

        qb = QuickBooks()
        current_app.logger.info(f'Getting customer with ID: {customer_id}')

        customer = qb.get_customer(qb.realm_id, customer_id)
        current_app.logger.info(f"Customer data: {customer}")

        # Check for errors in the response
        if 'Fault' in customer:
            return jsonify({
                'success': False,
                'error': 'Customer not found or error occurred',
                'details': customer['Fault']['Error'][0]['Message'] if customer['Fault']['Error'] else 'Unknown error'
            }), 404

        current_app.logger.info("Customer retrieved successfully")
        return jsonify({
            'success': True,
            'data': customer,
            'message': 'Customer retrieved successfully'
        }), 200

    except Exception as e:
        current_app.logger.error(f"Error getting customer: {e}")
        return jsonify({
            'success': False,
            'error': 'Error getting customer',
            'details': str(e)
        }), 500
    
@quickbooks_bp.route('/get_custom_field_definitions', methods=['GET'])
def get_custom_field_definitions():
    """Get all custom field definitions."""
    try:
        # Check if QuickBooks is configured
        if not QuickBooksConfig.is_connected():
            return jsonify({
                'success': False,
                'error': 'QuickBooks not connected',
                'message': 'Please connect to QuickBooks first'
            }), 400

        qb = QuickBooks()
        current_app.logger.info('Getting custom field definitions')

        custom_fields = qb.get_custom_field_definitions(qb.realm_id)
        current_app.logger.info(f"Custom field definitions retrieved successfully: {custom_fields}")

        # Check for errors in the response
        if 'error' in custom_fields:
            return jsonify({
                'success': False,
                'error': custom_fields['error'],
                'details': custom_fields.get('details', '')
            }), 500

        return jsonify({
            'success': True,
            'number_of_custom_fields': len(custom_fields) if isinstance(custom_fields, list) else 0,
            'data': custom_fields,
            'message': 'Custom field definitions retrieved successfully'
        }), 200

    except Exception as e:
        current_app.logger.error(f"Error getting custom field definitions: {e}")
        return jsonify({
            'success': False,
            'error': 'Error getting custom field definitions',
            'details': str(e)
        }), 500

@quickbooks_bp.route('/get_customer_types', methods=['GET'])
def get_customer_types():
    """Get all customer types."""
    try:
        # Check if QuickBooks is configured
        if not QuickBooksConfig.is_connected():
            return jsonify({
                'success': False,
                'error': 'QuickBooks not connected',
                'message': 'Please connect to QuickBooks first'
            }), 400

        qb = QuickBooks()
        current_app.logger.info('Getting customer types')

        customer_types = qb.get_customer_types(qb.realm_id)
        current_app.logger.info(f"Customer types retrieved successfully: {customer_types}")

        # Check for errors in the response
        if 'error' in customer_types:
            return jsonify({
                'success': False,
                'error': customer_types['error'],
                'details': customer_types.get('details', '')
            }), 500

        return jsonify({
            'success': True,
            'number_of_customer_types': len(customer_types) if isinstance(customer_types, list) else 0,
            'data': customer_types,
            'message': 'Customer types retrieved successfully'
        }), 200

    except Exception as e:
        current_app.logger.error(f"Error getting customer types: {e}")
        return jsonify({
            'success': False,
            'error': 'Error getting customer types',
            'details': str(e)
        }), 500
    