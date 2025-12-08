from celery import shared_task
from datetime import datetime
from application import create_app
from flask import current_app
import os
import traceback
from celery import group
import redis
from application.models.mis_models import TblOnlineApplication, TblImvoice, TblPersonalUg, TblIncomeCategory, Payment
from application.services.customer_sync import CustomerSyncService
from application.models.central_models import QuickBooksConfig
from application.services.quickbooks import QuickBooks

# Initialize Redis client (add this at the top of your file with other imports)
redis_client = redis.Redis(
    host=os.getenv('REDIS_HOST', 'localhost'),
    port=int(os.getenv('REDIS_PORT', 6379)),
    db=int(os.getenv('REDIS_DB', 0)),
    decode_responses=True
)
app = create_app()


@shared_task
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
    with app.app_context():
        try:
            # Handle offset
            if reset_offset:
                redis_client.set(offset_key, 0)
                current_app.logger.info("Sync offset reset to 0")
            
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
                    current_app.logger.info("No more applicants to sync. Offset reset to 0.")
                
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

            current_app.logger.info(
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
                
                current_app.logger.info(
                    f"Updated sync offset from {current_offset} to {new_offset}"
                )
            else:
                new_offset = None
            
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            current_app.logger.info(
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
            current_app.logger.error(error_msg)
            current_app.logger.error(traceback.format_exc())
            
            return {
                'success': False,
                'error': error_msg,
                'details': traceback.format_exc(),
                'offset': current_offset if 'current_offset' in locals() else None
            }

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
    with app.app_context():
        current_app.logger.info(f"Processing batch {batch_num}/{total_batches} with {len(tracking_ids)} students")
        
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
                    # Update applicant status to synced
                    TblOnlineApplication.update_applicant_status(tracking_id, 1)
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
