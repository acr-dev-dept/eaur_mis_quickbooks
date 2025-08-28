import requests
import base64
import json
import traceback
from dotenv import load_dotenv
import os
import logging
import urllib.parse  # For URL encoding
import re  # For regular expressions
from flask import current_app
from application.helpers.quickbooks_helpers import QuickBooksHelper

load_dotenv()

class QuickBooks:
    """
    A class to interact with the QuickBooks Online API, including methods for authentication
    and accessing various endpoints.
    """
    def __init__(self):
        """
        Initialize the QuickBooks client for single-tenant EAUR system.
        """
        from application.models.central_models import QuickBooksConfig
        from flask import current_app

        current_app.logger.info("Initializing QuickBooks client for EAUR")

        # Load QuickBooks configuration
        self.config = QuickBooksConfig.get_config()

        # QuickBooks API configuration
        self.client_id = os.getenv("QUICK_BOOKS_CLIENT_ID")
        self.client_secret = os.getenv("QUICK_BOOKS_SECRET")
        self.redirect_uri = os.getenv("QUICK_BOOKS_REDIRECT_URI")
        self.api_base_url = os.getenv("QUICK_BOOKS_BASEURL_SANDBOX")
        self.token_url = "https://oauth.platform.intuit.com/oauth2/v1/tokens/bearer"

        # Initialize tokens
        self.access_token = None
        self.refresh_token = None
        self.realm_id = None

        if self.config:
            current_app.logger.info("QuickBooks configuration found in database")

            # Decrypt and store tokens
            try:
                if self.config.refresh_token:
                    self.refresh_token = QuickBooksHelper.decrypt(self.config.refresh_token)
                    current_app.logger.info("Refresh token decrypted successfully")
                else:
                    current_app.logger.warning("No refresh token found in database")

                if self.config.access_token:
                    self.access_token = QuickBooksHelper.decrypt(self.config.access_token)
                    current_app.logger.info("Access token decrypted successfully")
                else:
                    current_app.logger.warning("No access token found in database")

                self.realm_id = self.config.realm_id
                current_app.logger.info(f"Realm ID: {self.realm_id}")

            except Exception as e:
                current_app.logger.error(f"Error decrypting tokens: {str(e)}")
                self.refresh_token = None
                self.access_token = None
        else:
            current_app.logger.info("No QuickBooks configuration found - first time setup")

        current_app.logger.info("QuickBooks client initialized successfully")

    def _get_auth_header(self):
        """Generate the Basic Auth header required for token requests."""
        auth_str = f"{self.client_id}:{self.client_secret}"
        auth_bytes = base64.b64encode(auth_str.encode()).decode()
        return {"Authorization": f"Basic {auth_bytes}"}

    def get_quickbooks_access_token(self, code):
        """
        Exchange the authorization code for an access token.

        Args:
            code (str): The authorization code received from QuickBooks.

        Returns:
            dict: The response containing the access token and refresh token.
        """
        headers = self._get_auth_header()
        headers["Content-Type"] = "application/x-www-form-urlencoded"

        data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": self.redirect_uri
        }

        response = requests.post(self.token_url, headers=headers, data=data)
        if response.status_code == 200:
            tokens = response.json()
            self.access_token = tokens['access_token']
            self.refresh_token = tokens['refresh_token']
            # Update QuickBooks configuration in the database
            try:
                from application.models.central_models import QuickBooksConfig
                QuickBooksConfig.update_config(
                    access_token=QuickBooksHelper.encrypt(self.access_token),
                    refresh_token=QuickBooksHelper.encrypt(self.refresh_token)
                )
                current_app.logger.info("QuickBooks configuration updated successfully.")
            except Exception as e:
                current_app.logger.error(f"Error updating QuickBooks configuration: {e}")
            return tokens
        else:
            raise Exception(f"Failed to get access token: {response.status_code} {response.text}")

    def refresh_access_token(self):
        """Refresh the QuickBooks access token using the refresh token."""
        current_app.logger.info(f"Starting token refresh with refresh token: {self.refresh_token}")

        if not self.refresh_token:
            current_app.logger.error("No refresh token available for refresh")
            raise ValueError("Refresh token is required to refresh the access token.")

        headers = self._get_auth_header()
        headers["Content-Type"] = "application/x-www-form-urlencoded"

        data = {
            "grant_type": "refresh_token",
            "refresh_token": self.refresh_token
        }

        current_app.logger.info(f"Sending refresh token request to: {self.token_url}")
        response = requests.post(self.token_url, headers=headers, data=data)
        current_app.logger.info(f"Token refresh response status: {response.status_code}")

        if response.status_code == 200:
            tokens = response.json()
            current_app.logger.info(f"Received new tokens. Access token starts with: {tokens['access_token'][:10]}...")
            current_app.logger.info(f"New refresh token: {tokens['refresh_token']}")

            self.access_token = tokens['access_token']
            self.refresh_token = tokens['refresh_token']  # Update refresh token

            # Update QuickBooks configuration in the database
            try:
                encrypted_access_token = QuickBooksHelper.encrypt(self.access_token)
                encrypted_refresh_token = QuickBooksHelper.encrypt(self.refresh_token)

                current_app.logger.info("Updating QuickBooks configuration with new tokens")

                from application.models.central_models import QuickBooksConfig
                config = QuickBooksConfig.update_config(
                    access_token=encrypted_access_token,
                    refresh_token=encrypted_refresh_token
                )

                if config:
                    current_app.logger.info("QuickBooks configuration updated successfully with new tokens.")
                    # Update local config reference
                    self.config = config
                else:
                    current_app.logger.error("Failed to update QuickBooks configuration with new tokens.")
            except Exception as e:
                current_app.logger.error(f"Error updating QuickBooks configuration: {e}")
                current_app.logger.error(f"Error details: {str(e)}")
            return tokens
        else:
            error_msg = f"Failed to refresh token: {response.status_code} {response.text}"
            current_app.logger.error(error_msg)
            raise Exception(error_msg)

    def make_request(self, endpoint, method="GET", data=None, params=None):
        """
        Make a request to the QuickBooks API with automatic token refresh if expired.

        Args:
            endpoint (str): The API endpoint (e.g., "/customer").
            method (str): HTTP method (e.g., "GET", "POST").
            data (dict): Data to be sent in the body of the request (for POST/PUT requests).
            params (dict): Query parameters for the request.

        Returns:
            dict: The JSON response from the QuickBooks API.
        """
        current_app.logger.info(f"Making {method} request to endpoint: {endpoint}")

        # Check token status
        if not self.access_token:
            if self.refresh_token:
                current_app.logger.warning("No access token available. Attempting to refresh...")
                self.refresh_access_token()
                current_app.logger.info(f"After refresh - Access token: {self.access_token[:10]}... Refresh token: {self.refresh_token}")
            else:
                current_app.logger.error("No access token or refresh token available")
                raise ValueError("Access token is required to make requests.")
        else:
            current_app.logger.info(f"Using existing access token: {self.access_token[:10]}...")

        def _make_http_call():
            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Accept": "application/json",
                "Content-Type": "application/json",
            }

            url = f"{self.api_base_url}/{endpoint}"
            current_app.logger.info(f"Making request to URL: {url}")

            if method.upper() == "GET":
                current_app.logger.info(f"GET request with params: {params}")
                return requests.get(url, headers=headers, params=params)
            elif method.upper() == "POST":
                current_app.logger.info(f"POST request with data: {data}")
                return requests.post(url, headers=headers, json=data)
            elif method.upper() == "PUT":
                current_app.logger.info(f"PUT request with data: {data}")
                return requests.put(url, headers=headers, json=data)
            else:
                current_app.logger.error(f"Unsupported HTTP method: {method}")
                raise ValueError(f"Unsupported HTTP method: {method}")

        # Attempt initial request
        current_app.logger.info("Making initial API request")
        response = _make_http_call()
        current_app.logger.info(f"Initial response status code: {response.status_code}")

        # Handle token expiration
        if response.status_code == 401:
            current_app.logger.warning(f"Received 401 response: {response.text}")
            if "token" in response.text.lower() or "authentication" in response.text.lower():
                current_app.logger.warning("Access token appears to be expired. Attempting to refresh...")
                try:
                    # Log current tokens before refresh
                    current_app.logger.info(f"Before refresh - Access token: {self.access_token[:10]}... Refresh token: {self.refresh_token}")

                    # Refresh the token
                    refresh_result = self.refresh_access_token()
                    current_app.logger.info(f"Token refresh successful: {refresh_result is not None}")
                    current_app.logger.info(f"After refresh - Access token: {self.access_token[:10]}... Refresh token: {self.refresh_token}")

                    # Retry the request with the new token
                    current_app.logger.info("Retrying request with new token")
                    response = _make_http_call()
                    current_app.logger.info(f"Retry response status code: {response.status_code}")
                except Exception as e:
                    current_app.logger.error(f"Token refresh failed: {e}")
                    current_app.logger.error(f"Error details: {str(e)}")
                    raise

        if response.status_code in [200, 201]:
            current_app.logger.info("API request successful")
            return response.json()
        else:
            # Log the error details
            current_app.logger.error(f"Final API call failed: {response.status_code} {response.text}")

            # Log the current tokens for debugging
            current_app.logger.error(f"Current access token: {self.access_token[:10]}...")
            current_app.logger.error(f"Current refresh token: {self.refresh_token}")

            # Raise exception with error details
            raise Exception(f"API request failed: {response.status_code} {response.text}")



    def get_company_info(self, realm_id):
        """Retrieve company information for the specified realm ID."""
        endpoint = f"{realm_id}/companyinfo/{realm_id}"
        return self.make_request(endpoint, method="GET")

    def create_customer(self, realm_id, customer_data):
        """Create a new customer in QuickBooks."""
        endpoint = f"{realm_id}/customer"
        return self.make_request(endpoint, method="POST", data=customer_data)

    def get_customers(self, realm_id, params=None):
        """Retrieve a list of customers."""
        endpoint = f"{realm_id}/query"
        query = "SELECT * FROM Customer"
        if params:
            query += " WHERE " + " AND ".join(f"{k}='{v}'" for k, v in params.items())
        return self.make_request(endpoint, method="GET", params={"query": query})

    def update_customer(self, realm_id, customer_id, customer_data):
        """Update an existing customer in QuickBooks."""
        endpoint = f"{realm_id}/customer/{customer_id}"
        return self.make_request(endpoint, method="POST", data=customer_data)

    def get_customer(self, realm_id, customer_id):
        """Retrieve a specific customer by ID."""
        endpoint = f"{realm_id}/customer/{customer_id}"
        return self.make_request(endpoint, method="GET")

    def get_invoices(self, realm_id, params=None):
        """
        Retrieve a list of invoices from QuickBooks.

        Args:
            realm_id (str): The QuickBooks company ID.
            params (dict): Additional query parameters for filtering.

        Returns:
            dict: The response from the QuickBooks API.
        """
        query = "SELECT * FROM Invoice MAXRESULTS 1000"
        if params:
            conditions = []
            for key, value in params.items():
                if key.lower() == 'customerref':
                    conditions.append(f"CustomerRef = '{value}'")
                elif key.lower() == 'docnumber':
                    conditions.append(f"DocNumber = '{value}'")
                elif key.lower() == 'active':
                    conditions.append(f"Active = {str(value).lower()}")
            if conditions:
                query += " WHERE " + " AND ".join(conditions)

        endpoint = f"{realm_id}/query"
        try:
            current_app.logger.info(f"Getting invoices with query: {query}")
            response = self.make_request(endpoint, method="GET", params={"query": query})
            current_app.logger.info("Invoices retrieved successfully")
            return response
        except Exception as e:
            current_app.logger.error(f"Error getting invoices: {str(e)}")
            return {"error": "Error getting invoices", "details": str(e)}

    def get_payments(self, realm_id, params=None):
        """
        Retrieve a list of payments from QuickBooks.

        Args:
            realm_id (str): The QuickBooks company ID.
            params (dict): Additional query parameters for filtering.

        Returns:
            dict: The response from the QuickBooks API.
        """
        query = "SELECT * FROM Payment MAXRESULTS 1000"
        if params:
            conditions = []
            for key, value in params.items():
                if key.lower() == 'customerref':
                    conditions.append(f"CustomerRef = '{value}'")
                elif key.lower() == 'txndate':
                    conditions.append(f"TxnDate = '{value}'")
                elif key.lower() == 'active':
                    conditions.append(f"Active = {str(value).lower()}")
            if conditions:
                query += " WHERE " + " AND ".join(conditions)

        endpoint = f"{realm_id}/query"
        try:
            current_app.logger.info(f"Getting payments with query: {query}")
            response = self.make_request(endpoint, method="GET", params={"query": query})
            current_app.logger.info("Payments retrieved successfully")
            return response
        except Exception as e:
            current_app.logger.error(f"Error getting payments: {str(e)}")
            return {"error": "Error getting payments", "details": str(e)}

    def get_accounts(self, realm_id):
        """
        Fetch all accounts from QuickBooks Online using the Query endpoint.

        Args:
            realm_id (str): The QuickBooks company ID.

        Returns:
            dict: The response from the QuickBooks API, or an error message.
        """
        # Relative endpoint for the query and get response of at least 1000
        query = "SELECT * FROM Account MAXRESULTS 1000"
        endpoint = f"{realm_id}/query"

        # Query parameters
        params = {
            "query": query,
        }

        try:
            # Make the GET request using the helper method
            response = self.make_request(endpoint, method="GET", params=params)
            return response
        except Exception as e:
            current_app.logger.error(f"Error getting accounts: {str(e)}")
            current_app.logger.error(f"Current refresh token: {self.refresh_token}")
            return {"error": "Error getting accounts", "details": str(e)}

    def get_vendors(self, realm_id, params=None):
        """
        Fetch all vendors from QuickBooks Online using the Query endpoint.

        Args:
            realm_id (str): The QuickBooks company ID.
            params (dict): Additional query parameters.

        Returns:
            dict: The response from the QuickBooks API, or an error message.
        """
        # Relative endpoint for the query
        query = "SELECT * FROM Vendor"
        endpoint = f"{realm_id}/query"

        # Query parameters
        params = {
            "query": query,
        }

        try:
            # Make the GET request using the helper method
            response = self.make_request(endpoint, method="GET", params=params)
            current_app.logger.info(f"Vendors: {response}")
            return response
        except Exception as e:
            current_app.logger.error(f"Error getting vendors: {str(e)}")
            return {"error": "Error getting vendors", "details": str(e)}

    def get_departments(self, realm_id):
        """
        Fetch all departments (classes) from QuickBooks Online using the Query endpoint.

        In QuickBooks, departments are represented as "Classes".

        Args:
            realm_id (str): The QuickBooks company ID.

        Returns:
            dict: The response from the QuickBooks API, or an error message.
        """
        # Relative endpoint for the query
        query = "SELECT * FROM Class WHERE Active = true"
        endpoint = f"{realm_id}/query"

        # Query parameters
        params = {
            "query": query,
        }

        try:
            # Make the GET request using the helper method
            response = self.make_request(endpoint, method="GET", params=params)
            current_app.logger.info(f"Departments (Classes): {response}")
            return response
        except Exception as e:
            current_app.logger.error(f"Error getting departments (classes): {str(e)}")
            return {"error": "Error getting departments", "details": str(e)}

    def get_locations(self, realm_id):
        """
        Fetch all locations from QuickBooks Online using the Query endpoint.

        In QuickBooks, locations are represented as "Departments".

        Args:
            realm_id (str): The QuickBooks company ID.

        Returns:
            dict: The response from the QuickBooks API, or an error message.
        """
        # Relative endpoint for the query
        query = "SELECT * FROM Department WHERE Active = true"
        endpoint = f"{realm_id}/query"

        # Query parameters
        params = {
            "query": query,
        }

        try:
            # Make the GET request using the helper method
            response = self.make_request(endpoint, method="GET", params=params)
            current_app.logger.info(f"Locations (Departments): {response}")
            return response
        except Exception as e:
            current_app.logger.error(f"Error getting locations (departments): {str(e)}")
            return {"error": "Error getting locations", "details": str(e)}


    def create_journal_entry(self, realm_id, journal_entry_data):
        """
        Create a journal entry in QuickBooks.

        Args:
            realm_id (str): The realm ID of the company.
            journal_entry_data (dict): The data for the journal entry, including lines.

        Returns:
            dict: The response from the QuickBooks API.
        """
        endpoint = f"{realm_id}/journalentry"
        try:
            current_app.logger.info(f"Creating journal entry with data: {journal_entry_data}")
            response = self.make_request(endpoint, method="POST", data=journal_entry_data)
            current_app.logger.info(f"Journal entry created successfully: {response}")
            return response
        except Exception as e:
            current_app.logger.error(f"Error creating journal entry: {str(e)}")
            # Return a structured error response instead of a string
            return {
                "Fault": {
                    "Error": [
                        {
                            "Message": f"Error creating journal entry: {str(e)}",
                            "Detail": traceback.format_exc()
                        }
                    ]
                }
            }

    def create_account(self, realm_id, account_data):
        """
        Create an account in QuickBooks.

        Args:
            realm_id (str): The realm ID of the company.
            account_data (dict): The data for the account.

        Returns:
            dict: The response from the QuickBooks API.
        """
        endpoint = f"{realm_id}/account"
        try:
            request = self.make_request(endpoint, method="POST", data=account_data)
            return request
        except Exception as e:
            print("Error:", str(e))
            return "Error creating account"


    def normalize_account_type_subtype(self, account_type, account_subtype):
        """
        Normalize AccountType and AccountSubType by trimming and converting to lowercase.
        Removes any special characters and extra spaces.

        Args:
            account_type (str): Account type value.
            account_subtype (str): Account subtype value.

        Returns:
            tuple: Normalized account type and subtype.
        """
        normalized_type = re.sub(r'\s+', '', account_type.strip().lower())  # Remove spaces and convert to lowercase
        normalized_subtype = re.sub(r'\s+', '', account_subtype.strip().lower())  # Remove spaces and convert to lowercase

        return normalized_type, normalized_subtype

    def get_account_types(self, realm_id):
        """
        Fetch unique account types and subtypes from QuickBooks.

        Args:
            realm_id (str): The QuickBooks company ID.

        Returns:
            list: A list of dictionaries containing unique account types and subtypes.
        """
        try:
            # Query to fetch all accounts
            accounts_response = self.get_accounts(realm_id)
            accounts = accounts_response.get("QueryResponse", {}).get("Account", [])

            # Use a dictionary to track unique account types and subtypes
            account_type_dict = {}

            for account in accounts:
                account_type = account["AccountType"]
                account_subtype = account.get("AccountSubType", "N/A")
                print(f"Account type: {account_type}, Subtype: {account_subtype}")

                # Normalize account type and subtype
                normalized_type, normalized_subtype = self.normalize_account_type_subtype(account_type, account_subtype)

                # Use normalized values as dictionary key to avoid duplicates
                account_type_dict[(normalized_type, normalized_subtype)] = {
                    "AccountType": account_type.title(),
                    "AccountSubType": account_subtype.title() if account_subtype != "n/a" else "N/A"
                }

            # Convert the dictionary values to a list
            account_types = list(account_type_dict.values())

            return account_types

        except Exception as e:
            logging.error(f"Error fetching account types: {str(e)}")
            return []

    def get_authorization_url(self, state="Lion Of Judah", scopes=None):
        """
        Generate the QuickBooks OAuth2 authorization URL.

        Args:
            state (str): A unique state string to prevent CSRF attacks.
            scopes (list): A list of scopes for the requested permissions.

        Returns:
            str: The authorization URL for QuickBooks OAuth2.
        """
        if scopes is None:
            scopes = ["com.intuit.quickbooks.accounting"]

        base_url = "https://appcenter.intuit.com/connect/oauth2"
        scope_str = "%20".join(scopes)

        url = (
            f"{base_url}?"
            f"client_id={self.client_id}&"
            f"response_type=code&"
            f"scope={scope_str}&"
            f"redirect_uri={self.redirect_uri}&"
            f"state={state}"
        )
        return url       



    def disconnect_app(self):
        """
        Disconnect the app from QuickBooks by revoking the access or refresh token.
        This is done via a separate endpoint that does not use the standard API base URL.
        If no tokens are available, it will still clear any remaining data from the database.
        """
        current_app.logger.info("Starting QuickBooks disconnect process...")
        current_app.logger.info(f"Access token available: {bool(self.access_token)}")
        current_app.logger.info(f"Refresh token available: {bool(self.refresh_token)}")

        token_to_revoke = self.access_token or self.refresh_token

        # If no tokens are available, just clear the database and return success
        if not token_to_revoke:
            current_app.logger.info("No tokens available to revoke. Clearing database records only.")
            try:
                from application.models.central_models import QuickBooksConfig
                QuickBooksConfig.update_config(
                    access_token=None,
                    refresh_token=None,
                    authorization_code=None,
                    realm_id=None,
                    is_active=False
                )
                current_app.logger.info("Successfully cleared QuickBooks data from database (no tokens to revoke).")
                return True
            except Exception as e:
                current_app.logger.error(f"Failed to clear QuickBooks data from database: {e}")
                raise Exception("Failed to clear QuickBooks data from database.")

        # If we have tokens, attempt to revoke them with QuickBooks
        revoke_url = "https://developer.api.intuit.com/v2/oauth2/tokens/revoke"

        try:
            auth_header = self._get_auth_header()
        except Exception as e:
            current_app.logger.warning(f"Failed to get auth header for token revocation: {e}. Proceeding with database cleanup only.")
            # If we can't get auth header, just clear the database
            try:
                from application.models.central_models import QuickBooksConfig
                QuickBooksConfig.update_config(
                    access_token=None,
                    refresh_token=None,
                    authorization_code=None,
                    realm_id=None,
                    is_active=False
                )
                current_app.logger.info("Successfully cleared QuickBooks data from database (auth header failed).")
                return True
            except Exception as e:
                current_app.logger.error(f"Failed to clear QuickBooks data from database: {e}")
                raise Exception("Failed to clear QuickBooks data from database.")

        headers = {
            **auth_header,
            "Accept": "application/json",
            "Content-Type": "application/x-www-form-urlencoded"
        }

        # Send token as form data, not JSON
        payload = {"token": token_to_revoke}

        try:
            current_app.logger.info(f"Attempting to revoke token: {token_to_revoke[:10]}...")
            current_app.logger.info(f"Revocation URL: {revoke_url}")
            current_app.logger.info(f"Headers: {headers}")

            response = requests.post(revoke_url, headers=headers, data=payload)  # Use 'data' not 'json'

            current_app.logger.info(f"Revocation response status: {response.status_code}")
            current_app.logger.info(f"Revocation response text: {response.text}")

            if response.status_code == 200:
                current_app.logger.info("Successfully revoked QuickBooks token.")
            else:
                current_app.logger.warning(f"Failed to revoke QuickBooks token: {response.status_code} {response.text}. Proceeding with database cleanup.")

        except Exception as e:
            current_app.logger.warning(f"Exception during token revocation: {e}. Proceeding with database cleanup.")

        # Regardless of token revocation success/failure, clear the database
        try:
            from application.models.central_models import QuickBooksConfig
            QuickBooksConfig.update_config(
                access_token=None,
                refresh_token=None,
                authorization_code=None,
                realm_id=None,
                is_active=False
            )
            current_app.logger.info("Successfully disconnected QuickBooks and cleared all tokens and authorization data.")
            return True
        except Exception as e:
            current_app.logger.error(f"Failed to clear QuickBooks data from database after token revocation: {e}")
            raise Exception("Failed to clear QuickBooks data from database.")

    def create_invoice(self, realm_id, invoice_data):
        """
        Create an invoice in QuickBooks.

        Args:
            realm_id (str): The realm ID of the company.
            invoice_data (dict): The data for the invoice.

        Returns:
            dict: The response from the QuickBooks API.
        """
        endpoint = f"{realm_id}/invoice"
        try:
            current_app.logger.info(f"Creating invoice with data: {invoice_data}")
            response = self.make_request(endpoint, method="POST", data=invoice_data)
            current_app.logger.info(f"Invoice created successfully: {response}")
            return response
        except Exception as e:
            current_app.logger.error(f"Error creating invoice: {str(e)}")
            # Return a structured error response instead of a string
            return {
                "Fault": {
                    "Error": [
                        {
                            "Message": f"Error creating invoice: {str(e)}",
                            "Detail": traceback.format_exc()
                        }
                    ]
                }
            }
    def get_invoice(self, realm_id, invoice_id):
        """
        Retrieve an invoice by ID from QuickBooks.

        Args:
            realm_id (str): The realm ID of the company.
            invoice_id (str): The ID of the invoice to retrieve.

        Returns:
            dict: The response from the QuickBooks API.
        """
        endpoint = f"{realm_id}/invoice/{invoice_id}"
        try:
            current_app.logger.info(f"Retrieving invoice with ID: {invoice_id}")
            response = self.make_request(endpoint, method="GET")
            current_app.logger.info(f"Invoice retrieved successfully: {response}")
            return response
        except Exception as e:
            current_app.logger.error(f"Error retrieving invoice: {str(e)}")
            # Return a structured error response instead of a string
            return {
                "Fault": {
                    "Error": [
                        {
                            "Message": f"Error retrieving invoice: {str(e)}",
                            "Detail": traceback.format_exc()
                        }
                    ]
                }
            }
    def get_invoice_as_pdf(self, realm_id, invoice_id):
        """
        Retrieve an invoice as a PDF file from QuickBooks.
        Args:
            realm_id (str): The realm ID of the company.
            invoice_id (str): The ID of the invoice to retrieve as PDF.
        Returns:
            bytes: The PDF content of the invoice.
        """
        endpoint = f"{realm_id}/invoice/{invoice_id}/pdf"
        try:
            current_app.logger.info(f"Retrieving invoice {invoice_id} as PDF")
            response = self.make_request(endpoint, method="GET")
            if response.status_code == 200:
                current_app.logger.info("Invoice PDF retrieved successfully")
                return response.content  # Return the raw PDF content
            else:
                current_app.logger.error(f"Failed to retrieve invoice PDF: {response.status_code} {response.text}")
                raise Exception(f"Failed to retrieve invoice PDF: {response.status_code} {response.text}")
        except Exception as e:
            current_app.logger.error(f"Error retrieving invoice PDF: {str(e)}")
            # Return a structured error response instead of a string
            return {
                "Fault": {
                    "Error": [
                        {
                            "Message": f"Error retrieving invoice PDF: {str(e)}",
                            "Detail": traceback.format_exc()
                        }
                    ]
                }
            }

    def delete_invoice(self, realm_id, invoice_id):
        """
        Delete an invoice by ID from QuickBooks.

        Args:
            realm_id (str): The realm ID of the company.
            invoice_id (str): The ID of the invoice to delete.

        Returns:
            dict: The response from the QuickBooks API.
        """
        endpoint = f"{realm_id}/invoice/{invoice_id}"
        try:
            current_app.logger.info(f"Deleting invoice with ID: {invoice_id}")
            response = self.make_request(endpoint, method="DELETE")
            current_app.logger.info(f"Invoice deleted successfully: {response}")
            return response
        except Exception as e:
            current_app.logger.error(f"Error deleting invoice: {str(e)}")
            # Return a structured error response instead of a string
            return {
                "Fault": {
                    "Error": [
                        {
                            "Message": f"Error deleting invoice: {str(e)}",
                            "Detail": traceback.format_exc()
                        }
                    ]
                }
            }

    def void_invoice(self, realm_id, invoice_id):
        """
        Void an invoice by ID from QuickBooks.

        Args:
            realm_id (str): The realm ID of the company.
            invoice_id (str): The ID of the invoice to void.

        Returns:
            dict: The response from the QuickBooks API.
        """
        endpoint = f"{realm_id}/invoice/{invoice_id}/void"
        try:
            current_app.logger.info(f"Voiding invoice with ID: {invoice_id}")
            response = self.make_request(endpoint, method="POST")
            current_app.logger.info(f"Invoice voided successfully: {response}")
            return response
        except Exception as e:
            current_app.logger.error(f"Error voiding invoice: {str(e)}")
            # Return a structured error response instead of a string
            return {
                "Fault": {
                    "Error": [
                        {
                            "Message": f"Error voiding invoice: {str(e)}",
                            "Detail": traceback.format_exc()
                        }
                    ]
                }
            }
    
    def send_invoice_to_supplied_email(self, realm_id, invoice_id):
        """
        Send an invoice via email in QuickBooks supplied in the invoice.
        
        description: 
        This endpoint will send an invoice to email specified in the invoice object.

        args:
        realm_id(str): The realID of the company.
        invoice_id: The invoice ID.
        """
        endpoint = f"{realId}/invoice/{invoiceId}/send"
        try:
            current_app.logger.info(f"Voiding invoice with ID: {invoice_id}")
            response = self.make_request(endpoint, method="POST")
            current_app.logger.info(f"Invoice voided successfully: {response}")
            return response
        except Exception as e:
            current_app.logger.error(f"Error voiding invoice: {str(e)}")
            # Return a structured error response instead of a string
            return {
                "Fault": {
                    "Error": [
                        {
                            "Message": f"Error voiding invoice: {str(e)}",
                            "Detail": traceback.format_exc()
                        }
                    ]
                }
            }

    def send_invoice_to_a_given_email(self, realm_id, invoice_id, email):
        """ send an invoice to the given email address.
        Args:
            realm_id (str): The realm ID of the company.
            invoice_id (str): The ID of the invoice to send.
            email (str): The email address to send the invoice to.
        Returns:
            dict: The response from the QuickBooks API.
        """
        endpoint = f"{realm_id}/invoice/{invoice_id}/send?sendto={email}"
        try:
            current_app.logger.info(f"Sending invoice {invoice_id} to email: {email}")
            response = self.make_request(endpoint, method="POST")
            if response.status_code == 200:
                current_app.logger.info("Invoice sent successfully")
                return response.json()
            else:
                current_app.logger.error(f"Failed to send invoice: {response.status_code} {response.text}")
                raise Exception(f"Failed to send invoice: {response.status_code} {response.text}")
        except Exception as e:
            current_app.logger.error(f"Error sending invoice: {str(e)}")
            # Return a structured error response instead of a string
            return {
                "Fault": {
                    "Error": [
                        {
                            "Message": f"Error sending invoice: {str(e)}",
                            "Detail": traceback.format_exc()
                        }
                    ]
                }
            }

    def sparse_invoice_update(self, realm_id, invoice_id, update_data):
        """
        Update an invoice with sparse data in QuickBooks.

        Args:
            realm_id (str): The realm ID of the company.
            invoice_id (str): The ID of the invoice to update.
            update_data (dict): The sparse data to update in the invoice.

        Returns:
            dict: The response from the QuickBooks API.
        """
        endpoint = f"{realm_id}/invoice/{invoice_id}"
        try:
            current_app.logger.info(f"Updating invoice {invoice_id} with data: {update_data}")
            response = self.make_request(endpoint, method="POST", data=update_data)
            current_app.logger.info(f"Invoice updated successfully: {response}")
            return response
        except Exception as e:
            current_app.logger.error(f"Error updating invoice: {str(e)}")
            # Return a structured error response instead of a string
            return {
                "Fault": {
                    "Error": [
                        {
                            "Message": f"Error updating invoice: {str(e)}",
                            "Detail": traceback.format_exc()
                        }
                    ]
                }
            }

    def full_update_invoice(self, realm_id, invoice_id, full_data):
        """
        Update an invoice with full data in QuickBooks.
        Args:
            realm_id (str): The realm ID of the company.
            invoice_id (str): The ID of the invoice to update.
            full_data (dict): The full data to update in the invoice.
        Returns:
            dict: The response from the QuickBooks API.
        """
        endpoint = f"{realm_id}/invoice/{invoice_id}"
        try:
            current_app.logger.info(f"Updating invoice {invoice_id} with full data: {full_data}")
            response = self.make_request(endpoint, method="POST", data=full_data)
            current_app.logger.info(f"Invoice updated successfully: {response}")
            return response
        except Exception as e:
            current_app.logger.error(f"Error updating invoice: {str(e)}")
            # Return a structured error response instead of a string
            return {
                "Fault": {
                    "Error": [
                        {
                            "Message": f"Error updating invoice: {str(e)}",
                            "Detail": traceback.format_exc()
                        }
                    ]
                }
            }
    def create_payment(self, realm_id, payment_data):
        """
        Create a payment in QuickBooks.

        Args:
            realm_id (str): The realm ID of the company.
            payment_data (dict): The data for the payment.

        Returns:
            dict: The response from the QuickBooks API.
        """
        endpoint = f"{realm_id}/payment"
        try:
            current_app.logger.info(f"Creating payment with data: {payment_data}")
            response = self.make_request(endpoint, method="POST", data=payment_data)
            current_app.logger.info(f"Payment created successfully: {response}")
            return response
        except Exception as e:
            current_app.logger.error(f"Error creating payment: {str(e)}")
            # Return a structured error response instead of a string
            return {
                "Fault": {
                    "Error": [
                        {
                            "Message": f"Error creating payment: {str(e)}",
                            "Detail": traceback.format_exc()
                        }
                    ]
                }
            }
    def delete_payment(self, realm_id, payment_id):
        """
        Delete a payment by ID from QuickBooks.

        Args:
            realm_id (str): The realm ID of the company.
            payment_id (str): The ID of the payment to delete.

        Returns:
            dict: The response from the QuickBooks API.
        """
        endpoint = f"{realm_id}/payment/{payment_id}"
        try:
            current_app.logger.info(f"Deleting payment with ID: {payment_id}")
            response = self.make_request(endpoint, method="DELETE")
            current_app.logger.info(f"Payment deleted successfully: {response}")
            return response
        except Exception as e:
            current_app.logger.error(f"Error deleting payment: {str(e)}")
            # Return a structured error response instead of a string
            return {
                "Fault": {
                    "Error": [
                        {
                            "Message": f"Error deleting payment: {str(e)}",
                            "Detail": traceback.format_exc()
                        }
                    ]
                }
            }
    def get_payment(self, realm_id, payment_id):
        """
        Retrieve a payment by ID from QuickBooks.

        Args:
            realm_id (str): The realm ID of the company.
            payment_id (str): The ID of the payment to retrieve.

        Returns:
            dict: The response from the QuickBooks API.
        """
        endpoint = f"{realm_id}/payment/{payment_id}"
        try:
            current_app.logger.info(f"Retrieving payment with ID: {payment_id}")
            response = self.make_request(endpoint, method="GET")
            current_app.logger.info(f"Payment retrieved successfully: {response}")
            return response
        except Exception as e:
            current_app.logger.error(f"Error retrieving payment: {str(e)}")
            # Return a structured error response instead of a string
            return {
                "Fault": {
                    "Error": [
                        {
                            "Message": f"Error retrieving payment: {str(e)}",
                            "Detail": traceback.format_exc()
                        }
                    ]
                }
            }

    def void_payment(self, realm_id, payment_id):
        """
        Void a payment by ID from QuickBooks.

        Args:
            realm_id (str): The realm ID of the company.
            payment_id (str): The ID of the payment to void.

        Returns:
            dict: The response from the QuickBooks API.
        """
        endpoint = f"{realm_id}/payment/{payment_id}/void"
        try:
            current_app.logger.info(f"Voiding payment with ID: {payment_id}")
            response = self.make_request(endpoint, method="POST")
            current_app.logger.info(f"Payment voided successfully: {response}")
            return response
        except Exception as e:
            current_app.logger.error(f"Error voiding payment: {str(e)}")
            # Return a structured error response instead of a string
            return {
                "Fault": {
                    "Error": [
                        {
                            "Message": f"Error voiding payment: {str(e)}",
                            "Detail": traceback.format_exc()
                        }
                    ]
                }
            }

    def get_payment_as_pdf(self, realm_id, payment_id):
        """
        Retrieve a payment as a PDF file from QuickBooks.

        Args:
            realm_id (str): The realm ID of the company.
            payment_id (str): The ID of the payment to retrieve as PDF.

        Returns:
            bytes: The PDF content of the payment.
        """
        endpoint = f"{realm_id}/payment/{payment_id}/pdf"
        try:
            current_app.logger.info(f"Retrieving payment {payment_id} as PDF")
            response = self.make_request(endpoint, method="GET")
            if response.status_code == 200:
                current_app.logger.info("Payment PDF retrieved successfully")
                return response.content  # Return the raw PDF content
            else:
                current_app.logger.error(f"Failed to retrieve payment PDF: {response.status_code} {response.text}")
                raise Exception(f"Failed to retrieve payment PDF: {response.status_code} {response.text}")
        except Exception as e:
            current_app.logger.error(f"Error retrieving payment PDF: {str(e)}")
            # Return a structured error response instead of a string
            return {
                "Fault": {
                    "Error": [
                        {
                            "Message": f"Error retrieving payment PDF: {str(e)}",
                            "Detail": traceback.format_exc()
                        }
                    ]
                }
            }

    def read_payment_details(self, realm_id, payment_id):
        """
        Read the details of a payment by ID from QuickBooks.

        Args:
            realm_id (str): The realm ID of the company.
            payment_id (str): The ID of the payment to read.

        Returns:
            dict: The response from the QuickBooks API.
        """
        endpoint = f"{realm_id}/payment/{payment_id}"
        try:
            current_app.logger.info(f"Reading payment details with ID: {payment_id}")
            response = self.make_request(endpoint, method="GET")
            current_app.logger.info(f"Payment details retrieved successfully: {response}")
            return response
        except Exception as e:
            current_app.logger.error(f"Error reading payment details: {str(e)}")
            # Return a structured error response instead of a string
            return {
                "Fault": {
                    "Error": [
                        {
                            "Message": f"Error reading payment details: {str(e)}",
                            "Detail": traceback.format_exc()
                        }
                    ]
                }
            }

    def send_payment(self, realm_id, payment_id, email):
        """
        Send a payment via email in QuickBooks.

        Args:
            realm_id (str): The realm ID of the company.
            payment_id (str): The ID of the payment to send.
            email (str): The email address to send the payment to.

        Returns:
            dict: The response from the QuickBooks API.
        """
        endpoint = f"{realm_id}/payment/{payment_id}/send?sendto={email}"
        try:
            current_app.logger.info(f"Sending payment {payment_id} to email: {email}")
            response = self.make_request(endpoint, method="POST")
            if response.status_code == 200:
                current_app.logger.info("Payment sent successfully")
                return response.json()
            else:
                current_app.logger.error(f"Failed to send payment: {response.status_code} {response.text}")
                raise Exception(f"Failed to send payment: {response.status_code} {response.text}")
        except Exception as e:
            current_app.logger.error(f"Error sending payment: {str(e)}")
            # Return a structured error response instead of a string
            return {
                "Fault": {
                    "Error": [
                        {
                            "Message": f"Error sending payment: {str(e)}",
                            "Detail": traceback.format_exc()
                        }
                    ]
                }
            }

    def update_payment(self, realm_id, payment_id, update_data):
        """
        Update a payment with sparse data in QuickBooks.

        Args:
            realm_id (str): The realm ID of the company.
            payment_id (str): The ID of the payment to update.
            update_data (dict): The sparse data to update in the payment.

        Returns:
            dict: The response from the QuickBooks API.
        """
        endpoint = f"{realm_id}/payment/{payment_id}"
        try:
            current_app.logger.info(f"Updating payment {payment_id} with data: {update_data}")
            response = self.make_request(endpoint, method="POST", data=update_data)
            current_app.logger.info(f"Payment updated successfully: {response}")
            return response
        except Exception as e:
            current_app.logger.error(f"Error updating payment: {str(e)}")
            # Return a structured error response instead of a string
            return {
                "Fault": {
                    "Error": [
                        {
                            "Message": f"Error updating payment: {str(e)}",
                            "Detail": traceback.format_exc()
                        }
                    ]
                }
            } 

        


if __name__ == "__main__":
    # Import Flask app factory to create application context
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    from application import create_app

    # Create Flask app context for standalone testing
    app = create_app('development')

    with app.app_context():
        # Load all QuickBooks configuration from .env
        client_id = os.getenv("QUICK_BOOKS_CLIENT_ID")
        client_secret = os.getenv("QUICK_BOOKS_SECRET")
        redirect_uri = os.getenv("QUICK_BOOKS_REDIRECT_URI", "https://www.netpipo.com")
        access_token = os.getenv("QUICK_BOOKS_ACCESS_TOKEN")
        refresh_token = os.getenv("QUICK_BOOKS_REFRESH_TOKEN")
        authorization_code = os.getenv("QUICK_BOOKS_AUTHORIZATION_CODE")
        realm_id = os.getenv("QUICK_BOOKS_REALM_ID")
        api_base_url = os.getenv("QUICK_BOOKS_BASEURL_SANDBOX")

        print("📋 QuickBooks Configuration from .env:")
        print(f"client_id: {client_id}")
        print(f"client_secret: {client_secret}")
        print(f"redirect_uri: {redirect_uri}")
        print(f"access_token: {access_token[:10] + '...' if access_token else 'None'}")
        print(f"refresh_token: {refresh_token[:10] + '...' if refresh_token else 'None'}")
        print(f"authorization_code: {authorization_code[:10] + '...' if authorization_code else 'None'}")
        print(f"realm_id: {realm_id}")
        print(f"api_base_url: {api_base_url}")

        # Validate required environment variables
        required_vars = {
            'QUICK_BOOKS_CLIENT_ID': client_id,
            'QUICK_BOOKS_SECRET': client_secret,
            'QUICK_BOOKS_REALM_ID': realm_id
        }

        missing_vars = [var for var, value in required_vars.items() if not value]
        if missing_vars:
            print(f"❌ Missing required environment variables: {', '.join(missing_vars)}")
            return

        # Generate Fernet key if not provided
        fernet_key = os.getenv("FERNET_KEY")
        if not fernet_key:
            from cryptography.fernet import Fernet
            fernet_key = Fernet.generate_key().decode()
            print(f"⚠️  Generated Fernet key (add to .env): FERNET_KEY={fernet_key}")
            os.environ["FERNET_KEY"] = fernet_key

        # Populate database with .env configuration
        print("\n🔄 Populating database with .env configuration...")
        try:
            from application.models.central_models import QuickBooksConfig
            from application.helpers.quickbooks_helpers import QuickBooksHelper
            from application import db

            # Get or create config
            config = QuickBooksConfig.get_config()
            if not config:
                config = QuickBooksConfig()
                print("📝 Creating new QuickBooks configuration...")
            else:
                print("� Updating existing QuickBooks configuration...")

            # Encrypt and store tokens if provided
            if access_token:
                config.access_token = QuickBooksHelper.encrypt(access_token)
                print("✅ Access token encrypted and stored")

            if refresh_token:
                config.refresh_token = QuickBooksHelper.encrypt(refresh_token)
                print("✅ Refresh token encrypted and stored")

            if authorization_code:
                config.authorization_code = QuickBooksHelper.encrypt(authorization_code)
                print("✅ Authorization code encrypted and stored")

            # Store realm_id and set active
            config.realm_id = realm_id
            config.is_active = True

            # Save to database
            db.session.add(config)
            db.session.commit()
            print("✅ Database updated successfully!")

        except Exception as e:
            print(f"❌ Error populating database: {e}")
            return

        # Initialize QuickBooks client (will now load from database)
        try:
            qb = QuickBooks()
            print(f"✅ QuickBooks client created and loaded from database")
            print(f"   - Realm ID: {qb.realm_id}")
            print(f"   - Has access token: {bool(qb.access_token)}")
            print(f"   - Has refresh token: {bool(qb.refresh_token)}")
        except Exception as e:
            print(f"❌ Error creating QuickBooks client: {e}")
            return

        # Test the configuration
        print("\n🧪 Testing QuickBooks API connection...")
        try:
            # If we have an access token, try a direct API call
            if qb.access_token:
                print("� Testing with existing access token...")
                accounts = qb.get_account_types(qb.realm_id)
                print(f"✅ API test successful! Retrieved {len(accounts) if accounts else 0} account types")

            # If we only have refresh token, try to refresh first
            elif qb.refresh_token:
                print("🔄 No access token found, attempting token refresh...")
                tokens = qb.refresh_access_token()
                print("✅ Token refresh successful!")

                # Now test API
                accounts = qb.get_account_types(qb.realm_id)
                print(f"✅ API test successful! Retrieved {len(accounts) if accounts else 0} account types")

            else:
                print("⚠️  No tokens available for testing")

        except Exception as e:
            print(f"❌ API test failed: {e}")
            if "401" in str(e) or "authentication" in str(e).lower():
                print("💡 Tokens may be expired. Please update your .env with fresh tokens.")

        print("\n🎉 Script completed!")

        """try:
            # Get company info
            company_info = qb.get_company_info(realm_id)
            print(f"Company Info: {company_info}")
            company_name = company_info["CompanyInfo"]["CompanyName"]
            print(f"Company Name: {company_name}")
            address = company_info["CompanyInfo"]["CompanyAddr"]
            print(f"Company Address: {address}")
        except Exception as e:
            print("Error:", str(e))
        """

        if qb:
            # Get account types
            try:
                accounts = qb.get_account_types(qb.realm_id)
                print(f"Account types: {accounts}")
            except Exception as e:
                print("Error:", str(e))