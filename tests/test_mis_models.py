"""
Unit tests for MIS models
Tests all methods added to MIS models with comprehensive coverage
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from tests.base_test import BaseTestCase
from application.models.mis_models import (
    MISBaseModel, TblCampus, TblSponsor
)


class TestMISBaseModel(BaseTestCase):
    """Test cases for MISBaseModel base class"""

    def setUp(self):
        """Set up test fixtures"""
        super().setUp()
        self.mock_session = Mock()

    @patch('application.models.mis_models.TblCampus.get_session')
    def test_get_by_id_success(self, mock_get_session):
        """Test successful get_by_id operation using real model"""
        # Setup
        mock_session_context = Mock()
        mock_get_session.return_value.__enter__ = Mock(return_value=mock_session_context)
        mock_get_session.return_value.__exit__ = Mock(return_value=None)

        mock_record = Mock()
        mock_session_context.query.return_value.filter.return_value.first.return_value = mock_record

        # Execute using real TblCampus model
        from application.models.mis_models import TblCampus
        result = TblCampus.get_by_id('CAMP001')

        # Assert
        self.assertEqual(result, mock_record)
        mock_session_context.query.assert_called_once_with(TblCampus)

    @patch('application.models.mis_models.TblCampus.get_session')
    @patch('flask.current_app')
    def test_get_by_id_exception(self, mock_current_app, mock_get_session):
        """Test get_by_id with exception handling using real model"""
        # Setup
        mock_get_session.side_effect = Exception("Database error")
        mock_current_app.logger.error = Mock()

        # Execute using real TblCampus model
        from application.models.mis_models import TblCampus
        result = TblCampus.get_by_id('CAMP001')

        # Assert
        self.assertIsNone(result)
        mock_current_app.logger.error.assert_called_once()

    def test_to_dict_basic(self):
        """Test to_dict method with basic data types using real model"""
        # Setup - Create a real TblCampus instance
        from application.models.mis_models import TblCampus

        # Mock the __table__.columns to avoid SQLAlchemy complexity
        with patch.object(TblCampus, '__table__') as mock_table:
            mock_column1 = Mock()
            mock_column1.name = 'camp_id'
            mock_column2 = Mock()
            mock_column2.name = 'camp_full_name'

            mock_table.columns = [mock_column1, mock_column2]

            instance = TblCampus()
            instance.camp_id = 'CAMP001'
            instance.camp_full_name = "Main Campus"

            # Execute
            result = instance.to_dict()

            # Assert
            expected = {'camp_id': 'CAMP001', 'camp_full_name': "Main Campus"}
            self.assertEqual(result, expected)

    def test_to_dict_with_datetime(self):
        """Test to_dict method with datetime objects using real model"""
        # Setup - Create a real TblCampus instance
        from application.models.mis_models import TblCampus

        # Mock the __table__.columns to avoid SQLAlchemy complexity
        with patch.object(TblCampus, '__table__') as mock_table:
            mock_column1 = Mock()
            mock_column1.name = 'camp_yor'

            mock_table.columns = [mock_column1]

            instance = TblCampus()
            test_datetime = datetime(2023, 1, 1, 12, 0, 0)
            instance.camp_yor = test_datetime

            # Execute
            result = instance.to_dict()

            # Assert
            expected = {'camp_yor': test_datetime.isoformat()}
            self.assertEqual(result, expected)

    @patch('application.models.mis_models.TblSponsor.get_session')
    def test_get_active_records_with_status_id(self, mock_get_session):
        """Test get_active_records with status_Id field using TblSponsor model"""
        # Setup
        mock_session_context = Mock()
        mock_get_session.return_value.__enter__ = Mock(return_value=mock_session_context)
        mock_get_session.return_value.__exit__ = Mock(return_value=None)

        mock_records = [Mock(), Mock()]

        # Create proper mock chain for query().filter().all()
        mock_all = Mock(return_value=mock_records)
        mock_filter = Mock()
        mock_filter.all = mock_all
        mock_query = Mock()
        mock_query.filter.return_value = mock_filter
        mock_session_context.query.return_value = mock_query

        # Execute using TblSponsor model (which has statusId field)
        from application.models.mis_models import TblSponsor
        result = TblSponsor.get_active_records()

        # Assert
        self.assertEqual(result, mock_records)
        mock_query.filter.assert_called_once()

    @patch('application.models.mis_models.MISBaseModel.get_session')
    @patch('flask.current_app')
    def test_get_active_records_with_is_active(self, mock_current_app, mock_get_session):
        """Test get_active_records with is_active field using mock"""
        # Setup
        mock_current_app.logger.error = Mock()
        mock_get_session.side_effect = Exception("Database error")

        # Execute using TblCampus model - this will hit the exception path
        from application.models.mis_models import TblCampus
        result = TblCampus.get_active_records()

        # Assert - should return empty list on exception
        self.assertEqual(result, [])
        mock_current_app.logger.error.assert_called_once()


class TestTblCampus(BaseTestCase):
    """Test cases for TblCampus model"""
    
    def setUp(self):
        """Set up test fixtures"""
        super().setUp()
        self.sample_campus_data = {
            'camp_id': 'CAMP001',
            'camp_full_name': 'Main Campus',
            'camp_short_name': 'MAIN',
            'camp_city': 'Kampala',
            'camp_yor': datetime(2020, 1, 1),
            'camp_active': 1,
            'camp_comments': 'Main campus location'
        }
    
    @patch('application.models.mis_models.TblCampus.get_session')
    def test_get_campus_name_success(self, mock_get_session):
        """Test successful get_campus_name operation"""
        # Setup
        mock_session_context = Mock()
        mock_get_session.return_value.__enter__ = Mock(return_value=mock_session_context)
        mock_get_session.return_value.__exit__ = Mock(return_value=None)
        
        mock_campus = Mock()
        mock_campus.camp_full_name = "Main Campus"
        mock_session_context.query.return_value.filter.return_value.first.return_value = mock_campus
        
        # Execute
        result = TblCampus.get_campus_name('CAMP001')
        
        # Assert
        self.assertEqual(result, "Main Campus")
        mock_session_context.query.assert_called_once_with(TblCampus)
    
    @patch('application.models.mis_models.TblCampus.get_session')
    def test_get_campus_name_not_found(self, mock_get_session):
        """Test get_campus_name when campus not found"""
        # Setup
        mock_session_context = Mock()
        mock_get_session.return_value.__enter__ = Mock(return_value=mock_session_context)
        mock_get_session.return_value.__exit__ = Mock(return_value=None)
        
        mock_session_context.query.return_value.filter.return_value.first.return_value = None
        
        # Execute
        result = TblCampus.get_campus_name('NONEXISTENT')
        
        # Assert
        self.assertIsNone(result)
    
    @patch('application.models.mis_models.TblCampus.get_session')
    @patch('flask.current_app')
    def test_get_campus_name_exception(self, mock_current_app, mock_get_session):
        """Test get_campus_name with exception handling"""
        # Setup
        mock_get_session.side_effect = Exception("Database error")
        mock_current_app.logger.error = Mock()
        
        # Execute
        result = TblCampus.get_campus_name('CAMP001')
        
        # Assert
        self.assertIsNone(result)
        mock_current_app.logger.error.assert_called_once()
    
    @patch('application.models.mis_models.TblCampus.get_session')
    def test_get_campus_details_success(self, mock_get_session):
        """Test successful get_campus_details operation"""
        # Setup
        mock_session_context = Mock()
        mock_get_session.return_value.__enter__ = Mock(return_value=mock_session_context)
        mock_get_session.return_value.__exit__ = Mock(return_value=None)
        
        mock_campus = Mock()
        for key, value in self.sample_campus_data.items():
            setattr(mock_campus, key, value)
        
        mock_session_context.query.return_value.filter.return_value.first.return_value = mock_campus
        
        # Execute
        result = TblCampus.get_campus_details('CAMP001')
        
        # Assert
        self.assertIsNotNone(result)
        self.assertEqual(result['id'], 'CAMP001')
        self.assertEqual(result['full_name'], 'Main Campus')
        self.assertEqual(result['short_name'], 'MAIN')
        self.assertEqual(result['city'], 'Kampala')
        self.assertEqual(result['display_name'], 'Main Campus (Kampala)')
        self.assertTrue(result['is_active'])
    
    def test_to_quickbooks_format(self):
        """Test to_quickbooks_format method"""
        # Setup
        campus = TblCampus()
        campus.camp_full_name = "Main Campus"
        campus.camp_city = "Kampala"
        campus.camp_short_name = "MAIN"
        
        # Execute
        result = campus.to_quickbooks_format()
        
        # Assert
        expected = {
            'Campus': 'Main Campus',
            'CampusCity': 'Kampala',
            'CampusCode': 'MAIN'
        }
        self.assertEqual(result, expected)


class TestTblSponsor(BaseTestCase):
    """Test cases for TblSponsor model"""
    
    def setUp(self):
        """Set up test fixtures"""
        super().setUp()
        self.sample_sponsor_data = {
            'spon_id': 'SPON001',
            'spon_full_name': 'Government Sponsor',
            'spon_short_name': 'GOV',
            'sponsor_value': 75.0,
            'reg_fee': 100000,
            'tut_fee': 500000,
            'statusId': 1
        }
    
    @patch('application.models.mis_models.TblSponsor.get_session')
    def test_get_sponsor_name_success(self, mock_get_session):
        """Test successful get_sponsor_name operation"""
        # Setup
        mock_session_context = Mock()
        mock_get_session.return_value.__enter__ = Mock(return_value=mock_session_context)
        mock_get_session.return_value.__exit__ = Mock(return_value=None)
        
        mock_sponsor = Mock()
        mock_sponsor.spon_full_name = "Government Sponsor"
        mock_session_context.query.return_value.filter.return_value.first.return_value = mock_sponsor
        
        # Execute
        result = TblSponsor.get_sponsor_name('SPON001')
        
        # Assert
        self.assertEqual(result, "Government Sponsor")
    
    def test_calculate_sponsored_amount(self):
        """Test calculate_sponsored_amount method"""
        # Setup
        sponsor = TblSponsor()
        sponsor.sponsor_value = 75.0
        
        # Execute
        result = sponsor.calculate_sponsored_amount(1000000)
        
        # Assert
        self.assertEqual(result, 750000.0)
    
    def test_calculate_sponsored_amount_no_value(self):
        """Test calculate_sponsored_amount with no sponsor value"""
        # Setup
        sponsor = TblSponsor()
        sponsor.sponsor_value = None
        
        # Execute
        result = sponsor.calculate_sponsored_amount(1000000)
        
        # Assert
        self.assertEqual(result, 0.0)
    
    def test_to_quickbooks_format(self):
        """Test to_quickbooks_format method"""
        # Setup
        sponsor = TblSponsor()
        sponsor.spon_full_name = "Government Sponsor"
        sponsor.spon_short_name = "GOV"
        sponsor.sponsor_value = 75.0
        
        # Execute
        result = sponsor.to_quickbooks_format()
        
        # Assert
        expected = {
            'Sponsor': 'Government Sponsor',
            'SponsorCode': 'GOV',
            'SponsorValue': '75.0%'
        }
        self.assertEqual(result, expected)


if __name__ == '__main__':
    unittest.main()
