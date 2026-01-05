from flask import Blueprint, jsonify
from application import db
from application.models.central_models import ApiClient

admin_api_clients_bp = Blueprint(
    "admin_api_clients",
    __name__,
    url_prefix="/api/v1/admin/api-clients"
)


@admin_api_clients_bp.route("/urubuto-pay/setup", methods=["POST"])
def setup_urubuto_pay_client_api():
    """
    Setup API client for Urubuto Pay
    """
    try:
        db.create_all()

        existing_client = ApiClient.get_by_gateway("urubuto_pay")
        if existing_client:
            return jsonify({
                "success": True,
                "message": "Urubuto Pay client already exists",
                "client": {
                    "id": existing_client.id,
                    "username": existing_client.username,
                    "permissions": existing_client.permissions
                }
            }), 200

        client = ApiClient.create_client(
            client_name="Urubuto Pay",
            username="urubuto_pay_client",
            password="urubuto_secure_password_2024",  # ENV in prod
            client_type="payment_gateway",
            gateway_name="urubuto_pay",
            permissions=["validation", "notifications", "status_check"]
        )

        return jsonify({
            "success": True,
            "message": "Urubuto Pay client created successfully",
            "client": {
                "id": client.id,
                "username": client.username,
                "permissions": client.permissions
            }
        }), 201

    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@admin_api_clients_bp.route("/school-gear/setup", methods=["POST"])
def setup_school_gear_client_api():
    """
    Setup API client for School Gear
    """
    try:
        db.create_all()

        existing_client = ApiClient.get_by_gateway("school_gear")
        if existing_client:
            return jsonify({
                "success": True,
                "message": "School Gear client already exists",
                "client": {
                    "id": existing_client.id,
                    "username": existing_client.username,
                    "permissions": existing_client.permissions
                }
            }), 200

        client = ApiClient.create_client(
            client_name="School Gear",
            username="school_gear_client",
            password="schoolgear_secure_password_2024",  # ENV in prod
            client_type="payment_gateway",
            gateway_name="school_gear",
            permissions=["validation", "notifications", "payments", "status_check"]
        )

        return jsonify({
            "success": True,
            "message": "School Gear client created successfully",
            "client": {
                "id": client.id,
                "username": client.username,
                "permissions": client.permissions
            }
        }), 201

    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@admin_api_clients_bp.route("", methods=["GET"])
def list_api_clients():
    """
    List all active API clients
    """
    clients = ApiClient.get_active_clients()

    return jsonify({
        "success": True,
        "count": len(clients),
        "clients": [
            {
                "id": client.id,
                "client_name": client.client_name,
                "username": client.username,
                "gateway": client.gateway_name,
                "permissions": client.permissions,
                "created_at": client.created_at
            }
            for client in clients
        ]
    }), 200
