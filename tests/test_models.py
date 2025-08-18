"""
Tests for database models
"""

import unittest
from datetime import datetime
from tests.base_test import BaseTestCase
from application.models.central_models import QuickBooksConfig, QuickbooksAuditLog, SystemConfiguration, IntegrationLog


class TestQuickBooksConfig(BaseTestCase):
    """Test cases for QuickBooksConfig model"""
    
    def test_create_quickbooks_config(self):
        """Test creating a QuickBooks configuration"""
        config = QuickBooksConfig.update_config(
            access_token="test_access_token",
            refresh_token="test_refresh_token",
            realm_id="test_realm_id",
            is_active=True
        )
        
        self.assertIsNotNone(config)
        self.assertEqual(config.access_token, "test_access_token")
        self.assertEqual(config.refresh_token, "test_refresh_token")
        self.assertEqual(config.realm_id, "test_realm_id")
        self.assertTrue(config.is_active)
    
    def test_get_config_single_instance(self):
        """Test that get_config returns single instance"""
        # Create first config
        config1 = QuickBooksConfig.update_config(
            access_token="token1",
            realm_id="realm1"
        )
        
        # Update config (should update same instance, not create new)
        config2 = QuickBooksConfig.update_config(
            access_token="token2",
            realm_id="realm2"
        )
        
        # Should be same instance
        self.assertEqual(config1.id, config2.id)
        self.assertEqual(config2.access_token, "token2")
        self.assertEqual(config2.realm_id, "realm2")
        
        # Verify only one config exists
        all_configs = QuickBooksConfig.query.all()
        self.assertEqual(len(all_configs), 1)
    
    def test_is_connected_method(self):
        """Test is_connected class method"""
        # Initially not connected
        self.assertFalse(QuickBooksConfig.is_connected())
        
        # Create config but not active
        QuickBooksConfig.update_config(
            access_token="test_token",
            refresh_token="test_refresh",
            is_active=False
        )
        self.assertFalse(QuickBooksConfig.is_connected())
        
        # Make it active but missing tokens
        QuickBooksConfig.update_config(is_active=True, access_token=None)
        self.assertFalse(QuickBooksConfig.is_connected())
        
        # Fully connected
        QuickBooksConfig.update_config(
            access_token="test_token",
            refresh_token="test_refresh",
            is_active=True
        )
        self.assertTrue(QuickBooksConfig.is_connected())
    
    def test_config_timestamps(self):
        """Test that timestamps are set correctly"""
        config = QuickBooksConfig.update_config(
            access_token="test_token",
            connected_at=datetime.utcnow()
        )
        
        self.assertIsNotNone(config.created_at)
        self.assertIsNotNone(config.updated_at)
        self.assertIsNotNone(config.connected_at)


class TestQuickbooksAuditLog(BaseTestCase):
    """Test cases for QuickbooksAuditLog model"""
    
    def test_create_audit_log(self):
        """Test creating an audit log entry"""
        log_entry = QuickbooksAuditLog.add_audit_log(
            action_type="Test Action",
            operation_status="Success",
            request_payload={"test": "data"},
            response_payload={"result": "success"}
        )
        
        self.assertIsNotNone(log_entry)
        self.assertEqual(log_entry.action_type, "Test Action")
        self.assertEqual(log_entry.operation_status, "Success")
        self.assertEqual(log_entry.request_payload, {"test": "data"})
        self.assertEqual(log_entry.response_payload, {"result": "success"})
    
    def test_audit_log_with_error(self):
        """Test creating an audit log entry with error"""
        log_entry = QuickbooksAuditLog.add_audit_log(
            action_type="Failed Action",
            operation_status="Failure",
            error_message="Test error message"
        )
        
        self.assertIsNotNone(log_entry)
        self.assertEqual(log_entry.action_type, "Failed Action")
        self.assertEqual(log_entry.operation_status, "Failure")
        self.assertEqual(log_entry.error_message, "Test error message")
    
    def test_audit_log_timestamps(self):
        """Test that audit log timestamps are set"""
        log_entry = QuickbooksAuditLog.add_audit_log(
            action_type="Timestamp Test",
            operation_status="Success"
        )
        
        self.assertIsNotNone(log_entry.created_at)
        self.assertIsNotNone(log_entry.updated_at)


class TestSystemConfiguration(BaseTestCase):
    """Test cases for SystemConfiguration model"""
    
    def test_create_system_config(self):
        """Test creating a system configuration"""
        config = SystemConfiguration(
            key="test_key",
            value="test_value",
            description="Test configuration"
        )
        
        from application import db
        db.session.add(config)
        db.session.commit()
        
        self.assertIsNotNone(config.id)
        self.assertEqual(config.key, "test_key")
        self.assertEqual(config.value, "test_value")
        self.assertEqual(config.description, "Test configuration")


class TestIntegrationLog(BaseTestCase):
    """Test cases for IntegrationLog model"""
    
    def test_create_integration_log(self):
        """Test creating an integration log entry"""
        log_entry = IntegrationLog(
            system_name="QuickBooks",
            operation="Sync Students",
            status="Success"
        )

        from application import db
        db.session.add(log_entry)
        db.session.commit()

        self.assertIsNotNone(log_entry.id)
        self.assertEqual(log_entry.system_name, "QuickBooks")
        self.assertEqual(log_entry.operation, "Sync Students")
        self.assertEqual(log_entry.status, "Success")


if __name__ == '__main__':
    unittest.main()
