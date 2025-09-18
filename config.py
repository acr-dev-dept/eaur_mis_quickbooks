"""
Configuration settings for EAUR MIS-QuickBooks Integration
"""

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    """Base configuration class"""
    
    # Flask Configuration
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    SECURITY_PASSWORD_SALT = os.environ.get('SECURITY_PASSWORD_SALT') or 'dev-salt-change-in-production'
    
    # Database Configuration
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_RECORD_QUERIES = True
    
    # Session Configuration
    SESSION_TYPE = 'filesystem'
    SESSION_PERMANENT = False
    SESSION_USE_SIGNER = True
    
    # JWT Configuration
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY') or 'jwt-secret-change-in-production'
    JWT_ACCESS_TOKEN_EXPIRES = int(os.environ.get('JWT_ACCESS_TOKEN_EXPIRES', 86400))  # 24 hours
    JWT_REFRESH_TOKEN_EXPIRES = int(os.environ.get('JWT_REFRESH_TOKEN_EXPIRES', 2592000))  # 30 days
    JWT_TOKEN_LOCATION = ['headers']
    
    # QuickBooks Configuration
    QUICKBOOKS_CLIENT_ID = os.environ.get('QUICK_BOOKS_CLIENT_ID')
    QUICKBOOKS_CLIENT_SECRET = os.environ.get('QUICK_BOOKS_SECRET')
    QUICKBOOKS_REDIRECT_URI = os.environ.get('QUICK_BOOKS_REDIRECT_URI')
    QUICKBOOKS_SANDBOX_BASE_URL = os.environ.get('QUICK_BOOKS_BASEURL_SANDBOX')
    QUICKBOOKS_PRODUCTION_BASE_URL = os.environ.get('QUICK_BOOKS_BASEURL_PRODUCTION')
    QUICKBOOKS_DEFAULT_DEPOSIT_ACCOUNT_ID = os.environ.get('QUICKBOOKS_DEFAULT_DEPOSIT_ACCOUNT_ID', '35') # Default to '35' (e.g., Checking)
    QUICKBOOKS_DEFAULT_PAYMENT_METHOD_ID = os.environ.get('QUICKBOOKS_DEFAULT_PAYMENT_METHOD_ID', '2')   # Default to '2' (e.g., Cash)
    
    # Encryption Configuration
    FERNET_KEY = os.environ.get('FERNET_KEY')
    
    # MIS Database Configuration
    MIS_DB_HOST = os.environ.get('MIS_DB_HOST')
    MIS_DB_PORT = int(os.environ.get('MIS_DB_PORT', 3306))
    MIS_DB_USER = os.environ.get('MIS_DB_USER')
    MIS_DB_PASSWORD = os.environ.get('MIS_DB_PASSWORD')
    MIS_DB_NAME = os.environ.get('MIS_DB_NAME')
    
    # Redis Configuration (for caching)
    REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
    
    # Logging Configuration
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
    LOG_FILE = os.environ.get('LOG_FILE', 'logs/app.log')
    
    # API Configuration
    API_RATE_LIMIT = os.environ.get('API_RATE_LIMIT', '100 per hour')
    
    @property
    def MIS_DATABASE_URL(self):
        """Construct MIS database URL"""
        if not all([self.MIS_DB_HOST, self.MIS_DB_USER, self.MIS_DB_PASSWORD, self.MIS_DB_NAME]):
            return None
        return (
            f"mysql+pymysql://{self.MIS_DB_USER}:"
            f"{self.MIS_DB_PASSWORD}@"
            f"{self.MIS_DB_HOST}:"
            f"{self.MIS_DB_PORT}/"
            f"{self.MIS_DB_NAME}"
            f"?charset=utf8mb4"
        )

    def get_mis_database_url(self):
        """Get MIS database URL (method version for compatibility)"""
        return self.MIS_DATABASE_URL

class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    TESTING = False
    
    # Central database for development
    SQLALCHEMY_DATABASE_URI = os.environ.get('DEV_DATABASE_URL') or \
        'sqlite:///dev_central.db'
    
    # QuickBooks sandbox for development
    QUICKBOOKS_BASE_URL = Config.QUICKBOOKS_SANDBOX_BASE_URL

class TestingConfig(Config):
    """Testing configuration"""
    DEBUG = False
    TESTING = True
    
    # Use in-memory database for testing
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    
    # Disable CSRF for testing
    WTF_CSRF_ENABLED = False
    
    # Use sandbox for testing
    QUICKBOOKS_BASE_URL = Config.QUICKBOOKS_SANDBOX_BASE_URL

class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    TESTING = False
    
    # Production database
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        os.environ.get('SQLALCHEMY_DATABASE_URI')
    
    # Production QuickBooks
    QUICKBOOKS_BASE_URL = Config.QUICKBOOKS_PRODUCTION_BASE_URL
    
    # Enhanced security for production
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'

# Configuration dictionary
config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}

def get_config(config_name=None):
    """Get configuration class by name"""
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'development')
    return config.get(config_name, config['default'])
