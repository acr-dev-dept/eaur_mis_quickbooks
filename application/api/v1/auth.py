from flask import Blueprint, request, jsonify, current_app

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/authenticate', methods=['POST'])
def authenticate():
    """

    Login endpoint that authenticates a user and returns a token if successful.

    request body should contain:
        "username": "username",
        "password": "password"

    Returns:
        JSON response with authentication status and token (if successful)

    """
    data = request.get_json()
    
    if not data or 'user_name' not in data or 'password' not in data:
        return jsonify({'message': 'Missing user_name or password'}), 400
    
    username = data['user_name']
    password = data['password']

    try:
        from application.models.central_models import AuthenticationService
        success, token_or_error = AuthenticationService.authenticate_and_generate_token(username, password)
        if success:
            current_app.logger.info(f"User '{username}' authenticated successfully.")
            return jsonify({
                'message': 'Authentication successful',
                'token': token_or_error
            }), 200
        else:
            current_app.logger.warning(f"Authentication failed for user '{username}': {token_or_error}")
            return jsonify({'message': token_or_error}), 401
    except Exception as e:
        current_app.logger.error(f"Error during authentication for user '{username}': {str(e)}")
        return jsonify({'message': 'Internal server error'}), 500