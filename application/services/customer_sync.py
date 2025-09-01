"""
Customer Synchronization Service for EAUR MIS-QuickBooks Integration

This service handles the synchronization of applicants and students from MIS to QuickBooks
as customers with proper custom fields and data enrichment.
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum
import json
import time

from flask import current_app
from sqlalchemy import and_, or_, func
from sqlalchemy.orm import joinedload

from application.models.mis_models import TblOnlineApplication, TblPersonalUg
from application.models.central_models import QuickBooksConfig, QuickbooksAuditLog
from application.services.quickbooks import QuickBooks
from application.utils.database import db_manager
from application import db

logger = logging.getLogger(__name__)

class CustomerSyncStatus(Enum):
    """Customer synchronization status enumeration"""
    NOT_SYNCED = 0
    SYNCED = 1
    FAILED = 2
    IN_PROGRESS = 3

@dataclass
class CustomerSyncStats:
    """Statistics for customer synchronization process"""
    total_applicants: int = 0
    applicants_not_synced: int = 0
    applicants_synced: int = 0
    applicants_failed: int = 0
    applicants_in_progress: int = 0
    
    total_students: int = 0
    students_not_synced: int = 0
    students_synced: int = 0
    students_failed: int = 0
    students_in_progress: int = 0
    
    def to_dict(self) -> Dict:
        return {
            'applicants': {
                'total': self.total_applicants,
                'not_synced': self.applicants_not_synced,
                'synced': self.applicants_synced,
                'failed': self.applicants_failed,
                'in_progress': self.applicants_in_progress
            },
            'students': {
                'total': self.total_students,
                'not_synced': self.students_not_synced,
                'synced': self.students_synced,
                'failed': self.students_failed,
                'in_progress': self.students_in_progress
            },
            'overall': {
                'total_customers': self.total_applicants + self.total_students,
                'total_not_synced': self.applicants_not_synced + self.students_not_synced,
                'total_synced': self.applicants_synced + self.students_synced,
                'total_failed': self.applicants_failed + self.students_failed
            }
        }

@dataclass
class CustomerSyncResult:
    """Result of a single customer synchronization"""
    customer_id: str
    customer_type: str  # 'Applicant' or 'Student'
    success: bool
    quickbooks_id: Optional[str] = None
    error_message: Optional[str] = None
    details: Optional[Dict] = None

class CustomerSyncService:
    """
    Service for synchronizing MIS applicants and students to QuickBooks customers
    """
    
    def __init__(self):
        self.qb_service = None
        self.batch_size = 50  # Process customers in batches
        self.max_retries = 3
        self.retry_delay = 5  # seconds
        
    def _get_qb_service(self) -> QuickBooks:
        """Get QuickBooks service instance"""
        if not self.qb_service:
            if not QuickBooksConfig.is_connected():
                raise Exception("QuickBooks is not connected. Please authenticate first.")
            self.qb_service = QuickBooks()
        return self.qb_service
    
    def analyze_customer_sync_requirements(self) -> CustomerSyncStats:
        """
        Analyze current customer synchronization status
        """
        try:
            with db_manager.get_mis_session() as session:
                # Analyze applicants
                total_applicants = session.query(func.count(TblOnlineApplication.appl_Id)).scalar()
                applicants_not_synced = session.query(func.count(TblOnlineApplication.appl_Id)).filter(
                    or_(TblOnlineApplication.QuickBk_Status == 0, TblOnlineApplication.QuickBk_Status.is_(None))
                ).scalar()
                applicants_synced = session.query(func.count(TblOnlineApplication.appl_Id)).filter(
                    TblOnlineApplication.QuickBk_Status == 1
                ).scalar()
                applicants_failed = session.query(func.count(TblOnlineApplication.appl_Id)).filter(
                    TblOnlineApplication.QuickBk_Status == 2
                ).scalar()
                applicants_in_progress = session.query(func.count(TblOnlineApplication.appl_Id)).filter(
                    TblOnlineApplication.QuickBk_Status == 3
                ).scalar()

                # Analyze students
                total_students = session.query(func.count(TblPersonalUg.per_id_ug)).scalar()
                students_not_synced = session.query(func.count(TblPersonalUg.per_id_ug)).filter(
                    or_(TblPersonalUg.QuickBk_Status == 0, TblPersonalUg.QuickBk_Status.is_(None))
                ).scalar()
                students_synced = session.query(func.count(TblPersonalUg.per_id_ug)).filter(
                    TblPersonalUg.QuickBk_Status == 1
                ).scalar()
                students_failed = session.query(func.count(TblPersonalUg.per_id_ug)).filter(
                    TblPersonalUg.QuickBk_Status == 2
                ).scalar()
                students_in_progress = session.query(func.count(TblPersonalUg.per_id_ug)).filter(
                    TblPersonalUg.QuickBk_Status == 3
                ).scalar()

                stats = CustomerSyncStats(
                    total_applicants=total_applicants,
                    applicants_not_synced=applicants_not_synced,
                    applicants_synced=applicants_synced,
                    applicants_failed=applicants_failed,
                    applicants_in_progress=applicants_in_progress,

                    total_students=total_students,
                    students_not_synced=students_not_synced,
                    students_synced=students_synced,
                    students_failed=students_failed,
                    students_in_progress=students_in_progress
                )

                logger.info(f"Customer sync analysis: {stats.to_dict()}")
                return stats

        except Exception as e:
            logger.error(f"Error analyzing customer sync requirements: {e}")
            raise

    
    def get_unsynchronized_applicants(self, limit: Optional[int] = None, offset: int = 0) -> List[TblOnlineApplication]:
        """
        Get applicants that haven't been synchronized to QuickBooks
        
        Args:
            limit: Maximum number of applicants to return
            offset: Number of applicants to skip
            
        Returns:
            List of unsynchronized applicant objects
        """
        try:
            with db_manager.get_mis_session() as session:
            
                query = session.query(TblOnlineApplication).filter(
                    or_(TblOnlineApplication.QuickBk_Status == 0, TblOnlineApplication.QuickBk_Status.is_(None))
                ).order_by(TblOnlineApplication.appl_date.desc())
                
                if limit:
                    query = query.limit(limit)
                if offset:
                    query = query.offset(offset)
                    
                applicants = query.all()
                logger.info(f"Retrieved {len(applicants)} unsynchronized applicants")
                return applicants
            
        except Exception as e:
            logger.error(f"Error getting unsynchronized applicants: {e}")
            raise
        finally:
            if 'session' in locals():
                session.close()
    
    def get_unsynchronized_students(self, limit: Optional[int] = None, offset: int = 0) -> List[TblPersonalUg]:
        """
        Get students that haven't been synchronized to QuickBooks
        
        Args:
            limit: Maximum number of students to return
            offset: Number of students to skip
            
        Returns:
            List of unsynchronized student objects
        """
        try:
            with db_manager.get_mis_session() as session:
            
                query = session.query(TblPersonalUg).filter(
                    or_(TblPersonalUg.QuickBk_Status == 0, TblPersonalUg.QuickBk_Status.is_(None))
                ).order_by(TblPersonalUg.reg_date.desc())
                
                if limit:
                    query = query.limit(limit)
                if offset:
                    query = query.offset(offset)
                    
                students = query.all()
                logger.info(f"Retrieved {len(students)} unsynchronized students")
                return students
                
        except Exception as e:
            logger.error(f"Error getting unsynchronized students: {e}")
            raise
        finally:
            if 'session' in locals():
                session.close()

    def map_applicant_to_quickbooks_customer(self, applicant: TblOnlineApplication) -> Dict:
        """
        Map MIS applicant data to QuickBooks customer format

        Args:
            applicant: MIS applicant object

        Returns:
            Dictionary formatted for QuickBooks Customer API
        """
        try:
            # Get enriched applicant data
            applicant_data = applicant.to_dict_for_quickbooks()

            # Create QuickBooks customer structure
            qb_customer = {
                "Name": applicant_data['display_name'],
                "DisplayName": applicant_data['display_name'],
                "GivenName": applicant_data['first_name'],
                "FamilyName": applicant_data['family_name'],
                "MiddleName": applicant_data['middle_name'],
                "PrimaryPhone": {
                    "FreeFormNumber": applicant_data['phone']
                } if applicant_data['phone'] else None,
                "PrimaryEmailAddr": {
                    "Address": applicant_data['email']
                } if applicant_data['email'] else None,
                "CustomField": [
                    {
                        "DefinitionId": "1",
                        "Name": "CustomerType",
                        "StringValue": "Applicant"
                    },
                    {
                        "DefinitionId": "2",
                        "Name": "ApplicationID",
                        "StringValue": str(applicant_data['appl_Id'])
                    },
                    {
                        "DefinitionId": "3",
                        "Name": "TrackingID",
                        "StringValue": applicant_data['tracking_id']
                    },
                    {
                        "DefinitionId": "4",
                        "Name": "Gender",
                        "StringValue": applicant_data['sex']
                    },
                    {
                        "DefinitionId": "5",
                        "Name": "BirthCountry",
                        "StringValue": applicant_data['country_of_birth']
                    },
                    {
                        "DefinitionId": "6",
                        "Name": "NationalID",
                        "StringValue": applicant_data['national_id']
                    },
                    {
                        "DefinitionId": "7",
                        "Name": "Campus",
                        "StringValue": applicant_data['campus_name']
                    },
                    {
                        "DefinitionId": "8",
                        "Name": "Intake",
                        "StringValue": applicant_data['intake_details']
                    },
                    {
                        "DefinitionId": "9",
                        "Name": "Program",
                        "StringValue": applicant_data['program_name']
                    },
                    {
                        "DefinitionId": "10",
                        "Name": "ProgramMode",
                        "StringValue": applicant_data['program_mode']
                    }
                ],
                "Notes": f"Applicant synchronized from MIS - Application ID: {applicant_data['appl_Id']}, Tracking ID: {applicant_data['tracking_id']}"
            }

            # Remove None values to clean up the payload
            qb_customer = {k: v for k, v in qb_customer.items() if v is not None}

            return qb_customer

        except Exception as e:
            logger.error(f"Error mapping applicant {applicant.appl_Id} to QuickBooks format: {e}")
            raise

    def map_student_to_quickbooks_customer(self, student: TblPersonalUg) -> Dict:
        """
        Map MIS student data to QuickBooks customer format

        Args:
            student: MIS student object

        Returns:
            Dictionary formatted for QuickBooks Customer API
        """
        try:
            # Get enriched student data
            student_data = student.to_dict_for_quickbooks()

            # Create QuickBooks customer structure
            qb_customer = {
                "Name": student_data['display_name'],
                "DisplayName": student_data['display_name'],
                "GivenName": student_data['first_name'],
                "FamilyName": student_data['last_name'],
                "MiddleName": student_data['middle_name'],
                "PrimaryPhone": {
                    "FreeFormNumber": student_data['phone']
                } if student_data['phone'] else None,
                "PrimaryEmailAddr": {
                    "Address": student_data['email']
                } if student_data['email'] else None,
                "CustomField": [
                    {
                        "DefinitionId": "1",
                        "Name": "CustomerType",
                        "StringValue": "Student"
                    },
                    {
                        "DefinitionId": "2",
                        "Name": "RegNo",
                        "StringValue": student_data['reg_no']
                    },
                    {
                        "DefinitionId": "3",
                        "Name": "Gender",
                        "StringValue": student_data['sex']
                    },
                    {
                        "DefinitionId": "4",
                        "Name": "Level",
                        "StringValue": student_data['level_name']
                    },
                    {
                        "DefinitionId": "5",
                        "Name": "Campus",
                        "StringValue": student_data['campus_name']
                    },
                    {
                        "DefinitionId": "6",
                        "Name": "Intake",
                        "StringValue": student_data['intake_details']
                    },
                    {
                        "DefinitionId": "7",
                        "Name": "Program",
                        "StringValue": student_data['program_name']
                    },
                    {
                        "DefinitionId": "8",
                        "Name": "NationalID",
                        "StringValue": student_data['national_id']
                    },
                    {
                        "DefinitionId": "9",
                        "Name": "ProgramType",
                        "StringValue": student_data['program_type']
                    }
                ],
                "Notes": f"Student synchronized from MIS - Registration Number: {student_data['reg_no']}"
            }

            # Remove None values to clean up the payload
            qb_customer = {k: v for k, v in qb_customer.items() if v is not None}

            return qb_customer

        except Exception as e:
            logger.error(f"Error mapping student {student.reg_no} to QuickBooks format: {e}")
            raise

    def sync_single_applicant(self, applicant: TblOnlineApplication) -> CustomerSyncResult:
        """
        Synchronize a single applicant to QuickBooks

        Args:
            applicant: MIS applicant object to synchronize

        Returns:
            CustomerSyncResult: Result of the synchronization attempt
        """
        try:
            # Mark applicant as in progress
            self._update_applicant_sync_status(applicant.appl_Id, CustomerSyncStatus.IN_PROGRESS.value)

            # Get QuickBooks service
            qb_service = self._get_qb_service()

            # Map applicant data
            qb_customer_data = self.map_applicant_to_quickbooks_customer(applicant)

            # Create customer in QuickBooks
            response = qb_service.create_customer(qb_service.realm_id, qb_customer_data)

            if 'Customer' in response:
                # Success - update sync status
                qb_customer_id = response['Customer']['Id']
                self._update_applicant_sync_status(
                    applicant.appl_Id,
                    CustomerSyncStatus.SYNCED.value,
                    quickbooks_id=qb_customer_id
                )

                # Log successful sync
                self._log_customer_sync_audit(applicant.appl_Id, 'Applicant', 'SUCCESS', f"Synced to QuickBooks ID: {qb_customer_id}")

                return CustomerSyncResult(
                    customer_id=str(applicant.appl_Id),
                    customer_type='Applicant',
                    success=True,
                    quickbooks_id=qb_customer_id,
                    details=response
                )
            else:
                # Handle API error
                error_msg = response.get('Fault', {}).get('Error', [{}])[0].get('Detail', 'Unknown error')
                self._update_applicant_sync_status(applicant.appl_Id, CustomerSyncStatus.FAILED.value)
                self._log_customer_sync_audit(applicant.appl_Id, 'Applicant', 'ERROR', error_msg)

                return CustomerSyncResult(
                    customer_id=str(applicant.appl_Id),
                    customer_type='Applicant',
                    success=False,
                    error_message=error_msg,
                    details=response
                )

        except Exception as e:
            # Handle exception
            error_msg = str(e)
            self._update_applicant_sync_status(applicant.appl_Id, CustomerSyncStatus.FAILED.value)
            self._log_customer_sync_audit(applicant.appl_Id, 'Applicant', 'ERROR', error_msg)

            return CustomerSyncResult(
                customer_id=str(applicant.appl_Id),
                customer_type='Applicant',
                success=False,
                error_message=error_msg
            )

    def sync_single_student(self, student: TblPersonalUg) -> CustomerSyncResult:
        """
        Synchronize a single student to QuickBooks

        Args:
            student: MIS student object to synchronize

        Returns:
            CustomerSyncResult: Result of the synchronization attempt
        """
        try:
            # Mark student as in progress
            self._update_student_sync_status(student.per_id_ug, CustomerSyncStatus.IN_PROGRESS.value)

            # Get QuickBooks service
            qb_service = self._get_qb_service()

            # Map student data
            qb_customer_data = self.map_student_to_quickbooks_customer(student)

            # Create customer in QuickBooks
            response = qb_service.create_customer(qb_service.realm_id, qb_customer_data)

            if 'Customer' in response:
                # Success - update sync status
                qb_customer_id = response['Customer']['Id']
                self._update_student_sync_status(
                    student.per_id_ug,
                    CustomerSyncStatus.SYNCED.value,
                    quickbooks_id=qb_customer_id
                )

                # Log successful sync
                self._log_customer_sync_audit(student.per_id_ug, 'Student', 'SUCCESS', f"Synced to QuickBooks ID: {qb_customer_id}")

                return CustomerSyncResult(
                    customer_id=student.reg_no,
                    customer_type='Student',
                    success=True,
                    quickbooks_id=qb_customer_id,
                    details=response
                )
            else:
                # Handle API error
                error_msg = response.get('Fault', {}).get('Error', [{}])[0].get('Detail', 'Unknown error')
                self._update_student_sync_status(student.per_id_ug, CustomerSyncStatus.FAILED.value)
                self._log_customer_sync_audit(student.per_id_ug, 'Student', 'ERROR', error_msg)

                return CustomerSyncResult(
                    customer_id=student.reg_no,
                    customer_type='Student',
                    success=False,
                    error_message=error_msg,
                    details=response
                )

        except Exception as e:
            # Handle exception
            error_msg = str(e)
            self._update_student_sync_status(student.per_id_ug, CustomerSyncStatus.FAILED.value)
            self._log_customer_sync_audit(student.per_id_ug, 'Student', 'ERROR', error_msg)

            return CustomerSyncResult(
                customer_id=student.reg_no,
                customer_type='Student',
                success=False,
                error_message=error_msg
            )

    def _update_applicant_sync_status(self, appl_id: int, status: int, quickbooks_id: Optional[str] = None):
        """
        Update applicant synchronization status in MIS database

        Args:
            appl_id: MIS applicant ID
            status: Sync status (0=not synced, 1=synced, 2=failed, 3=in progress)
            quickbooks_id: QuickBooks customer ID if successfully synced
        """
        try:
            session = db_manager.get_mis_session()

            applicant = session.query(TblOnlineApplication).filter(TblOnlineApplication.appl_Id == appl_id).first()
            if applicant:
                applicant.QuickBk_Status = status
                applicant.pushed_date = datetime.now()
                applicant.pushed_by = "CustomerSyncService"

                session.commit()
                logger.info(f"Updated applicant {appl_id} sync status to {status}")

        except Exception as e:
            logger.error(f"Error updating applicant sync status: {e}")
            if 'session' in locals():
                session.rollback()
            raise
        finally:
            if 'session' in locals():
                session.close()

    def _update_student_sync_status(self, per_id_ug: int, status: int, quickbooks_id: Optional[str] = None):
        """
        Update student synchronization status in MIS database

        Args:
            per_id_ug: MIS student personal ID
            status: Sync status (0=not synced, 1=synced, 2=failed, 3=in progress)
            quickbooks_id: QuickBooks customer ID if successfully synced
        """
        try:
            session = db_manager.get_mis_session()

            student = session.query(TblPersonalUg).filter(TblPersonalUg.per_id_ug == per_id_ug).first()
            if student:
                student.QuickBk_Status = status
                student.pushed_date = datetime.now()
                student.pushed_by = "CustomerSyncService"

                # Store QuickBooks ID in existing qk_id field
                if quickbooks_id and status == CustomerSyncStatus.SYNCED.value:
                    student.qk_id = quickbooks_id

                session.commit()
                logger.info(f"Updated student {per_id_ug} sync status to {status}")

        except Exception as e:
            logger.error(f"Error updating student sync status: {e}")
            if 'session' in locals():
                session.rollback()
            raise
        finally:
            if 'session' in locals():
                session.close()

    def _log_customer_sync_audit(self, customer_id: int, customer_type: str, action: str, details: str):
        """
        Log customer synchronization audit trail

        Args:
            customer_id: MIS customer ID (appl_Id or per_id_ug)
            customer_type: 'Applicant' or 'Student'
            action: Action performed (SUCCESS, ERROR, etc.)
            details: Additional details about the action
        """
        try:
            audit_log = QuickBooksAuditLog(
                action=f"CUSTOMER_SYNC_{action}",
                details=f"{customer_type} ID: {customer_id} - {details}",
                timestamp=datetime.now()
            )
            db.session.add(audit_log)
            db.session.commit()

        except Exception as e:
            logger.error(f"Error logging customer sync audit: {e}")
            if db.session:
                db.session.rollback()
