from flask import Blueprint, request, jsonify, current_app
from datetime import datetime, timedelta
from application.models.mis_models import TblImvoice, TblPersonalUg, TblOnlineApplication
from application.utils.database import db_manager
from sqlalchemy.orm import joinedload
import traceback
import jwt
import os

urubuto_bp = Blueprint('urubuto', __name__)

def validate_bearer_token():
    """
    Helper function to validate Bearer token from Authorization header.

    Returns:
        tuple: (is_valid: bool, error_response: dict or None)
    """
    try:
        auth_header = request.headers.get('Authorization')
        if not auth_header:
            return False, {
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "message": "Missing Authorization header",
                "status": 401
            }

        if not auth_header.startswith('Bearer '):
            return False, {
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "message": "Invalid Authorization header format. Expected: Bearer <token>",
                "status": 401
            }

        token = auth_header.split(' ')[1]
        secret_key = os.getenv('SECRET_KEY', 'your-secret-key-here')

        # Decode and validate JWT token
        payload = jwt.decode(token, secret_key, algorithms=['HS256'])
        current_app.logger.info(f"Valid token for user: {payload.get('username')}")
        return True, None

    except jwt.ExpiredSignatureError:
        return False, {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "message": "Token has expired",
            "status": 401
        }
    except jwt.InvalidTokenError:
        return False, {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "message": "Invalid token",
            "status": 401
        }
    except Exception as e:
        current_app.logger.error(f"Token validation error: {str(e)}")
        return False, {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "message": "Token validation failed",
            "status": 401
        }

@urubuto_bp.route('/authentication', methods=['POST'])
def authentication():
    """
    Authentication endpoint for Urubuto Pay integration.

    This endpoint provides Bearer tokens for Urubuto Pay to access protected APIs.
    Tokens are valid for 24 hours as per Urubuto Pay specification.

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

        # Get credentials from environment variables
        expected_username = os.getenv('URUBUTO_PAY_USERNAME', 'bkTechPymtGtwy')
        expected_password = os.getenv('URUBUTO_PAY_PASSWORD', 'myPss@2020')

        # Validate credentials
        if username != expected_username or password != expected_password:
            current_app.logger.warning(f"Invalid authentication attempt for user: {username}")
            return jsonify({
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "message": "Invalid credentials",
                "status": 401
            }), 401

        # Generate JWT token valid for 24 hours
        secret_key = os.getenv('SECRET_KEY', 'your-secret-key-here')
        payload = {
            'username': username,
            'exp': datetime.utcnow() + timedelta(hours=24),
            'iat': datetime.utcnow(),
            'iss': 'EAUR-MIS-QuickBooks'
        }

        token = jwt.encode(payload, secret_key, algorithm='HS256')
        bearer_token = f"Bearer {token}"

        current_app.logger.info(f"Authentication successful for user: {username}")

        return jsonify({
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "message": "Successful",
            "status": 200,
            "data": {
                "token": bearer_token
            }
        }), 200

    except Exception as e:
        current_app.logger.error(f"Error in authentication: {str(e)}")
        current_app.logger.error(traceback.format_exc())
        return jsonify({
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "message": "Internal server error",
            "status": 500
        }), 500

@urubuto_bp.route('/validation', methods=['POST'])
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
        merchant_code = data.get('merchant_code')
        payer_code = data.get('payer_code')

        if not merchant_code or not payer_code:
            return jsonify({
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "message": "Missing required parameters: merchant_code and payer_code",
                "status": 400
            }), 400

        current_app.logger.info(f"Payer validation request - Merchant: {merchant_code}, Payer: {payer_code}")

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

@urubuto_bp.route('/payments/notification', methods=['POST'])
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
    try:
        # Validate Bearer token
        is_valid, error_response = validate_bearer_token()
        if not is_valid:
            return jsonify(error_response), 401

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
        status = data.get('status')
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
        required_fields = ['status', 'transaction_status', 'transaction_id', 'merchant_code',
                          'payer_code', 'payment_channel', 'amount', 'currency', 'payment_date_time']

        missing_fields = [field for field in required_fields if not data.get(field)]
        if missing_fields:
            return jsonify({
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "message": f"Missing required parameters: {', '.join(missing_fields)}",
                "status": 400
            }), 400

        current_app.logger.info(f"Payment notification received - Transaction: {transaction_id}, "
                               f"Payer: {payer_code}, Status: {transaction_status}, Amount: {amount}")

        # Only process successful payments
        if transaction_status not in ['VALID', 'PENDING']:
            current_app.logger.info(f"Ignoring payment with status: {transaction_status}")
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
