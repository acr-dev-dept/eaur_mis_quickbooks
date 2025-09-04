"""
Urubuto Pay Service for EAUR MIS-QuickBooks Integration

This service handles all interactions with the Urubuto Pay payment gateway API,
including payment initiation, transaction status checking, and API authentication.

Based on Urubuto Pay API Documentation v.151
"""

import requests
import logging
from datetime import datetime
from flask import current_app
import os
import traceback
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

class UrubutoPay:
    """
    Service class for Urubuto Pay payment gateway integration.
    
    Handles payment initiation, transaction status checking, and API communication
    with the Urubuto Pay gateway system.
    """
    
    def __init__(self):
        """Initialize Urubuto Pay service with configuration."""
        self.api_base_url = os.getenv('URUBUTO_PAY_API_URL', 'https://staging.urubutopay.rw/api/v2')
        self.api_token = os.getenv('URUBUTO_PAY_API_KEY')
        self.merchant_code = os.getenv('URUBUTO_PAY_MERCHANT_CODE')
        self.service_code = os.getenv('URUBUTO_PAY_SERVICE_CODE')
        
        if not self.api_token:
            logger.warning("URUBUTO_PAY_API_KEY not configured")
        if not self.merchant_code:
            logger.warning("URUBUTO_PAY_MERCHANT_CODE not configured")
    
    def _make_request(self, endpoint, method="GET", data=None, headers=None):
        """
        Make HTTP request to Urubuto Pay API.
        
        Args:
            endpoint (str): API endpoint path
            method (str): HTTP method (GET, POST, PUT, DELETE)
            data (dict): Request payload for POST/PUT requests
            headers (dict): Additional headers
            
        Returns:
            requests.Response: HTTP response object
        """
        try:
            # Prepare headers
            request_headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {self.api_token}'
            }
            
            if headers:
                request_headers.update(headers)
            
            url = f"{self.api_base_url}/{endpoint}"
            logger.info(f"Making {method} request to: {url}")
            
            if method.upper() == "GET":
                response = requests.get(url, headers=request_headers, params=data)
            elif method.upper() == "POST":
                response = requests.post(url, headers=request_headers, json=data)
            elif method.upper() == "PUT":
                response = requests.put(url, headers=request_headers, json=data)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            logger.info(f"Response status: {response.status_code}")
            return response
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in API request: {str(e)}")
            raise
    
    def initiate_payment(self, payer_code, amount, channel_name, phone_number=None, 
                        card_type=None, redirection_url=None, payer_names=None, 
                        payer_email=None):
        """
        Initiate a payment through Urubuto Pay gateway.
        
        Args:
            payer_code (str): Reference number/invoice ID
            amount (float): Payment amount
            channel_name (str): Payment channel (MOMO, AIRTEL_MONEY, CARD)
            phone_number (str): Phone number for wallet payments
            card_type (str): Card type for card payments
            redirection_url (str): URL to redirect after payment
            payer_names (str): Payer's full name
            payer_email (str): Payer's email address
            
        Returns:
            dict: API response with payment initiation result
        """
        try:
            if not self.merchant_code:
                raise ValueError("Merchant code not configured")
            
            # Prepare payment data
            payment_data = {
                "merchant_code": self.merchant_code,
                "payer_code": str(payer_code),
                "amount": float(amount),
                "channel_name": channel_name,
                "card_type_to_be_used": card_type or "NOT_APPLICABLE",
                "phone_number": phone_number or "",
                "redirection_url": redirection_url or "",
                "payer_names": payer_names or "",
                "payer_email": payer_email or "",
                "service_code": self.service_code
            }
            
            logger.info(f"Initiating payment for payer_code: {payer_code}, amount: {amount}, channel: {channel_name}")
            
            response = self._make_request("payment/initiate", method="POST", data=payment_data)
            current_app.logger.info(f"Payment initiation response: {response.status_code} - {response.text} and the full response: {response}")
            if response.status_code == 200:
                result = response.json()
                logger.info(f"Payment initiation successful: {result.get('message', 'Success')}")
                return {
                    'success': True,
                    'data': result,
                    'status_code': response.status_code
                }
            else:
                error_data = response.json() if response.content else {}
                logger.error(f"Payment initiation failed: {response.status_code} - {error_data}")
                return {
                    'success': False,
                    'error': error_data.get('message', 'Payment initiation failed'),
                    'data': error_data,
                    'status_code': response.status_code
                }
                
        except Exception as e:
            logger.error(f"Error initiating payment: {str(e)}")
            logger.error(traceback.format_exc())
            return {
                'success': False,
                'error': f'Payment initiation error: {str(e)}',
                'data': None,
                'status_code': 500
            }
    
    def check_transaction_status(self, transaction_id):
        """
        Check the status of a transaction using Urubuto Pay API.
        
        Args:
            transaction_id (str): Urubuto Pay transaction ID
            
        Returns:
            dict: Transaction status information
        """
        try:
            if not self.merchant_code:
                raise ValueError("Merchant code not configured")
            
            status_data = {
                "transaction_id": transaction_id,
                "merchant_code": self.merchant_code
            }
            
            logger.info(f"Checking transaction status for: {transaction_id}")
            
            response = self._make_request("payment/transaction/status", method="POST", data=status_data)
            
            if response.status_code == 200:
                result = response.json()
                logger.info(f"Transaction status check successful for {transaction_id}")
                return {
                    'success': True,
                    'data': result,
                    'status_code': response.status_code
                }
            else:
                error_data = response.json() if response.content else {}
                logger.error(f"Transaction status check failed: {response.status_code} - {error_data}")
                return {
                    'success': False,
                    'error': error_data.get('message', 'Transaction status check failed'),
                    'data': error_data,
                    'status_code': response.status_code
                }
                
        except Exception as e:
            logger.error(f"Error checking transaction status: {str(e)}")
            logger.error(traceback.format_exc())
            return {
                'success': False,
                'error': f'Transaction status check error: {str(e)}',
                'data': None,
                'status_code': 500
            }
    
    def validate_webhook_data(self, webhook_data):
        """
        Validate webhook data received from Urubuto Pay.
        
        Args:
            webhook_data (dict): Webhook payload from Urubuto Pay
            
        Returns:
            tuple: (is_valid: bool, error_message: str or None)
        """
        try:
            required_fields = [
                'status', 'transaction_status', 'transaction_id', 
                'merchant_code', 'payer_code', 'amount', 'currency'
            ]
            
            missing_fields = [field for field in required_fields if not webhook_data.get(field)]
            
            if missing_fields:
                return False, f"Missing required fields: {', '.join(missing_fields)}"
            
            # Validate merchant code
            if webhook_data.get('merchant_code') != self.merchant_code:
                return False, "Invalid merchant code"
            
            # Validate transaction status
            valid_statuses = ['VALID', 'PENDING', 'FAILED', 'CANCELED']
            if webhook_data.get('transaction_status') not in valid_statuses:
                return False, f"Invalid transaction status: {webhook_data.get('transaction_status')}"
            
            return True, None
            
        except Exception as e:
            logger.error(f"Error validating webhook data: {str(e)}")
            return False, f"Validation error: {str(e)}"

if __name__ == "__main__":
    # Example usage
    urubuto_service = UrubutoPay()
    try:
        payment_response = urubuto_service.initiate_payment(
            payer_code="INV123456",
            amount=20000,
            channel_name="MOMO",
            phone_number="0781049931",
            payer_names="Alex Rugema",
            payer_email="alex.rugema@example.com"
        )
        print(payment_response)
    except Exception as e:
        print(f"Error occurred: {str(e)}")