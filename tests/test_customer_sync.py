"""
Tests for Customer Synchronization Service
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tests.base_test import BaseTestCase
from application.services.customer_sync import CustomerSyncService, CustomerSyncStats, CustomerSyncResult, CustomerSyncStatus
from application.models.mis_models import TblOnlineApplication, TblPersonalUg


class TestCustomerSyncService(BaseTestCase):
    """Test cases for CustomerSyncService"""
    
    def setUp(self):
        """Set up test fixtures"""
        super().setUp()
        self.sync_service = CustomerSyncService()
    
    def test_customer_sync_stats_creation(self):
        """Test CustomerSyncStats dataclass creation"""
        stats = CustomerSyncStats(
            total_applicants=100,
            applicants_not_synced=80,
            applicants_synced=15,
            applicants_failed=3,
            applicants_in_progress=2,
            total_students=200,
            students_not_synced=150,
            students_synced=40,
            students_failed=8,
            students_in_progress=2
        )
        
        self.assertEqual(stats.total_applicants, 100)
        self.assertEqual(stats.applicants_not_synced, 80)
        self.assertEqual(stats.total_students, 200)
        self.assertEqual(stats.students_synced, 40)
        
        # Test to_dict method
        stats_dict = stats.to_dict()
        self.assertIn('applicants', stats_dict)
        self.assertIn('students', stats_dict)
        self.assertIn('overall', stats_dict)
        
        # Check overall calculations
        self.assertEqual(stats_dict['overall']['total_customers'], 300)
        self.assertEqual(stats_dict['overall']['total_synced'], 55)
    
    def test_customer_sync_result_creation(self):
        """Test CustomerSyncResult dataclass creation"""
        # Test successful applicant result
        success_result = CustomerSyncResult(
            customer_id="123",
            customer_type="Applicant",
            success=True,
            quickbooks_id="QB-456"
        )
        
        self.assertEqual(success_result.customer_id, "123")
        self.assertEqual(success_result.customer_type, "Applicant")
        self.assertTrue(success_result.success)
        self.assertEqual(success_result.quickbooks_id, "QB-456")
        self.assertIsNone(success_result.error_message)
        
        # Test failed student result
        failed_result = CustomerSyncResult(
            customer_id="STU001",
            customer_type="Student",
            success=False,
            error_message="Customer creation failed"
        )
        
        self.assertEqual(failed_result.customer_id, "STU001")
        self.assertEqual(failed_result.customer_type, "Student")
        self.assertFalse(failed_result.success)
        self.assertEqual(failed_result.error_message, "Customer creation failed")
        self.assertIsNone(failed_result.quickbooks_id)
    
    @patch('application.services.customer_sync.QuickBooksConfig.is_connected')
    def test_get_qb_service_not_connected(self, mock_is_connected):
        """Test _get_qb_service when QuickBooks is not connected"""
        mock_is_connected.return_value = False
        
        with self.assertRaises(Exception) as context:
            self.sync_service._get_qb_service()
        
        self.assertIn("QuickBooks is not connected", str(context.exception))
    
    @patch('application.services.customer_sync.db_manager')
    def test_analyze_customer_sync_requirements(self, mock_db_manager):
        """Test analyze_customer_sync_requirements method"""
        # Mock database session and queries
        mock_session = Mock()
        mock_db_manager.get_mis_session.return_value = mock_session
        
        # Mock query results for applicants and students
        mock_session.query.return_value.scalar.side_effect = [
            100, 80, 15, 3, 2,  # Applicant stats
            200, 150, 40, 8, 2  # Student stats
        ]
        
        stats = self.sync_service.analyze_customer_sync_requirements()
        
        self.assertIsInstance(stats, CustomerSyncStats)
        self.assertEqual(stats.total_applicants, 100)
        self.assertEqual(stats.applicants_not_synced, 80)
        self.assertEqual(stats.total_students, 200)
        self.assertEqual(stats.students_not_synced, 150)
        
        # Verify session was closed
        mock_session.close.assert_called_once()
    
    @patch('application.services.customer_sync.db_manager')
    def test_get_unsynchronized_applicants(self, mock_db_manager):
        """Test get_unsynchronized_applicants method"""
        # Mock database session and query
        mock_session = Mock()
        mock_db_manager.get_mis_session.return_value = mock_session
        
        # Create mock applicant objects
        mock_applicant1 = Mock(spec=TblOnlineApplication)
        mock_applicant1.appl_Id = 1
        mock_applicant1.tracking_id = "APP001"
        
        mock_applicant2 = Mock(spec=TblOnlineApplication)
        mock_applicant2.appl_Id = 2
        mock_applicant2.tracking_id = "APP002"
        
        mock_applicants = [mock_applicant1, mock_applicant2]
        
        # Mock query chain
        mock_query = Mock()
        mock_session.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.all.return_value = mock_applicants
        
        applicants = self.sync_service.get_unsynchronized_applicants(limit=10, offset=0)
        
        self.assertEqual(len(applicants), 2)
        self.assertEqual(applicants[0].appl_Id, 1)
        self.assertEqual(applicants[1].appl_Id, 2)
        
        # Verify session was closed
        mock_session.close.assert_called_once()
    
    @patch('application.services.customer_sync.db_manager')
    def test_get_unsynchronized_students(self, mock_db_manager):
        """Test get_unsynchronized_students method"""
        # Mock database session and query
        mock_session = Mock()
        mock_db_manager.get_mis_session.return_value = mock_session
        
        # Create mock student objects
        mock_student1 = Mock(spec=TblPersonalUg)
        mock_student1.per_id_ug = 1
        mock_student1.reg_no = "STU001"
        
        mock_student2 = Mock(spec=TblPersonalUg)
        mock_student2.per_id_ug = 2
        mock_student2.reg_no = "STU002"
        
        mock_students = [mock_student1, mock_student2]
        
        # Mock query chain
        mock_query = Mock()
        mock_session.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.all.return_value = mock_students
        
        students = self.sync_service.get_unsynchronized_students(limit=10, offset=0)
        
        self.assertEqual(len(students), 2)
        self.assertEqual(students[0].per_id_ug, 1)
        self.assertEqual(students[1].per_id_ug, 2)
        
        # Verify session was closed
        mock_session.close.assert_called_once()
    
    def test_map_applicant_to_quickbooks_customer(self):
        """Test map_applicant_to_quickbooks_customer method"""
        # Create mock applicant
        mock_applicant = Mock(spec=TblOnlineApplication)
        mock_applicant.appl_Id = 123
        mock_applicant.to_dict_for_quickbooks.return_value = {
            'appl_Id': 123,
            'tracking_id': 'APP123',
            'display_name': 'John Doe',
            'first_name': 'John',
            'family_name': 'Doe',
            'middle_name': '',
            'phone': '+250123456789',
            'email': 'john@example.com',
            'sex': 'Male',
            'country_of_birth': 'Rwanda',
            'national_id': '1234567890123456',
            'campus_name': 'Nyagatare Campus',
            'intake_details': 'January 2024',
            'program_name': 'Computer Science',
            'program_mode': 'Evening'
        }
        
        qb_customer = self.sync_service.map_applicant_to_quickbooks_customer(mock_applicant)
        
        # Verify mapping
        self.assertEqual(qb_customer['Name'], 'John Doe')
        self.assertEqual(qb_customer['DisplayName'], 'John Doe')
        self.assertEqual(qb_customer['GivenName'], 'John')
        self.assertEqual(qb_customer['FamilyName'], 'Doe')
        self.assertEqual(qb_customer['PrimaryPhone']['FreeFormNumber'], '+250123456789')
        self.assertEqual(qb_customer['PrimaryEmailAddr']['Address'], 'john@example.com')
        
        # Check custom fields
        custom_fields = qb_customer['CustomField']
        customer_type_field = next(field for field in custom_fields if field['Name'] == 'CustomerType')
        self.assertEqual(customer_type_field['StringValue'], 'Applicant')
        
        app_id_field = next(field for field in custom_fields if field['Name'] == 'ApplicationID')
        self.assertEqual(app_id_field['StringValue'], '123')
    
    def test_map_student_to_quickbooks_customer(self):
        """Test map_student_to_quickbooks_customer method"""
        # Create mock student
        mock_student = Mock(spec=TblPersonalUg)
        mock_student.reg_no = "STU001"
        mock_student.to_dict_for_quickbooks.return_value = {
            'per_id_ug': 456,
            'reg_no': 'STU001',
            'display_name': 'Jane Smith',
            'first_name': 'Jane',
            'last_name': 'Smith',
            'middle_name': '',
            'phone': '+250987654321',
            'email': 'jane@example.com',
            'sex': 'Female',
            'national_id': '9876543210987654',
            'level_name': 'Bachelor Level 1',
            'campus_name': 'Kigali Campus',
            'intake_details': 'September 2023',
            'program_name': 'Business Administration',
            'program_type': 'Regular'
        }
        
        qb_customer = self.sync_service.map_student_to_quickbooks_customer(mock_student)
        
        # Verify mapping
        self.assertEqual(qb_customer['Name'], 'Jane Smith')
        self.assertEqual(qb_customer['DisplayName'], 'Jane Smith')
        self.assertEqual(qb_customer['GivenName'], 'Jane')
        self.assertEqual(qb_customer['FamilyName'], 'Smith')
        self.assertEqual(qb_customer['PrimaryPhone']['FreeFormNumber'], '+250987654321')
        self.assertEqual(qb_customer['PrimaryEmailAddr']['Address'], 'jane@example.com')
        
        # Check custom fields
        custom_fields = qb_customer['CustomField']
        customer_type_field = next(field for field in custom_fields if field['Name'] == 'CustomerType')
        self.assertEqual(customer_type_field['StringValue'], 'Student')
        
        reg_no_field = next(field for field in custom_fields if field['Name'] == 'RegNo')
        self.assertEqual(reg_no_field['StringValue'], 'STU001')
    
    @patch('application.services.customer_sync.db_manager')
    def test_update_applicant_sync_status(self, mock_db_manager):
        """Test _update_applicant_sync_status method"""
        # Mock database session
        mock_session = Mock()
        mock_db_manager.get_mis_session.return_value = mock_session
        
        # Mock applicant object
        mock_applicant = Mock(spec=TblOnlineApplication)
        mock_session.query.return_value.filter.return_value.first.return_value = mock_applicant
        
        # Test status update
        self.sync_service._update_applicant_sync_status(123, CustomerSyncStatus.SYNCED.value, "QB-456")
        
        # Verify updates
        self.assertEqual(mock_applicant.QuickBk_Status, CustomerSyncStatus.SYNCED.value)
        self.assertEqual(mock_applicant.pushed_by, "CustomerSyncService")
        self.assertIsNotNone(mock_applicant.pushed_date)
        
        # Verify session operations
        mock_session.commit.assert_called_once()
        mock_session.close.assert_called_once()
    
    @patch('application.services.customer_sync.db_manager')
    def test_update_student_sync_status(self, mock_db_manager):
        """Test _update_student_sync_status method"""
        # Mock database session
        mock_session = Mock()
        mock_db_manager.get_mis_session.return_value = mock_session
        
        # Mock student object
        mock_student = Mock(spec=TblPersonalUg)
        mock_session.query.return_value.filter.return_value.first.return_value = mock_student
        
        # Test status update
        self.sync_service._update_student_sync_status(456, CustomerSyncStatus.SYNCED.value, "QB-789")
        
        # Verify updates
        self.assertEqual(mock_student.QuickBk_Status, CustomerSyncStatus.SYNCED.value)
        self.assertEqual(mock_student.pushed_by, "CustomerSyncService")
        self.assertEqual(mock_student.qk_id, "QB-789")
        self.assertIsNotNone(mock_student.pushed_date)
        
        # Verify session operations
        mock_session.commit.assert_called_once()
        mock_session.close.assert_called_once()


if __name__ == '__main__':
    unittest.main()
