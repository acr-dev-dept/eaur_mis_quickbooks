"""
Database connection and management utilities
"""

import os
import logging
from contextlib import contextmanager
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.pool import QueuePool
from sqlalchemy.exc import DisconnectionError
from flask import current_app
import os
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

class DatabaseManager:
    """
    Manages database connections for both central app database and MIS database
    """
    
    def __init__(self):
        self.engines = {}
        self.session_factories = {}
        self._setup_engines()
    
    def _setup_engines(self):
        """Setup database engines for different databases"""
        # This will be called when the app context is available
        pass
    
    def setup_mis_connection(self, config):
        """
        Setup connection to MIS MySQL database
        
        Args:
            config: Flask configuration object
        """
        if not config.SQLALCHEMY_DATABASE_URI:
            logger.warning("MIS database URL not configured")
            return
        
        try:
            engine = create_engine(
                config.SQLALCHEMY_DATABASE_URI,
                poolclass=QueuePool,
                pool_size=10,
                max_overflow=20,
                pool_pre_ping=True,  # Verify connections before use
                pool_recycle=3600,   # Recycle connections every hour
                echo=config.DEBUG,   # Log SQL queries in debug mode
                connect_args={
                    "charset": "utf8mb4",
                    "use_unicode": True,
                    "autocommit": False
                }
            )
            
            # Add connection event listeners
            self._add_connection_listeners(engine)
            
            self.engines['mis'] = engine
            self.session_factories['mis'] = scoped_session(
                sessionmaker(bind=engine, expire_on_commit=False)
            )
            
            logger.info("MIS database connection established")
            
        except Exception as e:
            logger.error(f"Failed to setup MIS database connection: {e}")
            raise
    
    def _add_connection_listeners(self, engine):
        """Add event listeners for connection management"""
        
        @event.listens_for(engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            """Set database-specific settings on connect"""
            if 'mysql' in str(engine.url):
                # MySQL specific settings
                cursor = dbapi_connection.cursor()
                cursor.execute("SET SESSION sql_mode='STRICT_TRANS_TABLES'")
                cursor.execute("SET SESSION time_zone='+00:00'")
                cursor.close()
        
        @event.listens_for(engine, "checkout")
        def receive_checkout(dbapi_connection, connection_record, connection_proxy):
            """Handle connection checkout"""
            logger.debug("Connection checked out from pool")
        
        @event.listens_for(engine, "checkin")
        def receive_checkin(dbapi_connection, connection_record):
            """Handle connection checkin"""
            logger.debug("Connection checked in to pool")
    
    @contextmanager
    def get_mis_session(self):
        """
        Get MIS database session with automatic cleanup
        
        Yields:
            Session: SQLAlchemy session for MIS database
        """
        if 'mis' not in self.session_factories:
            raise RuntimeError("MIS database not configured")
        
        session = self.session_factories['mis']()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Database session error: {e}")
            raise
        finally:
            session.close()
    
    def test_mis_connection(self):
        """
        Test MIS database connection
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            with self.get_mis_session() as session:
                session.execute("SELECT 1")
                return True
        except Exception as e:
            logger.error(f"MIS database connection test failed: {e}")
            return False
    
    def close_all_connections(self):
        """Close all database connections"""
        for name, session_factory in self.session_factories.items():
            try:
                session_factory.remove()
                logger.info(f"Closed {name} database sessions")
            except Exception as e:
                logger.error(f"Error closing {name} database sessions: {e}")
        
        for name, engine in self.engines.items():
            try:
                engine.dispose()
                logger.info(f"Disposed {name} database engine")
            except Exception as e:
                logger.error(f"Error disposing {name} database engine: {e}")
    
    def get_engine(self, database_name):
        """
        Get database engine by name
        
        Args:
            database_name (str): Name of the database ('mis', 'central', etc.)
            
        Returns:
            Engine: SQLAlchemy engine instance
        """
        return self.engines.get(database_name)
    
    def health_check(self):
        """
        Perform health check on all configured databases
        
        Returns:
            dict: Health status of each database
        """
        health_status = {}
        
        for db_name in self.engines.keys():
            try:
                if db_name == 'mis':
                    health_status[db_name] = self.test_mis_connection()
                else:
                    # For other databases, implement similar test methods
                    health_status[db_name] = True
            except Exception as e:
                logger.error(f"Health check failed for {db_name}: {e}")
                health_status[db_name] = False
        
        return health_status

# Global database manager instance
db_manager = DatabaseManager()

def init_database_manager(app):
    """
    Initialize database manager with Flask app
    
    Args:
        app: Flask application instance
    """
    with app.app_context():
        try:
            db_manager.setup_mis_connection(app.config)
            app.logger.info("Database manager initialized successfully")
        except Exception as e:
            app.logger.error(f"Failed to initialize database manager: {e}")
            raise
