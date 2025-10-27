from application.api.v1.customer_sync_api import create_response
from application.models.central_models import QuickBooksConfig
from application.utils.celery_utils import make_celery
from application import create_app
import os
import logging
from flask import current_app
from application.services.payment_sync import PaymentSyncService
import requests
from application.services.customer_sync import CustomerSyncService
from application.services.invoice_sync import InvoiceSyncService
from concurrent.futures import ThreadPoolExecutor, as_completed
import traceback
from application.models.mis_models import TblOnlineApplication, TblCountry, TblPersonalUg
from datetime import datetime
from celery import group, shared_task

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


@celery.task(bind=True)
def sync_invoices(self, batch_size=20):
    """
    Celery task to synchronize unsynchronized invoices from MIS to QuickBooks.
    """
    try:
        sync_service = InvoiceSyncService()
        unsynchronized_invoices = sync_service.get_unsynchronized_invoices(limit=batch_size)
        flask_app.logger.info(
            f"Retrieved {len(unsynchronized_invoices)} unsynchronized invoices "
            f"and the type is {type(unsynchronized_invoices)}"
        )
        succeeded = 0
        invoice_ids = []

        for invoice in unsynchronized_invoices:
            invoice = invoice.to_dict()
            invoice_id = invoice.get('id')
            payload = {"invoice_id": invoice_id}
            try:
                url = f"https://api.eaur.ac.rw/api/v1/invoices/sync_single_invoice"
                response = requests.post(url, json=payload, timeout=30)

                if response.status_code == 200:
                    succeeded += 1
                    invoice_ids.append(invoice_id)
                    flask_app.logger.info(
                        f"Successfully synchronized invoice ID {invoice_id}, response: {response.text}"
                    )
                else:
                    flask_app.logger.error(
                        f"Failed to sync invoice ID {invoice_id}, status: {response.status_code}, body: {response.text}"
                    )

            except Exception as e:
                flask_app.logger.error(f"Exception syncing invoice ID {invoice_id}: {e}")
                continue
        flask_app.logger.info(
            f"Invoice sync completed: {succeeded}/{len(unsynchronized_invoices)} succeeded"
        )
        return {
            "total_succeeded": succeeded,
            "total_attempted": len(unsynchronized_invoices),
            "invoice_ids": invoice_ids,
        }
    except Exception as e:
        flask_app.logger.error(f"Error during invoice sync process: {e}")
        return {"error": str(e)}
    

# application/tasks/scheduled_tasks.py
@celery.task(bind=True, max_retries=3, default_retry_delay=60)
def sync_single_applicant_task(self, tracking_id):
    """
    Celery task to synchronize a single applicant to QuickBooks

    Args:
        tracking_id: Applicant tracking ID
        
    Returns:
        dict: Result with success status and details
    """
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
def bulk_sync_applicants_task(self, tracking_ids=None, batch_size=50, filter_unsynced=True):
    """
    Celery task to synchronize multiple applicants in batches

    Args:
        tracking_ids: List of applicant tracking IDs (optional, fetches all if None)
        batch_size: Number of applicants to process in each batch
        filter_unsynced: Only sync applicants not already in QuickBooks
    Returns:
        dict: Summary of the bulk sync operation
    """
    start_time = datetime.now()
    
    try:
        # Get list of applicants to sync
        if tracking_ids is None:
            # Fetch all applicants (or unsynced applicants)
            if filter_unsynced:
                applicants = TblOnlineApplication.get_unsynced_applicants()
            else:
                applicants = TblOnlineApplication.get_all_applicants()

            tracking_ids = [a.get('tracking_id') for a in applicants if a.get('tracking_id')]

        total_applicants = len(tracking_ids)

        if total_applicants == 0:
            return {
                'success': True,
                'message': 'No applicants to sync',
                'total': 0,
                'synced': 0,
                'failed': 0,
                'skipped': 0
            }
        
        # Create batches
        batches = [tracking_ids[i:i + batch_size] for i in range(0, len(tracking_ids), batch_size)]

        flask_app.logger.info(f"Starting bulk sync of {total_applicants} applicants in {len(batches)} batches")

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
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        flask_app.logger.info(
            f"Bulk sync completed: {total_synced} synced, {total_failed} failed, "
            f"{total_skipped} skipped in {duration:.2f} seconds"
        )
        
        return {
            'success': True,
            'message': f'Bulk sync completed in {duration:.2f} seconds',
            'total': total_applicants,
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
