from flask import Blueprint, request, jsonify, current_app
from datetime import datetime, timedelta
from application.models.mis_models import TblImvoice, TblPersonalUg, TblOnlineApplication, Payment
from application.utils.database import db_manager
from application.utils.auth_decorators import require_auth, require_gateway, log_api_access
from sqlalchemy.orm import joinedload
import traceback
import jwt
import os

urubuto_bp = Blueprint('urubuto', __name__)
# Initialize Urubuto Pay service
from application.services.urubuto_pay import UrubutoPay
urubuto_service = UrubutoPay()



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
            current_app.logger.warning(f"Authentication failed for user {username}: {token_or_error}")
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
@require_gateway('urubuto_pay')
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

        # get invoice details given the reference number (payer_code)
        try:            
            invoice_balance = TblImvoice.get_invoice_balance(payer_code)
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
            #make sure it doesn't have decimal places
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

        
        # We are going to stop here and respond with successful response
        return jsonify({
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "message": "Successful",
            "status": 200,
            "data": {
                "merchant_code": merchant_code,
                "payer_code": payer_code,
                "payer_names": "Unknown Student",
                "department_code": "0",
                "department_name": "Unknown Department",
                "class_name": "Unknown Class",
                "amount": invoice_balance,
                "currency": "RWF",
                "payer_must_pay_total_amount": "NO",
                "payer_names": "Unknown Student"
            }
        }), 200

        # Query invoice by reference number (assuming payer_code is invoice ID for now)
        # This will be updated when reference_number field is added to invoice table
        session = db_manager.get_mis_session()
        try:
            invoice = session.query(TblImvoice).options(
                joinedload(TblImvoice.level),
                joinedload(TblImvoice.fee_category_rel),
                joinedload(TblImvoice.module),
                joinedload(TblImvoice.intake)
            ).filter(TblImvoice.id == payer_code).first()

            if not invoice:
                current_app.logger.warning(f"No invoice found for payer_code: {payer_code}")
                return jsonify({
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "message": f"No data found for this code: {payer_code}",
                    "status": 404
                }), 404

            # Get student information
            student_name = "Unknown Student"
            department_name = "Unknown Department"
            class_name = "Unknown Class"

            if invoice.reg_no:
                # Try to get student details from personal table
                student = session.query(TblPersonalUg).filter(
                    TblPersonalUg.reg_no == invoice.reg_no
                ).first()

                if student:
                    student_name = f"{student.first_name or ''} {student.last_name or ''}".strip()
                    if not student_name:
                        student_name = student.reg_no

            # Get department and class information from relationships
            if invoice.level:
                class_name = invoice.level.level_full_name or "Unknown Class"

            # Calculate amount (convert balance to float)
            try:
                amount = float(invoice.balance) if invoice.balance else 0.0
            except (ValueError, TypeError):
                amount = 0.0

            # Get fee category information
            service_name = "School Fees"
            service_code = "school-fees"
            if invoice.fee_category_rel:
                service_name = invoice.fee_category_rel.income_category_name or "School Fees"
                service_code = invoice.fee_category_rel.income_category_name.lower().replace(' ', '-') if invoice.fee_category_rel.income_category_name else "school-fees"

            # Build response according to Urubuto Pay API specification
            response_data = {
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "message": "Successful",
                "status": 200,
                "data": {
                    "merchant_code": merchant_code,
                    "payer_code": payer_code,
                    "payer_names": student_name,
                    "department_code": str(invoice.level_id) if invoice.level_id else "0",
                    "department_name": department_name,
                    "class_name": class_name,
                    "service_group_code": str(invoice.fee_category) if invoice.fee_category else "0",
                    "service_group_name": service_name,
                    "amount": amount,
                    "currency": "RWF",
                    "payer_must_pay_total_amount": "YES",
                    "comment": invoice.comment or "Student fee payment",
                    "services": [
                        {
                            "service_id": 1,
                            "service_code": service_code,
                            "service_name": service_name,
                            "account_number": "000500025695727",  # This should be configured
                            "amount": amount
                        }
                    ]
                }
            }

            current_app.logger.info(f"Payer validation successful for {payer_code}: {student_name}, Amount: {amount}")
            return jsonify(response_data), 200

        finally:
            session.close()

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
@require_gateway('urubuto_pay')
def payment_callback():
    """
    Payment callback endpoint for Urubuto Pay integration.

    This endpoint receives payment callbacks from Urubuto Pay and updates
    payment records in the MIS payments table.
    """
    current_app.logger.info("PAYMENT CALLBACK ENDPOINT CALLED ===")
    current_app.logger.info(f"Request method: {request.method}")
    current_app.logger.info(f"Request endpoint: {request.endpoint}")
    current_app.logger.info(f"Request remote addr: {request.remote_addr}")
    current_app.logger.info(f"Request content type: {request.content_type}")
    current_app.logger.info(f"Token payload available: {hasattr(request, 'token_payload')}")
    current_app.logger.info(f"data received: {request.get_json()}")

    # Process the callback data
    data = request.get_json()
    current_app.logger.info(f"Callback data: {data}")
    if not data:
        message = f"No data found for this code: {data.get('payer_code')}"
        return jsonify({
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "message": message,
            "status": 404
        }), 404

    # Fetch some data from the callback for logging
    transaction_id = data.get('transaction_id')
    status = data.get('status')
    transaction_status = data.get('transaction_status')
    amount = data.get('amount')
    payment_date_time = data.get('payment_date_time')
    payer_code = data.get('payer_code')
    # Generate a random internal transaction in form of 625843
    internal_transaction_id = str(datetime.now().timestamp()).replace('.', '')[:20]

    # Check if the transaction_id is not in the payment table so that we do not duplicate payments
    try:
        existing_payment = Payment.get_payment_details_by_external_id(transaction_id)
        current_app.logger.info(f"Existing payment check for transaction {transaction_id}: {existing_payment}")
        if existing_payment:
            message = f"Payment already exists for transaction: {transaction_id}"
            return jsonify({
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "message": "Successful",
                "status": 200,
                "data": {
                    "external_transaction_id": transaction_id,
                    "internal_transaction_id": str(existing_payment.id)
                }
            }), 200
    except Exception as e:
        current_app.logger.error(f"Error checking existing payment for transaction {transaction_id}: {str(e)}")
        current_app.logger.error(traceback.format_exc())

    # check the transaction status so that we know how to update the balance in invoice
    # table and the payment table
    if transaction_status == "VALID":
        # Update invoice balance
        try:
            updated = TblImvoice.update_invoice_balance(payer_code, amount)
            current_app.logger.info(f"Invoice {payer_code} balance updated: {updated}")
            # Make sure the invoice balance has been updated before creating payment record
            if updated[0] is not None: # The method returns (new_balance, invoice) tuple
                # Create payment record
                try:
                    payment = Payment.create_payment(
                        external_transaction_id=transaction_id,
                        trans_code=transaction_id,
                        description=f"Urubuto Pay Via Microservice",
                        payment_chanel=data.get('payment_channel_name'),
                        invoi_ref=payer_code,
                        amount=amount,
                        level_id=updated[1].level_id if updated[1] else None,
                        fee_category=updated[1].fee_category if updated[1] else None,
                        reg_no=updated[1].reg_no if updated[1] else None,
                        appl_Id=updated[1].appl_Id if updated[1] else None,
                        user="URUBUTOPAY",
                        bank_id=2
                    )
                    current_app.logger.info(f"Payment record created: {payment}")
                except Exception as e:
                    current_app.logger.error(f"Error creating payment record for transaction {transaction_id}: {str(e)}")
                    current_app.logger.error(traceback.format_exc())
        except Exception as e:
            current_app.logger.error(f"Error updating invoice balance for {payer_code}: {str(e)}")
            current_app.logger.error(traceback.format_exc())
    elif transaction_status == "PENDING_SETTLEMENT":  # tHIS SHOWS THAT THE STUDENT HAS PAID, ONLY THAT THE BANK HAS NOT CREDITED THE MERCHANT
        current_app.logger.warning(f"Transaction {transaction_id} for {payer_code} is pending.")
        # WE update the balance because the student has paid, only that the bank has not credited the merchant
        try:
            updated = TblImvoice.update_invoice_balance(payer_code, amount)
            current_app.logger.info(f"Invoice {payer_code} balance updated: {updated}")
            # Make sure the invoice balance has been updated before creating payment record
            if updated[0] is not None: # The method returns (new_balance, invoice) tuple
                # Create payment record
                try:
                    payment = Payment.create_payment(
                        external_transaction_id=transaction_id,
                    description=f"Urubuto Pay Via Microservice",
                    trans_code=transaction_id,
                    payment_chanel=data.get('payment_channel_name'),
                    invoi_ref=payer_code,
                    level_id=updated[1].level_id if updated[1] else None,
                    amount=amount,
                    fee_category=updated[1].fee_category if updated[1] else None,
                    reg_no=updated[1].reg_no if updated[1] else None,
                    appl_Id=updated[1].appl_Id if updated[1] else None,
                    user="URUBUTOPAY",
                    bank_id=2
                    )
                    current_app.logger.info(f"Payment record created: {payment}")
                except Exception as e:
                    current_app.logger.error(f"Error creating payment record for transaction {transaction_id}: {str(e)}")
                    current_app.logger.error(traceback.format_exc())
        except Exception as e:
            current_app.logger.error(f"Error updating invoice balance for {payer_code}: {str(e)}")
            current_app.logger.error(traceback.format_exc())
    else:
        current_app.logger.warning(f"Transaction {transaction_id} for {payer_code} has status: {transaction_status}. No balance update performed.")
        # Log the transaction status
        current_app.logger.info(f"Transaction {transaction_id} for {payer_code} has status: {transaction_status}. No balance update performed.")


    return jsonify(
        {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "message": "Successful",
            "data": {
                "external_transaction_id": transaction_id,
                "internal_transaction_id": internal_transaction_id
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
        "payment_channel": "WALLET",
        "payment_channel_name": "MOMO",
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
        payment_channel = data.get('payment_channel')
        payment_channel_name = data.get('payment_channel_name')
        amount = data.get('amount')
        currency = data.get('currency')
        payment_date_time = data.get('payment_date_time')
        slip_number = data.get('slip_number', '')

        # Validate required fields
        required_fields = ['transaction_id', 'merchant_code',
                          'payer_code', 'payment_channel', 'amount', 'currency', 'payment_date_time']

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
                status = urubuto_service.check_transaction_status(transaction_id)
                current_app.logger.info(f"Transaction status check result: {status}")
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

        # Get database session
        session = db_manager.get_mis_session()
        try:
            # Find the invoice by payer_code (reference number)
            invoice = session.query(TblImvoice).filter(TblImvoice.id == payer_code).first()

            if not invoice:
                current_app.logger.error(f"No invoice found for payer_code: {payer_code}")
                return jsonify({
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "message": f"No data found for this code: {payer_code}",
                    "status": 404
                }), 404

            # Check if payment already exists
            from application.models.mis_models import Payment
            existing_payment = session.query(Payment).filter(
                Payment.external_transaction_id == transaction_id
            ).first()

            if existing_payment:
                current_app.logger.warning(f"Payment already exists for transaction: {transaction_id}")
                return jsonify({
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "message": "Payment already processed",
                    "status": 200,
                    "data": {
                        "external_transaction_id": transaction_id,
                        "internal_transaction_id": str(existing_payment.id),
                        "payer_phone_number": "",
                        "payer_email": ""
                    }
                }), 200

            # Create new payment record
            from application.models.mis_models import Payment
            new_payment = Payment(
                trans_code=f"URUBUTO_{transaction_id[:10]}",
                reg_no=invoice.reg_no,
                level_id=invoice.level_id,
                bank_id=1,  # Default bank ID - should be configured
                slip_no=slip_number or transaction_id,
                user="URUBUTO_PAY",
                acad_cycle_id="2024",  # Should be dynamic
                date=payment_date_time.split(' ')[0] if payment_date_time else datetime.now().strftime("%Y-%m-%d"),
                fee_category=invoice.fee_category,
                amount=float(amount),
                description=f"Payment via Urubuto Pay - {payment_channel_name}",
                recorded_date=datetime.now(),
                Remark=f"Urubuto Pay transaction: {transaction_id}",
                action="PAYMENT",
                external_transaction_id=transaction_id,
                payment_chanel="URUBUTO_PAY",
                payment_notifi="RECEIVED",
                invoi_ref=str(invoice.id),
                QuickBk_Status=0,  # Will be synced to QuickBooks later
                pushed_by="URUBUTO_PAY_WEBHOOK",
                pushed_date=datetime.now()
            )

            session.add(new_payment)
            session.commit()

            # Update invoice balance if needed
            try:
                current_balance = float(invoice.balance) if invoice.balance else 0.0
                new_balance = max(0, current_balance - float(amount))
                invoice.balance = str(new_balance)
                session.commit()
                current_app.logger.info(f"Updated invoice {invoice.id} balance from {current_balance} to {new_balance}")
            except (ValueError, TypeError) as e:
                current_app.logger.warning(f"Could not update invoice balance: {e}")

            current_app.logger.info(f"Payment created successfully - ID: {new_payment.id}, "
                                   f"Amount: {amount}, Transaction: {transaction_id}")

            # Return success response
            return jsonify({
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "message": "Successful",
                "status": 200,
                "data": {
                    "external_transaction_id": transaction_id,
                    "internal_transaction_id": str(new_payment.id),
                    "payer_phone_number": "",  # Could be extracted from payment data if available
                    "payer_email": ""  # Could be extracted from student data if available
                }
            }), 200

        finally:
            session.close()

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

        # Initiate payment
        try:
            result = urubuto_service.initiate_payment(
                payer_code=payer_code,
                amount=amount,
                channel_name=channel_name,
                phone_number=data.get('phone_number'),
                card_type=data.get('card_type'),
                redirection_url=data.get('redirection_url'),
                payer_names=data.get('payer_names'),
                payer_email=data.get('payer_email'),
                service_code=service_code
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
                    "payment_channel": payment.payment_chanel,
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
    current_app.logger.info("🧪 === TEST AUTH ENDPOINT REACHED ===")
    current_app.logger.info("✅ Authentication successful - endpoint reached")

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