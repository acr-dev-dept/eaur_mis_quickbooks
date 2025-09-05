# QuickBooks Service — application/services/quickbooks.py

## Purpose

This document explains the `QuickBooks` service implemented in `application/services/quickbooks.py`.

High-level: the `QuickBooks` class wraps QuickBooks Online API interaction for the EAUR system. It handles OAuth2 token exchange/refresh, basic request wiring, and a variety of convenience methods for common QuickBooks resources (customers, invoices, payments, accounts, vendors, departments/classes, locations/departments, journal entries, etc.).

## Key responsibilities

- Read QuickBooks configuration stored in the database (`QuickBooksConfig` in `application.models.central_models`).
- Load client credentials and base API URL from environment variables.
- Manage OAuth2 tokens: exchange authorization code, refresh tokens, and revoke tokens (disconnect).
- Make API calls to QuickBooks with automatic token refresh on 401 responses.
- Provide CRUD convenience methods for many QuickBooks endpoints (customers, invoices, payments, accounts, vendors, journal entries).
- Expose a small CLI block (if run directly) to populate the database from `.env` and run a basic API smoke test.

## Important dependencies

- requests — HTTP client used for all API calls.
- python-dotenv (`load_dotenv`) — to load `.env` values when running standalone.
- Flask `current_app` — used for logging and expect to run inside a Flask application context.
- `QuickBooksHelper` (from `application.helpers.quickbooks_helpers`) — used to encrypt/decrypt tokens stored in DB.
- `QuickBooksConfig` model (from `application.models.central_models`) — persistent store for tokens and realm id.
- cryptography (indirectly) — used by `QuickBooksHelper` for encryption (FERNET_KEY env var).

## Environment variables used

- QUICK_BOOKS_CLIENT_ID
- QUICK_BOOKS_SECRET
- QUICK_BOOKS_REDIRECT_URI
- QUICK_BOOKS_BASEURL_SANDBOX (API base URL)
- FERNET_KEY (used to encrypt/decrypt tokens)
- Optional development tokens used by the CLI block:
  - QUICK_BOOKS_ACCESS_TOKEN
  - QUICK_BOOKS_REFRESH_TOKEN
  - QUICK_BOOKS_AUTHORIZATION_CODE
  - QUICK_BOOKS_REALM_ID

## Class overview and method contracts

All methods assume you're running inside a Flask app context (they call `current_app.logger`).

Constructor: QuickBooks.__init__()
- Inputs: None
- Behavior: loads `QuickBooksConfig.get_config()` and decrypts `access_token` and `refresh_token` (via `QuickBooksHelper`) if present, sets `realm_id` and fields from env.
- Side effects: sets instance attributes (`access_token`, `refresh_token`, `realm_id`, `client_id`, `client_secret`, `redirect_uri`, `api_base_url`).

Authentication helpers:
- _get_auth_header()
  - Returns Basic Authorization header for token endpoint using client id/secret.
- get_quickbooks_access_token(code)
  - Exchanges an authorization `code` for access and refresh tokens.
  - Stores encrypted tokens in DB via `QuickBooksConfig.update_config`.
  - Returns token response dict from QuickBooks.
- refresh_access_token()
  - Uses the stored refresh token to obtain new tokens from QuickBooks token endpoint.
  - Updates DB with encrypted tokens.
  - Returns token response dict.
- disconnect_app()
  - Attempts to revoke tokens at QuickBooks revoke endpoint.
  - Regardless of revoke success, clears tokens/authorization data in DB (set to None and is_active=False).
  - Returns True on success or raises on DB update failure.

Core HTTP helper:
- make_request(endpoint, method="GET", data=None, params=None)
  - Builds request URL as `api_base_url + '/' + endpoint`.
  - Ensures there is an access token available; if missing it attempts refresh using stored refresh token.
  - Adds Authorization: Bearer <access_token>, Accept/Content-Type headers.
  - Supports GET/POST/PUT (others raise ValueError).
  - On initial 401 responses that indicate token expiration, it calls `refresh_access_token()` and retries the request once.
  - On success returns `response.json()` for 200/201; on failure logs tokens and raises Exception.

Resource convenience methods (common signatures):
- get_company_info(realm_id)
- create_customer(realm_id, customer_data)
- get_customers(realm_id, params=None)
- update_customer(realm_id, customer_id, customer_data)
- get_customer(realm_id, customer_id)
- get_invoices(realm_id, params=None)
- get_payments(realm_id, params=None)
- get_accounts(realm_id)
- get_vendors(realm_id, params=None)
- get_departments(realm_id)  # maps to Class in QuickBooks
- get_locations(realm_id)    # maps to Department in QuickBooks
- create_journal_entry(realm_id, journal_entry_data)
- create_account(realm_id, account_data)
- get_account_types(realm_id)  # convenience: returns normalized unique AccountType/AccountSubType list
- get_authorization_url(state, scopes)
- create_invoice(realm_id, invoice_data)
- get_invoice(realm_id, invoice_id)
- get_invoice_as_pdf(realm_id, invoice_id)
- delete_invoice(realm_id, invoice_id)
- void_invoice(realm_id, invoice_id)
- send_invoice_to_supplied_email(realm_id, invoice_id)  # NOTE: contains bugs (see Known issues)
- send_invoice_to_a_given_email(realm_id, invoice_id, email)
- sparse_invoice_update(realm_id, invoice_id, update_data)
- full_update_invoice(realm_id, invoice_id, full_data)
- create_payment(realm_id, payment_data)
- delete_payment(realm_id, payment_id)
- get_payment(realm_id, payment_id)
- void_payment(realm_id, payment_id)
- get_payment_as_pdf(realm_id, payment_id)
- read_payment_details(realm_id, payment_id)
- send_payment(realm_id, payment_id, email)
- update_payment(realm_id, payment_id, update_data)

Return shapes:
- Most success flows return the parsed JSON (dict) from QuickBooks API (`response.json()`), or a structured error dict under a `Fault` key when exceptions are caught.
- `make_request` returns `response.json()` on success but several higher-level methods incorrectly expect the `requests.Response` object (see Known issues).

## Known issues and inconsistencies (important to read before editing/using)

1. make_request returns parsed JSON (`dict`) on success. Several methods (for example `get_invoice_as_pdf`, `get_payment_as_pdf`, `send_invoice_to_a_given_email`, `send_payment`) assume `make_request` returns a `requests.Response` object and access `response.status_code`, `response.content` or `response.text`. This is inconsistent and can cause attribute errors. Fix by either:
   - Changing `make_request` to return the raw `requests.Response` object for non-JSON endpoints (PDF endpoints), or
   - Having PDF/send methods call `requests` directly when they need raw response content/status, or
   - Add an optional parameter to `make_request` (e.g., `raw_response=False`) to return response object.

2. `send_invoice_to_supplied_email` contains a clear bug: it uses undefined variables `realId` and `invoiceId` (note different casing) when building `endpoint`. Should use `realm_id` and `invoice_id`. Also method logging messages refer to "Voiding invoice" likely copy/paste errors.

3. `send_invoice_to_a_given_email` appends the `email` to the endpoint query string without URL-encoding; this may break for emails with special characters. Use `urllib.parse.quote_plus(email)`.

4. Some methods return strings like "Error creating account" or a structured `Fault` dict. Standardize on returning structured errors (dict) or raising exceptions consistently.

5. Token logging currently logs partial tokens to app logs. Avoid logging tokens in production; redaction or safer logs are recommended.

6. The authorization and token endpoint URLs use sandbox/prod env vars indirectly; verify `QUICK_BOOKS_BASEURL_SANDBOX` is set correctly for the environment.

7. Thread-safety: the instance stores tokens on `self` and updates them during refresh. If the same QuickBooks instance is used across threads (or multiple Flask requests) you may have race conditions. Consider making token refresh locked or refreshing via a central store (DB) and reloading from DB every request.

8. `get_account_types` prints account types and uses `.title()` which may produce unexpected capitalization for subtypes; it's minor but worth noting.

## Usage example (inside Flask app context)

1. Ensure Flask app context is active (e.g., inside request handling or `with app.app_context():`).
2. Instantiate and call:

```python
from application.services.quickbooks import QuickBooks

qb = QuickBooks()
realm_id = qb.realm_id  # or pass an explicit realm_id

# Get invoices
invoices = qb.get_invoices(realm_id, params={'customerRef': '123'})

# Create an invoice
invoice_data = { /* QuickBooks invoice JSON payload */ }
created = qb.create_invoice(realm_id, invoice_data)
```

Notes: many methods require `realm_id` — the QuickBooks company id — which is stored in `QuickBooksConfig` and set on the QuickBooks instance at init.

## Quick start checklist (to get running locally)

- [ ] Activate your Python virtualenv for the project.
- [ ] Install requirements from `requirements.txt` (ensure `requests`, `python-dotenv`, `cryptography` are included). If not present:
  - pip install requests python-dotenv cryptography
- [ ] Set required env vars in `.env`:
  - QUICK_BOOKS_CLIENT_ID, QUICK_BOOKS_SECRET, QUICK_BOOKS_REDIRECT_URI
  - QUICK_BOOKS_BASEURL_SANDBOX (set to QuickBooks base URL for sandbox or production as appropriate)
  - FERNET_KEY (if not present, the module's CLI block can generate one for you)
- [ ] Populate DB `QuickBooksConfig` with encrypted tokens (you can run `application/services/quickbooks.py` directly in a Flask app context or use the web UI endpoints that exist in the API layer).
- [ ] Use the service within a Flask app context so `current_app` logging works.

## Suggested immediate fixes (low risk)

- Fix `send_invoice_to_supplied_email` variable names (use `realm_id` and `invoice_id`) and logging messages.
- Update `make_request` to support a `raw_response` flag, or update PDF/send endpoints to call `requests` directly when raw body/status is required.
- URL-encode query parameters like the `email` parameter in `send_invoice_to_a_given_email`.
- Standardize error handling: choose between raising exceptions or returning structured error dicts and apply consistently.
- Reduce token logging or redact tokens before writing to logs.

## Recommended next steps (medium effort)

- Add unit tests for:
  - Token refresh flow (mock QuickBooks token endpoint)
  - make_request retry on 401
  - PDF endpoints returning binary content
- Consider extracting a small adapter layer that handles raw HTTP calls vs parsed JSON responses.
- Add thread-safety (lock on refresh) or re-read tokens from DB before requests.

## Where to look in the code

- Token storage and DB interactions: `application/models/central_models.py` (search for `QuickBooksConfig`).
- Token encrypt/decrypt functions: `application/helpers/quickbooks_helpers.py`.
- API endpoints that use this service: `application/api/v1/quickbooks.py`.

## File created

- `documentation/QUICKBOOKS_SERVICE.md` — this file (purpose: explain `application/services/quickbooks.py`, list methods, usage, known issues and next steps).

## Requirements coverage

- Generate a .md explaining the file: Done — `documentation/QUICKBOOKS_SERVICE.md` created and contains purpose, methods, env vars, examples, known issues, and next steps.

If you'd like, I can also:
- Create a small unit-test harness that tests `make_request` behavior (mocking `requests`) to demonstrate the 401->refresh->retry flow.
- Make the low-risk edits to fix the `send_invoice_to_supplied_email` bug and normalize `make_request` return behavior.

