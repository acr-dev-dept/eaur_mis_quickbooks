from celery import shared_task, group, chord
from datetime import datetime
from flask import current_app
import traceback
import redis
import os

from application.services.sales_receipt_sync import SalesReceiptSyncService
from application.models.central_models import QuickBooksConfig


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
# Flask app factory helper
# -------------------------------------------------------------------
def get_flask_app():
    from application import create_app
    return create_app()


# -------------------------------------------------------------------
# MAIN BULK SYNC TASK (OFFSET-BASED)
# -------------------------------------------------------------------
@shared_task
def bulk_sync_sales_recepts_task(
    sales_receipt_ids=None,
    batch_size=50,
    filter_unsynced=True,
    reset_offset=False
):
    """
    Orchestrates sales_receipt synchronization using offset-based batching.

    Args:
        sales_receipt_ids (list[int] | None): Explicit sales_receipt IDs to sync
        batch_size (int): Batch size
        filter_unsynced (bool): Only sync unsynced sales_receipts
        reset_offset (bool): Reset Redis offset before syncing

    Returns:
        dict
    """
    from application.models.mis_models import TblStudentWallet

    app = get_flask_app()
    start_time = datetime.now()
    offset_key = "sales_receipt_sync:offset"

    with app.app_context():
        try:
            # ----------------------------------------------------------
            # Offset handling
            # ----------------------------------------------------------
            if reset_offset:
                redis_client.set(offset_key, 0)
                current_app.logger.info("sales_receipt sync offset reset to 0")

            current_offset = int(redis_client.get(offset_key) or 0)

            # ----------------------------------------------------------
            # Fetch sales_receipt IDs
            # ----------------------------------------------------------
            if sales_receipt_ids is None:
                if not filter_unsynced:
                    raise ValueError("Bulk sales_receipt sync must filter unsynced sales_receipts")

                sales_receipts = TblStudentWallet.get_sales_receipts(
                    limit=batch_size,
                    offset=current_offset
                )

                sales_receipt_ids = [receipt["id"] for receipt in sales_receipts if receipt.get("id")]
            else:
                # Manual list → offset should not advance
                current_offset = None

            if not sales_receipt_ids:
                if current_offset is not None:
                    redis_client.set(offset_key, 0)

                return {
                    "success": True,
                    "message": "No sales_receipts to sync",
                    "total": 0,
                    "synced": 0,
                    "failed": 0,
                    "skipped": 0
                }

            # ----------------------------------------------------------
            # Batch creation
            # ----------------------------------------------------------
            batches = [
                sales_receipt_ids[i:i + batch_size]
                for i in range(0, len(sales_receipt_ids), batch_size)
            ]

            job_id = (
                f"sales_receipt_sync_"
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
                    "total_sales_receipts": len(sales_receipt_ids),
                    "total_batches": len(batches),
                    "synced": 0,
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
                process_sales_receipts_batch.s(batch, idx, len(batches), job_id)
                for idx, batch in enumerate(batches, 1)
            )

            result = chord(job)(
                aggregate_sales_receipt_results.s(job_id, current_offset)
            )

            current_app.logger.info(
                f"[Job {job_id}] Sales_receipt sync started "
                f"({len(sales_receipt_ids)}sales_receipts, {len(batches)} batches)"
            )

            return {
                "success": True,
                "job_id": job_id,
                "task_id": result.id,
                "total_sales_receipts": len(sales_receipt_ids),
                "total_batches": len(batches),
                "status": "processing",
            }

        except Exception as e:
            current_app.logger.error(
                f"Error starting sales_receipt sync: {str(e)}"
            )
            current_app.logger.error(traceback.format_exc())
            return {
                "success": False,
                "error": str(e),
            }


# -------------------------------------------------------------------
# BATCH PROCESSOR
# -------------------------------------------------------------------
@shared_task
def process_sales_receipts_batch(sales_receipt_ids, batch_num, total_batches, job_id):
    """
    Process a single batch of sales_receipts
    """
    from application.models.mis_models import TblStudentWallet

    app = get_flask_app()

    with app.app_context():
        current_app.logger.info(
            f"[Job {job_id}] Processing batch {batch_num}/{total_batches} "
            f"({len(sales_receipt_ids)} sales receipts)"
        )

        sync_service = SalesReceiptSyncService()

        results = {
            "batch_num": batch_num,
            "synced": 0,
            "failed": 0,
            "skipped": 0,
            "errors": [],
        }

        for sales_receipt_id in sales_receipt_ids:
            try:
                if not QuickBooksConfig.is_connected():
                    raise RuntimeError("QuickBooks not connected")

                sales_receipt = TblStudentWallet.get_sales_data(sales_receipt_id)

                if not sales_receipt:
                    raise ValueError("sales_receipt not found")

                if sales_receipt.quickbooks_id:
                    result = sync_service.update_single_sales_receipt(sales_receipt.id)
                    if result.success:
                        results["synced"] += 1
                    else:
                        raise RuntimeError(result.error_message)
                
                else:
                    result = sync_service.sync_single_sales_receipt(sales_receipt.id)

                    if result.success:
                        results["synced"] += 1
                    else:
                        raise RuntimeError(result.error_message)

            except Exception as e:
                results["failed"] += 1
                results["errors"].append({
                    "sales_receipt_id": sales_receipt_id,
                    "error": str(e),
                })
                current_app.logger.error(
                    f"[Job {job_id}] sales_receipt {sales_receipt_id}: {str(e)}"
                )

        # --------------------------------------------------------------
        # Update job counters
        # --------------------------------------------------------------
        try:
            redis_client.hincrby(f"job:{job_id}", "synced", results["synced"])
            redis_client.hincrby(f"job:{job_id}", "failed", results["failed"])
            redis_client.hincrby(f"job:{job_id}", "skipped", results["skipped"])
        except Exception:
            current_app.logger.warning(
                f"[Job {job_id}] Failed to update Redis counters"
            )

        return results


# -------------------------------------------------------------------
# AGGREGATOR (FINALIZER)
# -------------------------------------------------------------------
@shared_task
def aggregate_sales_receipt_results(batch_results, job_id, current_offset):
    """
    Aggregate all batch results and safely advance offset
    """
    app = get_flask_app()

    with app.app_context():
        try:
            total_synced = sum(r["synced"] for r in batch_results)
            total_failed = sum(r["failed"] for r in batch_results)
            total_skipped = sum(r["skipped"] for r in batch_results)

            job_info = redis_client.hgetall(f"job:{job_id}")
            start_time = datetime.fromisoformat(
                job_info.get("start_time")
            )

            duration = (datetime.now() - start_time).total_seconds()

            new_offset = None
            if current_offset is not None:
                new_offset = current_offset + total_synced + total_skipped
                redis_client.set("sales_receipt_sync:offset", new_offset)

            redis_client.hset(
                f"job:{job_id}",
                mapping={
                    "status": "completed",
                    "end_time": datetime.now().isoformat(),
                    "duration_seconds": duration,
                    "new_offset": new_offset or 0,
                },
            )

            current_app.logger.info(
                f"[Job {job_id}] Completed: "
                f"{total_synced} synced, "
                f"{total_failed} failed, "
                f"{total_skipped} skipped "
                f"in {duration:.2f}s"
            )

            return {
                "success": True,
                "job_id": job_id,
                "synced": total_synced,
                "failed": total_failed,
                "skipped": total_skipped,
                "duration_seconds": duration,
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
def scheduled_sales_receipt_sync_task():
    """
    Celery Beat entrypoint for progressive sales_receipt syncing
    """
    app = get_flask_app()

    with app.app_context():
        current_app.logger.info("Scheduled sales_receipt sync triggered")

        async_result = bulk_sync_sales_recepts_task.delay(
            sales_receipt_ids=None,
            batch_size=50,
            filter_unsynced=True,
            reset_offset=False,
        )

        return {
            "success": True,
            "scheduled": True,
            "task_id": async_result.id,
            "timestamp": datetime.now().isoformat(),
        }
