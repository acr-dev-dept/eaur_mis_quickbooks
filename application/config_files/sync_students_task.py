from celery import shared_task, group, chord
from datetime import datetime
from flask import current_app
import traceback
import redis
import os

from application.services.customer_sync import CustomerSyncService
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
def bulk_sync_students_task(reg_nos=None, batch_size=50, filter_unsynced=True, reset_offset=False):
    """
    Orchestrates student synchronization using batch processing and Redis offset tracking
    """
    from application.models.mis_models import TblPersonalUg

    app = get_flask_app()
    start_time = datetime.now()
    offset_key = "student_sync:offset"

    with app.app_context():
        try:
            if reset_offset:
                redis_client.set(offset_key, 0)
                current_app.logger.info("Student sync offset reset")

            current_offset = int(redis_client.get(offset_key) or 0)

            if reg_nos is None:
                if filter_unsynced:
                    students = TblPersonalUg.get_unsynced_students(
                        limit=batch_size,
                        offset=current_offset
                    )
                else:
                    raise ValueError("No students left to process")

                reg_nos = [s["reg_no"] for s in students if s.get("reg_no")]
            else:
                current_offset = None

            total_students = len(reg_nos)

            if total_students == 0:
                if current_offset is not None:
                    redis_client.set(offset_key, 0)

                return {
                    "success": True,
                    "message": "No students to sync",
                    "total": 0,
                    "synced": 0,
                    "failed": 0,
                    "skipped": 0
                }

            batches = [reg_nos[i:i + batch_size] for i in range(0, total_students, batch_size)]

            job_id = f"student_sync_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{current_offset or 'manual'}"

            redis_client.hset(f"job:{job_id}", mapping={
                "status": "processing",
                "total_students": total_students,
                "total_batches": len(batches),
                "synced": 0,
                "failed": 0,
                "skipped": 0,
                "current_offset": current_offset or 0,
                "start_time": start_time.isoformat()
            })
            redis_client.expire(f"job:{job_id}", 86400)

            job = group(
                process_students_batch.s(batch, idx, len(batches), job_id)
                for idx, batch in enumerate(batches, 1)
            )

            result = chord(job)(aggregate_student_results.s(job_id, current_offset))

            return {
                "success": True,
                "job_id": job_id,
                "task_id": result.id,
                "total_students": total_students,
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
def process_students_batch(reg_nos, batch_num, total_batches, job_id):
    """
    Processes a single batch of students
    """
    from application.models.mis_models import TblPersonalUg

    app = get_flask_app()

    with app.app_context():
        current_app.logger.info(
            f"[Job {job_id}] Batch {batch_num}/{total_batches} - {len(reg_nos)} students"
        )

        sync_service = CustomerSyncService()

        results = {
            "batch_num": batch_num,
            "synced": 0,
            "failed": 0,
            "skipped": 0,
            "errors": []
        }

        for reg_no in reg_nos:
            try:
                if not QuickBooksConfig.is_connected():
                    raise RuntimeError("QuickBooks not connected")

                student = TblPersonalUg.get_student_details(reg_no)

                if not student:
                    raise ValueError("Student not found")

                if student.get("quickbooks_status") == 1:
                    results["skipped"] += 1
                    continue

                result = sync_service.sync_single_student(student)

                if result.success:
                    results["synced"] += 1
                    TblPersonalUg.update_student_status(reg_no, 1)
                else:
                    raise RuntimeError(result.error_message)

            except Exception as e:
                results["failed"] += 1
                results["errors"].append({
                    "reg_no": reg_no,
                    "error": str(e)
                })
                current_app.logger.error(f"[Job {job_id}] {reg_no}: {str(e)}")

        redis_client.hincrby(f"job:{job_id}", "synced", results["synced"])
        redis_client.hincrby(f"job:{job_id}", "failed", results["failed"])
        redis_client.hincrby(f"job:{job_id}", "skipped", results["skipped"])

        return results


@shared_task
def aggregate_student_results(batch_results, job_id, current_offset):
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
            redis_client.set("student_sync:offset", new_offset)

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
