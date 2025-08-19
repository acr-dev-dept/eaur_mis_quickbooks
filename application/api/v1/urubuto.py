from flask import Blueprint, request, jsonify, current_app, session, flash, redirect, url_for

urubuto_bp = Blueprint('urubuto', __name__)

@urubuto_bp.route('/payments/notification', methods=['POST'])
def payment_notification():
    """Handle payment notifications from Urubuto"""
    data = request.json
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    # Log the received notification for debugging
    current_app.logger.info(f"Received payment notification: {data}")

    # Process the notification (this is a placeholder)
