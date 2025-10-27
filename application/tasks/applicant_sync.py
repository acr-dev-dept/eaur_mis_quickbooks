# application/tasks/customer_sync_tasks.py
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
    flask_app.logger.info(f"Processing batch {batch_num}/{total_batches} with {len(reg_nos)} students")
    
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
                current_app.logger.debug(f"Successfully synced applicant {tracking_id}")
            else:
                results['failed'] += 1
                results['errors'].append({
                    'tracking_id': tracking_id,
                    'error': result.error_message
                })
                current_app.logger.error(f"Failed to sync applicant {tracking_id}: {result.error_message}")

        except Exception as e:
            results['failed'] += 1
            results['errors'].append({
                'tracking_id': tracking_id,
                'error': str(e)
            })
            current_app.logger.error(f"Exception syncing applicant {tracking_id}: {str(e)}")
            current_app.logger.error(traceback.format_exc())
    
    current_app.logger.info(
        f"Batch {batch_num} completed: {results['synced']} synced, "
        f"{results['failed']} failed, {results['skipped']} skipped"
    )
    
    return results

