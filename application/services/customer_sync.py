"""
Customer Synchronization Service for EAUR MIS-QuickBooks Integration

This service handles the synchronization of applicants and students from MIS to QuickBooks
as customers with proper custom fields and data enrichment.
"""

import email
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum
import json
import time
import traceback

from flask import current_app
from sqlalchemy import and_, or_, func
from sqlalchemy.orm import joinedload

from application.models.mis_models import TblOnlineApplication, TblPersonalUg
from application.models.central_models import QuickBooksConfig, QuickbooksAuditLog
from application.services.quickbooks import QuickBooks
from application.utils.database import db_manager
from application import db
from application.helpers.json_field_helper import JSONFieldHelper
from application.helpers.json_encoder import EnhancedJSONEncoder
from application.helpers.SafeStringify import safe_stringify
from email_validator import validate_email, EmailNotValidError

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
        Get applicants that haven't been synchronized to QuickBooks with optimized batch loading

        Args:
            limit: Maximum number of applicants to return
            offset: Number of applicants to skip

        Returns:
            List of unsynchronized applicant objects with pre-loaded enrichment data
        """
        try:
            with db_manager.get_mis_session() as session:
                # Step 1: Get base applicants
                query = session.query(TblOnlineApplication).filter(
                    or_(TblOnlineApplication.QuickBk_Status != 1, TblOnlineApplication.QuickBk_Status.is_(None))
                ).order_by(TblOnlineApplication.appl_date.desc())

                if limit:
                    query = query.limit(limit)
                if offset:
                    query = query.offset(offset)

                applicants = query.all()
                logger.info(f"Retrieved {len(applicants)} unsynchronized applicants")

                if not applicants:
                    return applicants

                # Step 2: Batch load countries to avoid N+1 queries
                country_ids = []
                for app in applicants:
                    if app.country_of_birth and str(app.country_of_birth).isdigit():
                        country_ids.append(int(app.country_of_birth))

                country_map = {}
                if country_ids:
                    unique_country_ids = list(set(country_ids))
                    from application.models.mis_models import TblCountry
                    countries = session.query(TblCountry).filter(TblCountry.cntr_id.in_(unique_country_ids)).all()
                    country_map = {c.cntr_id: c for c in countries}
                    logger.debug(f"Batch loaded {len(countries)} countries for {len(unique_country_ids)} unique IDs")

                # Step 3: Batch load program modes to avoid N+1 queries
                mode_ids = []
                for app in applicants:
                    if app.prg_mode_id:
                        mode_ids.append(app.prg_mode_id)

                mode_map = {}
                if mode_ids:
                    unique_mode_ids = list(set(mode_ids))
                    from application.models.mis_models import TblProgramMode
                    modes = session.query(TblProgramMode).filter(TblProgramMode.prg_mode_id.in_(unique_mode_ids)).all()
                    mode_map = {m.prg_mode_id: m for m in modes}
                    logger.debug(f"Batch loaded {len(modes)} program modes for {len(unique_mode_ids)} unique IDs")

                # Step 4: Attach pre-loaded data to applicants for efficient access
                for app in applicants:
                    # Attach country data
                    if app.country_of_birth and str(app.country_of_birth).isdigit():
                        country_id = int(app.country_of_birth)
                        app._cached_country = country_map.get(country_id)
                    else:
                        app._cached_country = None

                    # Attach program mode data
                    app._cached_program_mode = mode_map.get(app.prg_mode_id) if app.prg_mode_id else None

                logger.info(f"Optimized batch loading completed: {len(applicants)} applicants, {len(country_map)} countries, {len(mode_map)} modes")
                return applicants
            
        except Exception as e:
            logger.error(f"Error getting unsynchronized applicants: {e}")
            raise
        finally:
            if 'session' in locals():
                session.close()
    
    def get_unsynchronized_students(self, limit: Optional[int] = None, offset: int = 0) -> List[TblPersonalUg]:
        """
        Get students that haven't been synchronized to QuickBooks with optimized batch loading

        Args:
            limit: Maximum number of students to return
            offset: Number of students to skip

        Returns:
            List of unsynchronized student objects with pre-loaded enrichment data
        """
        try:
            with db_manager.get_mis_session() as session:
                # Step 1: Get base students
                query = session.query(TblPersonalUg).filter(
                    or_(TblPersonalUg.QuickBk_Status != 1, TblPersonalUg.QuickBk_Status.is_(None))
                ).order_by(TblPersonalUg.reg_date.desc())

                if limit:
                    query = query.limit(limit)
                if offset:
                    query = query.offset(offset)

                students = query.all()
                logger.info(f"Retrieved {len(students)} unsynchronized students")

                if not students:
                    return students

                # Step 2: Batch load countries for nationality enrichment
                country_ids = []
                for student in students:
                    if student.nationality and student.nationality.isdigit():
                        country_ids.append(int(student.nationality))
                    if student.cntr_id:
                        country_ids.append(student.cntr_id)

                country_map = {}
                if country_ids:
                    unique_country_ids = list(set(country_ids))
                    from application.models.mis_models import TblCountry
                    countries = session.query(TblCountry).filter(TblCountry.cntr_id.in_(unique_country_ids)).all()
                    country_map = {c.cntr_id: c for c in countries}
                    logger.debug(f"Batch loaded {len(countries)} countries for {len(unique_country_ids)} unique IDs")

                # Step 3: Batch load registration program data for enrichment
                reg_nos = [s.reg_no for s in students if s.reg_no]
                reg_program_map = {}
                if reg_nos:
                    from application.models.mis_models import TblRegisterProgramUg
                    reg_programs = session.query(TblRegisterProgramUg).filter(TblRegisterProgramUg.reg_no.in_(reg_nos)).all()
                    reg_program_map = {rp.reg_no: rp for rp in reg_programs}
                    logger.debug(f"Batch loaded {len(reg_programs)} registration programs for {len(reg_nos)} students")

                # Step 4: Batch load related lookup data
                level_ids = []
                campus_ids = []
                specialization_ids = []
                intake_ids = []

                for reg_program in reg_programs:
                    if reg_program.level_id:
                        level_ids.append(reg_program.level_id)
                    if reg_program.camp_id:
                        campus_ids.append(reg_program.camp_id)
                    if reg_program.splz_id:
                        specialization_ids.append(reg_program.splz_id)
                    if reg_program.intake_id:
                        intake_ids.append(reg_program.intake_id)

                # Batch load levels
                level_map = {}
                if level_ids:
                    unique_level_ids = list(set(level_ids))
                    from application.models.mis_models import TblLevel
                    levels = session.query(TblLevel).filter(TblLevel.level_id.in_(unique_level_ids)).all()
                    level_map = {l.level_id: l for l in levels}
                    logger.debug(f"Batch loaded {len(levels)} levels")

                # Batch load campuses
                campus_map = {}
                if campus_ids:
                    unique_campus_ids = list(set(campus_ids))
                    from application.models.mis_models import TblCampus
                    campuses = session.query(TblCampus).filter(TblCampus.camp_id.in_(unique_campus_ids)).all()
                    campus_map = {c.camp_id: c for c in campuses}
                    logger.debug(f"Batch loaded {len(campuses)} campuses")

                # Batch load specializations
                specialization_map = {}
                if specialization_ids:
                    unique_spec_ids = list(set(specialization_ids))
                    from application.models.mis_models import TblSpecialization
                    specializations = session.query(TblSpecialization).filter(TblSpecialization.splz_id.in_(unique_spec_ids)).all()
                    specialization_map = {s.splz_id: s for s in specializations}
                    logger.debug(f"Batch loaded {len(specializations)} specializations")

                # Batch load intakes
                intake_map = {}
                if intake_ids:
                    unique_intake_ids = list(set(intake_ids))
                    from application.models.mis_models import TblIntake
                    intakes = session.query(TblIntake).filter(TblIntake.intake_id.in_(unique_intake_ids)).all()
                    intake_map = {i.intake_id: i for i in intakes}
                    logger.debug(f"Batch loaded {len(intakes)} intakes")

                # Step 5: Attach cached data to students
                for student in students:
                    # Attach country data
                    student._cached_country = None
                    if student.cntr_id and student.cntr_id in country_map:
                        student._cached_country = country_map[student.cntr_id]
                    elif student.nationality and student.nationality.isdigit():
                        country_id = int(student.nationality)
                        student._cached_country = country_map.get(country_id)

                    # Attach registration program data
                    reg_program = reg_program_map.get(student.reg_no)
                    student._cached_reg_program = reg_program

                    if reg_program:
                        student._cached_level = level_map.get(reg_program.level_id)
                        student._cached_campus = campus_map.get(reg_program.camp_id)
                        student._cached_specialization = specialization_map.get(reg_program.splz_id)
                        student._cached_intake = intake_map.get(reg_program.intake_id)
                    else:
                        student._cached_level = None
                        student._cached_campus = None
                        student._cached_specialization = None
                        student._cached_intake = None

                logger.info(f"Optimized batch loading completed: {len(students)} students with cached enrichment data")
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
        current_app.logger.info(f"Mapping applicant {applicant} and the type is {type(applicant)}")
        #check if type is already dict
        if isinstance(applicant, dict):
            current_app.logger.info(f"applicant is already a dict {applicant}")
            applicant_data = applicant
        else:
            current_app.logger.info(f"applicant is not a dict {applicant}")
            applicant_data = applicant.to_dict_for_quickbooks()
        try:
            # Create QuickBooks customer structure

            custom_fields_list = [
                {
                    "DefinitionId": "1000000001",
                    "StringValue": "Applicant"
                },
                {
                    "DefinitionId": "1000000002",
                    "StringValue": str(applicant_data['tracking_id'])
                },
                {
                    "DefinitionId": "1000000003",
                    "StringValue": applicant_data['sex']
                },
                {
                    "DefinitionId": "1000000008",
                    "Name": "NationalID",
                    "StringValue": applicant_data['national_id']
                },
                {
                    "DefinitionId": "1000000005",
                    "StringValue": applicant_data['campus_name']
                },
                {
                    "DefinitionId": "8",
                    "Name": "Intake",
                    "StringValue": safe_stringify(applicant_data['intake_details'], field_name="Intake")
                },
                {
                    "DefinitionId": "1000000009",
                    "StringValue": applicant_data['program_mode']
                }
            ]
            current_app.logger.info(f"custom fields {custom_fields_list}")

            # Filter out custom fields with no value
            filtered_custom_fields = [
                field for field in custom_fields_list if field.get('StringValue')
            ]

            # quickbooks require a valid email format, if email is invalid, set to None
            email = applicant_data.get('email')
            if not self.is_valid_email(email):
                email = None

            # Create the main QuickBooks customer dictionary
            qb_customer = {
                "DisplayName": applicant_data['tracking_id'],
                "GivenName": applicant_data['first_name'],
                "FamilyName": applicant_data['last_name'],
                "MiddleName": applicant_data['middle_name'],
                "CompanyName": f"{applicant_data['first_name']} {applicant_data['last_name']}",
                "PrimaryPhone": {
                    "FreeFormNumber": applicant_data['phone']
                } if applicant_data.get('phone') else None,
                "PrimaryEmailAddr": {
                    "Address": email
                } if email else None,
                "CustomerTypeRef": {
                    "value": "528730",
                    "name": "applicant"
                },
                "CustomField": filtered_custom_fields,
                "Notes": f"Applicant synchronized from MIS - Tracking ID: {applicant_data['tracking_id']}"
            }

            # Remove None values to clean up the payload
            qb_customer = {k: v for k, v in qb_customer.items() if v is not None}

            return qb_customer

        except Exception as e:
            logger.error(f"Error mapping applicant {applicant['appl_Id']} to QuickBooks format: {e}")

    def is_valid_email(self, email: str) -> bool:
        """
        Validate email format using email_validator library
        """
        try:
            # validate and get normalized form
            validate_email(email, check_deliverability=False)
            return True
        except EmailNotValidError:
            return False
    
    def map_student_to_quickbooks_customer(self, student: TblPersonalUg) -> Dict:
        """
        Map MIS student data to QuickBooks customer format
        """
        try:
            student_data = student
            # Create the CustomField list with only DefinitionId and StringValue
            custom_fields_list = [
                {
                    "DefinitionId": "1000000001",
                    "StringValue": "Student"
                },
                {
                    "DefinitionId": "1000000002",
                    "StringValue": student_data.get('reg_no', '')
                },
                {
                    "DefinitionId": "1000000003",
                    "StringValue": student_data.get('sex', '')
                },
                {
                    "DefinitionId": "1000000004",
                    "StringValue": student_data.get('level_name', '')
                },
                {
                    "DefinitionId": "1000000005",
                    "StringValue": student_data.get('campus_name', '')
                },
                {
                    "DefinitionId": "1000000006",
                    "StringValue": str(student_data.get('intake_details', ''))
                },
                {
                    "DefinitionId": "1000000007",
                    "StringValue": student_data.get('program_name', '')
                },
                {
                    "DefinitionId": "1000000008",
                    "StringValue": student_data.get('national_id', '')
                },
                {
                    "DefinitionId": "1000000009",
                    "StringValue": student_data.get('program_type', '')
                }
            ]
            current_app.logger.info(f"custom fields {custom_fields_list}")

            # Filter out custom fields with no value
            filtered_custom_fields = [
                field for field in custom_fields_list if field.get('StringValue')
            ]
            current_app.logger.info(f"student data {student_data}")
            email = student_data.get('email1')
            if email and isinstance(email, str):
                if not self.is_valid_email(email):
                    email = None
            else:
                email = None

            # Create the main QuickBooks customer dictionary
            qb_customer = {
                "DisplayName": student_data.get('reg_no', ''),
                "GivenName": student_data.get('first_name'),
                "FamilyName": student_data.get('last_name'),
                "MiddleName": student_data.get('middle_name'),
                "CompanyName": f"{student_data.get('first_name', '')} {student_data.get('last_name', '')}",
                "PrimaryPhone": {
                    "FreeFormNumber": student_data.get('phone')
                } if student_data.get('phone') else None,
                "PrimaryEmailAddr": {
                    "Address": email
                } if email else None,
                "CustomerTypeRef": {
                    "value": "528694",
                    "name": "student"
                },
                "CustomField": filtered_custom_fields,
                "Notes": f"Student synchronized from MIS - Registration Number: {student_data.get('reg_no', '')}"
            }

            # Remove None values and empty strings to clean up the payload
            qb_customer = {k: v for k, v in qb_customer.items() if v is not None and v != ''}
            
            return qb_customer

        except Exception as e:
            # ... your error handling ...
            raise


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
            self._update_student_sync_status(student.get('per_id_ug'), CustomerSyncStatus.IN_PROGRESS.value)

            # Get QuickBooks service
            qb_service = self._get_qb_service()

            # Map student data
            qb_customer_data = self.map_student_to_quickbooks_customer(student)

            # Create customer in QuickBooks
            response = qb_service.create_customer(qb_service.realm_id, qb_customer_data)
            current_app.logger.info(f"QuickBooks response for student {student.get('per_id_ug')}: {response}")

            if 'Customer' in response:
                # Success - update sync status
                qb_customer_id = response['Customer']['Id']
                self._update_student_sync_status(
                    student.get('per_id_ug'),
                    CustomerSyncStatus.SYNCED.value,
                    quickbooks_id=qb_customer_id
                )

                # Log successful sync
                self._log_customer_sync_audit(student.get('per_id_ug'), 'Student', 'SUCCESS', f"Synced to QuickBooks ID: {qb_customer_id}")

                return CustomerSyncResult(
                    customer_id=student.get('reg_no'),
                    customer_type='Student',
                    success=True,
                    quickbooks_id=qb_customer_id,
                    details=response
                )
            else:
                # Handle API error
                error_msg = response.get('Fault', {}).get('Error', [{}])[0].get('Detail', 'Unknown error')
                self._update_student_sync_status(student.get('per_id_ug'), CustomerSyncStatus.FAILED.value)
                self._log_customer_sync_audit(student.get('per_id_ug'), 'Student', 'ERROR', error_msg)

                return CustomerSyncResult(
                    customer_id=student.get('reg_no'),
                    customer_type='Student',
                    success=False,
                    error_message=error_msg,
                    details=response
                )

        except Exception as e:
            # Handle exception
            error_msg = str(e)
            self._update_student_sync_status(student.get('per_id_ug'), CustomerSyncStatus.FAILED.value)
            self._log_customer_sync_audit(student.get('per_id_ug'), 'Student', 'ERROR', error_msg)

            return CustomerSyncResult(
                customer_id=student.get('reg_no'),
                customer_type='Student',
                success=False,
                error_message=error_msg
            )
        
    
    def sync_batch_students(self, students):
        """
        Prepares and sends a batch request to QuickBooks Online to create multiple customers.
        
        Args:
            students (list): A list of student objects to synchronize.
            
        Returns:
            dict: A dictionary with 'successful' and 'failed' results.
        """
        # The quickbooks_client should be an authenticated client instance.
        quickbooks_client = self._get_qb_service()
        # Get the realm_id from the authenticated client
        realm_id = quickbooks_client.realm_id
        
        operations = []
        current_app.logger.info(f"Preparing batch sync students: {students}")
        for i, student in enumerate(students):
            customer_data = {
                "DisplayName": f"{student.get('reg_no')}",
                "GivenName": student.get('first_name'),
                "FamilyName": student.get('last_name'),
                "PrimaryEmailAddr": {
                    "Address": student.get('email_address')
                },
                "PrimaryPhone": {
                    "FreeFormNumber": student.get('phone_number')
                },
                "BillAddr": {
                    "Line1": student.get('address'),
                }
            }
            
            # Each operation in the batch request needs an operation and a unique ID
            operations.append({
                "operation": "create",
                "bId": str(i + 1), # A unique, client-generated ID for this operation
                "Customer": customer_data
            })
            
        # The main batch request payload
        batch_payload = {
            "BatchItemRequest": operations
        }

        try:
            # Make the single batch API call, including the realm_id
            batch_response = quickbooks_client.make_batch_request(realm_id, batch_payload)
            
            successful = []
            failed = []
            
            for item in batch_response.get('BatchItemResponse', []):
                # A successful creation will have a Customer object
                if "Customer" in item:
                    customer = item["Customer"]
                    successful.append({
                        "student_reg_no": students[int(item["bId"]) - 1].reg_no,
                        "quickbooks_id": customer.get("Id"),
                        "display_name": customer.get("DisplayName")
                    })
                    # You should also update your database here with the new QuickBooks ID
                    # students[int(item["bId"]) - 1].quickbooks_id = customer.get("Id")
                    # students[int(item["bId"]) - 1].save()
                else:
                    # An error response will have an error object
                    error_info = item.get("Fault", {}).get("Error", [{}])[0]
                    failed.append({
                        "student_reg_no": students[int(item["bId"]) - 1].reg_no,
                        "error_message": error_info.get("Detail", "Unknown error")
                    })

            return { "successful": successful, "failed": failed }

        except Exception as e:
            current_app.logger.error(f"QuickBooks batch API call failed: {e}")
            raise e

    def sync_all_unsynchronized_students_in_batches(self, batch_size: int = 20) -> Dict:
        """
        Fetches unsynchronized students in batches, maps their data to QuickBooks
        customer format, and sends them for batch creation/update in QuickBooks.
        Updates sync status and logs audit trails for each student.
        """
        realm_id = self._get_qb_service().realm_id  # Ensure qb_service is initialized

        total_processed = 0
        total_succeeded = 0
        total_failed = 0
        all_results = []
        offset = 0

        while True:
            # 1. Fetch a batch of unsynchronized students
            students_batch = self.get_unsynchronized_students(limit=batch_size, offset=offset)
            if not students_batch:
                current_app.logger.info("No more unsynchronized students to process.")
                break  # No more unsynchronized students

            current_app.logger.info(f"Processing batch of {len(students_batch)} unsynchronized students (offset: {offset})")

            batch_operations = []
            student_per_id_map = {}  # To map bId back to student for status update

            # 2. Prepare Batch Requests
            for i, student_orm in enumerate(students_batch):
                # Convert ORM object to dictionary for consistent access
                student_data = student_orm.to_dict_for_quickbooks()
                
                per_id_ug = student_data.get('per_id_ug')
                reg_no = student_data.get('reg_no')
                
                # Mark as IN_PROGRESS immediately to prevent reprocessing by other tasks
                self._update_student_sync_status(per_id_ug, CustomerSyncStatus.IN_PROGRESS.value)

                qb_customer_data = self.map_student_to_quickbooks_customer(student_data)
                
                # Assign a unique bId for each operation in the batch
                # Use per_id_ug as bId or a combination for unique identification
                bId = f"student-{per_id_ug}"
                student_per_id_map[bId] = student_data # Store the dictionary, not the ORM object

                batch_operations.append({
                    "operation": "create",  # Assuming new customer creation. Adjust for update if needed.
                    "bId": bId,
                    "Customer": qb_customer_data
                })

            batch_payload = {
                "BatchItemRequest": batch_operations
            }

            try:
                # 3. Execute Batch Request
                quickbooks_batch_response = self._get_qb_service().make_batch_request(realm_id, batch_payload)
                current_app.logger.info(f"QuickBooks batch response: {quickbooks_batch_response}")

                # 4. Process Batch Response
                for item_response in quickbooks_batch_response.get("BatchItemResponse", []):
                    bId = item_response.get("bId")
                    student_data = student_per_id_map.get(bId)  # Retrieve student dictionary

                    if not student_data:
                        current_app.logger.warning(f"Student with bId {bId} not found in map. Skipping status update.")
                        continue
                    
                    per_id_ug = student_data.get('per_id_ug')
                    reg_no = student_data.get('reg_no')

                    if "Customer" in item_response and item_response['Customer'].get('Id'):
                        # Success
                        quickbooks_id = item_response['Customer']['Id']
                        self._update_student_sync_status(per_id_ug, CustomerSyncStatus.SYNCED.value, quickbooks_id=quickbooks_id)
                        self._log_customer_sync_audit(per_id_ug, 'Student', 'SUCCESS', f"Synced to QuickBooks ID: {quickbooks_id}")
                        all_results.append(CustomerSyncResult(
                            customer_id=reg_no, customer_type='Student', success=True, quickbooks_id=quickbooks_id,
                            details=item_response
                        ))
                        total_succeeded += 1
                    else:
                        # Failure
                        error_detail = "Unknown error during batch sync."
                        if "Fault" in item_response and "Error" in item_response['Fault']:
                            error_detail = item_response['Fault']['Error'][0].get('Detail', error_detail)
                        
                        # Log the full error response for debugging
                        current_app.logger.error(f"Failed to sync student {reg_no} (bId: {bId}). Error: {error_detail}. Full response: {item_response}")

                        self._update_student_sync_status(per_id_ug, CustomerSyncStatus.FAILED.value)
                        self._log_customer_sync_audit(per_id_ug, 'Student', 'ERROR', f"Batch sync failed: {error_detail}")
                        all_results.append(CustomerSyncResult(
                            customer_id=reg_no, customer_type='Student', success=False, error_message=error_detail,
                            details=item_response
                        ))
                        total_failed += 1
            except Exception as e:
                current_app.logger.error(f"Overall error during QuickBooks batch request: {e}")
                current_app.logger.error(traceback.format_exc())
                # If the entire batch request fails, mark all students in the current batch as failed
                for student_orm in students_batch:
                    # In this outer exception, student_orm is the raw ORM object from students_batch
                    per_id_ug = student_orm.per_id_ug # Access directly from ORM object
                    reg_no = student_orm.reg_no     # Access directly from ORM object
                    self._update_student_sync_status(per_id_ug, CustomerSyncStatus.FAILED.value)
                    self._log_customer_sync_audit(per_id_ug, 'Student', 'ERROR', f"Overall batch request failed: {str(e)}")
                    all_results.append(CustomerSyncResult(
                        customer_id=reg_no, customer_type='Student', success=False, error_message=str(e)
                    ))
                    total_failed += 1

            total_processed += len(students_batch)
            offset += len(students_batch)  # Increment offset for the next batch

            # Add a small delay to avoid hitting API rate limits, if necessary
            time.sleep(1)  # Adjust as per QuickBooks API rate limits

        return {
            "total_processed": total_processed,
            "total_succeeded": total_succeeded,
            "total_failed": total_failed,
            "results": all_results
        }

    def sync_all_unsynchronized_applicants_in_batches(self, batch_size: int = 20) -> Dict:
        """
        Fetches unsynchronized applicants in batches, maps their data to QuickBooks
        customer format, and sends them for batch creation/update in QuickBooks.
        Updates sync status and logs audit trails for each applicant.
        """
        realm_id = self._get_qb_service().realm_id

        total_processed = 0
        total_succeeded = 0
        total_failed = 0
        all_results = []
        offset = 0

        while True:
            # 1. Fetch a batch of unsynchronized applicants
            applicants_batch = self.get_unsynchronized_applicants(limit=batch_size, offset=offset)
            current_app.logger.info(f"batch applicants {applicants_batch} and length {len(applicants_batch)}")
            if not applicants_batch:
                current_app.logger.info("No more unsynchronized applicants to process.")
                break

            current_app.logger.info(f"Processing batch of {len(applicants_batch)} unsynchronized applicants (offset: {offset})")

            batch_operations = []
            applicant_per_id_map = {}  # To map bId back to applicant for status update

            # 2. Prepare Batch Requests
            for i, applicant_orm in enumerate(applicants_batch):
                # Convert ORM object to dictionary for consistent access
                applicant_data = applicant_orm.to_dict_for_quickbooks()
                current_app.logger.info(f"applicant data {applicant_data}")
                appl_id = applicant_data.get('appl_Id')
                tracking_id = applicant_data.get('tracking_id')
                
                # Mark as IN_PROGRESS immediately to prevent reprocessing by other tasks
                self._update_applicant_sync_status(appl_id, CustomerSyncStatus.IN_PROGRESS.value)
                current_app.logger.info(f"Applicant data for QuickBooks mapping: {applicant_data}")
                qb_customer_data = self.map_applicant_to_quickbooks_customer(applicant_data)
                current_app.logger.info(f"QuickBooks customer data for applicant {appl_id}: {qb_customer_data}")

                # Assign a unique bId for each operation in the batch
                bId = f"applicant-{appl_id}"
                applicant_per_id_map[bId] = applicant_data # Store the dictionary

                batch_operations.append({
                    "operation": "create",  # Assuming new customer creation
                    "bId": bId,
                    "Customer": qb_customer_data
                })

            batch_payload = {
                "BatchItemRequest": batch_operations
            }

            try:
                # 3. Execute Batch Request
                quickbooks_batch_response = self._get_qb_service().make_batch_request(realm_id, batch_payload)
                current_app.logger.info(f"QuickBooks batch response for applicants: {quickbooks_batch_response}")

                # 4. Process Batch Response
                for item_response in quickbooks_batch_response.get("BatchItemResponse", []):
                    bId = item_response.get("bId")
                    applicant_data = applicant_per_id_map.get(bId)

                    if not applicant_data:
                        current_app.logger.warning(f"Applicant with bId {bId} not found in map. Skipping status update.")
                        continue
                    
                    appl_id = applicant_data.get('appl_Id')
                    tracking_id = applicant_data.get('tracking_id')

                    if "Customer" in item_response and item_response['Customer'].get('Id'):
                        # Success
                        quickbooks_id = item_response['Customer']['Id']
                        self._update_applicant_sync_status(appl_id, CustomerSyncStatus.SYNCED.value, quickbooks_id=quickbooks_id)
                        self._log_customer_sync_audit(appl_id, 'Applicant', 'SUCCESS', f"Synced to QuickBooks ID: {quickbooks_id}")
                        all_results.append(CustomerSyncResult(
                            customer_id=tracking_id, customer_type='Applicant', success=True, quickbooks_id=quickbooks_id,
                            details=item_response
                        ))
                        total_succeeded += 1
                        update_db_data = TblOnlineApplication.update_applicant_quickbooks_status(tracking_id, quickbooks_id, pushed_by="ApplicantSyncService", QuickBk_Status=1)
                        if update_db_data:
                            current_app.logger.info(f"Successfully updated applicant {appl_id} with QuickBooks ID {quickbooks_id}")
                    else:
                        # Failure
                        error_detail = "Unknown error during batch sync."
                        if "Fault" in item_response and "Error" in item_response['Fault']:
                            error_detail = item_response['Fault']['Error'][0].get('Detail', error_detail)
                        
                        current_app.logger.error(f"Failed to sync applicant {tracking_id} (bId: {bId}). Error: {error_detail}. Full response: {item_response}")

                        self._update_applicant_sync_status(appl_id, CustomerSyncStatus.FAILED.value)
                        self._log_customer_sync_audit(appl_id, 'Applicant', 'ERROR', f"Batch sync failed: {error_detail}")
                        all_results.append(CustomerSyncResult(
                            customer_id=tracking_id, customer_type='Applicant', success=False, error_message=error_detail,
                            details=item_response
                        ))
                        total_failed += 1
            except Exception as e:
                current_app.logger.error(f"Overall error during QuickBooks batch request for applicants: {e}")
                current_app.logger.error(traceback.format_exc())
                # If the entire batch request fails, mark all applicants in the current batch as failed
                for applicant_orm in applicants_batch:
                    appl_id = applicant_orm.appl_Id
                    tracking_id = applicant_orm.tracking_id
                    self._update_applicant_sync_status(appl_id, CustomerSyncStatus.FAILED.value)
                    self._log_customer_sync_audit(appl_id, 'Applicant', 'ERROR', f"Overall batch request failed: {str(e)}")
                    all_results.append(CustomerSyncResult(
                        customer_id=tracking_id, customer_type='Applicant', success=False, error_message=str(e)
                    ))
                    total_failed += 1

            total_processed += len(applicants_batch)
            offset += len(applicants_batch) # Increment offset for the next batch

            time.sleep(1) # Adjust as per QuickBooks API rate limits

        return {
            "total_processed": total_processed,
            "total_succeeded": total_succeeded,
            "total_failed": total_failed,
            "results": all_results
        }

    def sync_single_applicant(self, applicant: TblOnlineApplication) -> CustomerSyncResult:
        """
        Synchronize a single applicant to QuickBooks

        Args:
            applicant: MIS applicant object to synchronize

        Returns:
            CustomerSyncResult: Result of the synchronization attempt
        """
        current_app.logger.info(f"Syncing single applicant: {applicant} and the type is {type(applicant)}")
        try:
           # Mark applicant as in progress
            self._update_applicant_sync_status(applicant.appl_Id, CustomerSyncStatus.IN_PROGRESS.value)

            # Get QuickBooks service
            qb_service = self._get_qb_service()

            # Map applicant data
            qb_customer_data = self.map_applicant_to_quickbooks_customer(applicant)
            current_app.logger.info(f"QuickBooks customer data for applicant {applicant.appl_Id}: {qb_customer_data}")

            # Create customer in QuickBooks
            response = qb_service.create_customer(qb_service.realm_id, qb_customer_data)
            current_app.logger.info(f"QuickBooks response for applicant {applicant.appl_Id}: {response}")
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
                    customer_id=applicant.tracking_id,
                    customer_type='Applicant',
                    success=True,
                    quickbooks_id=qb_customer_id,
                    details=response
                )
            else:
                # Handle API error
                error_msg = response.get('Fault', {}).get('Error', [{}])[0].get('Detail', 'Unknown error')
                self._update_applicant_sync_status(applicant.get('appl_Id'), CustomerSyncStatus.FAILED.value)
                self._log_customer_sync_audit(applicant.get('appl_Id'), 'Applicant', 'ERROR', error_msg)

                return CustomerSyncResult(
                    customer_id=applicant.tracking_id,
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
                customer_id=applicant.tracking_id,
                customer_type='Applicant',
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
            with db_manager.get_mis_session() as session:

                    applicant = session.query(TblOnlineApplication).filter(TblOnlineApplication.appl_Id == appl_id).first()
                    if applicant:
                        applicant.QuickBk_Status = status
                        applicant.pushed_date = datetime.now()
                        applicant.pushed_by = "CustomerSyncService"
                        # Store QuickBooks ID in existing quickbooks_id field
                        if quickbooks_id and status == CustomerSyncStatus.SYNCED.value:
                            applicant.quickbooks_id = quickbooks_id
                        session.commit()
                        logger.info(f"Updated applicant {appl_id} sync status to {status}")

        except Exception as e:
            logger.error(f"Error updating applicant sync status: {e}")
            with db_manager.get_mis_session() as session:
                session.rollback()

    def _update_student_sync_status(self, per_id_ug: int, status: int, quickbooks_id: Optional[str] = None):
        """
        Update student synchronization status in MIS database

        Args:
            per_id_ug: MIS student personal ID
            status: Sync status (0=not synced, 1=synced, 2=failed, 3=in progress)
            quickbooks_id: QuickBooks customer ID if successfully synced
        """
        try:
            with db_manager.get_mis_session() as session:

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
            with db_manager.get_mis_session() as session:
                session.rollback()

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
            audit_log = QuickbooksAuditLog(
                action_type=f"CUSTOMER_SYNC_{action}",
                operation_status=f"{'200' if action == 'SUCCESS' else '500'}",
                response_payload=f"{customer_type} ID: {customer_id} - {details}",
                
            )
            db.session.add(audit_log)
            db.session.commit()

        except Exception as e:
            logger.error(f"Error logging customer sync audit: {e}")
            if db.session:
                db.session.rollback()
