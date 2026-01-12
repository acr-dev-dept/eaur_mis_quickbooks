from flask import Blueprint, jsonify
from application import db
from application.models.central_models import ApiClient
import os
from flask import request

admin_api_clients_bp = Blueprint(
    "admin_api_clients",
    __name__,
    url_prefix="/api/v1/admin/api-clients"
)


@admin_api_clients_bp.route("/payment-gateway/setup", methods=["POST"])
def setup_urubuto_pay_client_api():
    """
    Setup API client for Urubuto Pay
    Expects JSON body with: username, password
    """
    try:
        db.create_all()

        data = request.get_json(silent=True)
        if not data:
            return jsonify({
                "success": False,
                "message": "Invalid or missing JSON payload"
            }), 400

        username = data.get("username")
        password = data.get("password")
        gateway_name = data.get("gateway_name")
        client_name = data.get("client_name")
        if not username or not password:
            return jsonify({
                "success": False,
                "message": "username and password are required"
            }), 400

        existing_client = ApiClient.get_by_gateway(gateway_name)
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
            client_name=client_name,
            username=username,
            password=password,
            client_type="payment_gateway",
            gateway_name=gateway_name,
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
            "message": "Failed to setup Urubuto Pay client",
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
