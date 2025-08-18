"""
Tests for QuickBooks API endpoints
"""

import unittest
from unittest.mock import patch, MagicMock
from tests.base_test import BaseTestCase
from application.models.central_models import QuickBooksConfig


class TestQuickBooksAPI(BaseTestCase):
    """Test cases for QuickBooks API endpoints"""
    
    def test_get_auth_url(self):
        """Test getting QuickBooks authorization URL"""
        with patch('application.api.v1.quickbooks.QuickBooks') as mock_qb:
            mock_instance = MagicMock()
            mock_instance.get_authorization_url.return_value = "https://test-auth-url.com"
            mock_qb.return_value = mock_instance

            response = self.client.get('/api/v1/quickbooks/get_auth_url')

            # Should redirect to the authorization URL
            self.assert_status_code(response, 302)
            self.assertEqual(response.location, "https://test-auth-url.com")
    
    def test_get_company_info_not_connected(self):
        """Test getting company info when QuickBooks is not connected"""
        response = self.client.get('/api/v1/quickbooks/get_company_info')
        
        self.assert_status_code(response, 400)
        self.assert_json_contains(response, 'error', 'QuickBooks not connected')
    
    def test_get_company_info_connected(self):
        """Test getting company info when QuickBooks is connected"""
        # Create test configuration
        self.create_test_config()
        
        with patch('application.api.v1.quickbooks.QuickBooks') as mock_qb:
            mock_instance = MagicMock()
            mock_instance.get_company_info.return_value = {"company": "Test Company"}
            mock_qb.return_value = mock_instance
            
            response = self.client.get('/api/v1/quickbooks/get_company_info')
            
            self.assert_status_code(response, 200)
            json_data = self.get_json_response(response)
            self.assertEqual(json_data, {"company": "Test Company"})
    
    def test_get_accounts_not_connected(self):
        """Test getting accounts when QuickBooks is not connected"""
        response = self.client.get('/api/v1/quickbooks/get_accounts')
        
        self.assert_status_code(response, 400)
        self.assert_json_contains(response, 'error', 'QuickBooks not connected')
    
    def test_get_accounts_connected(self):
        """Test getting accounts when QuickBooks is connected"""
        # Create test configuration
        self.create_test_config()
        
        with patch('application.api.v1.quickbooks.QuickBooks') as mock_qb:
            mock_instance = MagicMock()
            mock_instance.get_accounts.return_value = [{"id": 1, "name": "Test Account"}]
            mock_qb.return_value = mock_instance
            
            response = self.client.get('/api/v1/quickbooks/get_accounts')
            
            self.assert_status_code(response, 200)
            json_data = self.get_json_response(response)
            self.assertEqual(json_data, [{"id": 1, "name": "Test Account"}])
    
    def test_get_vendors_not_connected(self):
        """Test getting vendors when QuickBooks is not connected"""
        response = self.client.get('/api/v1/quickbooks/get_vendors')
        
        self.assert_status_code(response, 400)
        self.assert_json_contains(response, 'error', 'QuickBooks not connected')
    
    def test_get_vendors_connected(self):
        """Test getting vendors when QuickBooks is connected"""
        # Create test configuration
        self.create_test_config()
        
        with patch('application.api.v1.quickbooks.QuickBooks') as mock_qb:
            mock_instance = MagicMock()
            mock_instance.get_vendors.return_value = [{"id": 1, "name": "Test Vendor"}]
            mock_qb.return_value = mock_instance
            
            response = self.client.get('/api/v1/quickbooks/get_vendors')
            
            self.assert_status_code(response, 200)
            json_data = self.get_json_response(response)
            self.assertEqual(json_data, [{"id": 1, "name": "Test Vendor"}])
    
    def test_disconnect_not_connected(self):
        """Test disconnecting when QuickBooks is not connected"""
        response = self.client.get('/api/v1/quickbooks/disconnect')
        
        self.assert_status_code(response, 400)
        self.assert_json_contains(response, 'error', 'QuickBooks not connected')
    
    def test_disconnect_connected(self):
        """Test disconnecting when QuickBooks is connected"""
        # Create test configuration
        self.create_test_config()
        
        with patch('application.api.v1.quickbooks.QuickBooks') as mock_qb:
            mock_instance = MagicMock()
            mock_instance.disconnect_app.return_value = True
            mock_qb.return_value = mock_instance
            
            response = self.client.get('/api/v1/quickbooks/disconnect')
            
            self.assert_status_code(response, 200)
            self.assert_json_contains(response, 'success', True)
            self.assert_json_contains(response, 'message', 'QuickBooks integration disconnected successfully!')
    
    def test_webhook_callback(self):
        """Test QuickBooks OAuth webhook callback"""
        with patch('application.api.v1.quickbooks.QuickBooks') as mock_qb, \
             patch('application.api.v1.quickbooks.QuickBooksHelper') as mock_helper:
            
            mock_instance = MagicMock()
            mock_instance.get_quickbooks_access_token.return_value = {
                'access_token': 'test_access_token',
                'refresh_token': 'test_refresh_token'
            }
            mock_qb.return_value = mock_instance
            
            mock_helper.encrypt.side_effect = lambda x: f"encrypted_{x}"
            
            response = self.client.get('/api/v1/quickbooks/webhook?code=test_code&realmId=test_realm')
            
            self.assert_status_code(response, 200)
            self.assert_json_contains(response, 'success', True)
            self.assert_json_contains(response, 'message', 'QuickBooks integration successful')
    
    def test_webhook_callback_missing_params(self):
        """Test QuickBooks webhook callback with missing parameters"""
        # Missing code parameter
        response = self.client.get('/api/v1/quickbooks/webhook?realmId=test_realm')
        self.assert_status_code(response, 400)
        
        # Missing realmId parameter
        response = self.client.get('/api/v1/quickbooks/webhook?code=test_code')
        self.assert_status_code(response, 400)


if __name__ == '__main__':
    unittest.main()
