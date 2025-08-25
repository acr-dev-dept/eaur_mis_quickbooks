"""
MIS Data API endpoints for data enrichment and lookup
These endpoints will be implemented after database models are generated
"""

from flask import Blueprint, jsonify, current_app
from application.models.mis_models import TblBank

mis_data_bp = Blueprint('mis_data', __name__)

@mis_data_bp.route('/campus/<int:campus_id>', methods=['GET'])
def get_campus(campus_id):
    """Get campus details by ID"""
    # TODO: Implement after models are generated
    return jsonify({
        'message': 'Endpoint will be implemented after database models are generated',
        'campus_id': campus_id
    }), 501

@mis_data_bp.route('/intake/<int:intake_id>', methods=['GET'])
def get_intake(intake_id):
    """Get intake details by ID"""
    # TODO: Implement after models are generated
    return jsonify({
        'message': 'Endpoint will be implemented after database models are generated',
        'intake_id': intake_id
    }), 501

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
        if bank:
            return jsonify({
                'bank_id': bank.bank_id,
                'bank_name': bank.bank_name,
                'bank_code': bank.bank_code,
                'branch_name': bank.bank_branch,
                'currency': bank.currency,
                'account_number': bank.account_no,
                'status': bank.status

            }), 200
        else:
            return jsonify({'message': 'Bank not found'}), 404
    except Exception as e:
        current_app.logger.error(f"Error fetching bank details: {e}")
        return jsonify({'message': 'Internal server error'}), 500
   

@mis_data_bp.route('/register_program/<int:program_id>', methods=['GET'])
def get_register_program(program_id):
    """Get program details by ID"""
    # TODO: Implement after models are generated
    return jsonify({
        'message': 'Endpoint will be implemented after database models are generated',
        'program_id': program_id
    }), 501

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
