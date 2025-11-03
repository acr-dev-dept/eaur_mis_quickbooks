from application.api.v1.customer_sync_api import create_response
from application.models.central_models import QuickBooksConfig
from application.services.quickbooks import QuickBooks
from application.utils.celery_utils import make_celery
from application import create_app
import os
import logging
from flask import current_app, jsonify
from application.services.payment_sync import PaymentSyncService
import requests
from application.services.customer_sync import CustomerSyncService
from application.services.invoice_sync import InvoiceSyncService
from concurrent.futures import ThreadPoolExecutor, as_completed
import traceback
from application.models.mis_models import TblOnlineApplication, TblImvoice, TblPersonalUg, TblIncomeCategory, Payment
from datetime import datetime
from celery import group, shared_task
from application.services.income_sync import IncomeSyncService


import redis

# Initialize Redis client (add this at the top of your file with other imports)
redis_client = redis.Redis(
    host=os.getenv('REDIS_HOST', 'localhost'),
    port=int(os.getenv('REDIS_PORT', 6379)),
    db=int(os.getenv('REDIS_DB', 0)),
    decode_responses=True
)

flask_app = create_app(os.getenv('FLASK_ENV', 'development'))
flask_app.logger.setLevel(logging.DEBUG)
flask_app.logger.info("Starting QuickBooks sync task")
celery = make_celery(flask_app)




@celery.task(bind=True)
def sync_payments(self, limit=50, offset=0):
    """
    Celery task to synchronize unsynchronized payments from MIS to QuickBooks.
    """
    try:
        sync_service = PaymentSyncService()
        unsynchronized_payments = sync_service.get_unsynchronized_payments(
            limit=limit, offset=offset
        )
        flask_app.logger.info(
            f"Retrieved {len(unsynchronized_payments)} unsynchronized payments "
            f"and the type is {type(unsynchronized_payments)}"
        )
        succeeded = 0
        payment_ids = []

        for payment in unsynchronized_payments:
            payment = payment.to_dict()
            payment_id = payment.get('id')
            try:
                url = f"https://api.eaur.ac.rw/api/v1/sync/payments/sync_payment/{payment_id}"
                response = requests.post(url, timeout=30) 

                if response.status_code == 200:
                    succeeded += 1
                    payment_ids.append(payment_id)
                    flask_app.logger.info(
                        f"Successfully synchronized payment ID {payment_id}, response: {response.text}"
                    )
                else:
                    flask_app.logger.error(
                        f"Failed to sync payment ID {payment_id}, status: {response.status_code}, body: {response.text}"
                    )

            except Exception as e:
                flask_app.logger.error(f"Exception syncing payment ID {payment_id}: {e}")

        flask_app.logger.info(
            f"Payment sync completed: {succeeded}/{len(unsynchronized_payments)} succeeded"
        )

        return {
            "total_succeeded": succeeded,
            "total_attempted": len(unsynchronized_payments),
            "payment_ids": payment_ids,
        }

    except Exception as e:
        flask_app.logger.error(f"Error during payment sync process: {e}")
        return {"error": str(e)}


@celery.task(bind=True, max_retries=3, default_retry_delay=60)
def sync_single_student_task(self, reg_no):
    """
    Celery task to synchronize a single student to QuickBooks
    
    Args:
        reg_no: Student registration number
        
    Returns:
        dict: Result with success status and details
    """
    with flask_app.app_context():
        sync_service = CustomerSyncService()
        
        try:
            # Validate QuickBooks connection
            if not QuickBooksConfig.is_connected():
                return {
                    'success': False,
                    'reg_no': reg_no,
                    'error': 'QuickBooks not connected'
                }
            
            # Fetch student details
            student = TblPersonalUg.get_student_details(reg_no)
            
            if not student:
                return {
                    'success': False,
                    'reg_no': reg_no,
                    'error': f"Student with reg_no {reg_no} not found"
                }
            
            # Check if already synced
            if student.get("quickbooks_status") == 1:
                return {
                    'success': False,
                    'reg_no': reg_no,
                    'error': f"Student already synchronized",
                    'skipped': True
                }
            
            # Perform synchronization
            result = sync_service.sync_single_student(student)
            
            if result.success:
                return {
                    'success': True,
                    'reg_no': reg_no,
                    'student_id': result.customer_id,
                    'quickbooks_id': result.quickbooks_id,
                    'student_name': f"{student.get('first_name')} {student.get('last_name')}"
                }
            else:
                return {
                    'success': False,
                    'reg_no': reg_no,
                    'error': result.error_message
                }
                
        except Exception as e:
            # Log error and retry
            error_msg = f"Error syncing student {reg_no}: {str(e)}"
            flask_app.logger.error(error_msg)
            flask_app.logger.error(traceback.format_exc())
            
            # Retry the task
            try:
                raise self.retry(exc=e)
            except self.MaxRetriesExceededError:
                return {
                    'success': False,
                    'reg_no': reg_no,
                    'error': f"Max retries exceeded: {str(e)}"
                }


@celery.task(bind=True)
def bulk_sync_students_task(self, reg_nos=None, batch_size=50, filter_unsynced=True):
    """
    Celery task to synchronize multiple students in batches
    
    Args:
        reg_nos: List of registration numbers (optional, fetches all if None)
        batch_size: Number of students to process in each batch
        filter_unsynced: Only sync students not already in QuickBooks
        
    Returns:
        dict: Summary of the bulk sync operation
    """
    start_time = datetime.now()
    with flask_app.app_context():
        try:
            # Get list of students to sync
            if reg_nos is None:
                # Fetch all students (or unsynced students)
                if filter_unsynced:
                    students = TblPersonalUg.get_unsynced_students()
                else:
                    students = TblPersonalUg.get_all_students()
                
                reg_nos = [s.get('reg_no') for s in students if s.get('reg_no')]
            
            total_students = len(reg_nos)
            
            if total_students == 0:
                return {
                    'success': True,
                    'message': 'No students to sync',
                    'total': 0,
                    'synced': 0,
                    'failed': 0,
                    'skipped': 0
                }
            
            # Create batches
            batches = [reg_nos[i:i + batch_size] for i in range(0, len(reg_nos), batch_size)]
            
            flask_app.logger.info(f"Starting bulk sync of {total_students} students in {len(batches)} batches")
            
            # Process batches using Celery groups
            job = group(
                process_student_batch.s(batch, batch_idx, len(batches))
                for batch_idx, batch in enumerate(batches, 1)
            )
            
            # Execute and wait for results
            result = job.apply_async()
            batch_results = result.get()
            
            # Aggregate results
            total_synced = sum(r['synced'] for r in batch_results)
            total_failed = sum(r['failed'] for r in batch_results)
            total_skipped = sum(r['skipped'] for r in batch_results)
            
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            flask_app.logger.info(
                f"Bulk sync completed: {total_synced} synced, {total_failed} failed, "
                f"{total_skipped} skipped in {duration:.2f} seconds"
            )
            
            return {
                'success': True,
                'message': f'Bulk sync completed in {duration:.2f} seconds',
                'total': total_students,
                'synced': total_synced,
                'failed': total_failed,
                'skipped': total_skipped,
                'batches_processed': len(batches),
                'duration_seconds': duration
            }
            
        except Exception as e:
            error_msg = f"Error in bulk sync: {str(e)}"
            flask_app.logger.error(error_msg)
            flask_app.logger.error(traceback.format_exc())
            
            return {
                'success': False,
                'error': error_msg,
                'details': traceback.format_exc()
            }


@celery.task
def process_student_batch(reg_nos, batch_num, total_batches):
    """
    Process a batch of students
    
    Args:
        reg_nos: List of registration numbers in this batch
        batch_num: Current batch number
        total_batches: Total number of batches
        
    Returns:
        dict: Summary of batch processing
    """
    with flask_app.app_context():
        flask_app.logger.info(f"Processing batch {batch_num}/{total_batches} with {len(reg_nos)} students")
        
        sync_service = CustomerSyncService()
        
        results = {
            'batch_num': batch_num,
            'synced': 0,
            'failed': 0,
            'skipped': 0,
            'errors': []
        }
        
        for reg_no in reg_nos:
            try:
                # Validate QuickBooks connection
                if not QuickBooksConfig.is_connected():
                    results['failed'] += 1
                    results['errors'].append({
                        'reg_no': reg_no,
                        'error': 'QuickBooks not connected'
                    })
                    continue
                
                # Fetch student details
                student = TblPersonalUg.get_student_details(reg_no)
                
                if not student:
                    results['failed'] += 1
                    results['errors'].append({
                        'reg_no': reg_no,
                        'error': f"Student with reg_no {reg_no} not found"
                    })
                    continue
                
                # Check if already synced
                if student.get("quickbooks_status") == 1:
                    results['skipped'] += 1
                    continue
                
                # Perform synchronization
                result = sync_service.sync_single_student(student)
                
                if result.success:
                    results['synced'] += 1
                    flask_app.logger.debug(f"Successfully synced student {reg_no}")
                else:
                    results['failed'] += 1
                    results['errors'].append({
                        'reg_no': reg_no,
                        'error': result.error_message
                    })
                    flask_app.logger.error(f"Failed to sync student {reg_no}: {result.error_message}")
                    
            except Exception as e:
                results['failed'] += 1
                results['errors'].append({
                    'reg_no': reg_no,
                    'error': str(e)
                })
                flask_app.logger.error(f"Exception syncing student {reg_no}: {str(e)}")
                flask_app.logger.error(traceback.format_exc())
        
        flask_app.logger.info(
            f"Batch {batch_num} completed: {results['synced']} synced, "
            f"{results['failed']} failed, {results['skipped']} skipped"
        )
        
        return results


@celery.task(bind=True)
def sync_students_by_criteria(self, criteria=None, batch_size=50):
    """
    Sync students based on specific criteria (e.g., year, program, faculty)
    
    Args:
        criteria: Dict with filter criteria
        batch_size: Batch size for processing
        
    Returns:
        dict: Summary of sync operation
    """
    try:
        flask_app.logger.info(f"Starting criteria-based sync with criteria: {criteria}")
        
        # Get filtered students based on criteria
        students = TblPersonalUg.get_students_by_criteria(criteria or {})
        reg_nos = [s.get('reg_no') for s in students if s.get('reg_no')]
        
        flask_app.logger.info(f"Found {len(reg_nos)} students matching criteria")
        
        # Call bulk sync task directly (we're already in a task)
        result = bulk_sync_students_task(
            reg_nos=reg_nos, 
            batch_size=batch_size, 
            filter_unsynced=False
        )
        return result
        
    except Exception as e:
        error_msg = f"Error filtering students: {str(e)}"
        flask_app.logger.error(error_msg)
        flask_app.logger.error(traceback.format_exc())
        return {
            'success': False,
            'error': error_msg
        }




@celery.task(bind=True, max_retries=3, default_retry_delay=60)
def sync_single_applicant_task(self, tracking_id):
    """
    Celery task to synchronize a single applicant to QuickBooks

    Args:
        tracking_id: Applicant tracking ID
        
    Returns:
        dict: Result with success status and details
    """
    with flask_app.app_context():
        sync_service = CustomerSyncService()
        
        try:
            # Validate QuickBooks connection
            if not QuickBooksConfig.is_connected():
                return {
                    'success': False,
                    'tracking_id': tracking_id,
                    'error': 'QuickBooks not connected'
                }

            # Fetch applicant details
            applicant = TblOnlineApplication.get_applicant_details(tracking_id)

            if not applicant:
                return {
                    'success': False,
                    'tracking_id': tracking_id,
                    'error': f"Applicant with tracking_id {tracking_id} not found"
                }
            
            # Check if already synced
            if applicant.get("quickbooks_status") == 1:
                return {
                    'success': False,
                    'tracking_id': tracking_id,
                    'error': f"Applicant already synchronized",
                    'skipped': True
                }
            
            # Perform synchronization
            result = sync_service.sync_single_applicant(applicant)
            
            if result.success:
                return {
                    'success': True,
                    'tracking_id': tracking_id,
                    'applicant_id': result.customer_id,
                    'quickbooks_id': result.quickbooks_id,
                    'applicant_name': f"{applicant.get('first_name')} {applicant.get('last_name')}"
                }
            else:
                return {
                    'success': False,
                    'tracking_id': tracking_id,
                    'error': result.error_message
                }
                
        except Exception as e:
            # Log error and retry
            error_msg = f"Error syncing applicant {tracking_id}: {str(e)}"
            flask_app.logger.error(error_msg)
            flask_app.logger.error(traceback.format_exc())
            
            # Retry the task
            try:
                raise self.retry(exc=e)
            except self.MaxRetriesExceededError:
                return {
                    'success': False,
                    'tracking_id': tracking_id,
                    'error': f"Max retries exceeded: {str(e)}"
                }



@celery.task(bind=True)
def bulk_sync_applicants_task(self, tracking_ids=None, batch_size=50, filter_unsynced=True, reset_offset=False):
    """
    Celery task to synchronize multiple applicants in batches with offset tracking

    Args:
        tracking_ids: List of applicant tracking IDs (optional, fetches all if None)
        batch_size: Number of applicants to process in each batch
        filter_unsynced: Only sync applicants not already in QuickBooks
        reset_offset: If True, reset the offset to 0 and start from beginning
    Returns:
        dict: Summary of the bulk sync operation
    """
    start_time = datetime.now()
    offset_key = 'applicant_sync:offset'
    
    with flask_app.app_context():
        try:
            # Handle offset
            if reset_offset:
                redis_client.set(offset_key, 0)
                flask_app.logger.info("Sync offset reset to 0")
            
            # Get current offset from Redis
            current_offset = int(redis_client.get(offset_key) or 0)
            current_app.logger.info(f"Current sync offset: {current_offset}")
            # Get list of applicants to sync
            if tracking_ids is None:
                # Fetch applicants with offset
                if filter_unsynced:
                    applicants = TblOnlineApplication.get_unsynced_applicants(
                        limit=batch_size,
                        offset=current_offset
                    )
                else:
                    applicants = TblOnlineApplication.get_all_applicants(
                        limit=batch_size,
                        offset=current_offset
                    )

                tracking_ids = [a.get('tracking_id') for a in applicants if a.get('tracking_id')]
            else:
                # If specific tracking_ids provided, don't use offset
                current_offset = None

            total_applicants = len(tracking_ids)

            if total_applicants == 0:
                # Reset offset when no more records found
                if current_offset is not None:
                    redis_client.set(offset_key, 0)
                    flask_app.logger.info("No more applicants to sync. Offset reset to 0.")
                
                return {
                    'success': True,
                    'message': 'No applicants to sync',
                    'total': 0,
                    'synced': 0,
                    'failed': 0,
                    'skipped': 0,
                    'offset': current_offset,
                    'offset_reset': True
                }
            
            # Create batches
            batches = [tracking_ids[i:i + batch_size] for i in range(0, len(tracking_ids), batch_size)]

            flask_app.logger.info(
                f"Starting bulk sync at offset {current_offset} with {total_applicants} applicants in {len(batches)} batches"
            )

            # Process batches using Celery groups
            job = group(
                process_applicants_batch.s(batch, batch_idx, len(batches))
                for batch_idx, batch in enumerate(batches, 1)
            )
            
            # Execute and wait for results
            result = job.apply_async()
            batch_results = result.get()
            
            # Aggregate results
            total_synced = sum(r['synced'] for r in batch_results)
            total_failed = sum(r['failed'] for r in batch_results)
            total_skipped = sum(r['skipped'] for r in batch_results)
            
            # Update offset in Redis (only if we used offset-based fetching)
            if current_offset is not None:
                # Increment offset by successfully processed records (synced + skipped)
                # Don't count failed records so they can be retried
                new_offset = current_offset + total_synced + total_skipped
                redis_client.set(offset_key, new_offset)
                
                flask_app.logger.info(
                    f"Updated sync offset from {current_offset} to {new_offset}"
                )
            else:
                new_offset = None
            
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            flask_app.logger.info(
                f"Bulk sync completed: {total_synced} synced, {total_failed} failed, "
                f"{total_skipped} skipped in {duration:.2f} seconds"
            )
            
            # Check if we should trigger next batch
            has_more = len(applicants) == batch_size if tracking_ids is None else False
            
            return {
                'success': True,
                'message': f'Bulk sync completed in {duration:.2f} seconds',
                'total': total_applicants,
                'synced': total_synced,
                'failed': total_failed,
                'skipped': total_skipped,
                'batches_processed': len(batches),
                'duration_seconds': duration,
                'offset': current_offset,
                'new_offset': new_offset,
                'has_more': has_more
            }
            
        except Exception as e:
            error_msg = f"Error in bulk sync: {str(e)}"
            flask_app.logger.error(error_msg)
            flask_app.logger.error(traceback.format_exc())
            
            return {
                'success': False,
                'error': error_msg,
                'details': traceback.format_exc(),
                'offset': current_offset if 'current_offset' in locals() else None
            }


@celery.task
def continuous_sync_applicants_task(batch_size=50, max_batches=None):
    """
    Continuously sync applicants in batches until all are synced
    
    Args:
        batch_size: Number of applicants per batch
        max_batches: Maximum number of batches to process (None = unlimited)
    
    Returns:
        dict: Summary of all batches processed
    """
    with flask_app.app_context():
        flask_app.logger.info(f"Starting continuous sync with batch_size={batch_size}")
        
        all_synced = 0
        all_failed = 0
        all_skipped = 0
        batches_processed = 0
        
        try:
            while True:
                # Check if we've reached max batches
                if max_batches and batches_processed >= max_batches:
                    flask_app.logger.info(f"Reached max batches limit: {max_batches}")
                    break
                
                # Process one batch
                result = bulk_sync_applicants_task(
                    batch_size=batch_size,
                    filter_unsynced=True,
                    reset_offset=False
                )
                
                if not result.get('success'):
                    flask_app.logger.error(f"Batch failed: {result.get('error')}")
                    break
                
                # Accumulate results
                all_synced += result.get('synced', 0)
                all_failed += result.get('failed', 0)
                all_skipped += result.get('skipped', 0)
                batches_processed += 1
                
                # Check if there are more records
                if not result.get('has_more', False):
                    flask_app.logger.info("No more applicants to sync")
                    break
                
                # Wait a bit before next batch to avoid overwhelming the system
                import time
                time.sleep(2)
            
            return {
                'success': True,
                'message': f'Continuous sync completed',
                'total_batches': batches_processed,
                'total_synced': all_synced,
                'total_failed': all_failed,
                'total_skipped': all_skipped
            }
            
        except Exception as e:
            error_msg = f"Error in continuous sync: {str(e)}"
            flask_app.logger.error(error_msg)
            flask_app.logger.error(traceback.format_exc())
            
            return {
                'success': False,
                'error': error_msg,
                'batches_processed': batches_processed,
                'total_synced': all_synced,
                'total_failed': all_failed,
                'total_skipped': all_skipped
            }


@celery.task
def reset_applicant_sync_offset():
    """
    Reset the sync offset to start from beginning
    
    Returns:
        dict: Confirmation message
    """
    with flask_app.app_context():
        try:
            redis_client.set('applicant_sync:offset', 0)
            flask_app.logger.info("Applicant sync offset reset to 0")
            return {
                'success': True,
                'message': 'Sync offset reset to 0'
            }
        except Exception as e:
            flask_app.logger.error(f"Error resetting offset: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }


@celery.task
def get_sync_progress():
    """
    Get current sync progress information
    
    Returns:
        dict: Current offset and unsynced count
    """
    with flask_app.app_context():
        try:
            current_offset = int(redis_client.get('applicant_sync:offset') or 0)
            
            # Get total unsynced count
            total_unsynced = TblOnlineApplication.count_unsynced_applicants()
            
            return {
                'success': True,
                'current_offset': current_offset,
                'total_unsynced': total_unsynced,
                'remaining': max(0, total_unsynced - current_offset)
            }
        except Exception as e:
            flask_app.logger.error(f"Error getting sync progress: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
        

@celery.task
def process_applicants_batch(tracking_ids, batch_num, total_batches):
    """
    Process a batch of applicants

    Args:
        tracking_ids: List of tracking IDs in this batch
        batch_num: Current batch number
        total_batches: Total number of batches
        
    Returns:
        dict: Summary of batch processing
    """
    with flask_app.app_context():
        flask_app.logger.info(f"Processing batch {batch_num}/{total_batches} with {len(tracking_ids)} students")
        
        sync_service = CustomerSyncService()
        
        results = {
            'batch_num': batch_num,
            'synced': 0,
            'failed': 0,
            'skipped': 0,
            'errors': []
        }

        for tracking_id in tracking_ids:
            try:
                # Validate QuickBooks connection
                if not QuickBooksConfig.is_connected():
                    results['failed'] += 1
                    results['errors'].append({
                        'tracking_id': tracking_id,
                        'error': 'QuickBooks not connected'
                    })
                    continue

                # Fetch applicant details
                applicant = TblOnlineApplication.get_applicant_details(tracking_id)

                if not applicant:
                    results['failed'] += 1
                    results['errors'].append({
                        'tracking_id': tracking_id,
                        'error': f"Applicant with tracking_id {tracking_id} not found"
                    })
                    continue
                
                # Check if already synced
                if applicant.get("quickbooks_status") == 1:
                    results['skipped'] += 1
                    continue
                
                # Perform synchronization
                result = sync_service.sync_single_applicant(applicant)
                
                if result.success:
                    results['synced'] += 1
                    flask_app.logger.debug(f"Successfully synced applicant {tracking_id}")
                    # Update applicant status to synced
                    TblOnlineApplication.update_applicant_status(tracking_id, 1)
                else:
                    results['failed'] += 1
                    results['errors'].append({
                        'tracking_id': tracking_id,
                        'error': result.error_message
                    })
                    flask_app.logger.error(f"Failed to sync applicant {tracking_id}: {result.error_message}")

            except Exception as e:
                results['failed'] += 1
                results['errors'].append({
                    'tracking_id': tracking_id,
                    'error': str(e)
                })
                flask_app.logger.error(f"Exception syncing applicant {tracking_id}: {str(e)}")
                flask_app.logger.error(traceback.format_exc())
        
        flask_app.logger.info(
            f"Batch {batch_num} completed: {results['synced']} synced, "
            f"{results['failed']} failed, {results['skipped']} skipped"
        )
        
        return results



# Add to application/tasks/scheduled_tasks.py

@celery.task(bind=True, max_retries=3, default_retry_delay=60)
def sync_single_income_category_task(self, category_id):
    """
    Celery task to synchronize a single income category to QuickBooks

    Args:
        category_id: Income category ID
        
    Returns:
        dict: Result with success status and details
    """
    with flask_app.app_context():
        sync_service = IncomeSyncService()
        
        try:
            # Validate QuickBooks connection
            if not QuickBooksConfig.is_connected():
                return {
                    'success': False,
                    'category_id': category_id,
                    'error': 'QuickBooks not connected'
                }

            # Fetch income category details
            category = TblIncomeCategory.get_category_by_id(category_id)

            if not category:
                return {
                    'success': False,
                    'category_id': category_id,
                    'error': f"Income category with ID {category_id} not found"
                }
            
            # Check if already synced
            if category.get("income_account_status") == 1:
                return {
                    'success': False,
                    'category_id': category_id,
                    'error': f"Income category already synchronized",
                    'skipped': True
                }
            
            # Perform synchronization
            result = sync_service.sync_income_category(category=category)
            
            if hasattr(result, 'status') and result.status == 'SYNCED':
                return {
                    'success': True,
                    'category_id': category_id,
                    'qb_account_id': result.qb_account_id if hasattr(result, 'qb_account_id') else None,
                    'qb_sync_token': result.qb_sync_token if hasattr(result, 'qb_sync_token') else None,
                    'category_name': category.get('name', 'Unknown')
                }
            else:
                error_msg = result.error_message if hasattr(result, 'error_message') else 'Sync failed'
                return {
                    'success': False,
                    'category_id': category_id,
                    'error': error_msg
                }
                
        except Exception as e:
            # Log error and retry
            error_msg = f"Error syncing income category {category_id}: {str(e)}"
            flask_app.logger.error(error_msg)
            flask_app.logger.error(traceback.format_exc())
            
            # Retry the task
            try:
                raise self.retry(exc=e)
            except self.MaxRetriesExceededError:
                return {
                    'success': False,
                    'category_id': category_id,
                    'error': f"Max retries exceeded: {str(e)}"
                }


@celery.task
def process_income_categories_batch(category_ids, batch_num, total_batches):
    """
    Process a batch of income categories

    Args:
        category_ids: List of category IDs in this batch
        batch_num: Current batch number
        total_batches: Total number of batches
        
    Returns:
        dict: Summary of batch processing
    """
    with flask_app.app_context():
        flask_app.logger.info(
            f"Processing income category batch {batch_num}/{total_batches} with {len(category_ids)} categories"
        )
        
        sync_service = IncomeSyncService()
        
        results = {
            'batch_num': batch_num,
            'synced': 0,
            'failed': 0,
            'skipped': 0,
            'errors': []
        }

        for category_id in category_ids:
            try:
                # Validate QuickBooks connection
                if not QuickBooksConfig.is_connected():
                    results['failed'] += 1
                    results['errors'].append({
                        'category_id': category_id,
                        'error': 'QuickBooks not connected'
                    })
                    continue

                # Fetch income category details
                category = TblIncomeCategory.get_category_by_id(category_id)

                if not category:
                    results['failed'] += 1
                    results['errors'].append({
                        'category_id': category_id,
                        'error': f"Income category with ID {category_id} not found"
                    })
                    continue
                
                # Check if already synced
                if category.get("income_account_status") == 1:
                    results['skipped'] += 1
                    flask_app.logger.debug(f"Income category {category_id} already synced, skipping")
                    continue

                # Perform synchronization
                result = sync_service.sync_income_category(category=category)

                # Check if sync was successful based on the response structure
                if hasattr(result, 'status') and result.status == 'SYNCED':
                    results['synced'] += 1
                    results['synced_details'].append({
                        'category_id': category_id,
                        'qb_account_id': result.qb_account_id if hasattr(result, 'qb_account_id') else None,
                        'category_name': category.get('name', 'Unknown')
                    })
                    flask_app.logger.info(
                        f"Successfully synced income category {category_id} "
                        f"(QB Account ID: {getattr(result, 'qb_account_id', 'N/A')})"
                    )
                else:
                    results['failed'] += 1
                    error_msg = result.error_message if hasattr(result, 'error_message') else 'Sync failed - unknown status'
                    results['errors'].append({
                        'category_id': category_id,
                        'error': error_msg
                    })
                    flask_app.logger.error(f"Failed to sync income category {category_id}: {error_msg}")

            except Exception as e:
                results['failed'] += 1
                results['errors'].append({
                    'category_id': category_id,
                    'error': str(e)
                })
                flask_app.logger.error(f"Exception syncing income category {category_id}: {str(e)}")
                flask_app.logger.error(traceback.format_exc())
        
        flask_app.logger.info(
            f"Income category batch {batch_num} completed: {results['synced']} synced, "
            f"{results['failed']} failed, {results['skipped']} skipped"
        )
        
        return results


@celery.task(bind=True)
def bulk_sync_income_categories_task(self, category_ids=None, batch_size=50, filter_unsynced=True):
    """
    Celery task to synchronize multiple income categories in batches

    Args:
        category_ids: List of income category IDs (optional, fetches all if None)
        batch_size: Number of categories to process in each batch
        filter_unsynced: Only sync categories not already in QuickBooks
        
    Returns:
        dict: Summary of the bulk sync operation
    """
    start_time = datetime.now()
    
    with flask_app.app_context():
        try:
            # Get list of income categories to sync
            if category_ids is None:
                # Fetch all unsynced income categories at once
                if filter_unsynced:
                    categories = TblIncomeCategory.get_unsynced_income_categories()
                else:
                    categories = TblIncomeCategory.get_all_categories()

                category_ids = [c.get('id') for c in categories if c.get('id')]

            total_categories = len(category_ids)

            if total_categories == 0:
                flask_app.logger.info("No income categories found to sync")
                return {
                    'success': True,
                    'message': 'No income categories to sync',
                    'total': 0,
                    'synced': 0,
                    'failed': 0,
                    'skipped': 0
                }
            
            flask_app.logger.info(
                f"Found {total_categories} income categories to sync. "
                f"First few IDs: {category_ids[:10]}"
            )
            
            # Create batches
            batches = [category_ids[i:i + batch_size] for i in range(0, len(category_ids), batch_size)]

            flask_app.logger.info(
                f"Starting bulk sync of {total_categories} income categories in {len(batches)} batches"
            )

            # Process batches using Celery groups
            job = group(
                process_income_categories_batch.s(batch, batch_idx, len(batches))
                for batch_idx, batch in enumerate(batches, 1)
            )
            
            # Execute and wait for results
            result = job.apply_async()
            batch_results = result.get()
            
            # Aggregate results
            total_synced = sum(r['synced'] for r in batch_results)
            total_failed = sum(r['failed'] for r in batch_results)
            total_skipped = sum(r['skipped'] for r in batch_results)
            
            # Collect all synced details
            all_synced_details = []
            all_errors = []
            for r in batch_results:
                all_synced_details.extend(r.get('synced_details', []))
                all_errors.extend(r.get('errors', []))
            
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            flask_app.logger.info(
                f"Income category bulk sync completed: {total_synced} synced, {total_failed} failed, "
                f"{total_skipped} skipped in {duration:.2f} seconds"
            )
            
            return {
                'success': True,
                'message': f'Bulk sync completed in {duration:.2f} seconds',
                'total': total_categories,
                'synced': total_synced,
                'failed': total_failed,
                'skipped': total_skipped,
                'batches_processed': len(batches),
                'duration_seconds': duration,
                'synced_details': all_synced_details[:20],  # First 20 synced items
                'errors': all_errors[:20] if all_errors else []  # First 20 errors if any
            }
            
        except Exception as e:
            error_msg = f"Error in income category bulk sync: {str(e)}"
            flask_app.logger.error(error_msg)
            flask_app.logger.error(traceback.format_exc())
            
            return {
                'success': False,
                'error': error_msg,
                'details': traceback.format_exc()
            }


@celery.task
def get_income_category_sync_stats():
    """
    Get income category sync statistics
    
    Returns:
        dict: Sync statistics
    """
    with flask_app.app_context():
        try:
            total_count = TblIncomeCategory.get_total_income_count()
            unsynced_count = TblIncomeCategory.get_unsynced_income_count()
            synced_count = total_count - unsynced_count
            
            return {
                'success': True,
                'total_categories': total_count,
                'synced': synced_count,
                'unsynced': unsynced_count,
                'sync_percentage': round((synced_count / total_count * 100), 2) if total_count > 0 else 0
            }
        except Exception as e:
            flask_app.logger.error(f"Error getting income category sync stats: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }


@celery.task
def retry_failed_income_categories():
    """
    Retry syncing income categories that previously failed
    Fetches categories with quickbooks_status != 1 that have error messages
    
    Returns:
        dict: Summary of retry operation
    """
    with flask_app.app_context():
        try:
            # Get unsynced categories (which includes failed ones)
            failed_categories = TblIncomeCategory.get_unsynced_income_categories()
            
            if not failed_categories:
                return {
                    'success': True,
                    'message': 'No failed categories to retry',
                    'total': 0
                }
            
            flask_app.logger.info(f"Retrying {len(failed_categories)} failed income categories")
            
            # Trigger bulk sync for these categories
            category_ids = [c.get('id') for c in failed_categories if c.get('id')]
            result = bulk_sync_income_categories_task(
                category_ids=category_ids,
                batch_size=50,
                filter_unsynced=False  # Don't filter, we already have the list
            )
            
            return result
            
        except Exception as e:
            error_msg = f"Error retrying failed income categories: {str(e)}"
            flask_app.logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg
            }
        
@celery.task(bind=True, max_retries=3, default_retry_delay=60)
def sync_single_item_task(self, item_id):
    """
    Celery task to synchronize a single item to QuickBooks

    Args:
        item_id: Item ID
        
    Returns:
        dict: Result with success status and details
    """
    from application.services.quickbooks import QuickBooks
    with flask_app.app_context():
        sync_service = QuickBooks()
        
        try:
            # Validate QuickBooks connection
            if not QuickBooksConfig.is_connected():
                return {
                    'success': False,
                    'item_id': item_id,
                    'message': 'QuickBooks not connected'
                }

            # Fetch item details
            item = TblIncomeCategory.get_category_by_id_not_synced(item_id)

            if not item:
                return {
                    'success': False,
                    'item_id': item_id,
                    'message': f"Item with ID {item_id} not found"
                }
            
            if item['status_Id'] != 1:
                return {
                    'success': False,
                    'item_id': item_id,
                    'message': f"Item with ID {item_id} is not active"
                }
            
            if item['Quickbk_Status'] == 1:
                return {
                    'success': False,
                    'item_id': item_id,
                    'message': f"Item already synchronized",
                    'skipped': True
                }
            
            if len(item['name']) > 100:
                return {
                    'success': False,
                    'item_id': item_id,
                    'error': 'Item name too long',
                    'message': 'Item name must be 100 characters or fewer'
                }
            
            item_data = {
                "Name": item['name'],
                "Type": "Service",
                "IncomeAccount": {
                    "value": item['income_account_qb'],
                },
                "Description": item['description'] or "No description",
                "UnitPrice": 0.0,
            }

            result = sync_service.create_item(item_data)
            current_app.logger.info(f"QuickBooks response for item {item_id}: {result}")
            
            if not result.get('Item'):
                return {
                    'success': False,
                    'item_id': item_id,
                    'error': 'Failed to create item in QuickBooks',
                    'details': result
                }
            
            current_app.logger.info(f"Item synced successfully: {result.get('Item', {})}")

            item_id = result.get("Item", {}).get("Id")
            sync_token = result.get("Item", {}).get("SyncToken")

            current_app.logger.info(f"Item ID from QuickBooks: {item_id}")
            if not item_id:
                return jsonify({
                    'success': False,
                    'item_id': item_id,
                    'error': 'Failed to retrieve Item ID from QuickBooks response',
                    'details': 'Item ID is missing in the response data'
                }), 500
            update_status = TblIncomeCategory.update_quickbooks_status(category_id=item['id'], quickbooks_id=item_id, pushed_by="ItemSyncService", sync_token=sync_token)
            current_app.logger.info(f"QuickBooks status updated: {update_status}")
            if not update_status:
                return {
                    'success': False,
                    'item_id': item_id,
                    'error': 'Failed to update QuickBooks status in local database'
                }
            return jsonify({
                'success': True,
                'data': result,
                'message': f"Item {item['name']} synchronized successfully",
            }), 201
        
        except Exception as e:
            # Log error and retry
            error_msg = f"Error syncing item {item_id}: {str(e)}"
            flask_app.logger.error(error_msg)
            flask_app.logger.error(traceback.format_exc())
            
            # Retry the task
            try:
                raise self.retry(exc=e)
            except self.MaxRetriesExceededError:
                return jsonify({
                    'success': False,
                    'item_id': item_id,
                    'error': f"Max retries exceeded: {str(e)}"
                }), 500

@celery.task
def process_item_batch(item_ids, batch_num, total_batches):
    """
    Process a batch of items to synchronize with QuickBooks.

    Args:
        item_ids (list): List of item IDs in this batch
        batch_num (int): Current batch number
        total_batches (int): Total number of batches

    Returns:
        dict: Summary of batch processing
    """
    with flask_app.app_context():
        flask_app.logger.info(
            f"Processing QuickBooks item batch {batch_num}/{total_batches} with {len(item_ids)} items"
        )
    
        sync_service = QuickBooks()
        results = {
            'batch_num': batch_num,
            'synced': 0,
            'failed': 0,
            'skipped': 0,
            'errors': [],
            'synced_details': []
        }

        for item_id in item_ids:
            try:
                # Validate QuickBooks connection
                if not QuickBooksConfig.is_connected():
                    results['failed'] += 1
                    results['errors'].append({
                        'item_id': item_id,
                        'error': 'QuickBooks not connected'
                    })
                    continue

                # Fetch item details
                item = TblIncomeCategory.get_category_by_id_not_synced(item_id)

                if not item:
                    results['failed'] += 1
                    results['errors'].append({
                        'item_id': item_id,
                        'error': f"Item with ID {item_id} not found"
                    })
                    continue

                # Skip inactive items
                if item['status_Id'] != 1:
                    results['skipped'] += 1
                    flask_app.logger.debug(f"Item {item_id} inactive, skipping")
                    continue

                # Skip already synced items
                if item['Quickbk_Status'] == 1:
                    results['skipped'] += 1
                    flask_app.logger.debug(f"Item {item_id} already synced, skipping")
                    continue
                
                if len(item['name']) > 100:
                    results['failed'] += 1
                    results['errors'].append({
                        'item_id': item_id,
                        'error': 'Item name too long',
                        'message': 'Item name must be 100 characters or fewer'
                    })
                    flask_app.logger.error(f"Item {item_id} name too long, skipping")
                    continue
                
                if not item['income_account_qb']:
                    results['failed'] += 1
                    results['errors'].append({
                        'item_id': item_id,
                        'error': 'Income account not mapped',
                        'message': 'Please map the income account before syncing'
                    })
                    flask_app.logger.error(f"Item {item_id} income account not mapped, skipping")
                    continue

                item_data = {
                    "Name": item['name'],
                    "Type": "Service",
                    "IncomeAccount": {
                        "value": item['income_account_qb'],
                    },
                    "Description": item['description'] or "No description",
                    "UnitPrice": 0.0,
                }

                # Perform synchronization
                result = sync_service.create_item(sync_service.realm_id,item_data)

                # Handle result object or dict
                
                if (
                    isinstance(result, dict)
                    and result.get("success")                     # ← corresponds to top-level 'success': true
                    and "data" in result
                    and "Item" in result["data"]                  # ← corresponds to 'data': {'Item': {...}}
                ):
                    qb_item = result["data"]["Item"]              # ← 'Item' block from your response
                    qb_item_id = qb_item.get("Id")
                    sync_token = qb_item.get("SyncToken")
                    name = qb_item.get("Name")

                    # Update local DB (same as before)
                    TblIncomeCategory.update_quickbooks_status(
                        category_id=item['id'],
                        quickbooks_id=qb_item_id,
                        pushed_by="ItemSyncService",
                        sync_token=sync_token
                    )

                    results['synced'] += 1
                    results['synced_details'].append({
                        'item_id': item_id,
                        'qb_item_id': qb_item_id,
                        'sync_token': sync_token,
                        'name': name
                    })
                    flask_app.logger.info(
                        f"Successfully synced item {item_id} (QB Item ID: {qb_item_id})"
                    )

                else:
                    results['failed'] += 1
                    error_msg = result.get("message", "Unknown QuickBooks sync failure")
                    results['errors'].append({
                        'item_id': item_id,
                        'error': error_msg
                    })
                    flask_app.logger.error(f"Failed to sync item {item_id}: {error_msg}")

            except Exception as e:
                results['failed'] += 1
                results['errors'].append({
                    'item_id': item_id,
                    'error': str(e)
                })
                flask_app.logger.error(f"Exception syncing item {item_id}: {str(e)}")
                flask_app.logger.error(traceback.format_exc())

        flask_app.logger.info(
            f"Item batch {batch_num}/{total_batches} completed: "
            f"{results['synced']} synced, {results['failed']} failed, {results['skipped']} skipped"
        )

        return results


@celery.task(bind=True)
def bulk_sync_items_task(self, item_ids=None, batch_size=50, filter_unsynced=True):
    """
    Celery task to synchronize multiple QuickBooks items in batches.

    Args:
        item_ids (list, optional): List of item IDs to sync
        batch_size (int): Number of items to process per batch
        filter_unsynced (bool): Whether to include only unsynced items

    Returns:
        dict: Summary of the bulk synchronization process
    """
    start_time = datetime.now()

    with flask_app.app_context():
        try:
            # Fetch items to sync
            if item_ids is None:
                if filter_unsynced:
                    items = TblIncomeCategory.get_unsynced_categories()
                else:
                    items = TblIncomeCategory.get_all_categories()

                item_ids = [i.get('id') for i in items if i.get('id')]

            total_items = len(item_ids)

            if total_items == 0:
                flask_app.logger.info("No QuickBooks items found to sync.")
                return {
                    'success': True,
                    'message': 'No items to synchronize',
                    'total': 0,
                    'synced': 0,
                    'failed': 0,
                    'skipped': 0
                }

            flask_app.logger.info(
                f"Found {total_items} items to sync. First few IDs: {item_ids[:10]}"
            )

            # Create batches
            batches = [item_ids[i:i + batch_size] for i in range(0, len(item_ids), batch_size)]

            flask_app.logger.info(
                f"Starting bulk sync of {total_items} items in {len(batches)} batches"
            )

            # Schedule all batch jobs
            job = group(
                process_item_batch.s(batch, batch_idx, len(batches))
                for batch_idx, batch in enumerate(batches, 1)
            )

            result = job.apply_async()
            batch_results = result.get()

            # Aggregate results
            total_synced = sum(r['synced'] for r in batch_results)
            total_failed = sum(r['failed'] for r in batch_results)
            total_skipped = sum(r['skipped'] for r in batch_results)

            all_synced_details = []
            all_errors = []
            for r in batch_results:
                all_synced_details.extend(r.get('synced_details', []))
                all_errors.extend(r.get('errors', []))

            duration = (datetime.now() - start_time).total_seconds()

            flask_app.logger.info(
                f"Item bulk sync completed: {total_synced} synced, "
                f"{total_failed} failed, {total_skipped} skipped in {duration:.2f} seconds"
            )

            return {
                'success': True,
                'message': f"Bulk item sync completed in {duration:.2f} seconds",
                'total': total_items,
                'synced': total_synced,
                'failed': total_failed,
                'skipped': total_skipped,
                'batches_processed': len(batches),
                'duration_seconds': duration,
                'synced_details': all_synced_details[:20],
                'errors': all_errors[:20] if all_errors else []
            }

        except Exception as e:
            error_msg = f"Error in bulk item sync: {str(e)}"
            flask_app.logger.error(error_msg)
            flask_app.logger.error(traceback.format_exc())

            return {
                'success': False,
                'error': error_msg,
                'details': traceback.format_exc()
            }


@celery.task(bind=True, max_retries=3, default_retry_delay=60)
def sync_single_invoice_task(self, invoice_id):
    """
    Celery task to synchronize a single invoice to QuickBooks

    Args:
        invoice_id: Invoice ID
        
    Returns:
        dict: Result with success status and details
    """
    with flask_app.app_context():
        sync_service = InvoiceSyncService()
        
        try:
            # Validate QuickBooks connection
            if not QuickBooksConfig.is_connected():
                return {
                    'success': False,
                    'invoice_id': invoice_id,
                    'error': 'QuickBooks not connected'
                }

            # Fetch invoice details
            invoice_data = sync_service.fetch_invoice_data(invoice_id)

            if not invoice_data:
                return {
                    'success': False,
                    'invoice_id': invoice_id,
                    'error': f"Invoice with ID {invoice_id} not found"
                }
            
            # Check if already synced
            if invoice_data.get("QuickBk_Status") == 1:
                return {
                    'success': False,
                    'invoice_id': invoice_id,
                    'error': f"Invoice already synchronized",
                    'skipped': True
                }
            
            # Perform synchronization
            result = sync_service.sync_single_invoice(invoice_data)

            if result.success:
                return {
                    'success': True,
                    'invoice_id': invoice_id,
                    'quickbooks_id': result.quickbooks_id,
                    'doc_number': invoice_data.get('doc_number')
                }
            else:
                return {
                    'success': False,
                    'invoice_id': invoice_id,
                    'error': result.error_message
                }
            
        except Exception as e:
            # Log error and retry
            error_msg = f"Error syncing invoice {invoice_id}: {str(e)}"
            flask_app.logger.error(error_msg)
            flask_app.logger.error(traceback.format_exc())
            
            # Retry the task
            try:
                raise self.retry(exc=e)
            except self.MaxRetriesExceededError:
                return {
                    'success': False,
                    'invoice_id': invoice_id,
                    'error': f"Max retries exceeded: {str(e)}"
                }


@celery.task(bind=True)
def bulk_sync_invoices_task(self, invoice_ids=None, batch_size=50, filter_unsynced=True, reset_offset=False):
    """
    Celery task to synchronize multiple invoices in batches with offset tracking
    This is the MAIN task that uses Redis offset for progressive syncing

    Args:
        invoice_ids: List of invoice IDs (optional, fetches from DB if None)
        batch_size: Number of invoices to process in each batch
        filter_unsynced: Only sync invoices not already in QuickBooks
        reset_offset: If True, reset the offset to 0 and start from beginning

    Returns:
        dict: Summary of the bulk sync operation
    """
    start_time = datetime.now()
    offset_key = 'invoice_sync:offset'
    
    with flask_app.app_context():
        try:
            # Handle offset
            if reset_offset:
                redis_client.set(offset_key, 0)
                flask_app.logger.info("Invoice sync offset reset to 0")
            
            # Get current offset from Redis
            current_offset = int(redis_client.get(offset_key) or 0)
            flask_app.logger.info(f"Current invoice sync offset: {current_offset}")
            

            # count the number of unsynced invoices
            total_unsynced_invoices = TblImvoice.get_unsynced_invoice_count()
            flask_app.logger.info(f"Total unsynced invoices in DB: {total_unsynced_invoices}")
            if total_unsynced_invoices == 0 and invoice_ids is None:
                return {
                    'success': True,
                    'message': 'No unsynced invoices to sync',
                    'total': 0,
                    'synced': 0,
                    'failed': 0,
                    'skipped': 0,
                    'offset': current_offset
                }
        
            # Get list of invoices to sync
            if invoice_ids is None:
                # Fetch invoices with offset
                if filter_unsynced:
                    invoices = TblImvoice.get_unsynced_invoices(
                        limit=batch_size,
                        offset=current_offset
                    )
                else:
                    invoices = TblImvoice.get_all_invoices(
                        limit=batch_size,
                        offset=current_offset
                    )

                invoice_ids = [inv.get('id') for inv in invoices if inv.get('id')]
            else:
                # If specific invoice_ids provided, don't use offset
                current_offset = None

            total_invoices = len(invoice_ids)

            if total_invoices == 0:
                # Reset offset when no more records found
                if current_offset is not None:
                    redis_client.set(offset_key, 0)
                    flask_app.logger.info("No more invoices to sync. Offset reset to 0.")
                
                return {
                    'success': True,
                    'message': 'No invoices to sync',
                    'total': 0,
                    'synced': 0,
                    'failed': 0,
                    'skipped': 0,
                    'offset': current_offset,
                    'offset_reset': True
                }
            
            # Create batches
            batches = [invoice_ids[i:i + batch_size] for i in range(0, len(invoice_ids), batch_size)]

            flask_app.logger.info(
                f"Starting bulk invoice sync at offset {current_offset} with {total_invoices} invoices in {len(batches)} batches"
            )

            # Process batches using Celery groups
            job = group(
                process_invoices_batch.s(batch, batch_idx, len(batches))
                for batch_idx, batch in enumerate(batches, 1)
            )
            
            # Execute and wait for results
            result = job.apply_async()
            batch_results = result.get()
            
            # Aggregate results
            total_synced = sum(r['synced'] for r in batch_results)
            total_failed = sum(r['failed'] for r in batch_results)
            total_skipped = sum(r['skipped'] for r in batch_results)
            
            # Update offset in Redis (only if we used offset-based fetching)
            if current_offset is not None:
                # Increment offset by successfully processed records (synced + skipped)
                # Don't count failed records so they can be retried
                new_offset = current_offset + total_synced + total_skipped
                redis_client.set(offset_key, new_offset)
                
                flask_app.logger.info(
                    f"Updated invoice sync offset from {current_offset} to {new_offset}"
                )
            else:
                new_offset = None
            
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            flask_app.logger.info(
                f"Bulk invoice sync completed: {total_synced} synced, {total_failed} failed, "
                f"{total_skipped} skipped in {duration:.2f} seconds"
            )
            
            # Check if we should trigger next batch
            has_more = len(invoices) == batch_size if invoice_ids is None else False
            
            return {
                'success': True,
                'message': f'Bulk sync completed in {duration:.2f} seconds',
                'total': total_invoices,
                'synced': total_synced,
                'failed': total_failed,
                'skipped': total_skipped,
                'batches_processed': len(batches),
                'duration_seconds': duration,
                'offset': current_offset,
                'new_offset': new_offset,
                'has_more': has_more
            }
            
        except Exception as e:
            error_msg = f"Error in bulk invoice sync: {str(e)}"
            flask_app.logger.error(error_msg)
            flask_app.logger.error(traceback.format_exc())
            
            return {
                'success': False,
                'error': error_msg,
                'details': traceback.format_exc(),
                'offset': current_offset if 'current_offset' in locals() else None
            }


@celery.task
def process_invoices_batch(invoice_ids, batch_num, total_batches):
    """
    Process a batch of invoices

    Args:
        invoice_ids: List of invoice IDs in this batch
        batch_num: Current batch number
        total_batches: Total number of batches
        
    Returns:
        dict: Summary of batch processing
    """
    with flask_app.app_context():
        flask_app.logger.info(f"Processing invoice batch {batch_num}/{total_batches} with {len(invoice_ids)} invoices")
        
        sync_service = InvoiceSyncService()
        
        results = {
            'batch_num': batch_num,
            'synced': 0,
            'failed': 0,
            'skipped': 0,
            'errors': []
        }

        for invoice_id in invoice_ids:
            try:
                # Validate QuickBooks connection
                if not QuickBooksConfig.is_connected():
                    results['failed'] += 1
                    results['errors'].append({
                        'invoice_id': invoice_id,
                        'error': 'QuickBooks not connected'
                    })
                    continue

                # Fetch invoice data
                invoice_data = sync_service.fetch_invoice_data(invoice_id)

                if not invoice_data:
                    results['failed'] += 1
                    results['errors'].append({
                        'invoice_id': invoice_id,
                        'error': f"Invoice with ID {invoice_id} not found"
                    })
                    continue
                
                # Check if already synced
                if invoice_data.QuickBk_Status == 1:
                    results['skipped'] += 1
                    continue
                
                # Perform synchronization
                result = sync_service.sync_single_invoice(invoice_data)
                
                if result.success:
                    results['synced'] += 1
                    flask_app.logger.debug(f"Successfully synced invoice {invoice_id}")
                    
                else:
                    results['failed'] += 1
                    results['errors'].append({
                        'invoice_id': invoice_id,
                        'error': result.error_message
                    })
                    flask_app.logger.error(f"Failed to sync invoice {invoice_id}: {result.error_message}")

            except Exception as e:
                results['failed'] += 1
                results['errors'].append({
                    'invoice_id': invoice_id,
                    'error': str(e)
                })
                flask_app.logger.error(f"Exception syncing invoice {invoice_id}: {str(e)}")
                flask_app.logger.error(traceback.format_exc())
        
        flask_app.logger.info(
            f"Invoice batch {batch_num} completed: {results['synced']} synced, "
            f"{results['failed']} failed, {results['skipped']} skipped"
        )
        
        return results


@celery.task
def scheduled_invoice_sync_task():
    """
    THIS IS THE OPTIMAL WRAPPER TASK for Celery Beat
    
    Scheduled task to automatically sync pending invoices progressively.
    Uses offset tracking to sync a batch at a time without overwhelming the system.
    
    Returns:
        dict: Summary of sync results
    """
    with flask_app.app_context():
        flask_app.logger.info("Starting scheduled invoice sync (offset-based)")
        
        try:
            # Sync one batch of 50 invoices
            # The offset is automatically tracked in Redis
            result = bulk_sync_invoices_task(
                invoice_ids=None,       # Fetch from DB using offset
                batch_size=50,          # Process 50 at a time
                filter_unsynced=True,   # Only unsynced invoices
                reset_offset=False      # Don't reset, continue from last position
            )
            
            result['scheduled'] = True
            result['timestamp'] = datetime.now().isoformat()
            
            # Log progress
            if result.get('success'):
                flask_app.logger.info(
                    f"Scheduled sync completed: {result.get('synced')} synced, "
                    f"{result.get('failed')} failed, offset: {result.get('new_offset')}"
                )
            
            return result
            
        except Exception as e:
            error_msg = f"Error in scheduled invoice sync: {str(e)}"
            flask_app.logger.error(error_msg)
            flask_app.logger.error(traceback.format_exc())
            return {
                'success': False,
                'error': error_msg,
                'timestamp': datetime.now().isoformat()
            }
        
@celery.task(bind=True, max_retries=3, default_retry_delay=60)
def sync_single_payment_task(self, payment_id):
    """
    Celery task to synchronize a single payment to QuickBooks

    Args:
        payment_id: Payment ID
        
    Returns:
        dict: Result with success status and details
    """
    with flask_app.app_context():
        sync_service = PaymentSyncService()
        
        try:
            # Validate QuickBooks connection
            if not QuickBooksConfig.is_connected():
                return {
                    'success': False,
                    'payment_id': payment_id,
                    'error': 'QuickBooks not connected'
                }

            # Fetch payment details
            payment_data = Payment.get_payment_by_id(payment_id)

            if not payment_data:
                return {
                    'success': False,
                    'payment_id': payment_id,
                    'error': f"Payment with ID {payment_id} not found"
                }
            
            # Check if already synced
            if payment_data.QuickBk_Status == 1:
                return {
                    'success': False,
                    'payment_id': payment_id,
                    'error': f"Payment already synchronized",
                    'skipped': True
                }
            
            # Perform synchronization
            result = sync_service.sync_single_payment(payment_data)

            if result.success:
                return {
                    'success': True,
                    'payment_id': payment_id,
                    'quickbooks_id': result.quickbooks_id,
                }
            else:
                return {
                    'success': False,
                    'payment_id': payment_id,
                    'error': result.error_message
                }
            
        except Exception as e:
            # Log error and retry
            error_msg = f"Error syncing payment {payment_id}: {str(e)}"
            flask_app.logger.error(error_msg)
            flask_app.logger.error(traceback.format_exc())
            
            # Retry the task
            try:
                raise self.retry(exc=e)
            except self.MaxRetriesExceededError:
                return {
                    'success': False,
                    'payment_id': payment_id,
                    'error': f"Max retries exceeded: {str(e)}"
                }
            
@celery.task(bind=True)
def bulk_sync_payments_task(self, payment_ids=None, batch_size=75, filter_unsynced=True, reset_offset=False):
    """
    Celery task to synchronize multiple payments in batches.

    Args:
        payment_ids: List of payment IDs (optional, fetches from DB if None)
        batch_size: Number of payments to process in each batch
        filter_unsynced: Only sync payments not already in QuickBooks
        reset_offset: If True, reset the offset to 0 and start from beginning
    """
    start_time = datetime.now()
    offset_key = 'payment_sync:offset'
    
    with flask_app.app_context():
        try:
            # Handle offset
            if reset_offset:
                redis_client.set(offset_key, 0)
                flask_app.logger.info("Payment sync offset reset to 0")
            
            # Get current offset from Redis
            current_offset = int(redis_client.get(offset_key) or 0)
            flask_app.logger.info(f"Current payment sync offset: {current_offset}")
            
            # check if there are unsynced payments
            total_unsynced_payments = Payment.get_unsynced_payment_count()
            flask_app.logger.info(f"Total unsynced payments in DB: {total_unsynced_payments}")
            if total_unsynced_payments == 0 and payment_ids is None:
                return {
                    'success': True,
                    'message': 'No unsynced payments to sync',
                    'total': 0,
                    'synced': 0,
                    'failed': 0,
                    'skipped': 0,
                    'offset': current_offset,
                    'offset_reset': True
                }


            # Get list of payments to sync
            if payment_ids is None:
                # Fetch payments with offset
                if filter_unsynced:
                    payments = Payment.get_unsynced_payments(
                        limit=batch_size,
                        offset=current_offset
                    )
                else:
                    return jsonify({
                        'success': False,
                        'error': 'Fetching all payments without filtering is not supported in this task.'
                    }), 400

                payment_ids = [pay.id for pay in payments if pay.id]
            else:
                # If specific payment_ids provided, don't use offset
                current_offset = None

            total_payments = len(payment_ids)

            if total_payments == 0:
                # Reset offset when no more records found
                if current_offset is not None:
                    redis_client.set(offset_key, 0)
                    flask_app.logger.info("No more payments to sync. Offset reset to 0.")
                
                return {
                    'success': True,
                    'message': 'No payments to sync',
                    'total': 0,
                    'synced': 0,
                    'failed': 0,
                    'skipped': 0,
                    'offset': current_offset,
                    'offset_reset': True
                }
            
            # Create batches
            batches = [payment_ids[i:i + batch_size] for i in range(0, len(payment_ids), batch_size)]

            flask_app.logger.info(
                f"Starting bulk payment sync at offset {current_offset} with {total_payments} payments in {len(batches)} batches"
            )

            # Process batches using Celery groups
            job = group(
                process_payments_batch.s(batch, batch_idx, len(batches))
                for batch_idx, batch in enumerate(batches, 1)
            )
            
            # Execute and wait for results
            result = job.apply_async()
            batch_results = result.get()
            
            # Aggregate results
            total_synced = sum(r['synced'] for r in batch_results)
            total_failed = sum(r['failed'] for r in batch_results)
            total_skipped = sum(r['skipped'] for r in batch_results)

            # Update offset in Redis (only if we used offset-based fetching)
            if current_offset is not None:
                # Increment offset by successfully processed records (synced + skipped)
                # Don't count failed records so they can be retried
                new_offset = current_offset + total_synced + total_skipped
                redis_client.set(offset_key, new_offset)
                
                flask_app.logger.info(
                    f"Updated payment sync offset from {current_offset} to {new_offset}"
                )
            else:
                new_offset = None

            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()

            flask_app.logger.info(
                f"Bulk payment sync completed: {total_synced} synced, {total_failed} failed, "
                f"{total_skipped} skipped in {duration:.2f} seconds"
            )

            return {
                'success': True,
                'message': f'Bulk sync completed in {duration:.2f} seconds',
                'total': total_payments,
                'synced': total_synced,
                'failed': total_failed,
                'skipped': total_skipped,
                'batches_processed': len(batches),
                'duration_seconds': duration,
                'offset': current_offset,
                'new_offset': new_offset
            }
        
        except Exception as e:
            error_msg = f"Error in bulk payment sync: {str(e)}"
            flask_app.logger.error(error_msg)
            flask_app.logger.error(traceback.format_exc())
            
            return {
                'success': False,
                'error': error_msg,
                'details': traceback.format_exc(),
                'offset': current_offset if 'current_offset' in locals() else None
            }
        
@celery.task
def process_payments_batch(payment_ids, batch_num, total_batches):
    """
    Process a batch of payments

    Args:
        payment_ids: List of payment IDs in this batch
        batch_num: Current batch number
        total_batches: Total number of batches
        
    Returns:
        dict: Summary of batch processing
    """
    with flask_app.app_context():
        flask_app.logger.info(f"Processing payment batch {batch_num}/{total_batches} with {len(payment_ids)} payments")
        
        sync_service = PaymentSyncService()
        
        results = {
            'batch_num': batch_num,
            'synced': 0,
            'failed': 0,
            'skipped': 0,
            'errors': []
        }

        for payment_id in payment_ids:
            try:
                # Validate QuickBooks connection
                if not QuickBooksConfig.is_connected():
                    results['failed'] += 1
                    results['errors'].append({
                        'payment_id': payment_id,
                        'error': 'QuickBooks not connected'
                    })
                    continue

                # Fetch payment data
                payment_data = Payment.get_payment_by_id(payment_id)

                if not payment_data:
                    results['failed'] += 1
                    results['errors'].append({
                        'payment_id': payment_id,
                        'error': f"Payment with ID {payment_id} not found"
                    })
                    continue
                
                # Check if already synced
                if payment_data.QuickBk_Status == 1:
                    results['skipped'] += 1
                    continue
                
                # Perform synchronization
                result = sync_service.sync_single_payment(payment_data)

                if result.get('success'):
                    results['synced'] += 1
                    flask_app.logger.debug(f"Successfully synced payment {payment_id}")
                    
                else:
                    results['failed'] += 1
                    results['errors'].append({
                        'payment_id': payment_id,
                        'error': result.error_message
                    })
                    flask_app.logger.error(f"Failed to sync payment {payment_id}: {result.error_message}")

            except Exception as e:
                results['failed'] += 1
                results['errors'].append({
                    'payment_id': payment_id,
                    'error': str(e)
                })
                flask_app.logger.error(f"Exception syncing payment {payment_id}: {str(e)}")
                flask_app.logger.error(traceback.format_exc())
        
        flask_app.logger.info(
            f"Payment batch {batch_num} completed: {results['synced']} synced, "
            f"{results['failed']} failed, {results['skipped']} skipped"
        )

        return results
    
@celery.task
def scheduled_payment_sync_task():
    """
    Scheduled task to automatically sync pending payments progressively.
    Uses offset tracking to sync a batch at a time without overwhelming the system.
    
    Returns:
        dict: Summary of sync results
    """
    with flask_app.app_context():
        flask_app.logger.info("Starting scheduled payment sync (offset-based)")
        
        try:
            # Sync one batch of 50 payments
            # The offset is automatically tracked in Redis
            result = bulk_sync_payments_task(
                payment_ids=None,       # Fetch from DB using offset
                batch_size=50,          # Process 50 at a time
                filter_unsynced=True,   # Only unsynced payments
                reset_offset=False      # Don't reset, continue from last position
            )
            
            result['scheduled'] = True
            result['timestamp'] = datetime.now().isoformat()
            
            # Log progress
            if result.get('success'):
                flask_app.logger.info(
                    f"Scheduled payment sync completed: {result.get('synced')} synced, "
                    f"{result.get('failed')} failed, offset: {result.get('new_offset')}"
                )
            
            return result
            
        except Exception as e:
            error_msg = f"Error in scheduled payment sync: {str(e)}"
            flask_app.logger.error(error_msg)
            flask_app.logger.error(traceback.format_exc())
            return {
                'success': False,
                'error': error_msg,
                'timestamp': datetime.now().isoformat()
            }
   