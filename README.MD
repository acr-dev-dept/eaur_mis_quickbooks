# EAUR MIS-QuickBooks Integration Microservice

A Flask-based microservice for real-time synchronization between East African University Rwanda's Management Information System (MIS) and QuickBooks Online.

## Project Overview

This microservice provides:
- Real-time data synchronization between MIS and QuickBooks
- Event-driven architecture for instant updates
- Secure OAuth2 integration with QuickBooks Online
- Direct database access to MIS for optimal performance
- Comprehensive audit logging and error handling
- Payment gateway integration (Urubuto Pay, School Gear)

## Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   EAUR MIS      │    │  Flask           │    │  QuickBooks     │
│   (PHP/MySQL)   │◄──►│  Microservice    │◄──►│  Online         │
│                 │    │                  │    │                 │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                              │
                              ▼
                       ┌──────────────────┐
                       │  Payment         │
                       │  Gateways        │
                       │  (USSD)          │
                       └──────────────────┘
```

## Quick Start

### 1. Environment Setup

```bash
# Clone the repository
git clone <repository-url>
cd eaur_mis_quickbooks

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Setup environment variables
cp .env.example .env
# Edit .env with your actual configuration
```

### 2. Database Setup

```bash
# Initialize migrations
./scripts/setup_migrations.sh

# Apply migrations
./scripts/run_migrations.sh
```

### 3. MIS Database Integration

After receiving the MIS database dump:

```bash
# Analyze database and generate models
python tools/analyze_database.py --dump-file path/to/mis_dump.sql

# Or connect to live database
python tools/analyze_database.py --live-db --host localhost --user mis_user --password password --database mis_db
```

### 4. Run the Application

```bash
# Development mode
python app.py

# Or using Flask CLI
export FLASK_APP=app.py
export FLASK_ENV=development
flask run
```

## Configuration

### Environment Variables

Key configuration variables in `.env`:

```bash
# Flask Configuration
FLASK_ENV=development
SECRET_KEY=your-secret-key

# Central Database (Application)
DEV_DATABASE_URL=sqlite:///dev_central.db

# MIS Database (Legacy PHP)
MIS_DB_HOST=localhost
MIS_DB_USER=mis_user
MIS_DB_PASSWORD=mis_password
MIS_DB_NAME=eaur_mis

# QuickBooks Integration
QUICK_BOOKS_CLIENT_ID=your-client-id
QUICK_BOOKS_SECRET=your-client-secret
QUICK_BOOKS_REDIRECT_URI=http://localhost:5000/api/v1/quickbooks/webhook

# Encryption
FERNET_KEY=your-encryption-key
```

## API Endpoints

### Health Check
- `GET /health/` - Basic health check
- `GET /health/detailed` - Detailed system status

### QuickBooks Integration
- `GET /api/v1/quickbooks/get_auth_url` - Get OAuth authorization URL
- `GET /api/v1/quickbooks/webhook` - OAuth callback endpoint
- `GET /api/v1/quickbooks/get_accounts` - Fetch QuickBooks accounts
- `GET /api/v1/quickbooks/get_vendors` - Fetch QuickBooks vendors
- `GET /api/v1/quickbooks/disconnect` - Disconnect QuickBooks integration

### MIS Data Enrichment
- `GET /api/v1/mis/campus/<id>` - Get campus details
- `GET /api/v1/mis/intake/<id>` - Get intake details
- `GET /api/v1/mis/specialisation/<id>` - Get specialization details
- (Additional endpoints will be available after model generation)

## Database Schema

### Central Application Database
- `quickbooks_config` - QuickBooks integration configuration and settings
- `quickbooks_audit_logs` - Audit trail for QuickBooks operations
- `system_configurations` - System-wide settings
- `integration_logs` - General integration logs

### MIS Database Models
Models will be auto-generated from the existing MIS database schema using the database analysis tool.

## Development Workflow

### 1. Database Changes
```bash
# Create new migration
./scripts/run_migrations.sh --create-migration

# Apply migration
./scripts/run_migrations.sh

# Rollback if needed
./scripts/run_migrations.sh --downgrade

# Check migration status
./scripts/run_migrations.sh --status
```

### 2. Adding New Features
1. Create feature branch
2. Implement changes
3. Add tests
4. Update documentation
5. Create pull request

### 3. Testing
```bash
# Run all tests
python run_tests.py

# Run with coverage reporting
python run_tests.py --coverage

# Run specific test file
python run_tests.py --specific health

# Run with different verbosity
python run_tests.py --verbosity 1

# Run using unittest directly
python -m unittest discover tests -v
```

## Deployment

### Production Setup
1. Set `FLASK_ENV=production` in environment
2. Configure production database URLs
3. Set up proper logging
4. Configure reverse proxy (nginx)
5. Use production WSGI server (gunicorn)



## Security Considerations

- All QuickBooks tokens are encrypted using Fernet encryption
- Database connections use SSL/TLS
- API endpoints include rate limiting
- Comprehensive audit logging
- Input validation and sanitization
- CORS configuration for production

## Testing

### Test Framework
The project uses Python's built-in `unittest` framework for testing, providing:
- 25 comprehensive tests covering models, APIs, and health endpoints
- 56% code coverage with detailed reporting
- Mock-based testing for external services
- Database transaction isolation for clean tests

### Test Structure
```
tests/
├── __init__.py
├── base_test.py           # Base test class with utilities
├── test_health.py         # Health endpoint tests (5 tests)
├── test_models.py         # Database model tests (14 tests)
└── test_quickbooks_api.py # QuickBooks API tests (6 tests)
```

### Running Tests
```bash
# Run all tests with summary
python run_tests.py

# Generate coverage report
python run_tests.py --coverage

# Run specific test category
python run_tests.py --specific models
python run_tests.py --specific health
python run_tests.py --specific quickbooks_api

# Adjust verbosity (0=quiet, 1=normal, 2=verbose)
python run_tests.py --verbosity 2
```

### Coverage Reports
- Console coverage report shows line-by-line coverage
- HTML coverage report generated in `htmlcov/` directory
- Current coverage: 56% overall, 88% on models

## Monitoring and Logging

### Log Files
- Application logs: `logs/app.log`
- Error logs: Captured in application logs
- Audit logs: Stored in database

### Health Monitoring
- Health check endpoints for monitoring systems
- Database connectivity checks
- QuickBooks API connectivity validation

## Troubleshooting

### Common Issues

1. **Database Connection Failed**
   ```bash
   # Check database connectivity
   ./scripts/run_migrations.sh --status
   ```

2. **QuickBooks Authentication Issues**
   - Verify client ID and secret in `.env`
   - Check redirect URI configuration
   - Review QuickBooks developer console

3. **Migration Errors**
   ```bash
   # Reset database (WARNING: destroys data)
   ./scripts/run_migrations.sh --reset
   ```

### Debug Mode
```bash
export FLASK_ENV=development
export FLASK_DEBUG=1
python app.py
```

## Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

## License

This project is proprietary software developed for East African University Rwanda.

## Support
Call the given number

**Note**: This microservice is part of the EAUR MIS-QuickBooks Integration project. Ensure you have the necessary credentials and permissions before setting up the integration.


**Syncing to QuickBoooks**
While syncing to Quickbooks there are some concerns
requirements needed:

## Pre-requirements
   1. We found that there are some existing customers, items, and invoices already there in EAUR's quickbooks.
   2. We found that only applicants are not there, so they need to be synced, with quickbooks_id, and quickbooks_status, and Sync token
   3. With students who are already synced, we'll consider the qkbooks_id during sync and skip those with quickbooks_id not null
   4. Date formats to match the local format.
   5. Syncing Applicants Starting from Jan 01 2025
   6. Application of reference number (Urubuto, Invoices,Payments)


## Requirements
   1. IncomeAccountRef (which demands the corresponding income account for a specific item)
   
   2. ItemRef id while syncing invoices to quickbooks
   3. IncomeAccountRef while referencing syncing Payments to QB
   4. Classes (Student, Applicant)
   5. Departments/Locations (Kigali campus, Nyagatare Campus) for the purpose of invoicing
   6. Ensuring that there are all respective create and update endpoints to reflect the creation (sync) or update

## Order of Syncing
   000. Creating locations and departments in quickbooks, to hard code them inside Tbl_campus table and on classref before syncing invoices in sync single invoice method
   00. First and foremost we'll update all the invoices, customers, items and payments from 01/01/2025, setting their quicbooks status to 0, and quickbooks ID to NULL, in the EAUR mis db
   0. Before running bulk sync invoices sync a few and examine the effects

   1. Customers (Applicants and students), Inspect to add the address as in East African University live account
      - Create new customer types (Student, applicant)
   2. Income Accounts
   3. Items (dependent on Income accounts ref)
   4. Invoices (dependent on Items and income accounts)
      1. Upon syncing invoices, Only invoices with active items (status_Id == 1) are the only ones which sync
   5. Sync Banks (to be used as a DepositToAccountRef while syncing Payments)
   6. SYnc Payments
   6. Ensure the protection of api on order to be called only from EAUR MIS
Concerns
1. Deleting and updating student information when some data changes in MIS to directly change inside quickbooks too


# Don't Dos
1. Never update MIS data via Quickbooks directly, instead update via MIS and call the respective API to update the data inside quickbooks

# Database Setup
mysqldump miseaurac_db > sandbox_v3.sql;
mysql -e "CREATE DATABASE sandbox_v3";
mysql sandbox_v3 < sandbox_v3.sql 

Update the .env file from the microservice to point to the right database

GRANT ALL PRIVILEGES ON sandbox_v3.* TO 'eaurqb'@'178.62.215.167';

FLUSH PRIVILEGES;

# QB Connection
1. Intuit app, playground and proceed with keys generation and select the account to connect to



