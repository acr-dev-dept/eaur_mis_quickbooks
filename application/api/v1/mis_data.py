"""
MIS Data API endpoints for data enrichment and lookup
These endpoints will be implemented after database models are generated
"""

from flask import Blueprint, jsonify, current_app
from application.models.mis_models import (
    TblBank, TblCampus,TblRegisterProgramUg,
    TblIntake, TblSpecialization, TblProgramMode,
    TblSponsor, TblLevel, Modules, TblIncomeCategory, 
    TblPersonalUg, Payment, TblImvoice
)


mis_data_bp = Blueprint('mis_data', __name__)

@mis_data_bp.route('/campus/<int:campus_id>', methods=['GET'])
def get_campus(campus_id):
    """Get campus details by ID"""
    try:
        campus = TblCampus.get_by_id(campus_id)
        current_app.logger.debug(f"Fetched campus details: {campus}")
        if campus:
            # check if it is a dictionary
            if isinstance(campus, dict):
                return jsonify({'campus_details': campus}), 200
            else:
                # call the to_dict method if it's a model instance
                return jsonify({'campus_details': campus.to_dict()}), 200
        else:
            return jsonify({'message': 'Campus not found'}), 404
    except Exception as e:
        current_app.logger.error(f"Error fetching campus details: {e}")
        return jsonify({'message': 'Internal server error'}), 500

@mis_data_bp.route('/intake/<int:intake_id>', methods=['GET'])
def get_intake(intake_id):
    """Get intake details by ID"""
    try:
        intake = TblIntake.get_by_id(intake_id)
        current_app.logger.debug(f"Fetched intake details: {intake}")
        if intake:
            # check if it is a dictionary
            if isinstance(intake, dict):
                return jsonify({'intake_details': intake}), 200
            else:
                # call the to_dict method if it's a model instance
                return jsonify({'intake_details': intake.to_dict()}), 200
        else:
            return jsonify({'message': 'Intake not found'}), 404
    except Exception as e:
        current_app.logger.error(f"Error fetching intake details: {e}")
        return jsonify({'message': 'Internal server error'}), 500

@mis_data_bp.route('/specialisation/<int:specialisation_id>', methods=['GET'])
def get_specialisation(specialisation_id):
    """Get specialisation details by ID"""
    try:
        specialisation = TblSpecialization.get_by_id(specialisation_id)
        current_app.logger.debug(f"Fetched specialisation details: {specialisation}")
        if specialisation:
            # check if it is a dictionary
            if isinstance(specialisation, dict):
                return jsonify({'specialisation_details': specialisation}), 200
            else:
                # call the to_dict method if it's a model instance
                return jsonify({'specialisation_details': specialisation.to_dict()}), 200
        else:
            return jsonify({'message': 'Specialisation not found'}), 404
    except Exception as e:
        current_app.logger.error(f"Error fetching specialisation details: {e}")
        return jsonify({'message': 'Internal server error'}), 500

@mis_data_bp.route('/program_mode/<int:mode_id>', methods=['GET'])
def get_program_mode(mode_id):
    """Get program mode details by ID"""
    try:
        program_mode = TblProgramMode.get_by_id(mode_id)
        current_app.logger.debug(f"Fetched program mode details: {program_mode}")
        if program_mode:
            # check if it is a dictionary
            if isinstance(program_mode, dict):
                return jsonify({'program_mode_details': program_mode}), 200
            else:
                # call the to_dict method if it's a model instance
                return jsonify({'program_mode_details': program_mode.to_dict()}), 200
        else:
            return jsonify({'message': 'Program mode not found'}), 404
    except Exception as e:
        current_app.logger.error(f"Error fetching program mode details: {e}")
        return jsonify({'message': 'Internal server error'}), 500

@mis_data_bp.route('/bank/<int:bank_id>', methods=['GET'])
def get_bank(bank_id):
    """Get bank details by ID"""
    try:
        bank = TblBank.get_bank_details(bank_id)
        current_app.logger.debug(f"Fetched bank details: {bank}")
        if bank:
            # since the bank object is a dictionary, we can directly return it
            return jsonify({'bank_details': bank}), 200
        else:
            return jsonify({'message': 'Bank not found'}), 404
    except Exception as e:
        current_app.logger.error(f"Error fetching bank details: {e}")
        return jsonify({'message': 'Internal server error'}), 500
   

@mis_data_bp.route('/register_program/<int:program_id>', methods=['GET'])
def get_register_program(program_id):
    """Get program details by ID"""
    try:
        program = TblRegisterProgramUg.get_by_id(program_id)
        current_app.logger.debug(f"Fetched program details: {program}")
        if program:
            # check if it is a dictionary
            if isinstance(program, dict):
                return jsonify({'program_details': program}), 200
            else:
                # call the to_dict method if it's a model instance
                return jsonify({'program_details': program.to_dict()}), 200
        else:
            return jsonify({'message': 'Program not found'}), 404
    except Exception as e:
        current_app.logger.error(f"Error fetching program details: {e}")
        return jsonify({'message': 'Internal server error'}), 500

@mis_data_bp.route('/sponsor/<int:sponsor_id>', methods=['GET'])
def get_sponsor(sponsor_id):
    """Get sponsor details by ID"""
    try:
        sponsor = TblSponsor.get_by_id(sponsor_id)
        current_app.logger.debug(f"Fetched sponsor details: {sponsor}")
        if sponsor:
            # check if it is a dictionary
            if isinstance(sponsor, dict):
                return jsonify({'sponsor_details': sponsor}), 200
            else:
                # call the to_dict method if it's a model instance
                return jsonify({'sponsor_details': sponsor.to_dict()}), 200
        else:
            return jsonify({'message': 'Sponsor not found'}), 404
    except Exception as e:
        current_app.logger.error(f"Error fetching sponsor details: {e}")
        return jsonify({'message': 'Internal server error'}), 500

@mis_data_bp.route('/level/<int:level_id>', methods=['GET'])
def get_level(level_id):
    """Get level details by ID"""
    try:
        level = TblLevel.get_by_id(level_id)
        current_app.logger.debug(f"Fetched level details: {level}")
        if level:
            # check if it is a dictionary
            if isinstance(level, dict):
                return jsonify({'level_details': level}), 200
            else:
                # call the to_dict method if it's a model instance
                return jsonify({'level_details': level.to_dict()}), 200
        else:
            return jsonify({'message': 'Level not found'}), 404
    except Exception as e:
        current_app.logger.error(f"Error fetching level details: {e}")
        return jsonify({'message': 'Internal server error'}), 500

@mis_data_bp.route('/module/<int:module_id>', methods=['GET'])
def get_module(module_id):
    """Get module details by ID"""
    try:
        module = Modules.get_by_id(module_id)
        current_app.logger.debug(f"Fetched module details: {module}")
        if module:
            # check if it is a dictionary
            if isinstance(module, dict):
                return jsonify({'module_details': module}), 200
            else:
                # call the to_dict method if it's a model instance
                return jsonify({'module_details': module.to_dict()}), 200
        else:
            return jsonify({'message': 'Module not found'}), 404
    except Exception as e:
        current_app.logger.error(f"Error fetching module details: {e}")
        return jsonify({'message': 'Internal server error'}), 500

@mis_data_bp.route('/income_category/<int:category_id>', methods=['GET'])
def get_income_category(category_id):
    """Get income category details by ID"""
    try:
        category = TblIncomeCategory.get_by_id(category_id)
        current_app.logger.debug(f"Fetched income category details: {category}")
        if category:
            # check if it is a dictionary
            if isinstance(category, dict):
                return jsonify({'income_category_details': category}), 200
            else:
                # call the to_dict method if it's a model instance
                return jsonify({'income_category_details': category.to_dict()}), 200
        else:
            return jsonify({'message': 'Income category not found'}), 404
    except Exception as e:
        current_app.logger.error(f"Error fetching income category details: {e}")
        return jsonify({'message': 'Internal server error'}), 500

@mis_data_bp.route('/student_details/<int:student_id>', methods=['GET'])
def get_student(student_id):
    """Get student details by ID"""
    try:
        student = TblPersonalUg.get_by_id(student_id)
        current_app.logger.debug(f"Fetched student details: {student}")
        if student:
            # check if it is a dictionary
            if isinstance(student, dict):
                return jsonify({'student_details': student}), 200
            else:
                # call the to_dict method if it's a model instance
                return jsonify({'student_details': student.to_dict()}), 200
        else:
            return jsonify({'message': 'Student not found'}), 404
    except Exception as e:
        current_app.logger.error(f"Error fetching student details: {e}")
        return jsonify({'message': 'Internal server error'}), 500

@mis_data_bp.route('/get_student_by_regno', methods=['GET'])
def get_student_by_regno():
    """Get student details by registration number"""
    # get reg_no from query parameters
    from flask import request
    reg_no = request.args.get('reg_no')
    if not reg_no:
        return jsonify({'message': 'reg_no query parameter is required'}), 400
    try:
        student = TblPersonalUg.get_student_details(reg_no)
        current_app.logger.debug(f"Fetched student details by reg no: {student}")
        if student:
            # check if it is a dictionary
            if isinstance(student, dict):
                return jsonify({'student_details': student}), 200
            else:
                # call the to_dict method if it's a model instance
                return jsonify({'student_details': student.to_dict()}), 200
        else:
            return jsonify({'message': 'Student not found'}), 404
    except Exception as e:
        current_app.logger.error(f"Error fetching student details by reg no: {e}")
        return jsonify({'message': 'Internal server error'}), 500

@mis_data_bp.route('/payment/<int:payment_id>', methods=['GET'])
def get_payment(payment_id):
    """Get payment details by ID"""
    try:
        payment = Payment.get_by_id(payment_id)
        current_app.logger.debug(f"Fetched payment details: {payment}")
        if payment:
            # check if it is a dictionary
            if isinstance(payment, dict):
                return jsonify({'payment_details': payment}), 200
            else:
                # call the to_dict method if it's a model instance
                return jsonify({'payment_details': payment.to_dict()}), 200
        else:
            return jsonify({'message': 'Payment not found'}), 404
    except Exception as e:
        current_app.logger.error(f"Error fetching payment details: {e}")
        return jsonify({'message': 'Internal server error'}), 500

@mis_data_bp.route('/invoice/<int:invoice_id>', methods=['GET'])
def get_invoice(invoice_id):
    """Get invoice details by ID"""
    try:
        invoice = TblImvoice.get_by_id(invoice_id)
        current_app.logger.debug(f"Fetched invoice details: {invoice}")
        if invoice:
            # check if it is a dictionary
            if isinstance(invoice, dict):
                return jsonify({'invoice_details': invoice}), 200
            else:
                # call the to_dict method if it's a model instance
                return jsonify({'invoice_details': invoice.to_dict()}), 200
        else:
            return jsonify({'message': 'Invoice not found'}), 404
    except Exception as e:
        current_app.logger.error(f"Error fetching invoice details: {e}")
        return jsonify({'message': 'Internal server error'}), 500