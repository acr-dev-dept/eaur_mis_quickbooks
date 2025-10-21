# tasks/customer_sync_tasks.py
from celery import shared_task, group
from application.models.mis_models import TblOnlineApplication, TblCountry, TblPersonalUg
from application.services.customer_sync import CustomerSyncService
from application.models.central_models import QuickBooksConfig
import traceback
from datetime import datetime
from flask import current_app as flask_app
from application.utils.celery_utils import make_celery

celery = make_celery(flask_app)


@celery.task(bind=True, max_retries=3, default_retry_delay=60)
def sync_single_student_task(self, reg_no):
    """
    Celery task to synchronize a single student to QuickBooks
    
    Args:
        reg_no: Student registration number
        
    Returns:
        dict: Result with success status and details
    """
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
        print(error_msg)
        print(traceback.format_exc())
        
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
        print(error_msg)
        print(traceback.format_exc())
        
        return {
            'success': False,
            'error': error_msg,
            'details': traceback.format_exc()
        }


@celery.task(bind=True)
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
    print(f"Processing batch {batch_num}/{total_batches} with {len(reg_nos)} students")
    
    results = {
        'batch_num': batch_num,
        'synced': 0,
        'failed': 0,
        'skipped': 0,
        'errors': []
    }
    
    for reg_no in reg_nos:
        try:
            # CRITICAL: Call the task synchronously since we're already in a Celery task
            # Using delay() or apply_async() here would create unnecessary overhead
            result = sync_single_student_task(reg_no)
            
            if result['success']:
                results['synced'] += 1
            elif result.get('skipped'):
                results['skipped'] += 1
            else:
                results['failed'] += 1
                results['errors'].append({
                    'reg_no': reg_no,
                    'error': result.get('error')
                })
        except Exception as e:
            results['failed'] += 1
            results['errors'].append({
                'reg_no': reg_no,
                'error': str(e)
            })
    
    print(f"Batch {batch_num} completed: {results['synced']} synced, "
          f"{results['failed']} failed, {results['skipped']} skipped")
    
    return results


@celery.task(bind=True)
def sync_students_by_criteria(criteria=None, batch_size=50):
    """
    Sync students based on specific criteria (e.g., year, program, faculty)
    
    Args:
        criteria: Dict with filter criteria
        batch_size: Batch size for processing
        
    Returns:
        dict: Summary of sync operation
    """
    try:
        # Get filtered students based on criteria
        students = TblPersonalUg.get_students_by_criteria(criteria or {})
        reg_nos = [s.get('reg_no') for s in students if s.get('reg_no')]
        
        # Use bulk sync task
        return bulk_sync_students_task(reg_nos=reg_nos, batch_size=batch_size, filter_unsynced=False)
        
    except Exception as e:
        return {
            'success': False,
            'error': f"Error filtering students: {str(e)}"
        }