"""
Central application models for EAUR MIS-QuickBooks Integration

These models represent the central application database (not the MIS database)
Used for storing application-specific data like audit logs, configurations, etc.
"""

from datetime import datetime, timedelta
from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, JSON
from sqlalchemy.ext.declarative import declarative_base
from werkzeug.security import generate_password_hash, check_password_hash
import jwt
import traceback
from flask import current_app
from application import db
from sqlalchemy import or_, and_, cast, String


# Use Flask-SQLAlchemy's Model base class
class BaseModel(db.Model):
    """Base model with common fields"""
    __abstract__ = True
    
    id = Column(Integer, primary_key=True)
    created_at = Column(DateTime, default=datetime.now(), nullable=False)
    updated_at = Column(DateTime, default=datetime.now(), onupdate=datetime.now(), nullable=False)

class QuickBooksConfig(BaseModel):
    """QuickBooks integration configuration for single-tenant EAUR system"""
    __tablename__ = 'quickbooks_config'

    # QuickBooks Integration Fields
    id = Column(Integer, primary_key=True)
    access_token = Column(Text, nullable=True)  # Encrypted
    refresh_token = Column(Text, nullable=True)  # Encrypted
    authorization_code = Column(Text, nullable=True)  # Encrypted
    realm_id = Column(String(50), nullable=True)
    connected_at = Column(DateTime, nullable=True)
    last_sync_at = Column(DateTime, nullable=True)
    # Configuration
    is_active = Column(Boolean, default=True, nullable=False)
    configuration = Column(JSON, nullable=True)  # Store additional QB config as JSON

    def __repr__(self):
        return f'<QuickBooksConfig realm_id={self.realm_id}>'

    @classmethod
    def get_config(cls):
        """Get the QuickBooks configuration (single row)"""
        return cls.query.first()

    @classmethod
    def update_config(cls, **kwargs):
        """Update QuickBooks configuration"""
        try:
            config = cls.get_config()
            if not config:
                # Create new config if none exists
                config = cls(**kwargs)
                db.session.add(config)
            else:
                # Update existing config
                for key, value in kwargs.items():
                    if hasattr(config, key):
                        setattr(config, key, value)

            db.session.commit()
            return config
        except Exception as e:
            db.session.rollback()
            raise e

    @classmethod
    def is_connected(cls):
        """Check if QuickBooks is connected and active"""
        config = cls.get_config()
        return config and config.is_active and config.access_token and config.refresh_token

    @classmethod
    def get_error_log(cls):
        """Retrieve the latest error log from QuickBooks operations"""
        return QuickbooksAuditLog.query.filter_by(operation_status='Failure').order_by(QuickbooksAuditLog.created_at.desc()).first()


    @classmethod
    def validate_quickbooks_connection(cls):
        """Validate QuickBooks connection"""
        if not cls.is_connected():
            return False, {
                'success': False,
                'error': 'QuickBooks not connected',
                'message': 'Please authenticate with QuickBooks first',
                'status_code': 400
            }
        return True, None


class QuickbooksAuditLog(BaseModel):
    """Audit logs for QuickBooks operations"""
    __tablename__ = 'quickbooks_audit_logs'

    action_type = Column(String(100), nullable=False)  # e.g., 'Post Journal Entry', 'Create Customer'
    operation_status = Column(String(20), nullable=False)  # 'Success', 'Failure'
    error_message = Column(Text, nullable=True)

    # Request/Response Data
    request_payload = Column(JSON, nullable=True)
    response_payload = Column(JSON, nullable=True)

    # User tracking
    user_id = Column(Integer, nullable=True)  # From session or system user
    id = Column(Integer, primary_key=True, autoincrement=True)
    def __repr__(self):
        return f'<QuickbooksAuditLog {self.action_type} - {self.operation_status}>'

    @classmethod
    def add_audit_log(cls, **kwargs):
        """Add audit log entry"""
        try:
            log_entry = cls(**kwargs)
            db.session.add(log_entry)
            db.session.commit()
            return log_entry
        except Exception as e:
            db.session.rollback()
            raise e
        
    @classmethod
    def fetch_paginated_logs(cls, start=0, length=10, search=None):
        """Fetch logs for DataTables pagination"""
        query = cls.query

        if search:
            search_filter = f"%{search}%"
            query = query.filter(
                (cls.action_type.ilike(search_filter)) |
                (cls.error_message.ilike(search_filter))
            )

        total_records = query.count()
        logs = query.order_by(cls.id.desc()).offset(start).limit(length).all()

        return logs, total_records

    @staticmethod
    def update_log_status(id: int, status: str, error_message: str = None):
        """Update the status of an audit log entry"""
        try:
            log_entry = db.session.query(QuickbooksAuditLog).filter(QuickbooksAuditLog.id == id).first()
            if log_entry:
                log_entry.operation_status = status
                if error_message:
                    log_entry.error_message = error_message
                db.session.commit()
                return log_entry
            return None
        except Exception as e:
            db.session.rollback()
            raise e


class SystemConfiguration(BaseModel):
    """System-wide configuration settings"""
    __tablename__ = 'system_configurations'
    
    key = Column(String(100), unique=True, nullable=False)
    value = Column(Text, nullable=True)
    description = Column(Text, nullable=True)
    is_encrypted = Column(Boolean, default=False, nullable=False)
    
    def __repr__(self):
        return f'<SystemConfiguration {self.key}>'

class IntegrationLog(BaseModel):
    """General integration logs for all external systems"""
    __tablename__ = 'integration_logs'
    
    system_name = Column(String(50), nullable=False)  # 'QuickBooks', 'UrubutoPayy', 'SchoolGear'
    operation = Column(String(100), nullable=False)
    status = Column(String(20), nullable=False)  # 'Success', 'Failure', 'Pending'
    external_transaction_id = Column(String(255), nullable=True)
    request_data = Column(Text, nullable=True)
    response_data = Column(Text, nullable=True)
    error_details = Column(Text, nullable=True)
    payer_code = Column(String(255), nullable=True)
    started_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    completed_at = Column(DateTime, nullable=True)
    duration_ms = Column(Integer, nullable=True)
    
    def __repr__(self):
        return f'<IntegrationLog {self.system_name} - {self.operation}>'
    
    @classmethod
    def log_integration_operation(cls, **kwargs):
        """Log an integration operation"""
        try:
            log = cls(**kwargs)
            db.session.add(log)
            db.session.commit()
            return log
        except Exception as e:
            db.session.rollback()
            raise e

    @classmethod
    def get_log_by_transaction_id(cls, transaction_id):
        """Retrieve log by external transaction ID"""
        return cls.query.filter_by(external_transaction_id=transaction_id).first()

class ApiClient(BaseModel):
    """
    API client authentication model for external payment gateways.

    Manages authentication credentials and permissions for external systems
    like Urubuto Pay and School Gear that need to access MIS APIs.
    """
    __tablename__ = 'api_clients'

    # Client identification
    client_name = Column(String(100), nullable=False, unique=True)
    username = Column(String(100), nullable=False, unique=True)
    password_hash = Column(String(255), nullable=False)

    # Client categorization
    client_type = Column(String(50), nullable=False)  # 'payment_gateway', 'api_client', etc.
    gateway_name = Column(String(50), nullable=True)  # 'urubuto_pay', 'school_gear'

    # Permissions and access control
    permissions = Column(JSON, nullable=True)  # ['validation', 'notifications', 'payments']
    is_active = Column(Boolean, default=True, nullable=False)

    # Activity tracking
    last_login = Column(DateTime, nullable=True)
    login_count = Column(Integer, default=0, nullable=False)

    def __repr__(self):
        return f'<ApiClient {self.client_name} ({self.gateway_name})>'

    def set_password(self, password):
        """
        Set password hash for the API client.

        Args:
            password (str): Plain text password to hash and store
        """
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """
        Verify password against stored hash.

        Args:
            password (str): Plain text password to verify

        Returns:
            bool: True if password matches, False otherwise
        """
        return check_password_hash(self.password_hash, password)

    def generate_jwt_token(self):
        """
        Generate JWT token for authenticated API client.

        Creates a JWT token valid for 24 hours containing client information
        and permissions for API access.

        Returns:
            str: Bearer token string ready for Authorization header
        """
        payload = {
            'client_id': self.id,
            'client_name': self.client_name,
            'username': self.username,
            'client_type': self.client_type,
            'gateway_name': self.gateway_name,
            'permissions': self.permissions or [],
            'exp': datetime.utcnow() + timedelta(hours=24),
            'iat': datetime.utcnow(),
            'iss': 'EAUR-MIS-API'
        }

        secret_key = current_app.config.get('SECRET_KEY', 'fallback-secret-key')
        token = jwt.encode(payload, secret_key, algorithm='HS256')
        return f"Bearer {token}"

    def record_login(self):
        """
        Record successful login activity for the API client.

        Updates last_login timestamp and increments login counter
        for activity tracking and monitoring purposes.
        """
        self.last_login = datetime.utcnow()
        self.login_count += 1
        db.session.commit()

    def is_authorized_for(self, permission):
        """
        Check if API client has specific permission.

        Args:
            permission (str): Permission to check (e.g., 'validation', 'notifications')

        Returns:
            bool: True if client has permission, False otherwise
        """
        if not self.is_active:
            return False

        if not self.permissions:
            return False

        return permission in self.permissions

    @classmethod
    def authenticate(cls, username, password):
        """
        Authenticate API client with username and password.

        Args:
            username (str): Client username
            password (str): Client password

        Returns:
            ApiClient or None: Authenticated client instance or None if invalid
        """
        client = cls.query.filter_by(username=username, is_active=True).first()

        if client and client.check_password(password):
            client.record_login()
            return client

        return None

    @classmethod
    def create_client(cls, client_name, username, password, client_type,
                     gateway_name=None, permissions=None):
        """
        Create new API client with specified credentials and permissions.

        Args:
            client_name (str): Display name for the client
            username (str): Unique username for authentication
            password (str): Plain text password (will be hashed)
            client_type (str): Type of client (e.g., 'payment_gateway')
            gateway_name (str): Gateway identifier (e.g., 'urubuto_pay')
            permissions (list): List of permissions for the client

        Returns:
            ApiClient: Created client instance
        """
        client = cls(
            client_name=client_name,
            username=username,
            client_type=client_type,
            gateway_name=gateway_name,
            permissions=permissions or [],
            is_active=True
        )

        client.set_password(password)
        db.session.add(client)
        db.session.commit()

        return client

    @classmethod
    def get_by_gateway(cls, gateway_name):
        """
        Get API client by gateway name.

        Args:
            gateway_name (str): Gateway identifier (e.g., 'urubuto_pay')

        Returns:
            ApiClient or None: Client instance or None if not found
        """
        return cls.query.filter_by(gateway_name=gateway_name, is_active=True).first()

    @classmethod
    def get_active_clients(cls):
        """
        Get all active API clients.

        Returns:
            list: List of active ApiClient instances
        """
        return cls.query.filter_by(is_active=True).all()

class AuthenticationService:
    """
    Service class for handling API client authentication operations.

    Provides centralized authentication logic for payment gateway
    and other external API client authentication workflows.
    """

    @staticmethod
    def authenticate_and_generate_token(username, password):
        """
        Authenticate client credentials and generate JWT token.

        Args:
            username (str): Client username
            password (str): Client password

        Returns:
            tuple: (success: bool, token_or_error: str)
        """
        try:
            client = ApiClient.authenticate(username, password)

            if client:
                token = client.generate_jwt_token()
                return True, token
            else:
                return False, "Invalid credentials"

        except Exception as e:
            return False, f"Authentication error: {str(e)}"

    @staticmethod
    def validate_jwt_token(token):
        """
        Validate JWT token and extract client information.

        Args:
            token (str): JWT token string (without 'Bearer ' prefix)

        Returns:
            tuple: (is_valid: bool, payload_or_error: dict or str)
        """
        try:
            current_app.logger.info("🔍 === JWT VALIDATION START ===")
            current_app.logger.info(f"Token length: {len(token)}")
            current_app.logger.info(f"Token starts with: {token[:10]}...")
            current_app.logger.info(f"Token ends with: ...{token[-10:]}")

            secret_key = current_app.config.get('SECRET_KEY', 'fallback-secret-key')
            current_app.logger.info(f"Using secret key: {secret_key[:10]}... (length: {len(secret_key)})")
            current_app.logger.info(f"Secret key is fallback: {secret_key == 'fallback-secret-key'}")

            current_app.logger.info("🔍 Attempting JWT decode with HS256")
            payload = jwt.decode(token, secret_key, algorithms=['HS256'])
            current_app.logger.info("==YES==JWT decoded successfully")
            current_app.logger.info(f"Token payload keys: {list(payload.keys())}")
            current_app.logger.info(f"Token payload: {payload}")

            # Verify client still exists and is active
            client_id = payload.get('client_id')
            current_app.logger.info(f"🔍 Looking up client ID: {client_id}")

            client = ApiClient.query.get(client_id)
            current_app.logger.info(f"Client found in database: {bool(client)}")

            if client:
                current_app.logger.info(f"Client details: {client.client_name} ({client.gateway_name})")
                current_app.logger.info(f"Client active status: {client.is_active}")
                current_app.logger.info(f"Client permissions: {client.permissions}")
            else:
                current_app.logger.warning(f"❌ No client found with ID: {client_id}")

            if not client or not client.is_active:
                current_app.logger.warning("❌ Client no longer active or not found")
                return False, "Client no longer active"

            current_app.logger.info("==YES==JWT validation successful")
            current_app.logger.info("🔍 === JWT VALIDATION END ===")
            return True, payload

        except jwt.ExpiredSignatureError as e:
            current_app.logger.warning(f"❌ JWT token expired: {str(e)}")
            return False, "Token has expired"
        except jwt.InvalidTokenError as e:
            current_app.logger.warning(f"❌ Invalid JWT token: {str(e)}")
            current_app.logger.warning(f"Token that failed: {token[:50]}...")
            return False, "Invalid token"
        except Exception as e:
            current_app.logger.error(f"💥 JWT validation error: {str(e)}")
            current_app.logger.error(f"💥 Full traceback: {traceback.format_exc()}")
            return False, f"Token validation error: {str(e)}"

    @staticmethod
    def check_permission(token_payload, required_permission):
        """
        Check if token payload contains required permission.

        Args:
            token_payload (dict): Decoded JWT token payload
            required_permission (str): Permission to check for

        Returns:
            bool: True if permission granted, False otherwise
        """
        permissions = token_payload.get('permissions', [])
        return required_permission in permissions

class QuickBooksClasses(BaseModel):
    """QuickBooks Classes for categorization"""
    __tablename__ = 'quickbooks_classes'
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    quickbooks_id = Column(Integer, nullable=True)
    sync_token = Column(Integer, nullable=True)
    quickbooks_status = Column(Integer, default=None, nullable=False)  # 0 = unsynced, 1 = synced

    def __repr__(self):
        return f'<QuickBooksClasses {self.name} - QB ID: {self.quickbooks_id}>'
    
    def to_dict(self):
        """Convert model instance to dictionary"""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'quickbooks_id': self.quickbooks_id,
            'sync_token': self.sync_token,
            'quickbooks_status': self.quickbooks_status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }

    @staticmethod
    def get_unsynced_classes():
        """Retrieve all unsynced QuickBooks classes
        where quickbooks_status = 0 or is NULL
        """
        from application import db as db_manager
        try:
            with db_manager.get_session() as session:
                unsynced_classes = session.query(QuickBooksClasses).filter(
                    or_(QuickBooksClasses.quickbooks_status == 0, QuickBooksClasses.quickbooks_status.is_(None))
                ).all()
                return unsynced_classes
        except Exception as e:
            current_app.logger.error(f"Error retrieving unsynced classes: {e}")
            return []
        
    @staticmethod
    def insert_class(name: str, description: str = None):
        """Insert a new QuickBooks class into the database."""
        try:
            new_class = QuickBooksClasses(
                name=name,
                description=description,
                quickbooks_status=0  # Mark as unsynced initially
            )
            db.session.add(new_class)
            db.session.commit()
            return new_class
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error inserting QuickBooks class: {e}")
            return None
        
    @staticmethod
    def bulk_insert_classes(class_dict: dict):
        """Bulk insert multiple QuickBooks classes from a dictionary."""
        try:
            new_classes = []
            for name, description in class_dict.items():
                new_class = QuickBooksClasses(
                    name=name,
                    description=description,
                    quickbooks_status=0  # Mark as unsynced initially
                )
                new_classes.append(new_class)
                db.session.add(new_class)
            db.session.commit()
            return new_classes
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error bulk inserting QuickBooks classes: {e}")
            return []
        
    @staticmethod
    def update_quickbooks_status(id: int, quickbooks_id: int, sync_token: int, status: int):
        """Update QuickBooks status of a class."""
        try:
            qb_class = db.session.query(QuickBooksClasses).filter(QuickBooksClasses.id == id).first()
            if qb_class:
                qb_class.quickbooks_id = quickbooks_id
                qb_class.sync_token = sync_token
                qb_class.quickbooks_status = status
                db.session.commit()
                return qb_class
            return None
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error updating QuickBooks status: {e}")
            return None