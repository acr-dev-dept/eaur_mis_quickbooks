"""
Tests for Invoice Synchronization Service
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tests.base_test import BaseTestCase
from application.services.invoice_sync import InvoiceSyncService, SyncStats, SyncResult, SyncStatus
from application.models.mis_models import TblImvoice, TblPersonalUg


class TestInvoiceSyncService(BaseTestCase):
    """Test cases for InvoiceSyncService"""
    
    def setUp(self):
        """Set up test fixtures"""
        super().setUp()
        self.sync_service = InvoiceSyncService()
    
    def test_sync_stats_creation(self):
        """Test SyncStats dataclass creation"""
        stats = SyncStats(
            total_invoices=100,
            not_synced=80,
            already_synced=15,
            failed=3,
            in_progress=2
        )
        
        self.assertEqual(stats.total_invoices, 100)
        self.assertEqual(stats.not_synced, 80)
        self.assertEqual(stats.already_synced, 15)
        self.assertEqual(stats.failed, 3)
        self.assertEqual(stats.in_progress, 2)
        
        # Test to_dict method
        stats_dict = stats.to_dict()
        expected_dict = {
            'total_invoices': 100,
            'not_synced': 80,
            'already_synced': 15,
            'failed': 3,
            'in_progress': 2
        }
        self.assertEqual(stats_dict, expected_dict)
    
    def test_sync_result_creation(self):
        """Test SyncResult dataclass creation"""
        # Test successful result
        success_result = SyncResult(
            invoice_id=123,
            success=True,
            quickbooks_id="QB-456"
        )
        
        self.assertEqual(success_result.invoice_id, 123)
        self.assertTrue(success_result.success)
        self.assertEqual(success_result.quickbooks_id, "QB-456")
        self.assertIsNone(success_result.error_message)
        
        # Test failed result
        failed_result = SyncResult(
            invoice_id=124,
            success=False,
            error_message="Customer not found"
        )
        
        self.assertEqual(failed_result.invoice_id, 124)
        self.assertFalse(failed_result.success)
        self.assertEqual(failed_result.error_message, "Customer not found")
        self.assertIsNone(failed_result.quickbooks_id)
    
    @patch('application.services.invoice_sync.QuickBooksConfig.is_connected')
    def test_get_qb_service_not_connected(self, mock_is_connected):
        """Test _get_qb_service when QuickBooks is not connected"""
        mock_is_connected.return_value = False
        
        with self.assertRaises(Exception) as context:
            self.sync_service._get_qb_service()
        
        self.assertIn("QuickBooks is not connected", str(context.exception))
    
    @patch('application.services.invoice_sync.db_manager')
    def test_analyze_sync_requirements(self, mock_db_manager):
        """Test analyze_sync_requirements method"""
        # Mock database session and queries
        mock_session = Mock()
        mock_db_manager.get_mis_session.return_value = mock_session
        
        # Mock query results
        mock_session.query.return_value.scalar.side_effect = [100, 80, 15, 3, 2]
        
        stats = self.sync_service.analyze_sync_requirements()
        
        self.assertIsInstance(stats, SyncStats)
        self.assertEqual(stats.total_invoices, 100)
        self.assertEqual(stats.not_synced, 80)
        self.assertEqual(stats.already_synced, 15)
        self.assertEqual(stats.failed, 3)
        self.assertEqual(stats.in_progress, 2)
        
        # Verify session was closed
        mock_session.close.assert_called_once()
    
    @patch('application.services.invoice_sync.db_manager')
    def test_get_unsynchronized_invoices(self, mock_db_manager):
        """Test get_unsynchronized_invoices method"""
        # Mock database session and query
        mock_session = Mock()
        mock_db_manager.get_mis_session.return_value = mock_session
        
        # Create mock invoice objects
        mock_invoice1 = Mock(spec=TblImvoice)
        mock_invoice1.id = 1
        mock_invoice1.reg_no = "STU001"
        
        mock_invoice2 = Mock(spec=TblImvoice)
        mock_invoice2.id = 2
        mock_invoice2.reg_no = "STU002"
        
        mock_invoices = [mock_invoice1, mock_invoice2]
        
        # Mock query chain
        mock_query = Mock()
        mock_session.query.return_value = mock_query
        mock_query.options.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.all.return_value = mock_invoices
        
        invoices = self.sync_service.get_unsynchronized_invoices(limit=10, offset=0)
        
        self.assertEqual(len(invoices), 2)
        self.assertEqual(invoices[0].id, 1)
        self.assertEqual(invoices[1].id, 2)
        
        # Verify session was closed
        mock_session.close.assert_called_once()
    
    @patch('application.services.invoice_sync.db_manager')
    def test_get_student_details(self, mock_db_manager):
        """Test get_student_details method"""
        # Mock database session
        mock_session = Mock()
        mock_db_manager.get_mis_session.return_value = mock_session
        
        # Mock student object
        mock_student = Mock(spec=TblPersonalUg)
        mock_student.reg_no = "STU001"
        mock_student.first_name = "John"
        mock_student.last_name = "Doe"
        mock_student.email = "john.doe@example.com"
        mock_student.phone = "+250123456789"
        
        # Mock query
        mock_query = Mock()
        mock_session.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = mock_student
        
        student_details = self.sync_service.get_student_details("STU001")
        
        expected_details = {
            'reg_no': 'STU001',
            'first_name': 'John',
            'last_name': 'Doe',
            'email': 'john.doe@example.com',
            'phone': '+250123456789',
            'full_name': 'John Doe'
        }
        
        self.assertEqual(student_details, expected_details)
        
        # Verify session was closed
        mock_session.close.assert_called_once()
    
    @patch('application.services.invoice_sync.db_manager')
    def test_get_student_details_not_found(self, mock_db_manager):
        """Test get_student_details when student is not found"""
        # Mock database session
        mock_session = Mock()
        mock_db_manager.get_mis_session.return_value = mock_session
        
        # Mock query returning None
        mock_query = Mock()
        mock_session.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = None
        
        student_details = self.sync_service.get_student_details("NONEXISTENT")
        
        self.assertIsNone(student_details)
        
        # Verify session was closed
        mock_session.close.assert_called_once()
    
    def test_map_invoice_to_quickbooks(self):
        """Test map_invoice_to_quickbooks method"""
        # Create mock invoice
        mock_invoice = Mock(spec=TblImvoice)
        mock_invoice.id = 123
        mock_invoice.reg_no = "STU001"
        mock_invoice.dept = 1000.0
        mock_invoice.credit = 0.0
        mock_invoice.invoice_date = datetime(2024, 1, 15)
        mock_invoice.comment = "Tuition fee payment"
        mock_invoice.fee_category_rel = Mock()
        mock_invoice.fee_category_rel.name = "Tuition Fee"
        
        # Mock get_student_details
        with patch.object(self.sync_service, 'get_student_details') as mock_get_student:
            mock_get_student.return_value = {
                'full_name': 'John Doe',
                'reg_no': 'STU001'
            }
            
            qb_invoice = self.sync_service.map_invoice_to_quickbooks(mock_invoice)
            
            # Verify mapping
            self.assertEqual(qb_invoice['DocNumber'], 'MIS-123')
            self.assertEqual(qb_invoice['CustomerRef']['name'], 'John Doe')
            self.assertEqual(qb_invoice['TxnDate'], '2024-01-15')
            self.assertEqual(qb_invoice['Line'][0]['Amount'], 1000.0)
            self.assertIn('MIS-123', qb_invoice['PrivateNote'])
            self.assertIn('STU001', qb_invoice['PrivateNote'])
    
    def test_map_invoice_to_quickbooks_no_student(self):
        """Test map_invoice_to_quickbooks when student details are not found"""
        # Create mock invoice
        mock_invoice = Mock(spec=TblImvoice)
        mock_invoice.id = 123
        mock_invoice.reg_no = "STU001"
        mock_invoice.dept = 500.0
        mock_invoice.credit = 0.0
        mock_invoice.invoice_date = datetime(2024, 1, 15)
        mock_invoice.comment = "Fee payment"
        mock_invoice.fee_category_rel = None
        
        # Mock get_student_details returning None
        with patch.object(self.sync_service, 'get_student_details') as mock_get_student:
            mock_get_student.return_value = None
            
            qb_invoice = self.sync_service.map_invoice_to_quickbooks(mock_invoice)
            
            # Verify fallback customer name
            self.assertEqual(qb_invoice['CustomerRef']['name'], 'Student STU001')
            self.assertEqual(qb_invoice['Line'][0]['SalesItemLineDetail']['ItemRef']['name'], 'Tuition Fee')


if __name__ == '__main__':
    unittest.main()
