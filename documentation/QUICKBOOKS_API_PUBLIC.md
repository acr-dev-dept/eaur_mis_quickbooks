# QuickBooks Integration API — Public Documentation

This document describes the QuickBooks integration API provided by the EAUR system (service implemented in `application/services/quickbooks.py`). It is written for external developers who need to understand how to authenticate and interact with QuickBooks on behalf of a customer/company connected to EAUR.

Notes:
- This documentation focuses on the QuickBooks-related API surface and patterns used by the service. It is not a full reference for the entire EAUR application.
- All API examples assume you have valid OAuth2 credentials and a `realmId` (QuickBooks company id) for the target QuickBooks company.

**Base Concepts**
- OAuth2: The QuickBooks service uses OAuth2 (authorization code flow) to obtain access and refresh tokens.
- realmId: The QuickBooks company identifier. Many endpoints require `realmId`.
- API base URL: QuickBooks uses different base URLs for sandbox vs production. The service reads the base URL from environment variables.

**Authentication (OAuth2)**
- Grant type: `authorization_code` for initial exchange.
- Token refresh: `refresh_token` grant type used to rotate access tokens.
- Revoke: QuickBooks provides a revocation endpoint to disconnect an app.

Tokens are stored encrypted in the EAUR central database. Tokens are expected to be rotated when QuickBooks returns refreshed tokens.

---

## Authentication endpoints (Intuit OAuth end-points)

These are QuickBooks/Intuit endpoints (the EAUR service calls them):

1) Exchange authorization code (to obtain access & refresh token)

- Endpoint (Intuit): `POST https://oauth.platform.intuit.com/oauth2/v1/tokens/bearer`
- Grant type: `authorization_code`
- Required headers: `Authorization: Basic <base64(client_id:client_secret)>`, `Content-Type: application/x-www-form-urlencoded`
- Request form-data example:

```
grant_type=authorization_code
&code=<AUTHORIZATION_CODE>
&redirect_uri=<REDIRECT_URI>
```

- Successful JSON response includes: `access_token`, `refresh_token`, `expires_in`, `x_refresh_token_expires_in`.

2) Refresh access token

- Endpoint (Intuit): `POST https://oauth.platform.intuit.com/oauth2/v1/tokens/bearer`
- Grant type: `refresh_token`
- Request form-data:

```
grant_type=refresh_token
&refresh_token=<REFRESH_TOKEN>
```

- Successful response: new `access_token`, `refresh_token` (may rotate), and expiry fields.

3) Revoke tokens (disconnect app)

- Endpoint (Intuit): `POST https://developer.api.intuit.com/v2/oauth2/tokens/revoke`
- Required header: `Authorization: Basic <base64(client_id:client_secret)>`
- Form-data: `token=<TOKEN_TO_REVOKE>`

---

## EAUR QuickBooks Service: Public Resource Endpoints

Below are the common resource operations the service performs against QuickBooks. These are the actions you can expect to be available via the service. In many cases the EAUR application exposes HTTP API routes that call these service methods; the examples below show how the service interacts with QuickBooks and include representative request/response shapes.

Common headers required for QuickBooks API calls:
- `Authorization: Bearer <ACCESS_TOKEN>`
- `Accept: application/json`
- `Content-Type: application/json`

### 1) Invoices

- Get invoices (query/list)
  - QuickBooks endpoint: `GET /v3/company/<realmId>/query?query=SELECT%20*%20FROM%20Invoice%20MAXRESULTS%201000`
  - Use-case: list invoices, optionally with WHERE clause (by customerRef, TxnDate range, etc.)
  - Example Curl:

```
curl -H "Authorization: Bearer <ACCESS_TOKEN>" \
  "https://<QB_BASE>/v3/company/<realmId>/query?query=SELECT%20*%20FROM%20Invoice%20MAXRESULTS%201000"
```

- Create invoice
  - QuickBooks endpoint: `POST /v3/company/<realmId>/invoice`
  - Body: QuickBooks Invoice JSON. Minimal example:

```json
{
  "Line": [
    {
      "Amount": 100.00,
      "DetailType": "SalesItemLineDetail",
      "SalesItemLineDetail": { "ItemRef": { "value": "1" } }
    }
  ],
  "CustomerRef": { "value": "123" }
}
```

- Get invoice PDF
  - QuickBooks endpoint: `GET /v3/company/<realmId>/invoice/<invoiceId>/pdf`
  - Returns: binary PDF data. The EAUR service will fetch the raw response body (not JSON) and forward it to the caller.

- Send invoice (email)
  - QuickBooks endpoint (send): `POST /v3/company/<realmId>/invoice/<invoiceId>/send?sendTo=<email>` or a documented "send" path per QuickBooks docs.
  - Note: Email must be URL-encoded; response may be JSON or 204 depending on API.

- Delete or Void invoice
  - Delete: `DELETE /v3/company/<realmId>/invoice/<invoiceId>`
  - Void: QuickBooks supports `Void` calls by changing TxnType or using the `sparse` update — consult the Accounting API docs.

### 2) Payments

- Create payment
  - Endpoint: `POST /v3/company/<realmId>/payment`
  - Body: QuickBooks Payment JSON:

```json
{
  "CustomerRef": {"value": "123"},
  "TotalAmt": 100.0,
  "Line": [ /* linked invoices */ ]
}
```

- Get payment, PDF, delete, void
  - Similar semantics to invoices. PDF endpoints return binary; keep raw response.

### 3) Customers

- List customers: `GET /v3/company/<realmId>/query?query=SELECT%20*%20FROM%20Customer%20MAXRESULTS%201000`
- Get customer by id: `GET /v3/company/<realmId>/customer/<customerId>`
- Create/update: `POST /v3/company/<realmId>/customer` or `POST /v3/company/<realmId>/customer?operation=update` with required payload.

### 4) Accounts & Account Types

- List accounts: `GET /v3/company/<realmId>/account` or query via `/query`.
- Create account: `POST /v3/company/<realmId>/account` with account payload.
- The service normalizes `AccountType`/`AccountSubType` values for convenience.

### 5) Vendors, Departments (Classes), Locations

- Vendors: `GET /v3/company/<realmId>/vendor` or query via `/query`.
- Classes: `GET /v3/company/<realmId>/class`
- Locations/Departments: QuickBooks maps these differently depending on sandbox/prod; use `/department` or `/location` endpoints if present in your QuickBooks environment.

### 6) Journal entries

- Create journal entry: `POST /v3/company/<realmId>/journalentry`

### 7) Query API

- The service uses QuickBooks Query API extensively. Query syntax is SQL-like:
  - Example: `SELECT * FROM Invoice WHERE CustomerRef = '123' MAXRESULTS 1000`
- Watch MAXRESULTS and paging — use WHERE & LIMIT to avoid huge responses.

---

## Request/Response Examples

1) Create Invoice (curl)

```
curl -X POST \
  -H "Authorization: Bearer <ACCESS_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"CustomerRef":{"value":"123"},"Line":[{"Amount":100.0,"DetailType":"SalesItemLineDetail","SalesItemLineDetail":{"ItemRef":{"value":"1"}}}]}' \
  "https://<QB_BASE>/v3/company/<realmId>/invoice"
```

Sample successful response (abridged):

```json
{
  "Invoice": {
    "Id": "456",
    "SyncToken": "0",
    "TotalAmt": 100.0,
    "CustomerRef": {"value": "123"}
  },
  "time": "2025-08-01T12:00:00.000Z"
}
```

2) Fetch invoice PDF (curl)

```
curl -H "Authorization: Bearer <ACCESS_TOKEN>" \
  "https://<QB_BASE>/v3/company/<realmId>/invoice/<invoiceId>/pdf" --output invoice-<invoiceId>.pdf
```

This saves a raw PDF file. The EAUR service will forward such binary responses to the client.

---

## Errors and failure modes

- 401 Unauthorized: usually indicates expired access token. The EAUR service will attempt a token refresh using the stored `refresh_token` and retry once. If refresh fails, reauthorization is required.
- 429 Rate limit: QuickBooks enforces request limits. Implement exponential backoff and respect Retry-After headers.
- 400/422 Validation errors: QuickBooks returns structured error details. These are forwarded by the EAUR service.

Logging: avoid logging raw tokens. The EAUR service should redact or avoid printing tokens in production logs.

---

## Security

- Tokens are stored encrypted at rest in the EAUR database (FERNET). Keep the FERNET key secure.
- Only authorized EAUR backend components should have access to client secrets and FERNET key.
- For external sharing: do not include any live tokens or client secrets in communications.

---

## Quick Start — sandbox steps

1. Create a QuickBooks sandbox app at https://developer.intuit.com/ and set redirect URI to EAUR's callback endpoint.
2. Obtain `client_id` and `client_secret`, set them in EAUR environment variables.
3. Use the authorization URL generator described in the EAUR service to get an `authorization_code` and `realmId`.
4. Exchange code for tokens through EAUR (or directly via Intuit token endpoint for testing), then store tokens in EAUR database.
5. Test invoice creation and PDF fetch in sandbox.

---

## Contact & Support

For integration questions or to request additional operations to be exposed by EAUR:
- Contact: engineering@eaur.example (replace with real contact)
- Repo: acr-dev-dept/eaur_mis_quickbooks (internal)

---

## Appendix: Useful QuickBooks documentation links

- OAuth2 overview: https://developer.intuit.com/app/developer/qbo/docs/develop/authentication-and-authorization/oauth-2.0
- Token revocation: https://developer.intuit.com/app/developer/qbo/docs/develop/authentication-and-authorization/oauth-2.0#revoke
- Accounting API overview: https://developer.intuit.com/app/developer/qbo/docs/api/accounting/most-commonly-used
- Query API: https://developer.intuit.com/app/developer/qbo/docs/api/accounting/querying-quickbooks-online
- Invoice resource: https://developer.intuit.com/app/developer/qbo/docs/api/accounting/all-entities/invoice
- Error handling: https://developer.intuit.com/app/developer/qbo/docs/develop/error-handling


---

File created: `documentation/QUICKBOOKS_API_PUBLIC.md`

If you want, I can now:
- convert this doc into a one-page PDF for external sharing, or
- add example Postman collection / curl scripts and attach them to the repo.
Which would you prefer next?