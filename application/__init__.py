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

    # Setup application context
    with app.app_context():
        # Import central models to ensure they're registered with SQLAlchemy
        try:
            from application.models import central_models
            app.logger.info("Central models imported successfully")
        except ImportError as e:
            app.logger.warning(f"Could not import central models: {e}")

        # Import MIS models if they exist
        try:
            from application.models import mis_models
            app.logger.info("MIS models imported successfully")
        except ImportError:
            app.logger.info("MIS models not found - will be generated after database analysis")

        # Create tables if they don't exist (development only)
        if app.config.get('FLASK_ENV') == 'development':
            try:
                db.create_all()
                app.logger.info("Database tables created/verified")
            except Exception as e:
                app.logger.error(f"Error creating database tables: {e}")

    app.logger.info(f"Application created with config: {config_name}")
    return app

def setup_logging(app):
    """Setup application logging"""
    if not app.debug and not app.testing:
        # Create logs directory if it doesn't exist
        if not os.path.exists('logs'):
            os.mkdir('logs')

        # Setup file handler
        file_handler = logging.FileHandler(app.config.get('LOG_FILE', 'logs/app.log'))
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        ))
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)

        app.logger.setLevel(logging.INFO)
        app.logger.info('EAUR MIS-QuickBooks Integration startup')

def register_blueprints(app):
    """Register application blueprints"""
    # API v1 blueprint
    from application.api.v1 import api_v1_bp
    from application.api.health import health_bp
    from application.api.v1.urubuto import urubuto_bp
    from application.api.v1.quickbooks import quickbooks_bp
    

    # Register blueprints
    app.register_blueprint(api_v1_bp, url_prefix='/api/v1')   
    app.register_blueprint(health_bp, url_prefix='/health')
    app.register_blueprint(urubuto_bp, url_prefix='/api/v1/urubuto')
    app.register_blueprint(quickbooks_bp, url_prefix='/api/v1/quickbooks')

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
