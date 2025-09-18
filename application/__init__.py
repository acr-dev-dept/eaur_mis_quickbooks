"""
EAUR MIS-QuickBooks Integration Application Factory
"""

import os
import logging
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_jwt_extended import JWTManager
from flask_session import Session
from dotenv import load_dotenv

load_dotenv()

# Initialize extensions
db = SQLAlchemy()
migrate = Migrate()
jwt = JWTManager()
session = Session()

def create_app(config_name=None):
    """
    Application factory pattern for creating Flask app instances

    Args:
        config_name (str): Configuration environment name

    Returns:
        Flask: Configured Flask application instance
    """
    app = Flask(__name__)

    # Load configuration
    from config import get_config
    config_class = get_config(config_name)
    app.config.from_object(config_class)

    # Initialize extensions with app
    db.init_app(app)
    #migrate.init_app(app, db)
    jwt.init_app(app)
    session.init_app(app)

    # Setup logging
    setup_logging(app)

    # Initialize database connection manager
    from application.utils.database import DatabaseManager, init_database_manager
    app.config['db_manager'] = DatabaseManager()

    # Initialize database manager with app context
    try:
        init_database_manager(app)
    except Exception as e:
        app.logger.warning(f"Could not initialize MIS database connection: {e}")
        app.logger.info("MIS database will be configured after database credentials are provided")

    # Register blueprints
    register_blueprints(app)

    # Register error handlers
    register_error_handlers(app)

    # create a home page route
    @app.route('/')
    def home():
        #add a simple formatted home page message with inline html and some style
        message = """
        <html>
        <head>
            <title>EAUR MIS-QuickBooks Integration</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 40px; }
                h1 { color: #2c3e50; }
                p { font-size: 18px; }
            </style>
        </head>
        <body>
            <h1>Welcome to the EAUR MIS-QuickBooks Integration Service</h1>
            <p>This service facilitates integration between the EAUR Management Information System (MIS) and QuickBooks.</p>
            <p>Use the API endpoints to interact with the service.</p>
            <p>The services are being developed and improved continuously.</p>
            
        </body>
        </html>
        """
        return message

    # Setup application context
    with app.app_context():
        # Import central models to ensure they're registered with SQLAlchemy
        try:
            from application.models import central_models
            app.logger.info("Central models imported successfully")
            #check imported models
            # --- Get central models registered in metadata ---
            central_models_list = list(db.metadata.tables.keys())
            app.logger.info(f"Central models registered for db.create_all(): {central_models_list}")
        except ImportError as e:
            app.logger.warning(f"Could not import central models: {e}")

        flask_environment = os.getenv('FLASK_ENV', 'development')
        # Create tables if they don't exist (development only)
        if flask_environment == 'development':
            try:
                db.create_all()
                app.logger.info("Database tables created/verified")
            except Exception as e:
                app.logger.error(f"Error creating database tables: {e}")

    app.logger.info(f"Application created with config: {config_name}")
    return app


def setup_logging(app):
    """
    Sets up a simple file logging configuration for the Flask application.
    Logs will be written to a file named 'app.log' in the same directory
    as the application.
    
    Args:
        app: The Flask application instance.
    """
    # Only set up file logging if not in debug or testing mode
    if not app.debug and not app.testing:
        # Configure the Flask logger
        handler = logging.FileHandler('app.log')
        
        # Set the handler logging level to DEBUG to capture all logs
        handler.setLevel(logging.DEBUG)

        # Update formatter to include pathname, filename, and line number
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s - [in %(pathname)s:%(lineno)d]'
        )
        handler.setFormatter(formatter)
        
        # Add the file handler to the app logger
        app.logger.addHandler(handler)
        
        # Set the app logger's level to DEBUG
        app.logger.setLevel(logging.DEBUG)

        # Log a message to indicate successful startup
        app.logger.info('EAUR MIS-QuickBooks Integration startup')
        app.logger.info('Logging configured successfully to app.log')


def register_blueprints(app):
    """Register application blueprints"""
    # API v1 blueprint
    from application.api.v1 import api_v1_bp
    from application.api.health import health_bp
    from application.api.v1.urubuto import urubuto_bp
    from application.api.v1.quickbooks import quickbooks_bp
    from application.api.v1.mis_data import mis_data_bp
    #from application.api.v1.sync import sync_bp
    from application.api.v1.customer_sync_api import customer_sync_bp
    from application.api.v1.invoice import invoices_bp
    from application.api.v1.payment_sync_api import payment_sync_bp # New blueprint
    

    # Register blueprints
    app.register_blueprint(api_v1_bp, url_prefix='/api/v1')   
    app.register_blueprint(health_bp, url_prefix='/health')
    app.register_blueprint(urubuto_bp, url_prefix='/api/v1/urubuto')
    app.register_blueprint(quickbooks_bp, url_prefix='/api/v1/quickbooks')
    app.register_blueprint(mis_data_bp, url_prefix='/api/v1/mis_data')
    #app.register_blueprint(sync_bp, url_prefix='/api/v1/sync')
    app.register_blueprint(customer_sync_bp, url_prefix='/api/v1/sync/customers')
    app.register_blueprint(invoices_bp, url_prefix='/api/v1/invoices')
    app.register_blueprint(payment_sync_bp, url_prefix='/api/v1/sync/payments') # Register new blueprint

def register_error_handlers(app):
    """Register application error handlers"""

    @app.errorhandler(404)
    def not_found_error(error):
        return {'error': 'Resource not found'}, 404

    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return {'error': 'Internal server error'}, 500

    @app.errorhandler(400)
    def bad_request_error(error):
        return {'error': 'Bad request'}, 400
