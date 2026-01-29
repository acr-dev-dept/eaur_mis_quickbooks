from flask import Blueprint, request, jsonify, current_app
from datetime import datetime, timedelta
from application.models.mis_models import TblImvoice, TblPersonalUg, TblStudentWallet, Payment, TblOnlineApplication, TblStudentWalletHistory
from application.utils.database import db_manager
from application.utils.auth_decorators import require_auth, require_gateway, log_api_access
from sqlalchemy.orm import joinedload
import traceback
import jwt
import os
from application.services.payment_sync import PaymentSyncService
import requests
import random
import uuid
from application.utils.database import db_manager  # ← adjust to wherever db_manager is defined
from datetime import datetime, date
from application.models.central_models import IntegrationLog
from sqlalchemy.exc import IntegrityError



# Import the Celery task for syncing payment to QuickBooks


urubuto_bp = Blueprint('urubuto', __name__)
# Initialize Urubuto Pay service
from application.services.urubuto_pay import UrubutoPay
urubuto_service = UrubutoPay()


def resolve_payer_code(payer_code):
    """
    Determines whether payer_code is:
    - an invoice reference
    - a student registration number
    """
    invoice = TblImvoice.get_invoice_details(payer_code)
    if invoice:
        return "INVOICE", invoice

    student = TblPersonalUg.get_student_data(payer_code)
    applicant = TblOnlineApplication.get_applicant_data(payer_code)
    if applicant:
        return "APPLICANT", applicant
    if student:
        return "STUDENT", student

    return None, None



@urubuto_bp.route('/authentication', methods=['POST'])
def authentication():
    """
    Authentication endpoint for Urubuto Pay integration.

    This endpoint provides Bearer tokens for Urubuto Pay to access protected APIs.
    Tokens are valid for 24 hours.

    Expected request format:
    {
        "user_name": "bkTechPymtGtwy",
        "password": "myPss@2020"
    }

    Returns a Bearer token for API authentication.
    """
    try:
        # Validate request data
        if not request.is_json:
            return jsonify({
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "message": "Content-Type must be application/json",
                "status": 400
            }), 400

        data = request.get_json()
        if not data:
            return jsonify({
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "message": "No data provided",
                "status": 400
            }), 400

        # Validate required parameters
        username = data.get('user_name')
        password = data.get('password')

        if not username or not password:
            return jsonify({
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "message": "Missing required parameters: user_name and password",
                "status": 400
            }), 400

        current_app.logger.info(f"Authentication request for user: {username}")

        # Use AuthenticationService for credential validation and token generation
        from application.models.central_models import AuthenticationService

        success, token_or_error = AuthenticationService.authenticate_and_generate_token(username, password)

        if success:
            current_app.logger.info(f"Authentication successful for user: {username}")
            return jsonify({
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "message": "Successful",
                "status": 200,
                "data": {
                    "token": token_or_error
                }
            }), 200
        else:
            current_app.logger.warning(f"Authentication failed for user {username} with {password}: {token_or_error}")
            return jsonify({
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "message": "Invalid credentials",
                "status": 401
            }), 401

    except Exception as e:
        current_app.logger.error(f"Error in authentication: {str(e)}")
        current_app.logger.error(traceback.format_exc())
        return jsonify({
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "message": "Internal server error",
            "status": 500
        }), 500

@urubuto_bp.route('/validation', methods=['POST'])
@require_auth('validation')
@require_gateway(['urubuto_pay', 'school_gear'])
@log_api_access('payer_validation')
def payer_validation():
    """
    Payer validation endpoint for Urubuto Pay integration.

    This endpoint is called by Urubuto Pay to validate payer codes (reference numbers)
    and retrieve invoice/payment details for students.

    Expected request format from Urubuto Pay:
    {
        "merchant_code": "TH25369401",
        "payer_code": "UG253694"  // This is the reference number from invoice
    }

    Returns student details, invoice amount, and service information.
    """
    current_app.logger.info("PAYER VALIDATION ENDPOINT CALLED ===")
    current_app.logger.info(f"Request method: {request.method}")
    current_app.logger.info(f"Request endpoint: {request.endpoint}")
    current_app.logger.info(f"Request remote addr: {request.remote_addr}")
    current_app.logger.info(f"Request content type: {request.content_type}")
    current_app.logger.info(f"Token payload available: {hasattr(request, 'token_payload')}")

    if hasattr(request, 'token_payload'):
        current_app.logger.info(f"Authenticated client: {request.token_payload.get('client_name')}")
        current_app.logger.info(f"Client gateway: {request.token_payload.get('gateway_name')}")
        current_app.logger.info(f"Client permissions: {request.token_payload.get('permissions')}")

    try:
        # Validate request data
        if not request.is_json:
            return jsonify({
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "message": "Content-Type must be application/json",
                "status": 400
            }), 400

        data = request.get_json()
        current_app.logger.info(f"Validation request data: {data}")
        if not data:
            return jsonify({
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "message": "No data provided",
                "status": 400
            }), 400

        # Validate required parameters
        merchant_code = data.get('merchant_code')
        payer_code = data.get('payer_code')
        current_app.logger.info(f"Merchant code: {merchant_code}, Payer code: {payer_code}")

        if not merchant_code or not payer_code:
            return jsonify({
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "message": "Missing required parameters: merchant_code and payer_code",
                "status": 400
            }), 400

        current_app.logger.info(f"Payer validation request - Merchant: {merchant_code}, Payer: {payer_code}")

        
        payer_type, entity = resolve_payer_code(payer_code)
        payer_names=""
        if payer_type is None:
            return jsonify({
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "message": f"No data found for this code: {payer_code}",
                "status": 400
            }), 400
        # get invoice details given the reference number (payer_code)
        
        if payer_type == "INVOICE":
            
            try:  
                
                invoice_bal = TblImvoice.get_invoice_balance(payer_code)
                
                if not invoice_bal:
                    wallet = TblStudentWallet.get_by_reference_number(payer_code)
                    if wallet:
                        invoice_bal_wallet = wallet.dept
                    else:
                        invoice_bal_wallet = 0
                    invoice_balance = invoice_bal_wallet
                    current_app.logger.info(f"Invoice balance retrieved from wallet: {invoice_balance}")
                    return jsonify({
                        "message": "Successful",
                        "status": 200}), 200
                
                invoice_deposit_amount = TblImvoice.get_invoice_deposit_amount(payer_code)

                invoice_balance = invoice_bal or invoice_deposit_amount
                amount = invoice_balance
                
                if invoice_balance is None:
                    current_app.logger.warning(f"No invoice found for payer_code: {payer_code}")
                    return jsonify({
                        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "message": f"No data found for this code: {payer_code}",
                        "status": 400
                    }), 400
                # Make sure the balance is greater than zero
                if float(invoice_balance) == 0.0:
                    current_app.logger.warning(f"Invoice balance is zero for payer_code: {payer_code}")
                    return jsonify({
                        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "message": f"Invoice : {payer_code} has already been paid in full.",
                        "status": 400
                    }), 400
                # make sure it doesn't have decimal places
                invoice_balance = int(float(invoice_balance))
                current_app.logger.info(f"Invoice balance retrieved from MIS: {invoice_balance}")
                current_app.logger.info(f"Invoice balance type: {type(invoice_balance)} and value: {invoice_balance}")
            except Exception as e:
                current_app.logger.error(f"Error retrieving invoice details from Urubuto Pay: {str(e)}")
                current_app.logger.error(traceback.format_exc())
                return jsonify({
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "message": f"Error retrieving invoice details: {str(e)}",
                    "status": 500
                }), 500
            
        elif payer_type == "STUDENT":
            # Explicitly ignore balances
            amount = 0
            payer_names=f"{entity.fname or ''} {entity.lname or ''}".strip()
            if not payer_names:
                payer_names = entity.reg_no

            current_app.logger.info(
                f"Payer code {payer_code} identified as student registration number. "
                "No balance validation required."
            )

        elif payer_type == "APPLICANT":
            # Explicitly ignore balances
            amount = 0
            payer_names = f"{entity.first_name or ''} {entity.family_name or ''}".strip()
            if not payer_names:
                payer_names = entity.tracking_id

            current_app.logger.info(
                f"Payer code {payer_code} identified as applicant. "
                "No balance validation required."
            )
        else:
            return jsonify({
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "message": "Unknown payer type",
                "status": 400
            }), 400
        current_app.logger.info(f"Payer validation successful for payer_code: {payer_code} with amount: {amount}")
        # We are going to stop here and respond with successful response
        return jsonify({
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "message": "Successful",
            "status": 200,
            "data": {
                "merchant_code": merchant_code,
                "payer_code": payer_code,
                "payer_names": payer_names or "Unknown Student",
                "department_code": "0",
                "department_name": "Unknown Department",
                "class_name": "Unknown Class",
                "amount": amount,
                "currency": "RWF",
                "payer_must_pay_total_amount": "NO"
            }
        }), 200

    except Exception as e:
        current_app.logger.error(f"Error in payer validation: {str(e)}")
        current_app.logger.error(traceback.format_exc())
        return jsonify({
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "message": "Internal server error",
            "status": 500
        }), 500
    
@urubuto_bp.route('/callback', methods=['POST'])
@require_auth('notifications')
@require_gateway(['urubuto_pay', 'school_gear'])
def payment_callback():
    """
    Payment callback endpoint for UrubutoPay integration.
    Fully idempotent processing using database-enforced uniqueness and MIS session transaction.
    """
    if request.method != 'POST':
        current_app.logger.warning(f"Invalid method {request.method} on callback endpoint")
        return jsonify({"message": "Method not allowed"}), 405

    current_app.logger.info("PAYMENT CALLBACK ENDPOINT CALLED")
    current_app.logger.info(f"Request remote addr: {request.remote_addr}")
    current_app.logger.info(f"Request content type: {request.content_type}")

    data = request.get_json(silent=True)
    if not data or not isinstance(data, dict):
        return jsonify({
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "message": "Invalid or empty JSON payload",
            "status": 400
        }), 400

    # Required fields
    required_fields = ['transaction_id', 'transaction_status', 'amount', 'payer_code']
    missing = [f for f in required_fields if f not in data or data[f] is None]
    if missing:
        current_app.logger.warning(f"Missing required fields: {missing}")
        return jsonify({
            "message": f"Missing required fields: {', '.join(missing)}",
            "status": 400
        }), 400

    transaction_id = data['transaction_id']
    transaction_status = data['transaction_status']
    payer_code = data['payer_code']
    amount = data['amount']
    payment_channel = data.get('payment_channel_name')
    slip_no = data.get('slip_number') or data.get('initial_slip_number') or "N/A"

    started_at = datetime.now()

    try:
        with db_manager.get_mis_session() as session:

            # ────────────────────────────────────────────────
            # Non-VALID transaction: just log and acknowledge
            # ────────────────────────────────────────────────
            if transaction_status != "VALID" and transaction_status != "PENDING_SETTLEMENT":
                current_app.logger.info(
                    f"Non-VALID status '{transaction_status}' received for {transaction_id} – no processing"
                )
                IntegrationLog.log_integration_operation(
                    system_name="UrubutoPay",
                    operation="Wallet Payment",
                    status=transaction_status,
                    external_transaction_id=transaction_id,
                    payer_code=payer_code,
                    response_data=data,
                    started_at=started_at,
                    completed_at=datetime.now()
                )
                return jsonify({
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "message": f"Received {transaction_status}",
                    "status": 200,
                    "data": {"external_transaction_id": transaction_id}
                }), 200

            # ────────────────────────────────────────────────
            # Resolve payer
            # ────────────────────────────────────────────────
            student = TblPersonalUg.get_student_data(payer_code)
            applicant = None
            if not student:
                applicant = TblOnlineApplication.get_applicant_data(payer_code)

            if not student and not applicant:
                current_app.logger.error(f"Payer not found: {payer_code}")
                return jsonify({"message": "Payer not found", "status": 404}), 404

            reg_no = student.reg_no if student else applicant.tracking_id

            # ────────────────────────────────────────────────
            # Wallet record
            # ────────────────────────────────────────────────
            wallet = TblStudentWallet.get_by_reg_no(reg_no)

            # ────────────────────────────────────────────────
            # Insert wallet history first (DB enforces idempotency)
            # ────────────────────────────────────────────────
            try:
                balance_before = wallet.dept if wallet else 0.0
                balance_after = balance_before + amount

                history = TblStudentWalletHistory(
                    wallet_id=wallet.id if wallet else None,
                    reg_no=reg_no,
                    reference_number=wallet.reference_number if wallet else f"{int(datetime.now().strftime('%Y%m%d%H%M%S'))}_{reg_no}",
                    transaction_type="TOPUP",
                    slip_no=wallet.slip_no if wallet and wallet.slip_no else slip_no,
                    amount=amount,
                    balance_before=balance_before,
                    balance_after=balance_after,
                    trans_code=transaction_id,
                    external_transaction_id=transaction_id,
                    payment_chanel=payment_channel,
                    bank_id=wallet.bank_id if wallet else 2,
                    comment="Wallet top-up",
                    created_by="SYSTEM"
                )

                session.add(history)
                session.flush()  # ← triggers UNIQUE constraint immediately

                

            except IntegrityError:
                session.rollback()
                current_app.logger.info(f"Duplicate transaction ignored: {transaction_id}")
                return jsonify({
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "message": "Transaction already processed",
                    "status": 200,
                    "data": {"external_transaction_id": transaction_id}
                }), 200

            # ────────────────────────────────────────────────
            # Update or create wallet
            # ────────────────────────────────────────────────
            if wallet:
                # Update balance
                wallet.dept = balance_after
                wallet.external_transaction_id = transaction_id
                wallet.trans_code = transaction_id
                wallet.payment_date = datetime.now()
                session.add(wallet)
                session.flush()
                current_app.logger.info(f"Wallet topped up for {reg_no}: {amount}")

                # Async QuickBooks update
                """
                from application.config_files.wallet_sync import update_wallet_to_quickbooks_task
                update_wallet_to_quickbooks_task.delay(wallet.id)
                """
            else:
                # Create wallet entry
                created_wallet = TblStudentWallet.create_wallet_entry(
                    reg_prg_id=int(datetime.now().strftime("%Y%m%d%H%M%S")),
                    reg_no=reg_no,
                    reference_number=f"{int(datetime.now().strftime('%Y%m%d%H%M%S'))}_{reg_no}",
                    trans_code=transaction_id,
                    external_transaction_id=transaction_id,
                    payment_chanel=payment_channel,
                    payment_date=date.today(),
                    is_paid="Yes",
                    dept=amount,
                    fee_category=128,
                    bank_id=2,
                    slip_no=slip_no if slip_no else "N/A"
                )
                current_app.logger.info(f"New wallet entry created for payer {reg_no}")
                
                """
                if created_wallet and 'id' in created_wallet:
                    from application.config_files.wallet_sync import sync_wallet_to_quickbooks_task
                    sync_wallet_to_quickbooks_task.delay(created_wallet['id'])
                """
            # ────────────────────────────────────────────────
            # Integration log
            # ────────────────────────────────────────────────
            IntegrationLog.log_integration_operation(
                system_name="UrubutoPay",
                operation="Wallet Payment",
                status=transaction_status,
                external_transaction_id=transaction_id,
                payer_code=payer_code,
                response_data=data,
                started_at=started_at,
                completed_at=datetime.now()
            )

            # session.commit() handled automatically by context manager

    except Exception as e:
        current_app.logger.error(f"Payment callback processing failed for {transaction_id}: {str(e)}")
        current_app.logger.error(traceback.format_exc())
        return jsonify({
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "message": "Internal server error during payment processing",
            "status": 500
        }), 500

    # Success
    return jsonify({
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "message": "Wallet processed successfully",
        "status": 200,
        "data": {
            "external_transaction_id": transaction_id,
            "internal_transaction_id": str(wallet.id if wallet else created_wallet['id'])
        }
    }), 200
@urubuto_bp.route('/payments/notification', methods=['POST'])
@require_auth('notifications')
@require_gateway('urubuto_pay')
@log_api_access('payment_notification')
def payment_notification():
    """
    Payment notification callback endpoint for Urubuto Pay integration.

    This endpoint receives payment confirmations from Urubuto Pay and creates
    payment records in the MIS payments table.

    Expected request format from Urubuto Pay:
    {
        "status": 200,
        "transaction_status": "VALID",
        "transaction_id": "11202202011152166608",
        "merchant_code": "TH35409959",
        "payer_code": "2022011019",
        "payment_chanel": "WALLET",
        "payment_chanel_name": "MOMO",
        "amount": 100,
        "currency": "RWF",
        "payment_date_time": "2022-01-23 09:22:34",
        "slip_number": ""
    }
    """
    current_app.logger.info("PAYMENT NOTIFICATION ENDPOINT CALLED ===")
    current_app.logger.info(f"Request method: {request.method}")
    current_app.logger.info(f"Request endpoint: {request.endpoint}")
    current_app.logger.info(f"Request remote addr: {request.remote_addr}")
    current_app.logger.info(f"Request content type: {request.content_type}")
    current_app.logger.info(f"Token payload available: {hasattr(request, 'token_payload')}")
    current_app.logger.info(f"data received: {request.get_json()}")
    try:
        # Validate request data
        if not request.is_json:
            return jsonify({
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "message": "Content-Type must be application/json",
                "status": 400
            }), 400

        data = request.get_json()
        if not data:
            return jsonify({
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "message": "No data provided",
                "status": 400
            }), 400

        # Extract required fields
        transaction_status = data.get('transaction_status')
        transaction_id = data.get('transaction_id')
        merchant_code = data.get('merchant_code')
        payer_code = data.get('payer_code')
        payment_chanel = data.get('payment_chanel')
        payment_chanel_name = data.get('payment_chanel_name')
        amount = data.get('amount')
        currency = data.get('currency')
        payment_date_time = data.get('payment_date_time')
        slip_no = (
            data.get('slip_number')
            or data.get('initial_slip_number')
            or "N/A"
        )
        # Validate required fields
        required_fields = ['transaction_id', 'merchant_code',
                          'payer_code', 'payment_channel', 'amount', 'currency', 'payment_date_time', 'payment_channel_name']

        missing_fields = [field for field in required_fields if not data.get(field)]
        if missing_fields:
            return jsonify({
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "message": f"Missing required parameters: {', '.join(missing_fields)}",
                "status": 400
            }), 400

        current_app.logger.info(f"Payment notification received - Transaction: {transaction_id}, "
                               f"Payer: {payer_code}, Amount: {amount}")

        # Only process successful payments
        if transaction_id:
            # check the status of the transaction
            try:
                status = TblStudentWallet.get_by_external_transaction_id(transaction_id)
                current_app.logger.info(f"Transaction status check result: {status}")
                if status:
                    # update slip number if any
                    insert_slip = TblStudentWallet.update_slip_no(transaction_id, slip_no)
                    if insert_slip:
                        update_history = TblStudentWalletHistory.update_slip_no(transaction_id, slip_no)
                        current_app.logger.info(f"Slip number updated in history: {update_history}")
                        return jsonify({
                            "message": "Payment Successful",
                            "status": 200
                        }), 200
            except Exception as e:
                current_app.logger.error(f"Error checking transaction status: {e}")
                

            current_app.logger.info(f"Checking that the transaction_id is not empty: {transaction_id}")
            return jsonify({
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "message": "Payment status noted",
                "status": 200,
                "data": {
                    "external_transaction_id": transaction_id,
                    "internal_transaction_id": f"INT_{transaction_id}",
                    "payer_phone_number": "",
                    "payer_email": ""
                }
            }), 200
    except Exception as e:
        current_app.logger.error(f"Error processing payment notification: {str(e)}")
        current_app.logger.error(traceback.format_exc())
        return jsonify({
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "message": "Internal server error",
            "status": 500
        }), 500

@urubuto_bp.route('/payments/initiate', methods=['POST'])
@log_api_access('payment_initiation')
def initiate_payment():
    """
    Payment initiation endpoint for triggering Urubuto Pay transactions.

    This endpoint allows the MIS to initiate payments through Urubuto Pay gateway,
    triggering USSD popups or card payment flows for students.

    Expected request format:
    {
        "payer_code": "12345",
        "channel_name": "MOMO",
        "phone_number": "0788215324",
        "payer_names": "John Doe",
        "payer_email": "john@example.com",
        "redirection_url": "https://mis.eaur.ac.rw/payment-success"
    }
    """
    current_app.logger.info("PAYMENT INITIATION ENDPOINT CALLED ===")
    current_app.logger.info(f"Request method: {request.method}")
    current_app.logger.info(f"Request endpoint: {request.endpoint}")
    current_app.logger.info(f"Request remote addr: {request.remote_addr}")
    current_app.logger.info(f"Request content type: {request.content_type}")
    current_app.logger.info(f"data received: {request.get_json()}")
    try:
        # Validate request data
        if not request.is_json:
            return jsonify({
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "message": "Content-Type must be application/json",
                "status": 400
            }), 400

        data = request.get_json()
        if not data:
            return jsonify({
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "message": "No data provided",
                "status": 400
            }), 400

        # Extract and validate required fields
        payer_code = data.get('payer_code')
        amount = data.get('amount')
        channel_name = data.get('channel_name')
        service_code = data.get('service_code')
        merchant_code = data.get('merchant_code')
        phone_number=data.get('phone_number')
        card_type=data.get('card_type')
        redirection_url=data.get('redirection_url')
        payer_names=data.get('payer_names')
        payer_email=data.get('payer_email')

        if not all([payer_code,  channel_name]):
            return jsonify({
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "message": "Missing required parameters: payer_code, channel_name",
                "status": 400
            }), 400

        # Validate channel name
        valid_channels = ['MOMO', 'AIRTEL_MONEY', 'CARD']
        if channel_name not in valid_channels:
            return jsonify({
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "message": f"Invalid channel_name. Must be one of: {', '.join(valid_channels)}",
                "status": 400
            }), 400

        # For wallet payments, phone number is required
        if channel_name in ['MOMO', 'AIRTEL_MONEY'] and not data.get('phone_number'):
            return jsonify({
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "message": "phone_number is required for wallet payments",
                "status": 400
            }), 400

        current_app.logger.info(f"Payment initiation request - Payer: {payer_code}, "
                               f" Channel: {channel_name}")

        # try to access the service code
        try:
            service_code = urubuto_service.service_code
            current_app.logger.info(f"Urubuto Pay service initialized with service code: {service_code}")
        except Exception as e:
            current_app.logger.error(f"Error accessing Urubuto Pay service code: {str(e)}")
            current_app.logger.error(traceback.format_exc())
        
        # Validate the amount from invoice or wallet
        wallet_data = TblStudentWallet.get_by_reference_number(payer_code)
        if wallet_data:
            amount = wallet_data.dept
            if wallet_data.is_paid == 'Yes' and wallet_data.external_transaction_id:
                return jsonify({
                    "message": "Wallet payment is already made",
                    "status": 400
                }), 400

        

        # Initiate payment
        try:
            result = urubuto_service.initiate_payment(
                payer_code=payer_code,
                amount=amount,
                channel_name=channel_name,
                phone_number=phone_number,
                card_type=card_type,
                redirection_url=redirection_url,
                payer_names=payer_names,
                payer_email=payer_email,
                service_code=service_code,
                merchant_code=merchant_code
            )
            current_app.logger.info(f"Payment initiation result checking: {result}")

            if result['success']:
                current_app.logger.info(f"Payment initiation successful for payer: {payer_code}")
                return jsonify(result['data']), result['status_code']
            else:
                current_app.logger.error(f"Payment initiation failed: {result['error']}")
                return jsonify({
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "message": result['error'],
                    "status": result['status_code']
                }), result['status_code']
        except Exception as e:
            current_app.logger.error(f"Error in payment initiation: {str(e)}")
            current_app.logger.error(traceback.format_exc())
            message = f"Payment initiation error: {str(e)} and traceback: {traceback.format_exc()}"
            return jsonify({
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "message": message,
                "status": 405
            }), 405

    except Exception as e:
        current_app.logger.error(f"Error in payment initiation: {str(e)}")
        current_app.logger.error(traceback.format_exc())
        message = f"Payment initiation error: {str(e)} and traceback: {traceback.format_exc()}"
        return jsonify({
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "message": message,
            "status": 500
        }), 500

@urubuto_bp.route('/payments/status/<transaction_id>', methods=['GET'])
#@require_auth('status_check')
#@require_gateway('urubuto_pay')
#@log_api_access('transaction_status_check')
def check_transaction_status(transaction_id):
    """
    Transaction status checking endpoint for payment reconciliation.

    This endpoint allows checking the status of Urubuto Pay transactions
    for reconciliation and delayed payment confirmation.

    Args:
        transaction_id (str): Urubuto Pay transaction ID
    """
    try:
        if not transaction_id:
            return jsonify({
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "message": "Transaction ID is required",
                "status": 400
            }), 400

        current_app.logger.info(f"Transaction status check request for: {transaction_id}")

        # Initialize Urubuto Pay service
        from application.services.urubuto_pay import UrubutoPay
        urubuto_service = UrubutoPay()

        # Check transaction status
        result = urubuto_service.check_transaction_status(transaction_id)

        if result['success']:
            current_app.logger.info(f"Transaction status check successful for: {transaction_id}")
            return jsonify(result['data']), result['status_code']
        else:
            current_app.logger.error(f"Transaction status check failed: {result['error']}")
            return jsonify({
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "message": result['error'],
                "status": result['status_code']
            }), result['status_code']

    except Exception as e:
        current_app.logger.error(f"Error checking transaction status: {str(e)}")
        current_app.logger.error(traceback.format_exc())
        return jsonify({
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "message": "Internal server error",
            "status": 500
        }), 500

@urubuto_bp.route('/payments/status', methods=['POST'])
@require_auth('status_check')
@log_api_access('payment_status_by_reference')
def check_payment_status_by_reference():
    """
    Check payment status by reference number (payer_code).

    This endpoint allows checking if a payment has been processed
    for a specific reference number/invoice.

    Expected request format:
    {
        "payer_code": "12345"
    }
    """
    try:
        # Validate request data
        if not request.is_json:
            return jsonify({
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "message": "Content-Type must be application/json",
                "status": 400
            }), 400

        data = request.get_json()
        if not data:
            return jsonify({
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "message": "No data provided",
                "status": 400
            }), 400

        payer_code = data.get('payer_code')
        if not payer_code:
            return jsonify({
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "message": "payer_code is required",
                "status": 400
            }), 400

        current_app.logger.info(f"Payment status check by reference: {payer_code}")

        # Check payment status in local database
        session = db_manager.get_mis_session()
        try:
            from application.models.mis_models import Payment
            payments = session.query(Payment).filter(
                Payment.invoi_ref == str(payer_code)
            ).order_by(Payment.recorded_date.desc()).all()

            if not payments:
                return jsonify({
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "message": "No payments found for this reference",
                    "status": 404,
                    "data": {
                        "payer_code": payer_code,
                        "payment_status": "NOT_FOUND",
                        "payments": []
                    }
                }), 404

            # Format payment data
            payment_data = []
            for payment in payments:
                payment_data.append({
                    "payment_id": payment.id,
                    "transaction_id": payment.external_transaction_id,
                    "amount": payment.amount,
                    "payment_chanel": payment.payment_chanel,
                    "payment_date": payment.recorded_date.isoformat() if payment.recorded_date else None,
                    "status": "PROCESSED",
                    "quickbooks_status": payment.QuickBk_Status
                })

            return jsonify({
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "message": "Payments found",
                "status": 200,
                "data": {
                    "payer_code": payer_code,
                    "payment_status": "FOUND",
                    "payment_count": len(payments),
                    "payments": payment_data
                }
            }), 200

        finally:
            session.close()

    except Exception as e:
        current_app.logger.error(f"Error checking payment status by reference: {str(e)}")
        current_app.logger.error(traceback.format_exc())
        return jsonify({
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "message": "Internal server error",
            "status": 500
        }), 500

@urubuto_bp.route('/test-auth', methods=['POST'])
@require_auth()
def test_auth():
    """Test authentication endpoint for debugging token issues."""
    current_app.logger.info("++ === TEST AUTH ENDPOINT REACHED ===")
    current_app.logger.info("==YES==Authentication successful - endpoint reached")

    return jsonify({
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "message": "Authentication test successful",
        "status": 200,
        "data": {
            "client_name": request.token_payload.get('client_name'),
            "gateway_name": request.token_payload.get('gateway_name'),
            "permissions": request.token_payload.get('permissions'),
            "client_id": request.token_payload.get('client_id')
        }
    }), 200

@urubuto_bp.route('/get_student_invoices', methods=['POST'])
#@require_auth('payer_validation')
#@require_gateway('urubuto_pay')
#@log_api_access('get_student_invoices')
def get_student_invoices():
    """
    Retrieve all unpaid invoices for a student by their registration number.

    This endpoint allows fetching all unpaid invoices for a student,
    providing details such as invoice ID, amount due, fee category,
    level, and due date.

    Expected request format:
    {
        "reg_no": "2022011019"
    }
    """
    
    # Validate request data
    if not request.is_json:
        return jsonify({
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "message": "Content-Type must be application/json",
            "status": 400
        }), 400

    data = request.get_json()
    if not data:
        return jsonify({
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "message": "No data provided",
            "status": 400
        }), 400

    reg_no = data.get('reg_no')
    if not reg_no:
        return jsonify({
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "message": "reg_no is required",
            "status": 400
        }), 400

    current_app.logger.info(f"Fetching unpaid invoices for student: {reg_no}")

    with db_manager.get_mis_session() as session:
        # Fetch all invoices associated with the given registration number
        try:
            invoices = TblImvoice.get_all_invoices_associated_with_student(reg_no)
            current_app.logger.info(f"Found {len(invoices)} invoices for student {reg_no}")
            invoice_data = []
            invoice_num = len(invoices)
            for invoice in invoices:
                invoice_data.append({
                    "invoice_date": invoice.get('date'),
                    "invoice_id": str(invoice.get('id')),
                    "reference_number": invoice.get('reference_number', ''),
                    "amount": invoice.get('dept'),
                    "category": invoice.get('category'),
                    "description": invoice.get('description'),
                    "balance": invoice.get('balance'),
                })
            
            return jsonify({
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "message": f"Found {invoice_num} invoices for student {reg_no}",
                "status": 200,
                "data": {
                    "reg_no": reg_no,
                    "invoice_count": invoice_num,
                    "invoices": invoice_data
                }
            }), 200

        except Exception as e:
            current_app.logger.error(f"Error fetching invoices for student {reg_no}: {str(e)}")
            current_app.logger.error(traceback.format_exc())
            return jsonify({
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "message": "Error fetching invoices",
                "status": 400
            }), 400
        

@urubuto_bp.route('/payments/refund', methods=['POST'])
#@require_auth('refunds')
@require_gateway('urubuto_pay')
@log_api_access('process_refund')
def process_refund():
    """
    Process a refund for a specific transaction.

    This endpoint allows processing refunds for payments made via Urubuto Pay.
    It requires the original transaction ID and the amount to be refunded.

    Expected request format:
    {
        "transaction_id": "11202202011152166608",
        "amount": 50.0,
        "reason": "Overpayment"
    }
    """
    current_app.logger.info("REFUND PROCESSING ENDPOINT CALLED ===")
    current_app.logger.info(f"Request method: {request.method}")
    current_app.logger.info(f"Request endpoint: {request.endpoint}")
    current_app.logger.info(f"Request remote addr: {request.remote_addr}")
    current_app.logger.info(f"Request content type: {request.content_type}")
    current_app.logger.info(f"Token payload available: {hasattr(request, 'token_payload')}")
    current_app.logger.info(f"data received: {request.get_json()}")
    try:
        # Validate request data
        if not request.is_json:
            return jsonify({
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "message": "Content-Type must be application/json",
                "status": 400
            }), 400

        data = request.get_json()
        if not data:
            return jsonify({
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "message": "No data provided",
                "status": 400
            }), 400

        transaction_id = data.get('transaction_id')
        amount = data.get('amount')
        reason = data.get('reason', 'No reason provided')

        if not transaction_id or not amount:
            return jsonify({
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "message": "Missing required parameters: transaction_id, amount",
                "status": 400
            }), 400

        current_app.logger.info(f"Refund request - Transaction: {transaction_id}, Amount: {amount}, Reason: {reason}")

        # Process refund via Urubuto Pay service
        try:
            result = urubuto_service.process_refund(
                transaction_id=transaction_id,
                amount=amount,
                reason=reason
            )
            current_app.logger.info(f"Refund processing result checking: {result}")

            if result['success']:
                current_app.logger.info(f"Refund processed successfully for transaction: {transaction_id}")
                return jsonify(result['data']), result['status_code']
            else:
                current_app.logger.error(f"Refund processing failed: {result['error']}")
                return jsonify({
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "message": result['error'],
                    "status": result['status_code']
                }), result['status_code']
        except Exception as e:
            current_app.logger.error(f"Error in refund processing: {str(e)}")
            current_app.logger.error(traceback.format_exc())
            message = f"Refund processing error: {str(e)} and traceback: {traceback.format_exc()}"
            return jsonify({
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "message": message,
                "status": 405
            }), 405
    except Exception as e:
        current_app.logger.error(f"Error in refund processing: {str(e)}")
        current_app.logger.error(traceback.format_exc())
        message = f"Refund processing error: {str(e)} and traceback: {traceback.format_exc()}"
        return jsonify({
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "message": message,
            "status": 500
        }), 500 