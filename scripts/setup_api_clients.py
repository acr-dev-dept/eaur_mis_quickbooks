#!/usr/bin/env python3
"""
Setup script for initializing API clients for payment gateway authentication.

This script creates API client records for Urubuto Pay and School Gear
with appropriate permissions and credentials.

Usage:
    python scripts/setup_api_clients.py
"""

import sys
import os
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from application import create_app, db
from application.models.central_models import ApiClient

def setup_urubuto_pay_client():
    """
    Create API client for Urubuto Pay integration.
    
    Returns:
        ApiClient: Created Urubuto Pay client
    """
    print("Setting up Urubuto Pay API client...")
    
    # Check if client already exists
    existing_client = ApiClient.get_by_gateway('urubuto_pay')
    if existing_client:
        print(f"Urubuto Pay client already exists: {existing_client.username}")
        return existing_client
    
    # Create new Urubuto Pay client
    client = ApiClient.create_client(
        client_name='Urubuto Pay',
        username='urubuto_pay_client',
        password='urubuto_secure_password_2024',  # Change this in production
        client_type='payment_gateway',
        gateway_name='urubuto_pay',
        permissions=['validation', 'notifications', 'status_check']
    )
    
    print(f"Created Urubuto Pay client: {client.username}")
    print(f"Client ID: {client.id}")
    print(f"Permissions: {client.permissions}")
    
    return client

def setup_school_gear_client():
    """
    Create API client for School Gear integration.
    
    Returns:
        ApiClient: Created School Gear client
    """
    print("\nSetting up School Gear API client...")
    
    # Check if client already exists
    existing_client = ApiClient.get_by_gateway('school_gear')
    if existing_client:
        print(f"School Gear client already exists: {existing_client.username}")
        return existing_client
    
    # Create new School Gear client
    client = ApiClient.create_client(
        client_name='School Gear',
        username='school_gear_client',
        password='schoolgear_secure_password_2024',  # Change this in production
        client_type='payment_gateway',
        gateway_name='school_gear',
        permissions=['validation', 'notifications', 'payments', 'status_check']
    )
    
    print(f"Created School Gear client: {client.username}")
    print(f"Client ID: {client.id}")
    print(f"Permissions: {client.permissions}")
    
    return client

def display_client_info(client):
    """
    Display client information and sample authentication request.
    
    Args:
        client (ApiClient): API client to display info for
    """
    print(f"\n{'='*50}")
    print(f"Client: {client.client_name}")
    print(f"{'='*50}")
    print(f"Username: {client.username}")
    print(f"Gateway: {client.gateway_name}")
    print(f"Permissions: {', '.join(client.permissions)}")
    print(f"Created: {client.created_at}")
    
    print(f"\nSample Authentication Request:")
    print(f"POST /api/v1/urubuto/authentication")
    print(f"Content-Type: application/json")
    print(f"")
    print(f"{{")
    print(f'  "user_name": "{client.username}",')
    print(f'  "password": "your_password_here"')
    print(f"}}")

def main():
    """Main setup function."""
    print("API Client Setup Script")
    print("=" * 50)
    
    # Create Flask app context
    app = create_app()
    
    with app.app_context():
        try:
            # Create database tables if they don't exist
            db.create_all()
            print("Database tables created/verified.")
            
            # Setup API clients
            urubuto_client = setup_urubuto_pay_client()
            school_gear_client = setup_school_gear_client()
            
            # Display client information
            display_client_info(urubuto_client)
            display_client_info(school_gear_client)
            
            print(f"\n{'='*50}")
            print("Setup completed successfully!")
            print("=" * 50)
            
            print("\nNext Steps:")
            print("1. Update client passwords in production")
            print("2. Share credentials with payment gateway providers")
            print("3. Test authentication endpoints")
            print("4. Configure environment variables")
            
            # Display all active clients
            print(f"\nAll Active API Clients:")
            active_clients = ApiClient.get_active_clients()
            for client in active_clients:
                print(f"- {client.client_name} ({client.gateway_name}): {client.username}")
            
        except Exception as e:
            print(f"Error during setup: {str(e)}")
            import traceback
            traceback.print_exc()
            return 1
    
    return 0

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
