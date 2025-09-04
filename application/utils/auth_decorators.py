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
                current_app.logger.info(f"🔐 === AUTH START for {f.__name__} ===")
                current_app.logger.info(f"Required permission: {required_permission}")
                current_app.logger.info(f"Request method: {request.method}")
                current_app.logger.info(f"Request endpoint: {request.endpoint}")
                current_app.logger.info(f"Request remote addr: {request.remote_addr}")

                # Extract token from Authorization header
                auth_header = request.headers.get('Authorization')
                current_app.logger.info(f"Authorization header present: {bool(auth_header)}")

                if auth_header:
                    current_app.logger.info(f"Auth header length: {len(auth_header)}")
                    current_app.logger.info(f"Auth header starts with 'Bearer ': {auth_header.startswith('Bearer ')}")

                if not auth_header:
                    current_app.logger.warning("❌ Missing Authorization header")
                    return jsonify({
                        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "message": "Missing Authorization header",
                        "status": 401
                    }), 401

                if not auth_header.startswith('Bearer '):
                    current_app.logger.warning(f"❌ Invalid Authorization header format: {auth_header[:50]}...")
                    return jsonify({
                        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "message": "Invalid Authorization header format. Expected: Bearer <token>",
                        "status": 401
                    }), 401

                # Handle both "Bearer token" and "Bearer Bearer token" formats
                auth_parts = auth_header.split(' ')
                current_app.logger.info(f"Auth header parts: {len(auth_parts)} parts")
                current_app.logger.info(f"Auth header parts preview: {auth_parts[:3] if len(auth_parts) >= 3 else auth_parts}")

                if len(auth_parts) >= 3 and auth_parts[1].lower() == 'bearer':
                    # Handle "Bearer Bearer actual_token" format
                    token = auth_parts[2]
                    current_app.logger.info("Using token from position 2 (Bearer Bearer token format)")
                elif len(auth_parts) >= 2:
                    # Handle standard "Bearer token" format
                    token = auth_parts[1]
                    current_app.logger.info("Using token from position 1 (Bearer token format)")
                else:
                    current_app.logger.error("❌ Invalid Authorization header format - insufficient parts")
                    return jsonify({
                        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "message": "Invalid Authorization header format",
                        "status": 401
                    }), 401

                current_app.logger.info(f"Token extracted successfully")
                current_app.logger.info(f"Token length: {len(token)}")
                current_app.logger.info(f"Token preview: {token[:20]}...{token[-10:] if len(token) > 30 else token}")
                
                # Validate token using AuthenticationService
                from application.models.central_models import AuthenticationService

                current_app.logger.info("🔍 Calling AuthenticationService.validate_jwt_token")
                is_valid, payload_or_error = AuthenticationService.validate_jwt_token(token)

                current_app.logger.info(f"Token validation result: {is_valid}")
                if not is_valid:
                    current_app.logger.error(f"❌ Token validation failed: {payload_or_error}")
                    return jsonify({
                        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "message": payload_or_error,
                        "status": 401
                    }), 401
                else:
                    current_app.logger.info(f"✅ Token valid for client: {payload_or_error.get('client_name')} (ID: {payload_or_error.get('client_id')})")
                    current_app.logger.info(f"Client gateway: {payload_or_error.get('gateway_name')}")
                    current_app.logger.info(f"Client permissions: {payload_or_error.get('permissions', [])}")
                
                # Check permission if required
                if required_permission:
                    current_app.logger.info(f"🔍 Checking permission: {required_permission}")
                    has_permission = AuthenticationService.check_permission(payload_or_error, required_permission)
                    current_app.logger.info(f"Permission check result: {has_permission}")

                    if not has_permission:
                        current_app.logger.warning(
                            f"❌ Insufficient permissions for client {payload_or_error.get('client_name')}. "
                            f"Required: {required_permission}, Has: {payload_or_error.get('permissions', [])}"
                        )
                        return jsonify({
                            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            "message": f"Insufficient permissions. Required: {required_permission}",
                            "status": 403
                        }), 403
                    else:
                        current_app.logger.info(f"✅ Permission check passed: {required_permission}")

                # Add token payload to request context for use in route
                request.token_payload = payload_or_error
                current_app.logger.info("✅ Token payload added to request context")

                current_app.logger.info(
                    f"✅ Authentication successful for client: {payload_or_error.get('client_name')} "
                    f"({payload_or_error.get('gateway_name')})"
                )
                current_app.logger.info(f"🔐 === AUTH END for {f.__name__} - PROCEEDING ===")

                return f(*args, **kwargs)
                
            except Exception as e:
                current_app.logger.error(f"💥 Authentication decorator error in {f.__name__}: {str(e)}")
                current_app.logger.error(f"💥 Full traceback: {traceback.format_exc()}")
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
                current_app.logger.info(f"🚪 === GATEWAY CHECK for {f.__name__} ===")
                current_app.logger.info(f"Required gateway: {gateway_name}")

                # Check if token payload exists (should be set by @require_auth)
                if not hasattr(request, 'token_payload'):
                    current_app.logger.error("❌ Gateway decorator used without authentication")
                    return jsonify({
                        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "message": "Authentication required",
                        "status": 401
                    }), 401

                client_gateway = request.token_payload.get('gateway_name')
                current_app.logger.info(f"Client gateway: {client_gateway}")
                current_app.logger.info(f"Gateway match check: {client_gateway} == {gateway_name} = {client_gateway == gateway_name}")

                if client_gateway != gateway_name:
                    current_app.logger.warning(
                        f"❌ Gateway access denied. Client gateway: {client_gateway}, "
                        f"Required: {gateway_name}"
                    )
                    return jsonify({
                        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "message": f"Access restricted to {gateway_name} gateway",
                        "status": 403
                    }), 403

                current_app.logger.info(f"✅ Gateway access granted for {gateway_name}")
                current_app.logger.info(f"🚪 === GATEWAY CHECK END ===")
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
