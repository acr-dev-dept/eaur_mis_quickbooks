"""
MIS Data API endpoints for data enrichment and lookup
These endpoints will be implemented after database models are generated
"""

from flask import Blueprint, jsonify, current_app
from application.models.mis_models import TblBank, TblCampus, TblRegisterProgramUg, TblIntake

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
    # TODO: Implement after models are generated
    return jsonify({
        'message': 'Endpoint will be implemented after database models are generated',
        'specialisation_id': specialisation_id
    }), 501

@mis_data_bp.route('/program_mode/<int:mode_id>', methods=['GET'])
def get_program_mode(mode_id):
    """Get program mode details by ID"""
    # TODO: Implement after models are generated
    return jsonify({
        'message': 'Endpoint will be implemented after database models are generated',
        'mode_id': mode_id
    }), 501

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
    # TODO: Implement after models are generated
    return jsonify({
        'message': 'Endpoint will be implemented after database models are generated',
        'sponsor_id': sponsor_id
    }), 501

@mis_data_bp.route('/level/<int:level_id>', methods=['GET'])
def get_level(level_id):
    """Get level details by ID"""
    # TODO: Implement after models are generated
    return jsonify({
        'message': 'Endpoint will be implemented after database models are generated',
        'level_id': level_id
    }), 501

@mis_data_bp.route('/module/<int:module_id>', methods=['GET'])
def get_module(module_id):
    """Get module details by ID"""
    # TODO: Implement after models are generated
    return jsonify({
        'message': 'Endpoint will be implemented after database models are generated',
        'module_id': module_id
    }), 501

@mis_data_bp.route('/income_category/<int:category_id>', methods=['GET'])
def get_income_category(category_id):
    """Get income category details by ID"""
    # TODO: Implement after models are generated
    return jsonify({
        'message': 'Endpoint will be implemented after database models are generated',
        'category_id': category_id
    }), 501

@mis_data_bp.route('/personal_ug/<int:student_id>', methods=['GET'])
def get_student(student_id):
    """Get student details by ID"""
    # TODO: Implement after models are generated
    return jsonify({
        'message': 'Endpoint will be implemented after database models are generated',
        'student_id': student_id
    }), 501
