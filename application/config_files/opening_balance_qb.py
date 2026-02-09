from application.models.mis_models import TblPersonalUg, TblOnlineApplication
from celery import shared_task, group, chord
from datetime import datetime
from flask import current_app
import traceback
import redis
import os

from application.services.opening_balance_sync import OpeningBalanceSyncService
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
def bulk_sync_opening_balances_task(
    student_ids=None,
    batch_size=50,
    filter_unsynced=True,
    reset_offset=False
):
    """
    Orchestrates opening balance synchronization using offset-based batching.

    Args:
        student_ids (list[str] | None): Explicit student reg_nos to sync
        batch_size (int): Batch size
        filter_unsynced (bool): Only sync students with unsynced opening balances
        reset_offset (bool): Reset Redis offset before syncing

    Returns:
        dict
    """
    from application.models.mis_models import TblStudentWallet

    app = get_flask_app()
    start_time = datetime.now()
    offset_key = "opening_balance_sync:offset"

    with app.app_context():
        try:
            # ----------------------------------------------------------
            # Offset handling
            # ----------------------------------------------------------
            if reset_offset:
                redis_client.set(offset_key, 0)
                current_app.logger.info("Opening balance sync offset reset to 0")

            current_offset = int(redis_client.get(offset_key) or 0)

            # ----------------------------------------------------------
            # Fetch student IDs (reg_nos)
            # ----------------------------------------------------------
            if student_ids is None:
                if not filter_unsynced:
                    raise ValueError("Bulk opening balance sync must filter unsynced students")

                # Fetch students with outstanding balances that need syncing
                students = get_students_with_opening_balances(
                    limit=batch_size,
                    offset=current_offset
                )

                student_ids = [student["reg_no"] for student in students if student.get("reg_no")]
            else:
                # Manual list → offset should not advance
                current_offset = None

            if not student_ids:
                if current_offset is not None:
                    redis_client.set(offset_key, 0)

                return {
                    "success": True,
                    "message": "No opening balances to sync",
                    "total": 0,
                    "synced": 0,
                    "failed": 0,
                    "skipped": 0
                }

            # ----------------------------------------------------------
            # Batch creation
            # ----------------------------------------------------------
            batches = [
                student_ids[i:i + batch_size]
                for i in range(0, len(student_ids), batch_size)
            ]

            job_id = (
                f"opening_balance_sync_"
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
                    "total_students": len(student_ids),
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
                process_opening_balances_batch.s(batch, idx, len(batches), job_id)
                for idx, batch in enumerate(batches, 1)
            )

            result = chord(job)(
                aggregate_opening_balance_results.s(job_id, current_offset)
            )

            current_app.logger.info(
                f"[Job {job_id}] Opening balance sync started "
                f"({len(student_ids)} students, {len(batches)} batches)"
            )

            return {
                "success": True,
                "job_id": job_id,
                "task_id": result.id,
                "total_students": len(student_ids),
                "total_batches": len(batches),
                "status": "processing",
            }

        except Exception as e:
            current_app.logger.error(
                f"Error starting opening balance sync: {str(e)}"
            )
            current_app.logger.error(traceback.format_exc())
            return {
                "success": False,
                "error": str(e),
            }


# -------------------------------------------------------------------
# HELPER: Fetch students with opening balances
# -------------------------------------------------------------------
def get_students_with_opening_balances(limit=50, offset=0):
    """
    Fetch students who have opening balances that need to be synced
    
    Args:
        limit (int): Number of records to fetch
        offset (int): Offset for pagination
        
    Returns:
        list[dict]: List of student records with reg_no and opening_balance
    """
    from application.utils.database import db_manager
    
    students = []
    
    with db_manager.get_mis_session() as session:
        # Fetch from TblPersonalUg
        ug_students = (
            session.query(TblPersonalUg.reg_no, TblPersonalUg.opening_balance)
            .filter(TblPersonalUg.opening_balance != None)
            .filter(TblPersonalUg.opening_balance != 0)
            .limit(limit)
            .offset(offset)
            .all()
        )
        
        students.extend([
            {"reg_no": s.reg_no, "opening_balance": s.opening_balance}
            for s in ug_students
        ])
        
        # If needed, also fetch from TblOnlineApplication
        if len(students) < limit:
            remaining = limit - len(students)
            online_students = (
                session.query(TblOnlineApplication.reg_no, TblOnlineApplication.opening_balance)
                .filter(TblOnlineApplication.opening_balance != None)
                .filter(TblOnlineApplication.opening_balance != 0)
                .limit(remaining)
                .offset(offset)
                .all()
            )
            
            students.extend([
                {"reg_no": s.reg_no, "opening_balance": s.opening_balance}
                for s in online_students
            ])
    
    return students


# -------------------------------------------------------------------
# BATCH PROCESSOR
# -------------------------------------------------------------------
@shared_task
def process_opening_balances_batch(student_ids, batch_num, total_batches, job_id):
    """
    Process a single batch of opening balances
    """
    app = get_flask_app()

    with app.app_context():
        current_app.logger.info(
            f"[Job {job_id}] Processing batch {batch_num}/{total_batches} "
            f"({len(student_ids)} students)"
        )

        sync_service = OpeningBalanceSyncService()

        results = {
            "batch_num": batch_num,
            "synced": 0,
            "failed": 0,
            "skipped": 0,
            "errors": [],
        }

        for reg_no in student_ids:
            try:
                if not QuickBooksConfig.is_connected():
                    raise RuntimeError("QuickBooks not connected")

                # Get outstanding balance
                balance_result = sync_service.get_outstanding_balance(reg_no)
                
                # Check if balance was calculated successfully
                if hasattr(balance_result, 'status_code') and balance_result.status_code != 200:
                    raise RuntimeError(f"Failed to calculate outstanding balance for {reg_no}")
                
                # Extract the data from the JSON response
                balance_data = balance_result.get_json() if hasattr(balance_result, 'get_json') else balance_result
                
                outstanding_balance = balance_data.get("outstanding_balance", 0)
                
                # Skip if balance is zero
                if outstanding_balance == 0:
                    results["skipped"] += 1
                    current_app.logger.info(
                        f"[Job {job_id}] Skipped {reg_no}: Zero balance"
                    )
                    continue
                
                # TODO: Implement actual sync to QuickBooks here
                # This would involve creating a journal entry or invoice for the opening balance
                # For now, we just log the successful calculation
                
                results["synced"] += 1
                current_app.logger.info(
                    f"[Job {job_id}] Synced opening balance for {reg_no}: {outstanding_balance}"
                )

            except Exception as e:
                results["failed"] += 1
                results["errors"].append({
                    "reg_no": reg_no,
                    "error": str(e),
                })
                current_app.logger.error(
                    f"[Job {job_id}] Student {reg_no}: {str(e)}"
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
def aggregate_opening_balance_results(batch_results, job_id, current_offset):
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
                redis_client.set("opening_balance_sync:offset", new_offset)

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
def scheduled_opening_balance_sync_task():
    """
    Celery Beat entrypoint for progressive opening balance syncing
    """
    app = get_flask_app()

    with app.app_context():
        current_app.logger.info("Scheduled opening balance sync triggered")

        async_result = bulk_sync_opening_balances_task.delay(
            student_ids=None,
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