from celery import shared_task
from datetime import datetime
from flask import current_app
import os
import traceback
from celery import group, chord
import redis

from application.services.customer_sync import CustomerSyncService
from application.models.central_models import QuickBooksConfig
from application.services.quickbooks import QuickBooks

# Initialize Redis client
redis_client = redis.Redis(
    host=os.getenv('REDIS_HOST', 'localhost'),
    port=int(os.getenv('REDIS_PORT', 6379)),
    db=int(os.getenv('REDIS_DB', 0)),
    decode_responses=True
)


def get_flask_app():
    """Helper function to get Flask app context"""
    from application import create_app
    app = create_app()
    return app

@shared_task
def bulk_sync_applicants_task(tracking_ids=None, batch_size=50, filter_unsynced=True, reset_offset=False):
    """
    Celery task to synchronize multiple applicants in batches with offset tracking
    
    This task orchestrates batch processing asynchronously without blocking.

    Args:
        tracking_ids: List of applicant tracking IDs (optional, fetches all if None)
        batch_size: Number of applicants to process in each batch
        filter_unsynced: Only sync applicants not already in QuickBooks
        reset_offset: If True, reset the offset to 0 and start from beginning
    Returns:
        dict: Summary with task info for tracking
    """
    from application.models.mis_models import TblOnlineApplication
    app = get_flask_app()
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
                    # no applicants left to process
                    raise ValueError("No applicants left to process with the current offset.")

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

            # Create a unique job ID for tracking
            job_id = f"bulk_sync_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{current_offset or 'manual'}"
            
            # Initialize job tracking in Redis
            redis_client.hset(f'job:{job_id}', mapping={
                'status': 'processing',
                'total_applicants': total_applicants,
                'total_batches': len(batches),
                'synced': 0,
                'failed': 0,
                'skipped': 0,
                'current_offset': current_offset or 0,
                'start_time': start_time.isoformat(),
                'use_offset': 1 if current_offset is not None else 0
            })
            redis_client.expire(f'job:{job_id}', 86400)  # Expire after 24 hours

            # Process batches using Celery chord
            job = group(
                process_applicants_batch.s(batch, batch_idx, len(batches), job_id)
                for batch_idx, batch in enumerate(batches, 1)
            )
            
            # Use callback to aggregate results after all batches complete
            result = chord(job)(aggregate_batch_results.s(job_id, current_offset))
            
            current_app.logger.info(
                f"Bulk sync job {job_id} initiated with {len(batches)} batches"
            )
            
            return {
                'success': True,
                'message': f'Bulk sync initiated with {total_applicants} applicants in {len(batches)} batches',
                'job_id': job_id,
                'task_id': result.id,
                'total_applicants': total_applicants,
                'total_batches': len(batches),
                'offset': current_offset,
                'status': 'processing'
            }
            
        except Exception as e:
            error_msg = f"Error initiating bulk sync: {str(e)}"
            current_app.logger.error(error_msg)
            current_app.logger.error(traceback.format_exc())
            
            return {
                'success': False,
                'error': error_msg,
                'details': traceback.format_exc(),
                'offset': current_offset if 'current_offset' in locals() else None
            }


@shared_task
def process_applicants_batch(tracking_ids, batch_num, total_batches, job_id):
    """
    Process a batch of applicants

    Args:
        tracking_ids: List of tracking IDs in this batch
        batch_num: Current batch number
        total_batches: Total number of batches
        job_id: Unique job identifier for tracking
        
    Returns:
        dict: Summary of batch processing
    """
    from application.models.mis_models import TblOnlineApplication
    app = get_flask_app()
    with app.app_context():
        current_app.logger.info(
            f"[Job {job_id}] Processing batch {batch_num}/{total_batches} with {len(tracking_ids)} students"
        )
        
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
                    current_app.logger.error(
                        f"Failed to sync applicant {tracking_id}: {result.error_message}"
                    )

            except Exception as e:
                results['failed'] += 1
                results['errors'].append({
                    'tracking_id': tracking_id,
                    'error': str(e)
                })
                current_app.logger.error(f"Exception syncing applicant {tracking_id}: {str(e)}")
                current_app.logger.error(traceback.format_exc())
        
        # Update job tracking in Redis
        try:
            redis_client.hincrby(f'job:{job_id}', 'synced', results['synced'])
            redis_client.hincrby(f'job:{job_id}', 'failed', results['failed'])
            redis_client.hincrby(f'job:{job_id}', 'skipped', results['skipped'])
        except Exception as e:
            current_app.logger.error(f"Failed to update Redis for job {job_id}: {str(e)}")
        
        current_app.logger.info(
            f"[Job {job_id}] Batch {batch_num} completed: {results['synced']} synced, "
            f"{results['failed']} failed, {results['skipped']} skipped"
        )
        
        return results


@shared_task
def aggregate_batch_results(batch_results, job_id, current_offset):
    """
    Aggregate results from all batches and finalize the job
    
    This task runs after all batch tasks complete via Celery's chord.

    Args:
        batch_results: List of result dicts from each batch
        job_id: Unique job identifier
        current_offset: The offset used for this job (None if manual tracking_ids)
        
    Returns:
        dict: Final aggregated results
    """
    from application.models.mis_models import TblOnlineApplication
    app = get_flask_app()
    with app.app_context():
        try:
            # Aggregate results from all batches
            total_synced = sum(r['synced'] for r in batch_results)
            total_failed = sum(r['failed'] for r in batch_results)
            total_skipped = sum(r['skipped'] for r in batch_results)
            all_errors = []
            for r in batch_results:
                all_errors.extend(r.get('errors', []))
            
            # Get job info from Redis
            job_info = redis_client.hgetall(f'job:{job_id}')
            start_time = datetime.fromisoformat(job_info.get('start_time', datetime.now().isoformat()))
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            # Update offset in Redis (only if we used offset-based fetching)
            new_offset = None
            offset_key = 'applicant_sync:offset'
            
            if current_offset is not None:
                # Increment offset by successfully processed records (synced + skipped)
                # Don't count failed records so they can be retried
                new_offset = current_offset + total_synced + total_skipped
                redis_client.set(offset_key, new_offset)
                
                current_app.logger.info(
                    f"[Job {job_id}] Updated sync offset from {current_offset} to {new_offset}"
                )
            
            # Update final job status in Redis
            redis_client.hset(f'job:{job_id}', mapping={
                'status': 'completed',
                'end_time': end_time.isoformat(),
                'duration_seconds': duration,
                'new_offset': new_offset or 0
            })
            
            final_result = {
                'success': True,
                'job_id': job_id,
                'message': f'Bulk sync completed in {duration:.2f} seconds',
                'total': int(job_info.get('total_applicants', 0)),
                'synced': total_synced,
                'failed': total_failed,
                'skipped': total_skipped,
                'batches_processed': len(batch_results),
                'duration_seconds': duration,
                'offset': current_offset,
                'new_offset': new_offset,
                'errors': all_errors[:10]  # Limit errors in response
            }
            
            current_app.logger.info(
                f"[Job {job_id}] Bulk sync completed: {total_synced} synced, "
                f"{total_failed} failed, {total_skipped} skipped in {duration:.2f} seconds"
            )
            
            return final_result
            
        except Exception as e:
            error_msg = f"Error aggregating batch results for job {job_id}: {str(e)}"
            current_app.logger.error(error_msg)
            current_app.logger.error(traceback.format_exc())
            
            # Update job status to failed
            try:
                redis_client.hset(f'job:{job_id}', mapping={
                    'status': 'failed',
                    'error': error_msg,
                    'end_time': datetime.now().isoformat()
                })
            except Exception:
                pass
            
            return {
                'success': False,
                'job_id': job_id,
                'error': error_msg,
                'details': traceback.format_exc()
            }


@shared_task
def get_job_status(job_id):
    """
    Get the current status of a bulk sync job in order to monitor progress 
    
    Args:
        job_id: Unique job identifier
        
    Returns:
        dict: Current job status and metrics
    """
    app = get_flask_app()
    
    with app.app_context():
        try:
            job_info = redis_client.hgetall(f'job:{job_id}')
            
            if not job_info:
                return {
                    'success': False,
                    'error': f'Job {job_id} not found'
                }
            
            # Calculate progress
            total_applicants = int(job_info.get('total_applicants', 0))
            synced = int(job_info.get('synced', 0))
            failed = int(job_info.get('failed', 0))
            skipped = int(job_info.get('skipped', 0))
            processed = synced + failed + skipped
            progress = (processed / total_applicants * 100) if total_applicants > 0 else 0
            
            return {
                'success': True,
                'job_id': job_id,
                'status': job_info.get('status', 'unknown'),
                'progress': round(progress, 2),
                'total_applicants': total_applicants,
                'total_batches': int(job_info.get('total_batches', 0)),
                'processed': processed,
                'synced': synced,
                'failed': failed,
                'skipped': skipped,
                'start_time': job_info.get('start_time'),
                'end_time': job_info.get('end_time'),
                'duration_seconds': float(job_info.get('duration_seconds', 0)),
                'current_offset': int(job_info.get('current_offset', 0)),
                'new_offset': int(job_info.get('new_offset', 0))
            }
            
        except Exception as e:
            error_msg = f"Error getting job status for {job_id}: {str(e)}"
            current_app.logger.error(error_msg)
            
            return {
                'success': False,
                'error': error_msg
            }