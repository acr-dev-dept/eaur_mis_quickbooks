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
    def __init__(self, company_id):
        """
        Initialize the QuickBooks client with the company ID.
        Args:
            company_id (str): The ID of the company to connect to.
        """
        from application.models.central_models import Company
        from flask import current_app

        current_app.logger.info(f"Initializing QuickBooks client for company ID: {company_id}")

        self.company = Company.query.get(company_id)
        if not self.company:
            current_app.logger.error(f"Company with ID {company_id} not found")
            raise ValueError("Company not found")

        self.client_id = os.getenv("QUICK_BOOKS_CLIENT_ID")
        self.client_secret = os.getenv("QUICK_BOOKS_SECRET")
        self.redirect_uri = os.getenv("QUICK_BOOKS_REDIRECT_URI")
        self.api_base_url = os.getenv("QUICK_BOOKS_BASEURL_SANDBOX")

        # Log the encrypted tokens from the database
        current_app.logger.info(f"Encrypted refresh token from DB: {self.company.quickbooks_refresh_token}")
        current_app.logger.info(f"Encrypted access token from DB: {self.company.quickbooks_access_token}")

        # Decrypt and store tokens
        try:
            if self.company.quickbooks_refresh_token:
                self.refresh_token = QuickBooksHelper.decrypt(self.company.quickbooks_refresh_token)
                current_app.logger.info(f"Decrypted refresh token: {self.refresh_token}")
            else:
                current_app.logger.warning("No refresh token found in database")
                self.refresh_token = None

            if self.company.quickbooks_access_token:
                self.access_token = QuickBooksHelper.decrypt(self.company.quickbooks_access_token)
                current_app.logger.info(f"Decrypted access token (first 10 chars): {self.access_token[:10] if self.access_token else None}...")
            else:
                current_app.logger.warning("No access token found in database")
                self.access_token = None
        except Exception as e:
            current_app.logger.error(f"Error decrypting tokens: {str(e)}")
            current_app.logger.error(f"Error details: {str(e)}")
            self.refresh_token = None
            self.access_token = None

        self.realm_id = self.company.quickbooks_realm_id
        current_app.logger.info(f"Realm ID: {self.realm_id}")

        self.token_url = "https://oauth.platform.intuit.com/oauth2/v1/tokens/bearer"
        self.database_name = self.company.database_name

        current_app.logger.info(f"QuickBooks client initialized successfully for company: {self.company.company_name}")

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
            # Update the company's access and refresh tokens in the database
            try:
                result = self.company.update_company_data(
                    self.company.company_id,
                    quickbooks_access_token=QuickBooksHelper.encrypt(self.access_token),
                    quickbooks_refresh_token=QuickBooksHelper.encrypt(self.refresh_token)
                )
                if result:
                    current_app.logger.info("Company data updated successfully.")
                else:
                    current_app.logger.error("Failed to update company data.")
            except Exception as e:
                current_app.logger.error(f"Error updating company data: {e}")
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

            # Update the company's access and refresh tokens in the database
            try:
                encrypted_access_token = QuickBooksHelper.encrypt(self.access_token)
                encrypted_refresh_token = QuickBooksHelper.encrypt(self.refresh_token)

                current_app.logger.info(f"Encrypted access token: {encrypted_access_token[:10]}...")
                current_app.logger.info(f"Encrypted refresh token: {encrypted_refresh_token}")
                current_app.logger.info(f"Updating company ID: {self.company.company_id}")

                result = self.company.update_company_data(
                    self.company.company_id,
                    quickbooks_access_token=encrypted_access_token,
                    quickbooks_refresh_token=encrypted_refresh_token
                )

                if result:
                    current_app.logger.info("Company data updated successfully with new tokens.")
                    # Verify the update by retrieving the company again
                    from application.models.central_models import Company
                    updated_company = Company.query.get(self.company.company_id)
                    if updated_company:
                        current_app.logger.info(f"Verified company update. New refresh token in DB: {updated_company.quickbooks_refresh_token}")
                    else:
                        current_app.logger.error("Could not verify company update - company not found")
                else:
                    current_app.logger.error("Failed to update company data with new tokens.")
            except Exception as e:
                current_app.logger.error(f"Error updating company data: {e}")
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
        current_app.logger.info(f"Company ID: {self.company.company_id}")
        current_app.logger.info(f"Access token available: {bool(self.access_token)}")
        current_app.logger.info(f"Refresh token available: {bool(self.refresh_token)}")

        token_to_revoke = self.access_token or self.refresh_token

        # If no tokens are available, just clear the database and return success
        if not token_to_revoke:
            current_app.logger.info("No tokens available to revoke. Clearing database records only.")
            result = self.company.update_company_data(
                self.company.company_id,
                quickbooks_access_token=None,
                quickbooks_refresh_token=None,
                quickbooks_authorization_code=None,
                quickbooks_realm_id=None
            )

            if result:
                current_app.logger.info("Successfully cleared QuickBooks data from database (no tokens to revoke).")
                return True
            else:
                current_app.logger.error("Failed to clear QuickBooks data from database.")
                raise Exception("Failed to clear QuickBooks data from database.")

        # If we have tokens, attempt to revoke them with QuickBooks
        revoke_url = "https://developer.api.intuit.com/v2/oauth2/tokens/revoke"

        try:
            auth_header = self._get_auth_header()
        except Exception as e:
            current_app.logger.warning(f"Failed to get auth header for token revocation: {e}. Proceeding with database cleanup only.")
            # If we can't get auth header, just clear the database
            result = self.company.update_company_data(
                self.company.company_id,
                quickbooks_access_token=None,
                quickbooks_refresh_token=None,
                quickbooks_authorization_code=None,
                quickbooks_realm_id=None
            )

            if result:
                current_app.logger.info("Successfully cleared QuickBooks data from database (auth header failed).")
                return True
            else:
                current_app.logger.error("Failed to clear QuickBooks data from database.")
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
        result = self.company.update_company_data(
            self.company.company_id,
            quickbooks_access_token=None,
            quickbooks_refresh_token=None,
            quickbooks_authorization_code=None,
            quickbooks_realm_id=None
        )

        if result:
            current_app.logger.info("Successfully disconnected QuickBooks and cleared all tokens and authorization data.")
            return True
        else:
            current_app.logger.error("Failed to clear QuickBooks data from database after token revocation.")
            raise Exception("Failed to clear QuickBooks data from database.")

if __name__ == "__main__":
    client_id = os.getenv("QUICK_BOOKS_CLIENT_ID")
    client_secret = os.getenv("QUICK_BOOKS_SECRET")
    redirect_uri = "https://www.netpipo.com"
    refresh_token = os.getenv("QUICK_BOOKS_REFRESH_TOKEN")
    realm_id = os.getenv("QUICK_BOOKS_REALM_ID")
    api_base_url = os.getenv("QUICK_BOOKS_BASEURL_SANDBOX")
    print(f"client_id: {client_id}")
    print(f"client_secret: {client_secret}")
    print(f"redirect_uri: {redirect_uri}")
    print(f"refresh_token: {refresh_token}")
    print(f"realm_id: {realm_id}")
    print(f"api_base_url: {api_base_url}")

    try:
        qb = QuickBooks(client_id, client_secret, redirect_uri, api_base_url, refresh_token)
        print(f"QuickBooks client created: {qb}")
    except Exception as e:
        print("Error:", str(e))

    try:
        # Refresh the token
        tokens = qb.refresh_access_token()
        print("tokens:", tokens)
    except Exception as e:
        print("Error:", str(e))

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

    # Get account types

    try:
        accounts = qb.get_account_types(realm_id)
        print(f"Account types: {accounts}")
    except Exception as e:
        print("Error:", str(e))



    # Create an account
    """
    data = {
        "Name": "Net Salary Payable",
        "AccountType": "Accounts Payable",
        "AccountSubType": "AccountsPayable",
        "AcctNum": "1150040002",
        "CurrencyRef": {
            "value": "USD"
        }
    }
    """

    print("Creating account...")
    """
    try:
        account = qb.create_account(realm_id, data)
        print(f"Account: {account}")
    except Exception as e:
        print("Error:", str(e))

        """



    # Create a journal entry
    data = {
    "Line": [
        {
            "JournalEntryLineDetail": {
                "PostingType": "Debit",
                "AccountRef": {
                    "name": "gross salary",
                    "value": "1150040000"
                }
            },
            "DetailType": "JournalEntryLineDetail",
            "Amount": 6577450,
            "Description": "Gross Salary"
        },
        {
            "JournalEntryLineDetail": {
                "PostingType": "Debit",
                "AccountRef": {
                    "name": "Pension  (5%)",
                    "value": "1150040001"
                }
            },
            "DetailType": "JournalEntryLineDetail",
            "Amount": 265971,
            "Description": "Pension Expense"
        },
        {
            "JournalEntryLineDetail": {
                "PostingType": "Debit",
                "AccountRef": {
                    "name": "Maternity Expense (0.3%)",
                    "value": "1150040003"
                }
            },
            "DetailType": "JournalEntryLineDetail",
            "Amount": 15958,
            "Description": "Maternity Expense"
        },
        {
            "JournalEntryLineDetail": {
                "PostingType": "Credit",
                "AccountRef": {
                    "name": "Salary advance",
                    "value": "1150040011"
                },
                "Entity": {
                    "Type": "Vendor",
                    "EntityRef": {
                        "name": "Remmittance LLC",
                        "value": "59"
                    }
                }
            },
            "DetailType": "JournalEntryLineDetail",
            "Amount": 0,
            "Description": "Salary advance"
        },
        {
            "JournalEntryLineDetail": {
                "PostingType": "Credit",
                "AccountRef": {
                    "name": "Net Salary Payable",
                    "value": "1150040012"
                }
            },
            "DetailType": "JournalEntryLineDetail",
            "Amount": 4773169,
            "Description": "Net Salary Payable"
        },
        {
            "JournalEntryLineDetail": {
                "PostingType": "Credit",
                "AccountRef": {
                    "name": "Pension Payable (8%)",
                    "value": "1150040012"
                }
            },
            "DetailType": "JournalEntryLineDetail",
            "Amount": 425553,
            "Description": "Pension Payable"
        },
        {
            "JournalEntryLineDetail": {
                "PostingType": "Credit",
                "AccountRef": {
                    "name": "Medical Contribution Payable",
                    "value": "1150040015"
                },
                "Entity": {
                    "Type": "Vendor",
                    "EntityRef": {
                        "name": "Remmittance LLC",
                        "value": "59"
                    }
                }
            },
            "DetailType": "JournalEntryLineDetail",
            "Amount": 0,
            "Description": "1150040006"
        },
        {
            "JournalEntryLineDetail": {
                "PostingType": "Credit",
                "AccountRef": {
                    "name": "Maternity Payable (0.6%)",
                    "value": "1150040017"
                },
                "Entity": {
                    "Type": "Vendor",
                    "EntityRef": {
                        "name": "Remmittance LLC",
                        "value": "59"
                    }
                }
            },
            "DetailType": "JournalEntryLineDetail",
            "Amount": 31916,
            "Description": "Maternity Payable"
        },
        {
            "JournalEntryLineDetail": {
                "PostingType": "Credit",
                "AccountRef": {
                    "name": "PAYE Payable",
                    "value": "1150040014"
                },
                "Entity": {
                    "Type": "Vendor",
                    "EntityRef": {
                        "name": "Remmittance LLC",
                        "value": "59"
                    }
                }
            },
            "DetailType": "JournalEntryLineDetail",
            "Amount": 1200905,
            "Description": "PAYE Payable"
        },
        {
            "JournalEntryLineDetail": {
                "PostingType": "Credit",
                "AccountRef": {
                    "name": "Other Deductions",
                    "value": "1150040014"
                },
                "Entity": {
                    "Type": "Vendor",
                    "EntityRef": {
                        "name": "Remmittance LLC",
                        "value": "59"
                    }
                }
            },
            "DetailType": "JournalEntryLineDetail",
            "Amount": 401831,
            "Description": "Other Deductions"
        },
        {
            "JournalEntryLineDetail": {
                "PostingType": "Credit",
                "AccountRef": {
                    "name": "CBHI Payable (0.5%)",
                    "value": "1150040016"
                },
                "Entity": {
                    "Type": "Vendor",
                    "EntityRef": {
                        "name": "Remmittance LLC",
                        "value": "59"
                    }
                }
            },
            "DetailType": "JournalEntryLineDetail",
            "Amount": 26005,
            "Description": "CBHI Payable"
        },
        {
            "JournalEntryLineDetail": {
                "PostingType": "Credit",
                "AccountRef": {
                    "name": "Net Salary Payable",
                    "value": "1150040012"
                }
            },
            "DetailType": "JournalEntryLineDetail",
            "Amount": 0,
            "Description": "Net Salary Payable"
        }
    ]
}

    print("Creating journal entry...")

    try:
            journal_entry = qb.create_journal_entry(realm_id, data)
            print(f"Journal Entry: {journal_entry}")
            # Read existing entries, if any
            try:
                with open("journal_entry.json", "r") as f:
                    entries = json.load(f)
            except (FileNotFoundError, json.JSONDecodeError):
                entries = []

            # Add the new entry
            entries.append(journal_entry)

            # Save back to the file
            with open("journal_entry.json", "w") as f:
                json.dump(entries, f, indent=4)

    except Exception as e:
        print("Error:", str(e))