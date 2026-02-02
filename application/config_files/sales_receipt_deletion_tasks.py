from celery import shared_task, group, chord
from datetime import datetime
from flask import current_app
import traceback
import redis
import os
import re

from application.services.sales_receipt_sync import SalesReceiptSyncService
from application.models.central_models import QuickBooksConfig, QuickbooksAuditLog


# -------------------------------------------------------------------
# Redis client
# -------------------------------------------------------------------
redis_client = redis.Redis(
    host=os.getenv("REDIS_HOST", "localhost"),
    port=int(os.getenv("REDIS_PORT", 6379)),
    db=int(os.getenv("REDIS_DB", 0)),
    decode_responses=True
)


# -------------------------------------------------------------------
# Helper regex
# -------------------------------------------------------------------
QB_ID_REGEX = re.compile(r"ID:\s*(\d+)")


# -------------------------------------------------------------------
# Flask app factory helper
# -------------------------------------------------------------------
def get_flask_app():
    from application import create_app
    return create_app()


# -------------------------------------------------------------------
# Helper: Extract QuickBooks ID from audit log message
# -------------------------------------------------------------------
def extract_quickbooks_id(message: str) -> str | None:
    """Extract QuickBooks ID from audit log message."""
    if not message:
        return None
    match = QB_ID_REGEX.search(message)
    return match.group(1) if match else None


# -------------------------------------------------------------------
# MAIN BULK DELETION TASK (OFFSET-BASED)
# -------------------------------------------------------------------
@shared_task
def bulk_delete_sales_receipts_task(
    audit_log_ids=None,
    batch_size=50,
    reset_offset=False
):
    """
    Orchestrates sales_receipt deletion using offset-based batching from audit logs.

    Args:
        audit_log_ids (list[int] | None): Explicit audit log IDs to process
        batch_size (int): Batch size for processing
        reset_offset (bool): Reset Redis offset before deletion

    Returns:
        dict: Job status and metadata
    """
    from application import db

    app = get_flask_app()
    start_time = datetime.now()
    offset_key = "sales_receipt_deletion:offset"

    with app.app_context():
        try:
            # ----------------------------------------------------------
            # QuickBooks connection check
            # ----------------------------------------------------------
            if not QuickBooksConfig.is_connected():
                raise RuntimeError("QuickBooks not connected")

            # ----------------------------------------------------------
            # Offset handling
            # ----------------------------------------------------------
            if reset_offset:
                redis_client.set(offset_key, 0)
                current_app.logger.info("Sales receipt deletion offset reset to 0")

            current_offset = int(redis_client.get(offset_key) or 0)

            # ----------------------------------------------------------
            # Fetch audit log entries
            # ----------------------------------------------------------
            if audit_log_ids is None:
                logs = (
                    db.session.query(QuickbooksAuditLog)
                    .filter(
                        QuickbooksAuditLog.action_type == "sales_receipt",
                        QuickbooksAuditLog.operation_status == "SUCCESS",
                    )
                    .order_by(QuickbooksAuditLog.created_at.desc())
                    .limit(batch_size)
                    .offset(current_offset)
                    .all()
                )

                audit_log_ids = [log.id for log in logs]
            else:
                # Manual list → offset should not advance
                current_offset = None

            if not audit_log_ids:
                if current_offset is not None:
                    redis_client.set(offset_key, 0)

                return {
                    "success": True,
                    "message": "No audit logs to process",
                    "total": 0,
                    "deleted": 0,
                    "failed": 0,
                    "skipped": 0
                }

            # ----------------------------------------------------------
            # Batch creation
            # ----------------------------------------------------------
            batches = [
                audit_log_ids[i:i + batch_size]
                for i in range(0, len(audit_log_ids), batch_size)
            ]

            job_id = (
                f"sales_receipt_deletion_"
                f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_"
                f"{current_offset if current_offset is not None else 'manual'}"
            )

            # ----------------------------------------------------------
            # Initialize job tracking in Redis
            # ----------------------------------------------------------
            redis_client.hset(
                f"job:{job_id}",
                mapping={
                    "status": "processing",
                    "total_logs": len(audit_log_ids),
                    "total_batches": len(batches),
                    "deleted": 0,
                    "failed": 0,
                    "skipped": 0,
                    "current_offset": current_offset or 0,
                    "start_time": start_time.isoformat(),
                },
            )
            redis_client.expire(f"job:{job_id}", 86400)

            # ----------------------------------------------------------
            # Dispatch batches using chord
            # ----------------------------------------------------------
            job = group(
                process_deletion_batch.s(batch, idx, len(batches), job_id)
                for idx, batch in enumerate(batches, 1)
            )

            result = chord(job)(
                aggregate_deletion_results.s(job_id, current_offset)
            )

            current_app.logger.info(
                f"[Job {job_id}] Sales receipt deletion started "
                f"({len(audit_log_ids)} audit logs, {len(batches)} batches)"
            )

            return {
                "success": True,
                "job_id": job_id,
                "task_id": result.id,
                "total_logs": len(audit_log_ids),
                "total_batches": len(batches),
                "status": "processing",
            }

        except Exception as e:
            current_app.logger.error(
                f"Error starting sales receipt deletion: {str(e)}"
            )
            current_app.logger.error(traceback.format_exc())
            return {
                "success": False,
                "error": str(e),
            }


# -------------------------------------------------------------------
# BATCH PROCESSOR FOR DELETION
# -------------------------------------------------------------------
@shared_task
def process_deletion_batch(audit_log_ids, batch_num, total_batches, job_id):
    """
    Process a single batch of sales receipt deletions from audit logs.
    
    Args:
        audit_log_ids (list[int]): List of audit log IDs to process
        batch_num (int): Current batch number
        total_batches (int): Total number of batches
        job_id (str): Job identifier for tracking
        
    Returns:
        dict: Batch processing results
    """
    from application import db

    app = get_flask_app()

    with app.app_context():
        current_app.logger.info(
            f"[Job {job_id}] Processing deletion batch {batch_num}/{total_batches} "
            f"({len(audit_log_ids)} audit logs)"
        )

        sync_service = SalesReceiptSyncService()

        results = {
            "batch_num": batch_num,
            "deleted": 0,
            "failed": 0,
            "skipped": 0,
            "errors": [],
        }

        for audit_log_id in audit_log_ids:
            try:
                # Fetch audit log entry
                log = db.session.query(QuickbooksAuditLog).get(audit_log_id)
                
                if not log:
                    current_app.logger.warning(
                        f"[Job {job_id}] Audit log {audit_log_id} not found"
                    )
                    results["skipped"] += 1
                    continue

                # Extract QuickBooks ID
                qb_id = extract_quickbooks_id(log.error_message)
                
                if not qb_id:
                    current_app.logger.warning(
                        f"[Job {job_id}] No QB ID found in audit_log_id={audit_log_id}"
                    )
                    results["skipped"] += 1
                    continue

                # --------------------------------------------------
                # Determine SyncToken
                # --------------------------------------------------
                sync_token = "0"
                
                if log.error_message.startswith("Updated"):
                    # Fetch current SyncToken for updated receipts
                    current_app.logger.info(
                        f"[Job {job_id}] Fetching SyncToken for updated receipt qb_id={qb_id}"
                    )
                    
                    try:
                        sales_receipt = sync_service.get_sales_receipt_from_quickbooks(qb_id)
                        
                        if not sales_receipt:
                            current_app.logger.info(
                                f"[Job {job_id}] Receipt qb_id={qb_id} already deleted, skipping"
                            )
                            results["skipped"] += 1
                            QuickbooksAuditLog.update_log_status(
                                audit_log_id,
                                "SKIPPED",
                                f"SalesReceipt ID: {qb_id} already deleted.",
                            )
                            db.session.commit()
                            continue
                        
                        sync_token = sales_receipt['details']['SalesReceipt']['SyncToken']
                        
                    except Exception as e:
                        current_app.logger.error(
                            f"[Job {job_id}] Error fetching SyncToken for qb_id={qb_id}: {str(e)}"
                        )
                        results["failed"] += 1
                        results["errors"].append({
                            "audit_log_id": audit_log_id,
                            "qb_id": qb_id,
                            "error": f"SyncToken fetch failed: {str(e)}",
                        })
                        continue

                # --------------------------------------------------
                # Delete from QuickBooks
                # --------------------------------------------------
                current_app.logger.info(
                    f"[Job {job_id}] Deleting receipt qb_id={qb_id} sync_token={sync_token}"
                )
                
                result = sync_service.delete_sales_receipt_in_quickbooks(
                    qb_id,
                    sync_token
                )
                
                if not result:
                    current_app.logger.warning(
                        f"[Job {job_id}] Receipt qb_id={qb_id} already deleted"
                    )
                    results["skipped"] += 1
                    QuickbooksAuditLog.update_log_status(
                        audit_log_id,
                        "SKIPPED",
                        f"SalesReceipt ID: {qb_id} already deleted.",
                    )
                    db.session.commit()
                    continue
                
                if not result.get("success"):
                    error_msg = result.get("error_message", "Unknown error")
                    current_app.logger.error(
                        f"[Job {job_id}] Failed deleting qb_id={qb_id}: {error_msg}"
                    )
                    results["failed"] += 1
                    results["errors"].append({
                        "audit_log_id": audit_log_id,
                        "qb_id": qb_id,
                        "error": error_msg,
                    })
                    continue

                # --------------------------------------------------
                # Success - Update audit log
                # --------------------------------------------------
                results["deleted"] += 1
                QuickbooksAuditLog.update_log_status(
                    audit_log_id,
                    "DELETED",
                    f"SalesReceipt ID: {qb_id} deleted successfully.",
                )
                db.session.commit()

            except Exception as e:
                results["failed"] += 1
                results["errors"].append({
                    "audit_log_id": audit_log_id,
                    "error": str(e),
                })
                current_app.logger.error(
                    f"[Job {job_id}] Unhandled error for audit_log_id={audit_log_id}: {str(e)}"
                )
                current_app.logger.error(traceback.format_exc())
                
                # Rollback on error to prevent partial commits
                try:
                    db.session.rollback()
                except Exception:
                    pass

        # --------------------------------------------------------------
        # Update job counters in Redis
        # --------------------------------------------------------------
        try:
            redis_client.hincrby(f"job:{job_id}", "deleted", results["deleted"])
            redis_client.hincrby(f"job:{job_id}", "failed", results["failed"])
            redis_client.hincrby(f"job:{job_id}", "skipped", results["skipped"])
        except Exception as e:
            current_app.logger.warning(
                f"[Job {job_id}] Failed to update Redis counters: {str(e)}"
            )

        current_app.logger.info(
            f"[Job {job_id}] Batch {batch_num} completed: "
            f"{results['deleted']} deleted, "
            f"{results['failed']} failed, "
            f"{results['skipped']} skipped"
        )

        return results


# -------------------------------------------------------------------
# AGGREGATOR (FINALIZER)
# -------------------------------------------------------------------
@shared_task
def aggregate_deletion_results(batch_results, job_id, current_offset):
    """
    Aggregate all batch results and safely advance offset.
    
    Args:
        batch_results (list[dict]): Results from all batches
        job_id (str): Job identifier
        current_offset (int | None): Current offset position
        
    Returns:
        dict: Aggregated results
    """
    app = get_flask_app()

    with app.app_context():
        try:
            total_deleted = sum(r["deleted"] for r in batch_results)
            total_failed = sum(r["failed"] for r in batch_results)
            total_skipped = sum(r["skipped"] for r in batch_results)
            
            # Collect all errors
            all_errors = []
            for batch in batch_results:
                all_errors.extend(batch.get("errors", []))

            job_info = redis_client.hgetall(f"job:{job_id}")
            start_time = datetime.fromisoformat(
                job_info.get("start_time")
            )

            duration = (datetime.now() - start_time).total_seconds()

            # ----------------------------------------------------------
            # Advance offset only if this was an offset-based run
            # ----------------------------------------------------------
            new_offset = None
            if current_offset is not None:
                # Advance offset by successfully processed items (deleted + skipped)
                new_offset = current_offset + total_deleted + total_skipped
                redis_client.set("sales_receipt_deletion:offset", new_offset)

            # ----------------------------------------------------------
            # Store error summary if there are errors
            # ----------------------------------------------------------
            if all_errors:
                error_key = f"job:{job_id}:errors"
                redis_client.set(error_key, str(all_errors))
                redis_client.expire(error_key, 86400)

            # ----------------------------------------------------------
            # Update job status
            # ----------------------------------------------------------
            redis_client.hset(
                f"job:{job_id}",
                mapping={
                    "status": "completed",
                    "end_time": datetime.now().isoformat(),
                    "duration_seconds": duration,
                    "new_offset": new_offset or 0,
                    "error_count": len(all_errors),
                },
            )

            current_app.logger.info(
                f"[Job {job_id}] Completed: "
                f"{total_deleted} deleted, "
                f"{total_failed} failed, "
                f"{total_skipped} skipped "
                f"in {duration:.2f}s"
            )

            return {
                "success": True,
                "job_id": job_id,
                "deleted": total_deleted,
                "failed": total_failed,
                "skipped": total_skipped,
                "duration_seconds": duration,
                "errors": all_errors[:10],  # Return first 10 errors
                "total_errors": len(all_errors),
            }

        except Exception as e:
            current_app.logger.error(
                f"[Job {job_id}] Aggregation failed: {str(e)}"
            )
            current_app.logger.error(traceback.format_exc())

            redis_client.hset(
                f"job:{job_id}",
                mapping={
                    "status": "failed",
                    "end_time": datetime.now().isoformat(),
                    "error": str(e),
                },
            )

            return {
                "success": False,
                "job_id": job_id,
                "error": str(e),
            }


# -------------------------------------------------------------------
# CELERY BEAT WRAPPER (NON-BLOCKING)
# -------------------------------------------------------------------
@shared_task
def scheduled_sales_receipt_deletion_task():
    """
    Celery Beat entrypoint for progressive sales receipt deletion.
    
    This should be configured in Celery Beat schedule to run periodically.
    """
    app = get_flask_app()

    with app.app_context():
        current_app.logger.info("Scheduled sales receipt deletion triggered")

        async_result = bulk_delete_sales_receipts_task.delay(
            audit_log_ids=None,
            batch_size=100,
            reset_offset=False,
        )

        return {
            "success": True,
            "scheduled": True,
            "task_id": async_result.id,
            "timestamp": datetime.now().isoformat(),
        }


# -------------------------------------------------------------------
# UTILITY: Get Job Status
# -------------------------------------------------------------------
@shared_task
def get_deletion_job_status(job_id):
    """
    Retrieve the current status of a deletion job.
    
    Args:
        job_id (str): Job identifier
        
    Returns:
        dict: Job status and metadata
    """
    app = get_flask_app()

    with app.app_context():
        try:
            job_info = redis_client.hgetall(f"job:{job_id}")
            
            if not job_info:
                return {
                    "success": False,
                    "error": "Job not found",
                }

            # Retrieve errors if they exist
            error_key = f"job:{job_id}:errors"
            errors = redis_client.get(error_key)
            
            return {
                "success": True,
                "job_id": job_id,
                "status": job_info.get("status"),
                "deleted": int(job_info.get("deleted", 0)),
                "failed": int(job_info.get("failed", 0)),
                "skipped": int(job_info.get("skipped", 0)),
                "total_logs": int(job_info.get("total_logs", 0)),
                "total_batches": int(job_info.get("total_batches", 0)),
                "start_time": job_info.get("start_time"),
                "end_time": job_info.get("end_time"),
                "duration_seconds": float(job_info.get("duration_seconds", 0)),
                "current_offset": int(job_info.get("current_offset", 0)),
                "new_offset": int(job_info.get("new_offset", 0)),
                "has_errors": job_info.get("error_count", "0") != "0",
            }

        except Exception as e:
            current_app.logger.error(
                f"Error retrieving job status for {job_id}: {str(e)}"
            )
            return {
                "success": False,
                "error": str(e),
            }