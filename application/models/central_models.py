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
from flask import current_app
from application import db

# Use Flask-SQLAlchemy's Model base class
class BaseModel(db.Model):
    """Base model with common fields"""
    __abstract__ = True
    
    id = Column(Integer, primary_key=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

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
    
    request_data = Column(JSON, nullable=True)
    response_data = Column(JSON, nullable=True)
    error_details = Column(Text, nullable=True)
    
    # Timing information
    started_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    completed_at = Column(DateTime, nullable=True)
    duration_ms = Column(Integer, nullable=True)
    
    def __repr__(self):
        return f'<IntegrationLog {self.system_name} - {self.operation}>'

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
