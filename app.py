#!/usr/bin/env python3
"""
EAUR MIS-QuickBooks Integration Microservice
Main application entry point
"""

from application import create_app
import os

# Create Flask application instance
app = create_app(os.getenv('FLASK_ENV', 'development'))

if __name__ == '__main__':
    # Run the application
    debug_mode = os.getenv('FLASK_ENV') == 'development'
    app.run(
        host=os.getenv('FLASK_HOST', '0.0.0.0'),
        port=8000,
        debug=debug_mode
    )