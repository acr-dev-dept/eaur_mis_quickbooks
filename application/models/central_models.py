"""
Central application models for EAUR MIS-QuickBooks Integration

These models represent the central application database (not the MIS database)
Used for storing application-specific data like audit logs, configurations, etc.
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, JSON
from sqlalchemy.ext.declarative import declarative_base
from application import db

# Use Flask-SQLAlchemy's Model base class
class BaseModel(db.Model):
    """Base model with common fields"""
    __abstract__ = True
    
    id = Column(Integer, primary_key=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

class Company(BaseModel):
    """Company configuration and QuickBooks integration settings"""
    __tablename__ = 'companies'
    
    company_name = Column(String(255), nullable=False)
    database_name = Column(String(100), nullable=False)  # MIS database name
    
    # QuickBooks Integration Fields
    quickbooks_access_token = Column(Text, nullable=True)  # Encrypted
    quickbooks_refresh_token = Column(Text, nullable=True)  # Encrypted
    quickbooks_authorization_code = Column(Text, nullable=True)  # Encrypted
    quickbooks_realm_id = Column(String(50), nullable=True)
    quickbooks_connected_at = Column(DateTime, nullable=True)
    
    # Configuration
    is_active = Column(Boolean, default=True, nullable=False)
    configuration = Column(JSON, nullable=True)  # Store additional config as JSON
    
    def __repr__(self):
        return f'<Company {self.company_name}>'
    
    @classmethod
    def update_company_data(cls, company_id, **kwargs):
        """Update company data"""
        try:
            company = cls.query.get(company_id)
            if company:
                for key, value in kwargs.items():
                    if hasattr(company, key):
                        setattr(company, key, value)
                db.session.commit()
                return True
            return False
        except Exception as e:
            db.session.rollback()
            raise e

class QuickbooksAuditLog(BaseModel):
    """Audit logs for QuickBooks operations"""
    __tablename__ = 'quickbooks_audit_logs'
    
    company_id = Column(Integer, db.ForeignKey('companies.id'), nullable=False)
    action_type = Column(String(100), nullable=False)  # e.g., 'Post Journal Entry', 'Create Customer'
    operation_status = Column(String(20), nullable=False)  # 'Success', 'Failure'
    error_message = Column(Text, nullable=True)
    
    # Request/Response Data
    request_payload = Column(JSON, nullable=True)
    response_payload = Column(JSON, nullable=True)
    
    # User tracking
    user_id = Column(Integer, nullable=True)  # From session
    
    def __repr__(self):
        return f'<QuickbooksAuditLog {self.action_type} - {self.operation_status}>'
    
    @classmethod
    def add_quickbooks_audit_log(cls, session, **kwargs):
        """Add audit log entry"""
        try:
            log_entry = cls(**kwargs)
            session.add(log_entry)
            session.commit()
            return log_entry
        except Exception as e:
            session.rollback()
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
