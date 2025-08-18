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
- `GET /health/ready` - Kubernetes readiness probe
- `GET /health/live` - Kubernetes liveness probe

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
- `companies` - Company configurations and QuickBooks settings
- `quickbooks_audit_logs` - Audit trail for QuickBooks operations
- `system_configurations` - System-wide settings
- `integration_logs` - General integration logs

### MIS Database Models
Models will be auto-generated from the existing MIS database schema using the database analysis tool.

## Development Workflow

### 1. Database Changes
```bash
# Create new migration
flask db migrate -m "Description of changes"

# Apply migration
./scripts/run_migrations.sh

# Rollback if needed
./scripts/run_migrations.sh --downgrade
```

### 2. Adding New Features
1. Create feature branch
2. Implement changes
3. Add tests
4. Update documentation
5. Create pull request

### 3. Testing
```bash
# Run tests
pytest

# Run with coverage
pytest --cov=application

# Run specific test file
pytest tests/test_quickbooks.py
```

## Deployment

### Production Setup
1. Set `FLASK_ENV=production` in environment
2. Configure production database URLs
3. Set up proper logging
4. Configure reverse proxy (nginx)
5. Use production WSGI server (gunicorn)

### Docker Deployment
```bash
# Build image
docker build -t eaur-mis-quickbooks .

# Run container
docker run -p 5000:5000 --env-file .env eaur-mis-quickbooks
```

## Security Considerations

- All QuickBooks tokens are encrypted using Fernet encryption
- Database connections use SSL/TLS
- API endpoints include rate limiting
- Comprehensive audit logging
- Input validation and sanitization
- CORS configuration for production

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

For technical support or questions:
- Email: support@acr-online.rw
- Documentation: [Project Wiki](link-to-wiki)
- Issues: [GitHub Issues](link-to-issues)

---

**Note**: This microservice is part of the EAUR MIS-QuickBooks Integration project. Ensure you have the necessary credentials and permissions before setting up the integration.