"""
Authentication decorators for API route protection.

This module provides decorators for securing API endpoints with JWT token
validation and permission-based access control using the ApiClient authentication system.
"""

from functools import wraps
from flask import request, jsonify, current_app
from datetime import datetime
import traceback

def require_auth(required_permission=None):
    """
    Decorator to require valid JWT token for route access.
    
    This decorator validates JWT tokens and optionally checks for specific
    permissions before allowing access to protected routes.
    
    Args:
        required_permission (str): Optional specific permission required
                                 (e.g., 'validation', 'notifications', 'payments')
    
    Usage:
        @require_auth()  # Any valid token
        @require_auth('validation')  # Requires 'validation' permission
    
    Returns:
        Decorated function that validates authentication before execution
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            try:
                # Extract token from Authorization header
                auth_header = request.headers.get('Authorization')
                if not auth_header:
                    current_app.logger.warning("Missing Authorization header")
                    return jsonify({
                        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "message": "Missing Authorization header",
                        "status": 401
                    }), 401
                
                if not auth_header.startswith('Bearer '):
                    current_app.logger.warning("Invalid Authorization header format")
                    return jsonify({
                        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "message": "Invalid Authorization header format. Expected: Bearer <token>",
                        "status": 401
                    }), 401
                
                token = auth_header.split(' ')[1]
                
                # Validate token using AuthenticationService
                from application.models.central_models import AuthenticationService
                
                is_valid, payload_or_error = AuthenticationService.validate_jwt_token(token)
                if not is_valid:
                    current_app.logger.warning(f"Token validation failed: {payload_or_error}")
                    return jsonify({
                        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "message": payload_or_error,
                        "status": 401
                    }), 401
                
                # Check permission if required
                if required_permission:
                    if not AuthenticationService.check_permission(payload_or_error, required_permission):
                        current_app.logger.warning(
                            f"Insufficient permissions for client {payload_or_error.get('client_name')}. "
                            f"Required: {required_permission}, Has: {payload_or_error.get('permissions', [])}"
                        )
                        return jsonify({
                            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            "message": f"Insufficient permissions. Required: {required_permission}",
                            "status": 403
                        }), 403
                
                # Add token payload to request context for use in route
                request.token_payload = payload_or_error
                
                current_app.logger.info(
                    f"Authentication successful for client: {payload_or_error.get('client_name')} "
                    f"({payload_or_error.get('gateway_name')})"
                )
                
                return f(*args, **kwargs)
                
            except Exception as e:
                current_app.logger.error(f"Authentication decorator error: {str(e)}")
                current_app.logger.error(traceback.format_exc())
                return jsonify({
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "message": "Authentication error",
                    "status": 500
                }), 500
        
        return decorated_function
    return decorator

def require_gateway(gateway_name):
    """
    Decorator to restrict access to specific payment gateway.
    
    This decorator ensures that only clients from a specific gateway
    can access the protected route. Must be used after @require_auth.
    
    Args:
        gateway_name (str): Gateway name (e.g., 'urubuto_pay', 'school_gear')
    
    Usage:
        @require_auth('validation')
        @require_gateway('urubuto_pay')
        def urubuto_only_endpoint():
            pass
    
    Returns:
        Decorated function that validates gateway access before execution
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            try:
                # Check if token payload exists (should be set by @require_auth)
                if not hasattr(request, 'token_payload'):
                    current_app.logger.error("Gateway decorator used without authentication")
                    return jsonify({
                        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "message": "Authentication required",
                        "status": 401
                    }), 401
                
                client_gateway = request.token_payload.get('gateway_name')
                if client_gateway != gateway_name:
                    current_app.logger.warning(
                        f"Gateway access denied. Client gateway: {client_gateway}, "
                        f"Required: {gateway_name}"
                    )
                    return jsonify({
                        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "message": f"Access restricted to {gateway_name} gateway",
                        "status": 403
                    }), 403
                
                current_app.logger.info(f"Gateway access granted for {gateway_name}")
                return f(*args, **kwargs)
                
            except Exception as e:
                current_app.logger.error(f"Gateway decorator error: {str(e)}")
                current_app.logger.error(traceback.format_exc())
                return jsonify({
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "message": "Gateway validation error",
                    "status": 500
                }), 500
        
        return decorated_function
    return decorator

def log_api_access(operation_name=None):
    """
    Decorator to log API access for audit purposes.
    
    This decorator logs API access attempts with client information
    and operation details for monitoring and audit trails.
    
    Args:
        operation_name (str): Optional operation name for logging
    
    Usage:
        @require_auth('validation')
        @log_api_access('payer_validation')
        def validate_payer():
            pass
    
    Returns:
        Decorated function that logs access before execution
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            try:
                operation = operation_name or f.__name__
                
                # Log access attempt
                if hasattr(request, 'token_payload'):
                    client_info = request.token_payload
                    current_app.logger.info(
                        f"API Access - Operation: {operation}, "
                        f"Client: {client_info.get('client_name')}, "
                        f"Gateway: {client_info.get('gateway_name')}, "
                        f"IP: {request.remote_addr}"
                    )
                else:
                    current_app.logger.info(
                        f"API Access - Operation: {operation}, "
                        f"IP: {request.remote_addr} (unauthenticated)"
                    )
                
                return f(*args, **kwargs)
                
            except Exception as e:
                current_app.logger.error(f"Access logging error: {str(e)}")
                # Don't fail the request due to logging errors
                return f(*args, **kwargs)
        
        return decorated_function
    return decorator
