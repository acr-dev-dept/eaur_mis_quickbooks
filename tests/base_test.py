"""
Base test class for EAUR MIS-QuickBooks Integration tests
"""

import unittest
import os
import sys
from unittest.mock import patch

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from application import create_app, db


class BaseTestCase(unittest.TestCase):
    """Base test case that other test classes can inherit from"""
    
    def setUp(self):
        """Set up test fixtures before each test method"""
        # Create test app with testing configuration
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()
        self.client = self.app.test_client()
        
        # Create all database tables
        db.create_all()
        
    def tearDown(self):
        """Clean up after each test method"""
        # Remove database session and drop all tables
        db.session.remove()
        db.drop_all()
        
        # Pop the application context
        self.app_context.pop()
    
    def get_json_response(self, response):
        """Helper method to get JSON data from response"""
        return response.get_json()
    
    def assert_status_code(self, response, expected_status):
        """Helper method to assert response status code"""
        self.assertEqual(response.status_code, expected_status,
                        f"Expected status {expected_status}, got {response.status_code}")
    
    def assert_json_contains(self, response, key, expected_value=None):
        """Helper method to assert JSON response contains a key"""
        json_data = self.get_json_response(response)
        self.assertIn(key, json_data, f"Key '{key}' not found in response")
        
        if expected_value is not None:
            self.assertEqual(json_data[key], expected_value,
                           f"Expected {key}='{expected_value}', got '{json_data[key]}'")
    
    def create_test_config(self):
        """Create a test QuickBooks configuration"""
        from application.models.central_models import QuickBooksConfig
        
        config = QuickBooksConfig.update_config(
            access_token="test_access_token",
            refresh_token="test_refresh_token",
            realm_id="test_realm_id",
            is_active=True
        )
        db.session.commit()
        return config


if __name__ == '__main__':
    unittest.main()
