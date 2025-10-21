"""
Customer Synchronization API endpoints for EAUR MIS-QuickBooks Integration
Handles synchronization of applicants and students from MIS to QuickBooks as customers
"""

from flask import Blueprint, request, jsonify, current_app
from application.services.customer_sync import CustomerSyncService
from application.models.central_models import QuickBooksConfig, QuickbooksAuditLog
import traceback
from datetime import datetime
from application.models.mis_models import TblOnlineApplication, TblCountry, TblPersonalUg
from application.utils.database import db_manager

customer_sync_bp = Blueprint('customer_sync', __name__)

# Standard response format
def create_response(success=True, data=None, message="", error=None, details=None, status_code=200):
    """Create standardized API response"""
    response = {
        'success': success,
        'message': message,
        'timestamp': datetime.now().isoformat()
    }
    
    if success:
        response['data'] = data
    else:
        response['error'] = error
        if details:
            response['details'] = details
    
    return jsonify(response), status_code

def validate_quickbooks_connection():
    """Validate QuickBooks connection"""
    if not QuickBooksConfig.is_connected():
        return False, create_response(
            success=False,
            error='QuickBooks not connected',
            message='Please authenticate with QuickBooks first',
            status_code=400
        )
    return True, None

@customer_sync_bp.route('/analyze', methods=['GET'])
def analyze_customer_sync_requirements():
    """
    Analyze current customer synchronization requirements
    
    Returns statistics about applicants and students that need to be synchronized
    """
    try:
        # Validate QuickBooks connection
        is_connected, error_response = validate_quickbooks_connection()
        if not is_connected:
            return error_response

        sync_service = CustomerSyncService()
        stats = sync_service.analyze_customer_sync_requirements()
        
        current_app.logger.info(f"Customer sync analysis completed: {stats.to_dict()}")
        
        return create_response(
            success=True,
            data=stats.to_dict(),
            message='Customer synchronization analysis completed successfully'
        )
        
    except Exception as e:
        current_app.logger.error(f"Error analyzing customer sync requirements: {e}")
        current_app.logger.error(traceback.format_exc())
        return create_response(
            success=False,
            error='Error analyzing customer synchronization requirements',
            details=str(e),
            status_code=500
        )

@customer_sync_bp.route('/preview/applicants', methods=['GET'])
def preview_unsynchronized_applicants():
    """
    Preview applicants that will be synchronized
    
    Query parameters:
    - limit: Number of applicants to preview (default: 10)
    - offset: Number of applicants to skip (default: 0)
    """
    try:
        # Validate QuickBooks connection
        is_connected, error_response = validate_quickbooks_connection()
        if not is_connected:
            return error_response

        # Get query parameters
        limit = int(request.args.get('limit', 10))
        offset = int(request.args.get('offset', 0))
        
        # Validate parameters
        if limit > 100:
            return create_response(
                success=False,
                error='Limit cannot exceed 100',
                status_code=400
            )

        sync_service = CustomerSyncService()
        applicants = sync_service.get_unsynchronized_applicants(limit=limit, offset=offset)
        
        # Convert to dictionary format for JSON response with enhanced error tracking
        applicant_data = []
        conversion_errors = []

        for applicant in applicants:
            try:
                applicant_dict = applicant.to_dict_for_quickbooks()
                applicant_data.append(applicant_dict)

                # Log if enrichment failed
                if applicant_dict.get('error_occurred'):
                    conversion_errors.append({
                        'appl_Id': applicant.appl_Id,
                        'tracking_id': applicant.tracking_id,
                        'error': applicant_dict.get('error_message', 'Unknown error')
                    })
                    current_app.logger.warning(f"Enrichment failed for applicant {applicant.appl_Id}: {applicant_dict.get('error_message')}")

            except Exception as e:
                current_app.logger.error(f"Error converting applicant {applicant.appl_Id} to dict: {e}")
                conversion_errors.append({
                    'appl_Id': applicant.appl_Id,
                    'tracking_id': getattr(applicant, 'tracking_id', 'Unknown'),
                    'error': str(e)
                })
                continue
        
        # Prepare enhanced response data with performance metrics
        response_data = {
            'applicants': applicant_data,
            'count': len(applicant_data),
            'limit': limit,
            'offset': offset,
            'performance': {
                'optimized_batch_loading': True,
                'query_pattern': 'batch_loaded'
            }
        }

        # Add error information if any
        if conversion_errors:
            response_data['conversion_errors'] = conversion_errors
            response_data['errors_count'] = len(conversion_errors)

        message = f'Retrieved {len(applicant_data)} unsynchronized applicants'
        if conversion_errors:
            message += f' ({len(conversion_errors)} had enrichment errors)'

        return create_response(
            success=True,
            data=response_data,
            message=message
        )
        
    except Exception as e:
        current_app.logger.error(f"Error previewing unsynchronized applicants: {e}")
        current_app.logger.error(traceback.format_exc())
        return create_response(
            success=False,
            error='Error previewing unsynchronized applicants',
            details=str(e),
            status_code=500
        )

@customer_sync_bp.route('/preview/students', methods=['GET'])
def preview_unsynchronized_students():
    """
    Preview students that will be synchronized
    
    Query parameters:
    - limit: Number of students to preview (default: 10)
    - offset: Number of students to skip (default: 0)
    """
    try:
        # Validate QuickBooks connection
        is_connected, error_response = validate_quickbooks_connection()
        if not is_connected:
            return error_response

        # Get query parameters
        limit = int(request.args.get('limit', 10))
        offset = int(request.args.get('offset', 0))
        
        # Validate parameters
        if limit > 100:
            return create_response(
                success=False,
                error='Limit cannot exceed 100',
                status_code=400
            )

        sync_service = CustomerSyncService()
        students = sync_service.get_unsynchronized_students(limit=limit, offset=offset)
        
        # Convert to dictionary format for JSON response
        student_data = []
        conversion_errors = []

        for student in students:
            try:
                student_dict = student.to_dict_for_quickbooks()
                student_data.append(student_dict)

                # Log if enrichment failed
                if student_dict.get('error_occurred'):
                    conversion_errors.append({
                        'reg_no': student.reg_no,
                        'error': student_dict.get('error_message', 'Unknown error')
                    })
                    current_app.logger.warning(f"Enrichment failed for student {student.reg_no}: {student_dict.get('error_message')}")

            except Exception as e:
                current_app.logger.error(f"Error converting student {student.reg_no} to dict: {e}")
                conversion_errors.append({
                    'reg_no': student.reg_no,
                    'error': str(e)
                })
                continue
        
        # Prepare response data
        response_data = {
            'students': student_data,
            'count': len(student_data),
            'limit': limit,
            'offset': offset
        }

        # Add error information if any
        if conversion_errors:
            response_data['conversion_errors'] = conversion_errors
            response_data['errors_count'] = len(conversion_errors)

        message = f'Retrieved {len(student_data)} unsynchronized students'
        if conversion_errors:
            message += f' ({len(conversion_errors)} had enrichment errors)'

        return create_response(
            success=True,
            data=response_data,
            message=message
        )
        
    except Exception as e:
        current_app.logger.error(f"Error previewing unsynchronized students: {e}")
        current_app.logger.error(traceback.format_exc())
        return create_response(
            success=False,
            error='Error previewing unsynchronized students',
            details=str(e),
            status_code=500
        )

@customer_sync_bp.route('/applicants', methods=['POST'])
def sync_applicants():
    """
    Synchronize applicants to QuickBooks customers
    
    Request body (JSON):
    {
        "batch_size": 50  // Optional, defaults to 50
    }
    """
    try:
        # Validate QuickBooks connection
        is_connected, error_response = validate_quickbooks_connection()
        if not is_connected:
            return error_response

        # Get request data
        request_data = request.get_json() or {}
        batch_size = request_data.get('batch_size', 50)
        
        # Validate batch size
        if batch_size > 100:
            return create_response(
                success=False,
                error='Batch size cannot exceed 100',
                status_code=400
            )

        sync_service = CustomerSyncService()
        
        current_app.logger.info(f"Starting applicant synchronization with batch size: {batch_size}")
        
        # Get unsynchronized applicants
        applicants = sync_service.get_unsynchronized_applicants(limit=batch_size)
        
        if not applicants:
            return create_response(
                success=True,
                data={'total_processed': 0, 'successful': 0, 'failed': 0},
                message='No unsynchronized applicants found'
            )
        
        # Process applicants
        results = {
            'total_processed': 0,
            'successful': 0,
            'failed': 0,
            'errors': [],
            'success_details': []
        }
        
        for applicant in applicants:
            try:
                result = sync_service.sync_single_applicant(applicant)
                results['total_processed'] += 1
                
                if result.success:
                    results['successful'] += 1
                    results['success_details'].append({
                        'applicant_id': result.customer_id,
                        'quickbooks_id': result.quickbooks_id
                    })
                else:
                    results['failed'] += 1
                    results['errors'].append({
                        'applicant_id': result.customer_id,
                        'error': result.error_message
                    })
                
                # Add delay between requests to avoid rate limiting
                import time
                time.sleep(0.5)
                
            except Exception as e:
                results['failed'] += 1
                results['errors'].append({
                    'applicant_id': applicant.appl_Id,
                    'error': str(e)
                })
        
        return create_response(
            success=True,
            data=results,
            message=f'Applicant synchronization completed: {results["successful"]} successful, {results["failed"]} failed'
        )
        
    except Exception as e:
        current_app.logger.error(f"Error in applicant synchronization: {e}")
        current_app.logger.error(traceback.format_exc())
        return create_response(
            success=False,
            error='Error in applicant synchronization',
            details=str(e),
            status_code=500
        )
    
@customer_sync_bp.route('/sync_student', methods=['POST'])
def sync_student():
    """
    Synchronize a single student to QuickBooks customer by reg_no
    description: This endpoint fetches the student by reg_no and synchronizes them.
    1. Validates QuickBooks connection.
    2. Fetches the student using TblPersonalUg.get_student_details(reg_no).
    3. If student not found, returns 404.
    4. Calls sync_service.sync_single_student(student) to perform synchronization.
    5. Returns success or error response based on synchronization result.
    6. Handles exceptions and logs errors.
    Args:
        reg_no: Student registration number to synchronize
    """
    data = request.get_json() or {}
    reg_no = data.get('reg_no')
    if not reg_no:
        return create_response(
            success=False,
            error='reg_no is required',
            status_code=400
        )
    sync_service = CustomerSyncService()
    try:
        # Validate QuickBooks connection
        is_connected, error_response = validate_quickbooks_connection()
        if not is_connected:
            return error_response
    except Exception as e:
        current_app.logger.error(f"Error synchronizing student {reg_no}: {e}")
        current_app.logger.error(traceback.format_exc())
        return create_response(
            success=False,
            error=f'Error synchronizing student {reg_no}',
            details=str(e),
            status_code=500
        )
    try:
        # WE need to use the method to get student by reg_no
        student = TblPersonalUg.get_student_details(reg_no)
        current_app.logger.info(f"Fetched student for reg_no {reg_no}: {student}")
        if not student:
            return create_response(
                success=False,
                error=f"Student with reg_no {reg_no} not found",
                status_code=404
            )
        
        # check if student has already been synced
        if student.get("quickbooks_status") == 1:
            return create_response(
                success=False,
                error=f"Student with reg_no {reg_no} has already been synchronized to QuickBooks",
                status_code=400
            )

    except Exception as e:
        current_app.logger.error(f"Error fetching student {reg_no}: {e}")
        current_app.logger.debug(f"Traceback: {traceback.format_exc()}")
        return create_response(
            success=False,
            error=f'Error fetching student {reg_no}',
            details=str(e),
            status_code=500
        )
    try:
        result = sync_service.sync_single_student(student)
        current_app.logger.info(f"Synchronization result for student {reg_no}: {result}")
        if result.success:
            return create_response(
                success=True,
                data={
                    'student_id': result.customer_id,
                    'quickbooks_id': result.quickbooks_id,
                    'student_details': student,
                },
                message=f'Student {student.get("first_name")} {student.get("last_name")} ({reg_no}) synchronized successfully'
            )
        else:
            return create_response(
                success=False,
                error=f'Failed to synchronize student {reg_no}',
                details=result.error_message,
                status_code=500
            )
    except Exception as e:
        current_app.logger.error(f"Error synchronizing student {reg_no}: {e}")
        current_app.logger.debug(f"Traceback: {traceback.format_exc()}")
        # we wanna get exactly which line caused the error
        current_app.logger.error(traceback.format_exc())
        return create_response(
            success=False,
            error=f'Error synchronizing student {reg_no}',
            details=str(e),
            status_code=500
        )

@customer_sync_bp.route('/applicant/<int:tracking_id>', methods=['POST'])
def sync_single_applicant(tracking_id: int):
    """
    Synchronize a single applicant to QuickBooks customer by tracking_id
    """
    try:
        # Validate QuickBooks connection
        is_connected, error_response = validate_quickbooks_connection()
        if not is_connected:
            return error_response

        sync_service = CustomerSyncService()

        # Get DB session safely
        with db_manager.get_mis_session() as db:  
            applicant = TblOnlineApplication.get_applicant_details(tracking_id)
            if not applicant:
                return create_response(
                    success=False,
                    error=f"Applicant {tracking_id} not found",
                    status_code=404
                )

            if applicant.get('quickbooks_status') == 1:
                return create_response(
                    success=False,
                    error=f"Applicant {tracking_id} has already been synchronized to QuickBooks",
                    status_code=400
                )
            result = sync_service.sync_single_applicant(applicant)

            

            
            current_app.logger.info(f"Synchronization result for applicant {tracking_id}: {result}")
            if result.success:
                customer_data = result.get('data', {}).get('Customer', {})
                sync_token = customer_data.get('SyncToken')
                update = TblOnlineApplication.update_applicant_quickbooks_status(
                    tracking_id=tracking_id,
                    quickbooks_id=result.quickbooks_id,
                    pushed_by="ApplicantSyncService",
                    QuickBk_status=1,
                    sync_token=sync_token
                )
                if not update:
                    current_app.logger.warning(f"Failed to update QuickBooks status for applicant {tracking_id} after sync.")
                return create_response(
                    success=True,
                    data={
                        'applicant_id': result.customer_id,
                        'quickbooks_id': result.quickbooks_id
                    },
                    message=f'Applicant {tracking_id} synchronized successfully'
                )

            else:
                return create_response(
                    success=False,
                    error=f'Failed to synchronize applicant {tracking_id}',
                    details=result.error_message,
                    status_code=500
                )

    except Exception as e:
        current_app.logger.error(f"Error synchronizing applicant {tracking_id}: {e}")
        current_app.logger.error(traceback.format_exc())
        return create_response(
            success=False,
            error=f'Error synchronizing applicant {tracking_id}',
            details=str(e),
            status_code=500
        )

@customer_sync_bp.route('/applicant/update/<int:tracking_id>', methods=['POST'])
def update_single_applicant(tracking_id: int):
    """
    Update an existing QuickBooks customer for a single applicant by tracking_id.
    Performs a sparse update to avoid overwriting existing fields.
    """
    try:
        # Validate QuickBooks connection
        is_connected, error_response = validate_quickbooks_connection()
        if not is_connected:
            return error_response

        sync_service = CustomerSyncService()

        with db_manager.get_mis_session() as db:
            applicant = TblOnlineApplication.get_applicant_details(tracking_id)
            if not applicant:
                return create_response(
                    success=False,
                    error=f"Applicant {tracking_id} not found",
                    status_code=404
                )

            quickbooks_id = applicant['quickbooks_id']
            current_app.logger.info(f"Fetched applicant {tracking_id} with QuickBooks ID: {quickbooks_id}")
            if not quickbooks_id:
                return create_response(
                    success=False,
                    error=f"Applicant {tracking_id} has not been synced to QuickBooks yet",
                    status_code=400
                )
            if not applicant.get('sync_token'):
                fetch_result = sync_service.get_customer_by_quickbooks_id(quickbooks_id)
                customer_data = fetch_result.get('data', fetch_result).get('Customer', {})
                sync_token = customer_data.get('SyncToken')

            current_app.logger.info(f"Fetched QuickBooks customer for applicant {tracking_id}: {fetch_result} with type {type(fetch_result)}")
            qb_payload = sync_service.map_applicant_to_quickbooks_customer_update(
                applicant=applicant,
                qb_customer_id=quickbooks_id,
                sparse=True,
                SyncToken=sync_token if sync_token else None  # Default to "0" if SyncToken is missing
            )


            result = sync_service.update_quickbooks_customer(qb_customer_id=quickbooks_id, qb_customer_data=qb_payload)
            current_app.logger.info(f"Update result for applicant {tracking_id}: {result}")

            if result.get('Customer'):
                QuickbooksAuditLog.add_audit_log(
                    action_type="Update single applicant",
                    operation_status=200,
                    error_message=result.get('Error', "Something went wrong"),
                )
                return create_response(
                    success=True,
                    data={
                        'applicant_id': tracking_id,
                        'quickbooks_id': quickbooks_id
                    },
                    message=f"Applicant {tracking_id} updated successfully in QuickBooks"
                )
            else:
                QuickbooksAuditLog.add_audit_log(
                    action_type="Update single applicant",
                    operation_status=500,
                    error_message=result.error_message,
                )
                return create_response(
                    success=False,
                    error=f"Failed to update applicant {tracking_id} in QuickBooks",
                    details=result.error_message,
                    status_code=500
                )

    except Exception as e:
        current_app.logger.error(f"Error updating applicant {tracking_id}: {e}")
        current_app.logger.error(traceback.format_exc())
        return create_response(
            success=False,
            error=f"Error updating applicant {tracking_id}",
            details=str(e),
            status_code=500
        )


@customer_sync_bp.route('/students', methods=['POST'])
def sync_students():
    """
    Synchronize students to QuickBooks customers

    Request body (JSON):
    {
        "batch_size": 10  // Optional, defaults to 10
    }
    """
    try:
        # Validate QuickBooks connection
        is_connected, error_response = validate_quickbooks_connection()
        if not is_connected:
            return error_response

        # Get request data
        request_data = request.get_json() or {}
        batch_size = request_data.get('batch_size', 10)

        # Validate batch size
        if batch_size > 100:
            return create_response(
                success=False,
                error='Batch size cannot exceed 100',
                status_code=400
            )

        sync_service = CustomerSyncService()

        current_app.logger.info(f"Starting student synchronization with batch size: {batch_size}")

        # Get unsynchronized students
        students = sync_service.get_unsynchronized_students(limit=batch_size)
        current_app.logger.info(f"Fetched students for synchronization: {students}")

        if not students:
            return create_response(
                success=True,
                data={'total_processed': 0, 'successful': 0, 'failed': 0},
                message='No unsynchronized students found'
            )

        # Process students
        results = {
            'total_processed': 0,
            'successful': 0,
            'failed': 0,
            'errors': [],
            'success_details': []
        }
        # we are syncing with the batch method
        try:
            batch_results = sync_service.sync_batch_students(students)
            current_app.logger.info(f"Batch synchronization results: {batch_results}")

            results['total_processed'] = batch_results.get('total_processed', 0)
            results['successful'] = batch_results.get('successful', 0)
            results['failed'] = batch_results.get('failed', 0)
            results['errors'] = batch_results.get('errors', [])
            results['success_details'] = batch_results.get('success_details', [])

            return create_response(
                success=True,
                data=results,
                message=f'Student synchronization completed: {results["successful"]} successful, {results["failed"]} failed'
            )
        except Exception as e:
            current_app.logger.error(f"Error in batch student synchronization: {e}")
            current_app.logger.error(traceback.format_exc())
            return create_response(
                success=False,
                error=f'Error in batch student synchronization',
                details=str(e),
                status_code=500
            )
    except Exception as e:
        current_app.logger.error(f"Error in student synchronization: {e}")
        current_app.logger.error(traceback.format_exc())
        return create_response(
            success=False,
            error='Error in student synchronization',
            details=str(e),
            status_code=500
        )

@customer_sync_bp.route('/student/update', methods=['POST'])
def update_single_student():
    """
    Update an existing QuickBooks customer for a single student by reg_no.
    Performs a sparse update to avoid overwriting existing fields.
    """
    data = request.get_json() or {}
    reg_no = data.get('reg_no')
    try:
        # Validate QuickBooks connection
        is_connected, error_response = validate_quickbooks_connection()
        if not is_connected:
            return error_response

        sync_service = CustomerSyncService()

        with db_manager.get_mis_session() as db:
            student = TblPersonalUg.get_student_details(reg_no)
            if not student:
                return create_response(
                    success=False,
                    error=f"Student {reg_no} not found",
                    status_code=404
                )

            quickbooks_id = student['qk_id']
            current_app
            current_app.logger.info(f"Fetched student {reg_no} with QuickBooks ID: {quickbooks_id}")
            if not quickbooks_id:
                return create_response(
                    success=False,
                    error=f"Student {reg_no} has not been synced to QuickBooks yet",
                    status_code=400
                )
            if not student.get('sync_token'):
                fetch_result = sync_service.get_customer_by_quickbooks_id(quickbooks_id)
                customer_data = fetch_result.get('data', fetch_result).get('Customer', {})
                sync_token = customer_data.get('SyncToken')

            current_app.logger.info(f"Fetched QuickBooks customer for student {reg_no}: {fetch_result} with type {type(fetch_result)}")
            qb_payload = sync_service.map_student_to_quickbooks_customer_update(
                student=student,
                qb_customer_id=quickbooks_id,
                sparse=True,
                SyncToken=sync_token if sync_token else None  # Default to "0" if SyncToken is missing
            )

            result = sync_service.update_quickbooks_customer(qb_customer_id=quickbooks_id, qb_customer_data=qb_payload)
            current_app.logger.info(f"Update result for student {reg_no}: {result}")

            if result.get('Customer'):
                QuickbooksAuditLog.add_audit_log(
                    action_type="Update single student",
                    operation_status=200,
                    error_message=None,
                )

                # update the synctoken to match the current one
                student = TblPersonalUg.get_student_by_reg_no(reg_no)
                student.sync_token = result["Customer"]["SyncToken"]
                # add
                db.add(student)
                db.commit()

                return create_response(
                    success=True,
                    data={
                        'student_reg_no': reg_no,
                        'quickbooks_id': quickbooks_id
                    },
                    message=f"Student {reg_no} updated successfully in QuickBooks"
                )
            else:
                db.session.rollback()
                QuickbooksAuditLog.add_audit_log(
                    action_type="Update single student",
                    operation_status=500,
                    error_message=result.error_message,
                )
                return create_response(
                    success=False,
                    error=f"Failed to update student {reg_no} in QuickBooks",
                    details=result.error_message,
                    status_code=500
                )
    except Exception as e:
        current_app.logger.error(f"Error updating student {reg_no}: {e}")
        current_app.logger.error(traceback.format_exc())
        return create_response(
            success=False,
            error=f"Error updating student {reg_no}",
            details=str(e),
            status_code=500
        )

@customer_sync_bp.route('/all', methods=['POST'])
def sync_all_customers():
    """
    Synchronize all customers (applicants and students) to QuickBooks

    Request body (JSON):
    {
        "batch_size": 50,  // Optional, defaults to 50
        "sync_applicants": true,  // Optional, defaults to true
        "sync_students": true     // Optional, defaults to true
    }
    """
    try:
        # Validate QuickBooks connection
        is_connected, error_response = validate_quickbooks_connection()
        if not is_connected:
            return error_response

        # Get request data
        request_data = request.get_json() or {}
        batch_size = request_data.get('batch_size', 50)
        sync_applicants = request_data.get('sync_applicants', True)
        sync_students = request_data.get('sync_students', True)

        # Validate batch size
        if batch_size > 100:
            return create_response(
                success=False,
                error='Batch size cannot exceed 100',
                status_code=400
            )

        sync_service = CustomerSyncService()

        overall_results = {
            'applicants': {'total_processed': 0, 'successful': 0, 'failed': 0, 'errors': []},
            'students': {'total_processed': 0, 'successful': 0, 'failed': 0, 'errors': []},
            'start_time': datetime.now().isoformat()
        }

        # Sync applicants if requested
        if sync_applicants:
            current_app.logger.info("Starting applicant synchronization...")
            applicants = sync_service.get_unsynchronized_applicants(limit=batch_size)

            for applicant in applicants:
                try:
                    result = sync_service.sync_single_applicant(applicant)
                    overall_results['applicants']['total_processed'] += 1

                    if result.success:
                        overall_results['applicants']['successful'] += 1
                    else:
                        overall_results['applicants']['failed'] += 1
                        overall_results['applicants']['errors'].append({
                            'applicant_id': result.customer_id,
                            'error': result.error_message
                        })

                    import time
                    time.sleep(0.5)

                except Exception as e:
                    overall_results['applicants']['failed'] += 1
                    overall_results['applicants']['errors'].append({
                        'applicant_id': applicant.appl_Id,
                        'error': str(e)
                    })

        # Sync students if requested
        if sync_students:
            current_app.logger.info("Starting student synchronization...")
            students = sync_service.get_unsynchronized_students(limit=batch_size)

            for student in students:
                try:
                    result = sync_service.sync_single_student(student)
                    overall_results['students']['total_processed'] += 1

                    if result.success:
                        overall_results['students']['successful'] += 1
                    else:
                        overall_results['students']['failed'] += 1
                        overall_results['students']['errors'].append({
                            'student_id': result.customer_id,
                            'error': result.error_message
                        })

                    import time
                    time.sleep(0.5)

                except Exception as e:
                    overall_results['students']['failed'] += 1
                    overall_results['students']['errors'].append({
                        'student_id': student.reg_no,
                        'error': str(e)
                    })

        overall_results['end_time'] = datetime.now().isoformat()

        total_successful = overall_results['applicants']['successful'] + overall_results['students']['successful']
        total_failed = overall_results['applicants']['failed'] + overall_results['students']['failed']

        return create_response(
            success=True,
            data=overall_results,
            message=f'Customer synchronization completed: {total_successful} successful, {total_failed} failed'
        )

    except Exception as e:
        current_app.logger.error(f"Error in full customer synchronization: {e}")
        current_app.logger.error(traceback.format_exc())
        return create_response(
            success=False,
            error='Error in full customer synchronization',
            details=str(e),
            status_code=500
        )

@customer_sync_bp.route('/status', methods=['GET'])
def get_customer_sync_status():
    """
    Get current customer synchronization status and statistics
    """
    try:
        sync_service = CustomerSyncService()
        stats = sync_service.analyze_customer_sync_requirements()

        # Calculate progress percentages
        applicant_total = stats.total_applicants
        applicant_synced = stats.applicants_synced
        applicant_progress = (applicant_synced / applicant_total * 100) if applicant_total > 0 else 0

        student_total = stats.total_students
        student_synced = stats.students_synced
        student_progress = (student_synced / student_total * 100) if student_total > 0 else 0

        overall_total = applicant_total + student_total
        overall_synced = applicant_synced + student_synced
        overall_progress = (overall_synced / overall_total * 100) if overall_total > 0 else 0

        status_data = {
            'statistics': stats.to_dict(),
            'progress': {
                'applicants': round(applicant_progress, 2),
                'students': round(student_progress, 2),
                'overall': round(overall_progress, 2)
            },
            'quickbooks_connected': QuickBooksConfig.is_connected(),
            'last_updated': datetime.now().isoformat()
        }

        return create_response(
            success=True,
            data=status_data,
            message='Customer synchronization status retrieved successfully'
        )

    except Exception as e:
        current_app.logger.error(f"Error getting customer sync status: {e}")
        current_app.logger.error(traceback.format_exc())
        return create_response(
            success=False,
            error='Error getting customer synchronization status',
            details=str(e),
            status_code=500
        )

@customer_sync_bp.route('/debug/student/<reg_no>', methods=['GET'])
def debug_student_enrichment(reg_no):
    """
    Debug endpoint to test student enrichment methods

    Args:
        reg_no: Student registration number to debug
    """
    try:
        from application.models.mis_models import TblPersonalUg
        from application.utils.database import db_manager

        # Get student
        with db_manager.get_mis_session() as session:
            student = session.query(TblPersonalUg).filter_by(reg_no=reg_no).first()

            if not student:
                return create_response(
                    success=False,
                    error=f'Student with reg_no {reg_no} not found',
                    status_code=404
                )

            # Run debug enrichment
            debug_results = student.debug_enrichment()

            # Also get the full to_dict_for_quickbooks result
            try:
                full_result = student.to_dict_for_quickbooks()
                debug_results['full_quickbooks_dict'] = full_result
            except Exception as e:
                debug_results['full_quickbooks_dict_error'] = str(e)

            return create_response(
                success=True,
                data=debug_results,
                message=f'Debug results for student {reg_no}'
            )

    except Exception as e:
        current_app.logger.error(f"Error debugging student {reg_no}: {e}")
        current_app.logger.error(traceback.format_exc())
        return create_response(
            success=False,
            error=f'Error debugging student {reg_no}',
            details=str(e),
            status_code=500
        )

@customer_sync_bp.route('/debug/country/<reg_no>', methods=['GET'])
def debug_country_enrichment(reg_no):
    """
    Debug endpoint specifically for country enrichment

    Args:
        reg_no: Student registration number to debug
    """
    try:
        from application.models.mis_models import TblPersonalUg, TblCountry
        from application.utils.database import db_manager

        # Get student
        with db_manager.get_mis_session() as session:
            student = session.query(TblPersonalUg).filter_by(reg_no=reg_no).first()

            if not student:
                return create_response(
                    success=False,
                    error=f'Student with reg_no {reg_no} not found',
                    status_code=404
                )

            # Debug country data
            debug_info = {
                'reg_no': reg_no,
                'raw_data': {
                    'cntr_id': student.cntr_id,
                    'nationality': student.nationality,
                    'has_country_relationship': hasattr(student, 'country'),
                    'country_relationship_value': str(student.country) if hasattr(student, 'country') and student.country else None
                },
                'country_lookup_results': {}
            }

            # Test country lookup by cntr_id
            if student.cntr_id:
                country_by_id = session.query(TblCountry).filter_by(cntr_id=student.cntr_id).first()
                if country_by_id:
                    debug_info['country_lookup_results']['by_cntr_id'] = {
                        'found': True,
                        'cntr_name': country_by_id.cntr_name,
                        'cntr_nationality': country_by_id.cntr_nationality,
                        'cntr_code': country_by_id.cntr_code
                    }
                else:
                    debug_info['country_lookup_results']['by_cntr_id'] = {'found': False}

            # Test country lookup by nationality field
            if student.nationality and student.nationality.isdigit():
                country_by_nationality = session.query(TblCountry).filter_by(cntr_id=int(student.nationality)).first()
                if country_by_nationality:
                    debug_info['country_lookup_results']['by_nationality_field'] = {
                        'found': True,
                        'cntr_name': country_by_nationality.cntr_name,
                        'cntr_nationality': country_by_nationality.cntr_nationality,
                        'cntr_code': country_by_nationality.cntr_code
                    }
                else:
                    debug_info['country_lookup_results']['by_nationality_field'] = {'found': False}

            # Test enrichment method
            try:
                enriched_country = student._get_enriched_country_name()
                debug_info['enrichment_result'] = enriched_country
            except Exception as e:
                debug_info['enrichment_error'] = str(e)

            return create_response(
                success=True,
                data=debug_info,
                message=f'Country debug results for student {reg_no}'
            )

    except Exception as e:
        current_app.logger.error(f"Error debugging country for student {reg_no}: {e}")
        current_app.logger.error(traceback.format_exc())
        return create_response(
            success=False,
            error=f'Error debugging country for student {reg_no}',
            details=str(e),
            status_code=500
        )

@customer_sync_bp.route('/debug/applicant/<int:appl_id>', methods=['GET'])
def debug_applicant_enrichment(appl_id):
    """
    Debug endpoint to test applicant enrichment methods

    Args:
        appl_id: Applicant ID to debug
    """
    try:


        # Get applicant
        with db_manager.get_mis_session() as session:
            applicant = session.query(TblOnlineApplication).filter_by(appl_Id=appl_id).first()

            if not applicant:
                return create_response(
                    success=False,
                    error=f'Applicant with ID {appl_id} not found',
                    status_code=404
                )

            # Debug country data
            debug_info = {
                'appl_Id': appl_id,
                'tracking_id': applicant.tracking_id,
                'raw_data': {
                    'country_of_birth': applicant.country_of_birth,
                    'present_nationality': applicant.present_nationality,
                    'program_mode_id': applicant.prg_mode_id
                },
                'enrichment_results': {},
                'errors': []
            }

            # Test country enrichment
            try:
                country_result = applicant._get_enriched_country_name()
                debug_info['enrichment_results']['country_name'] = country_result
            except Exception as e:
                debug_info['errors'].append(f"Country enrichment error: {e}")

            # Test program mode enrichment
            try:
                mode_result = applicant._get_enriched_program_mode()
                debug_info['enrichment_results']['program_mode'] = mode_result
            except Exception as e:
                debug_info['errors'].append(f"Program mode enrichment error: {e}")

            # Test full QuickBooks dict
            try:
                full_result = applicant.to_dict_for_quickbooks()
                debug_info['full_quickbooks_dict'] = {
                    'country_of_birth': full_result.get('country_of_birth'),
                    'program_mode': full_result.get('program_mode'),
                    'display_name': full_result.get('display_name')
                }
            except Exception as e:
                debug_info['full_quickbooks_dict_error'] = str(e)

            return create_response(
                success=True,
                data=debug_info,
                message=f'Debug results for applicant {appl_id}'
            )

    except Exception as e:
        current_app.logger.error(f"Error debugging applicant {appl_id}: {e}")
        current_app.logger.error(traceback.format_exc())
        return create_response(
            success=False,
            error=f'Error debugging applicant {appl_id}',
            details=str(e),
            status_code=500
        )

@customer_sync_bp.route('/sync_unsynchronized_students_batch', methods=['POST'])
def sync_unsynchronized_students_batch():
    """
    Synchronize a batch of unsynchronized students to QuickBooks customers.
    description: This endpoint fetches unsynchronized students from the database
                 and synchronizes them to QuickBooks in batches.
    1. Validates QuickBooks connection.
    2. Retrieves an optional 'batch_size' from the request body.
    3. Calls sync_service.sync_all_unsynchronized_students_in_batches(batch_size).
    4. Returns a summary of successful and failed synchronizations.
    5. Handles exceptions and logs errors.
    200:
        description: Batch synchronization initiated successfully.
        content:
            application/json:
                schema:
                    type: object
                    properties:
                        success:
                            type: boolean
                            example: true
                        data:
                            type: object
                            properties:
                                total_processed:
                                    type: integer
                                    example: 100
                                total_succeeded:
                                    type: integer
                                    example: 95
                                total_failed:
                                    type: integer
                                    example: 5
                                results:
                                    type: array
                                    items:
                                        type: object # CustomerSyncResult schema
                        message:
                            type: string
                            example: "Batch synchronization completed."
    400:
        description: Bad request, e.g. QuickBooks not connected or invalid batch_size.
    500:
        description: Internal server error during batch synchronization.
    """
    data = request.get_json() or {}
    batch_size = data.get('batch_size', 50) # Default batch size to 50

    if not isinstance(batch_size, int) or batch_size <= 0:
        return create_response(
            success=False,
            error='Invalid batch_size. Must be a positive integer.',
            status_code=400
        )

    sync_service = CustomerSyncService()

    try:
        is_connected, error_response = validate_quickbooks_connection()
        if not is_connected:
            return error_response
    except Exception as e:
        current_app.logger.error(f"Error validating QuickBooks connection for batch sync: {e}")
        current_app.logger.error(traceback.format_exc())
        return create_response(
            success=False,
            error='Error validating QuickBooks connection',
            details=str(e),
            status_code=500
        )

    try:
        sync_summary = sync_service.sync_all_unsynchronized_students_in_batches(batch_size=batch_size)
        message = f"Batch synchronization completed. Processed: {sync_summary['total_processed']}, Succeeded: {sync_summary['total_succeeded']}, Failed: {sync_summary['total_failed']}."
        current_app.logger.info(message)
        return create_response(
            success=True,
            data=sync_summary,
            message=message
        )
    except Exception as e:
        current_app.logger.error(f"Error during batch student synchronization: {e}")
        current_app.logger.error(traceback.format_exc())
        return create_response(
            success=False,
            error='Error during batch student synchronization',
            details=str(e),
            status_code=500
        )

@customer_sync_bp.route('/count_all_students', methods=['GET'])
def count_all_students():
    """
    Count all students in the MIS database.
    """
    synced_students = 0
    unsynced_students = 0
    try:
        synced_students = TblPersonalUg.count_synced_students()
        unsynced_students = TblPersonalUg.count_unsynced_students()
    except Exception as e:
        current_app.logger.error(f"Error counting students: {str(e)}")
    return jsonify({
        'synced_students': synced_students,
        'unsynced_students': unsynced_students,
        'total_students': synced_students + unsynced_students
    })

@customer_sync_bp.route('/reg_nos_check', methods=['GET'])
def check_reg_nos_existence():
    try:
        students = TblPersonalUg.get_unsynced_students()
        if not students:
            return jsonify({
                'success': True,
                'message': 'No unsynced students found',
                'reg_nos': []
            })
        reg_nos = [s.get('reg_no') for s in students if s.get('reg_no')]
        if not reg_nos:
            return jsonify({
                'success': True,
                'message': 'No reg nos found',
                'reg_nos': []
            })
        return jsonify({
            'success': True,
            'message': f'Found {len(reg_nos)} unsynced students',
            'reg_nos': reg_nos
        })
    except Exception as e:
        error_msg = f"Error checking reg nos: {str(e)}"
        current_app.logger.error(error_msg)
        current_app.logger.error(traceback.format_exc())
        return jsonify({
            'success': False,
            'error': error_msg,
            'details': traceback.format_exc()
        }), 500