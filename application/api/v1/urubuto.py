from flask import Blueprint, request, jsonify, current_app
from datetime import datetime
from application.models.mis_models import TblImvoice, TblPersonalUg, TblOnlineApplication
from application.utils.database import db_manager
from sqlalchemy.orm import joinedload
import traceback

urubuto_bp = Blueprint('urubuto', __name__)

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
    """Handle payment notifications from Urubuto"""
    data = request.json
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    # Log the received notification for debugging
    current_app.logger.info(f"Received payment notification: {data}")

    # Process the notification (this is a placeholder)
