"""
Tests for health check endpoints
"""

import unittest
from tests.base_test import BaseTestCase


class TestHealthEndpoints(BaseTestCase):
    """Test cases for health check endpoints"""
    
    def test_basic_health_check(self):
        """Test basic health check endpoint"""
        response = self.client.get('/health/')
        
        self.assert_status_code(response, 200)
        self.assert_json_contains(response, 'status', 'healthy')
        self.assert_json_contains(response, 'service', 'EAUR MIS-QuickBooks Integration')
        self.assert_json_contains(response, 'version', '1.0.0')
        self.assert_json_contains(response, 'timestamp')
    
    def test_detailed_health_check(self):
        """Test detailed health check endpoint"""
        response = self.client.get('/health/detailed')
        
        # Should return 503 since no databases are configured in testing
        self.assert_status_code(response, 503)
        self.assert_json_contains(response, 'status', 'degraded')
        self.assert_json_contains(response, 'service', 'EAUR MIS-QuickBooks Integration')
        self.assert_json_contains(response, 'version', '1.0.0')
        self.assert_json_contains(response, 'checks')
        
        # Check that configuration checks are present
        json_data = self.get_json_response(response)
        self.assertIn('configuration', json_data['checks'])
        self.assertIn('databases', json_data['checks'])
    
    def test_kubernetes_endpoints_removed(self):
        """Test that Kubernetes endpoints are no longer available"""
        # Test that /health/ready returns 404
        response = self.client.get('/health/ready')
        self.assert_status_code(response, 404)
        
        # Test that /health/live returns 404
        response = self.client.get('/health/live')
        self.assert_status_code(response, 404)
    
    def test_health_check_structure(self):
        """Test the structure of health check responses"""
        response = self.client.get('/health/')
        json_data = self.get_json_response(response)
        
        # Check required fields are present
        required_fields = ['status', 'timestamp', 'service', 'version']
        for field in required_fields:
            self.assertIn(field, json_data, f"Required field '{field}' missing from health response")
        
        # Check timestamp format (should be ISO format)
        timestamp = json_data['timestamp']
        self.assertIsInstance(timestamp, str)
        self.assertIn('T', timestamp)  # ISO format contains 'T'
    
    def test_detailed_health_check_structure(self):
        """Test the structure of detailed health check responses"""
        response = self.client.get('/health/detailed')
        json_data = self.get_json_response(response)
        
        # Check required fields are present
        required_fields = ['status', 'timestamp', 'service', 'version', 'checks']
        for field in required_fields:
            self.assertIn(field, json_data, f"Required field '{field}' missing from detailed health response")
        
        # Check checks structure
        checks = json_data['checks']
        self.assertIn('configuration', checks)
        self.assertIn('databases', checks)
        
        # Check configuration checks
        config_checks = checks['configuration']
        expected_config_checks = ['encryption_key_configured', 'quickbooks_configured', 'mis_db_configured']
        for check in expected_config_checks:
            self.assertIn(check, config_checks, f"Configuration check '{check}' missing")


if __name__ == '__main__':
    unittest.main()
