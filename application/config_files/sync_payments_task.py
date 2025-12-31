from celery import shared_task, group, chord
from datetime import datetime
from flask import current_app
import traceback
import redis
import os

from application.services.payment_sync import PaymentSyncService
from application.models.central_models import QuickBooksConfig


# Redis client
redis_client = redis.Redis(
    host=os.getenv("REDIS_HOST", "localhost"),
    port=int(os.getenv("REDIS_PORT", 6379)),
    db=int(os.getenv("REDIS_DB", 0)),
    decode_responses=True
)


def get_flask_app():
    from application import create_app
    return create_app()


@shared_task
def bulk_sync_payments_task(payment_ids=None, batch_size=50, filter_unsynced=True, reset_offset=False):
    """
    Orchestrates payment synchronization using batch processing and Redis offset tracking
    """
    from application.models.mis_models import Payment

    app = get_flask_app()
    start_time = datetime.now()
    offset_key = "payment_sync:offset"

    with app.app_context():
        try:
            if reset_offset:
                redis_client.set(offset_key, 0)
                current_app.logger.info("Payment sync offset reset")

            current_offset = int(redis_client.get(offset_key) or 0)

            if payment_ids is None:
                if filter_unsynced:
                    payments = Payment.get_unsynced_payments(
                        limit=batch_size,
                        offset=current_offset
                    )
                else:
                    raise ValueError("No payments left to process")

                payment_ids = [p.id for p in payments if p.id is not None]
            else:
                current_offset = None

            total_payments = len(payment_ids)

            if total_payments == 0:
                if current_offset is not None:
                    redis_client.set(offset_key, 0)

                return {
                    "success": True,
                    "message": "No payments to sync",
                    "total": 0,
                    "synced": 0,
                    "failed": 0,
                    "skipped": 0
                }

            batches = [payment_ids[i:i + batch_size] for i in range(0, total_payments, batch_size)]

            job_id = f"payment_sync_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{current_offset or 'manual'}"

            redis_client.hset(f"job:{job_id}", mapping={
                "status": "processing",
                "total_payments": total_payments,
                "total_batches": len(batches),
                "synced": 0,
                "failed": 0,
                "skipped": 0,
                "current_offset": current_offset or 0,
                "start_time": start_time.isoformat()
            })
            redis_client.expire(f"job:{job_id}", 86400)

            job = group(
                process_payments_batch.s(batch, idx, len(batches), job_id)
                for idx, batch in enumerate(batches, 1)
            )

            result = chord(job)(aggregate_payment_results.s(job_id, current_offset))

            return {
                "success": True,
                "job_id": job_id,
                "task_id": result.id,
                "total_payments": total_payments,
                "total_batches": len(batches),
                "status": "processing"
            }

        except Exception as e:
            current_app.logger.error(traceback.format_exc())
            return {
                "success": False,
                "error": str(e)
            }


@shared_task
def process_payments_batch(payment_ids, batch_num, total_batches, job_id):
    """
    Processes a single batch of payments
    """
    from application.models.mis_models import Payment

    app = get_flask_app()

    with app.app_context():
        current_app.logger.info(
            f"[Job {job_id}] Batch {batch_num}/{total_batches} - {len(payment_ids)} payments"
        )

        sync_service = PaymentSyncService()

        results = {
            "batch_num": batch_num,
            "synced": 0,
            "failed": 0,
            "skipped": 0,
            "errors": []
        }

        for payment_id in payment_ids:
            try:
                if not QuickBooksConfig.is_connected():
                    raise RuntimeError("QuickBooks not connected")

                payment_obj = Payment.get_payment_by_id(payment_id)
                payment = payment_obj
                if not payment:
                    raise ValueError("Payment not found")

                if payment.qk_id:
                    results["skipped"] += 1
                    continue
                if payment.is_prepayment or payment.student_wallet_ref is not None:
                    results["skipped"] += 1
                    continue
                result = sync_service.sync_single_payment(payment)

                if result.success:
                    results["synced"] += 1
                    
                else:
                    raise RuntimeError(result.error_message)

            except Exception as e:
                results["failed"] += 1
                results["errors"].append({
                    "payment_id": payment_id,
                    "error": str(e)
                })
                current_app.logger.error(f"[Job {job_id}] Payment {payment_id}: {str(e)}")

        redis_client.hincrby(f"job:{job_id}", "synced", results["synced"])
        redis_client.hincrby(f"job:{job_id}", "failed", results["failed"])
        redis_client.hincrby(f"job:{job_id}", "skipped", results["skipped"])

        return results


@shared_task
def aggregate_payment_results(batch_results, job_id, current_offset):
    """
    Aggregates all batch results and updates Redis offset
    """
    app = get_flask_app()

    with app.app_context():
        total_synced = sum(r["synced"] for r in batch_results)
        total_failed = sum(r["failed"] for r in batch_results)
        total_skipped = sum(r["skipped"] for r in batch_results)

        start_time = datetime.fromisoformat(
            redis_client.hget(f"job:{job_id}", "start_time")
        )

        duration = (datetime.now() - start_time).total_seconds()

        new_offset = None
        if current_offset is not None:
            new_offset = current_offset + total_synced + total_skipped
            redis_client.set("payment_sync:offset", new_offset)

        redis_client.hset(f"job:{job_id}", mapping={
            "status": "completed",
            "end_time": datetime.now().isoformat(),
            "duration_seconds": duration,
            "new_offset": new_offset or 0
        })

        return {
            "success": True,
            "job_id": job_id,
            "synced": total_synced,
            "failed": total_failed,
            "skipped": total_skipped,
            "duration_seconds": duration
        }