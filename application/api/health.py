"""
Health check endpoints for monitoring and diagnostics
"""

from flask import Blueprint, jsonify, current_app
from datetime import datetime
import os
import sys

health_bp = Blueprint('health', __name__)

@health_bp.route('/', methods=['GET'])
def health_check():
    """Basic health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'service': 'EAUR MIS-QuickBooks Integration',
        'version': '1.0.0'
    })

@health_bp.route('/detailed', methods=['GET'])
def detailed_health_check():
    """Detailed health check including database connections"""
    health_status = {
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat(),
        'service': 'EAUR MIS-QuickBooks Integration',
        'version': '1.0.0',
        'environment': current_app.config.get('FLASK_ENV', 'unknown'),
        'python_version': sys.version,
        'checks': {}
    }
    
    # Check database connections
    try:
        db_manager = current_app.config.get('db_manager')
        if db_manager:
            db_health = db_manager.health_check()
            health_status['checks']['databases'] = db_health
            
            # If any database is unhealthy, mark overall status as unhealthy
            if not all(db_health.values()):
                health_status['status'] = 'unhealthy'
        else:
            health_status['checks']['databases'] = {'error': 'Database manager not initialized'}
            health_status['status'] = 'unhealthy'
    except Exception as e:
        health_status['checks']['databases'] = {'error': str(e)}
        health_status['status'] = 'unhealthy'
    
    # Check configuration
    try:
        config_checks = {
            'quickbooks_configured': bool(current_app.config.get('QUICKBOOKS_CLIENT_ID')),
            'encryption_key_configured': bool(current_app.config.get('FERNET_KEY')),
            'mis_db_configured': bool(current_app.config.get('MIS_DB_HOST'))
        }
        health_status['checks']['configuration'] = config_checks
        
        # If critical config is missing, mark as unhealthy
        if not all(config_checks.values()):
            health_status['status'] = 'degraded'
    except Exception as e:
        health_status['checks']['configuration'] = {'error': str(e)}
        health_status['status'] = 'unhealthy'
    
    # Return appropriate HTTP status code
    status_code = 200 if health_status['status'] == 'healthy' else 503
    return jsonify(health_status), status_code

@health_bp.route('/ready', methods=['GET'])
def readiness_check():
    """Readiness check for Kubernetes/container orchestration"""
    try:
        # Check if all critical components are ready
        db_manager = current_app.config.get('db_manager')
        if not db_manager:
            return jsonify({'status': 'not ready', 'reason': 'Database manager not initialized'}), 503
        
        # Test database connectivity
        if not db_manager.test_mis_connection():
            return jsonify({'status': 'not ready', 'reason': 'MIS database not accessible'}), 503
        
        return jsonify({'status': 'ready'})
    except Exception as e:
        return jsonify({'status': 'not ready', 'reason': str(e)}), 503

@health_bp.route('/live', methods=['GET'])
def liveness_check():
    """Liveness check for Kubernetes/container orchestration"""
    return jsonify({'status': 'alive'})
