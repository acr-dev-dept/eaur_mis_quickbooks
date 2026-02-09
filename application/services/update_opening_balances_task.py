from application.models.mis_models import TblPersonalUg, TblOnlineApplication, TblImvoice, Payment
from celery import shared_task, group, chord
from datetime import datetime
from flask import current_app
import traceback
import redis
import os
from sqlalchemy import extract, func

from application.utils.database import db_manager


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
# MAIN BULK UPDATE TASK (OFFSET-BASED)
# -------------------------------------------------------------------
@shared_task
def bulk_update_opening_balances_task(
    reg_nos=None,
    batch_size=100,
    reset_offset=False,
    student_table="TblPersonalUg"
):
    """
    Orchestrates opening balance updates using offset-based batching.

    Args:
        reg_nos (list[str] | None): Explicit reg_nos to update
        batch_size (int): Batch size
        reset_offset (bool): Reset Redis offset before updating
        student_table (str): Which table to process ("TblPersonalUg" or "TblOnlineApplication")

    Returns:
        dict
    """
    app = get_flask_app()
    start_time = datetime.now()
    offset_key = f"opening_balance_update:{student_table}:offset"

    with app.app_context():
        try:
            # ----------------------------------------------------------
            # Offset handling
            # ----------------------------------------------------------
            if reset_offset:
                redis_client.set(offset_key, 0)
                current_app.logger.info(f"Opening balance update offset reset to 0 for {student_table}")

            current_offset = int(redis_client.get(offset_key) or 0)

            # ----------------------------------------------------------
            # Fetch reg_nos
            # ----------------------------------------------------------
            if reg_nos is None:
                reg_nos = get_student_reg_nos(
                    student_table=student_table,
                    limit=batch_size,
                    offset=current_offset
                )
            else:
                # Manual list → offset should not advance
                current_offset = None

            if not reg_nos:
                if current_offset is not None:
                    redis_client.set(offset_key, 0)

                return {
                    "success": True,
                    "message": f"No students to update in {student_table}",
                    "total": 0,
                    "updated": 0,
                    "failed": 0,
                    "skipped": 0
                }

            # ----------------------------------------------------------
            # Batch creation
            # ----------------------------------------------------------
            batches = [
                reg_nos[i:i + batch_size]
                for i in range(0, len(reg_nos), batch_size)
            ]

            job_id = (
                f"opening_balance_update_{student_table}_"
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
                    "student_table": student_table,
                    "total_students": len(reg_nos),
                    "total_batches": len(batches),
                    "updated": 0,
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
                process_opening_balance_update_batch.s(
                    batch, idx, len(batches), job_id, student_table
                )
                for idx, batch in enumerate(batches, 1)
            )

            result = chord(job)(
                aggregate_opening_balance_update_results.s(
                    job_id, current_offset, student_table
                )
            )

            current_app.logger.info(
                f"[Job {job_id}] Opening balance update started for {student_table} "
                f"({len(reg_nos)} students, {len(batches)} batches)"
            )

            return {
                "success": True,
                "job_id": job_id,
                "task_id": result.id,
                "student_table": student_table,
                "total_students": len(reg_nos),
                "total_batches": len(batches),
                "status": "processing",
            }

        except Exception as e:
            current_app.logger.error(
                f"Error starting opening balance update for {student_table}: {str(e)}"
            )
            current_app.logger.error(traceback.format_exc())
            return {
                "success": False,
                "error": str(e),
            }


# -------------------------------------------------------------------
# HELPER: Fetch student reg_nos
# -------------------------------------------------------------------
def get_student_reg_nos(student_table="TblPersonalUg", limit=100, offset=0):
    """
    Fetch student reg_nos from TblImvoice for 2024 only
    
    Args:
        student_table (str): Table name ("TblPersonalUg" or "TblOnlineApplication") - used for validation
        limit (int): Number of records to fetch
        offset (int): Offset for pagination
        
    Returns:
        list[str]: List of unique reg_nos from 2024 invoices
    """
    reg_nos = []
    
    with db_manager.get_mis_session() as session:
        # Get distinct reg_nos from TblImvoice for 2024
        invoice_reg_nos = (
            session.query(TblImvoice.reg_no)
            .filter(TblImvoice.reg_no != None)
            .filter(TblImvoice.reg_no != "")
            .filter(extract('year', TblImvoice.date) == 2024)
            .distinct()
            .order_by(TblImvoice.reg_no)
            .limit(limit)
            .offset(offset)
            .all()
        )
        
        reg_nos = [r.reg_no for r in invoice_reg_nos]
        
        # Optional: Verify that these reg_nos exist in the specified student table
        if reg_nos and student_table:
            if student_table == "TblPersonalUg":
                existing_students = (
                    session.query(TblPersonalUg.reg_no)
                    .filter(TblPersonalUg.reg_no.in_(reg_nos))
                    .all()
                )
                existing_reg_nos = {s.reg_no for s in existing_students}
            elif student_table == "TblOnlineApplication":
                existing_students = (
                    session.query(TblOnlineApplication.reg_no)
                    .filter(TblOnlineApplication.reg_no.in_(reg_nos))
                    .all()
                )
                existing_reg_nos = {s.reg_no for s in existing_students}
            else:
                raise ValueError(f"Invalid student_table: {student_table}")
            
            # Filter to only include reg_nos that exist in the student table
            reg_nos = [rn for rn in reg_nos if rn in existing_reg_nos]
    
    return reg_nos


# -------------------------------------------------------------------
# HELPER: Calculate outstanding balance for a student
# -------------------------------------------------------------------
def calculate_outstanding_balance(session, reg_no):
    """
    Calculate outstanding balance for a student based on 2024 invoices and payments
    
    Args:
        session: SQLAlchemy session
        reg_no (str): Student registration number
        
    Returns:
        float: Outstanding balance
    """
    # Total invoices for 2024
    invoice_total = (
        session.query(func.coalesce(func.sum(TblImvoice.dept), 0))
        .filter(
            TblImvoice.reg_no == reg_no,
            extract('year', TblImvoice.invoice_date) == 2024
        )
        .scalar()
    )

    # Total payments for 2024
    payment_total = (
        session.query(func.coalesce(func.sum(Payment.amount), 0))
        .filter(
            Payment.reg_no == reg_no,
            extract('year', Payment.recorded_date) == 2024
        )
        .scalar()
    )

    outstanding_balance = float(invoice_total) - float(payment_total)
    
    return outstanding_balance


# -------------------------------------------------------------------
# BATCH PROCESSOR
# -------------------------------------------------------------------
@shared_task
def process_opening_balance_update_batch(
    reg_nos, batch_num, total_batches, job_id, student_table
):
    """
    Process a single batch of opening balance updates
    """
    app = get_flask_app()

    with app.app_context():
        current_app.logger.info(
            f"[Job {job_id}] Processing batch {batch_num}/{total_batches} "
            f"({len(reg_nos)} students from {student_table})"
        )

        results = {
            "batch_num": batch_num,
            "updated": 0,
            "failed": 0,
            "skipped": 0,
            "errors": [],
        }

        with db_manager.get_mis_session() as session:
            for reg_no in reg_nos:
                try:
                    # Calculate outstanding balance
                    outstanding_balance = calculate_outstanding_balance(session, reg_no)
                    
                    # Fetch student record
                    if student_table == "TblPersonalUg":
                        student = session.query(TblPersonalUg).filter_by(reg_no=reg_no).first()
                    elif student_table == "TblOnlineApplication":
                        student = session.query(TblOnlineApplication).filter_by(reg_no=reg_no).first()
                    else:
                        raise ValueError(f"Invalid student_table: {student_table}")
                    
                    if not student:
                        results["skipped"] += 1
                        current_app.logger.warning(
                            f"[Job {job_id}] Student {reg_no} not found in {student_table}"
                        )
                        continue
                    
                    # Check if update is needed
                    if student.opening_balance == outstanding_balance:
                        results["skipped"] += 1
                        current_app.logger.debug(
                            f"[Job {job_id}] {reg_no}: No change needed (balance: {outstanding_balance})"
                        )
                        continue
                    
                    # Update opening balance
                    old_balance = student.opening_balance
                    student.opening_balance = outstanding_balance
                    session.commit()
                    
                    results["updated"] += 1
                    current_app.logger.info(
                        f"[Job {job_id}] Updated {reg_no}: "
                        f"{old_balance} → {outstanding_balance}"
                    )

                except Exception as e:
                    results["failed"] += 1
                    results["errors"].append({
                        "reg_no": reg_no,
                        "error": str(e),
                    })
                    current_app.logger.error(
                        f"[Job {job_id}] Failed to update {reg_no}: {str(e)}"
                    )
                    # Rollback on error
                    session.rollback()

        # --------------------------------------------------------------
        # Update job counters in Redis
        # --------------------------------------------------------------
        try:
            redis_client.hincrby(f"job:{job_id}", "updated", results["updated"])
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
def aggregate_opening_balance_update_results(
    batch_results, job_id, current_offset, student_table
):
    """
    Aggregate all batch results and safely advance offset
    """
    app = get_flask_app()

    with app.app_context():
        try:
            total_updated = sum(r["updated"] for r in batch_results)
            total_failed = sum(r["failed"] for r in batch_results)
            total_skipped = sum(r["skipped"] for r in batch_results)

            job_info = redis_client.hgetall(f"job:{job_id}")
            start_time = datetime.fromisoformat(
                job_info.get("start_time")
            )

            duration = (datetime.now() - start_time).total_seconds()

            new_offset = None
            if current_offset is not None:
                new_offset = current_offset + total_updated + total_skipped
                offset_key = f"opening_balance_update:{student_table}:offset"
                redis_client.set(offset_key, new_offset)

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
                f"[Job {job_id}] Completed for {student_table}: "
                f"{total_updated} updated, "
                f"{total_failed} failed, "
                f"{total_skipped} skipped "
                f"in {duration:.2f}s"
            )

            return {
                "success": True,
                "job_id": job_id,
                "student_table": student_table,
                "updated": total_updated,
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
def scheduled_opening_balance_update_task():
    """
    Celery Beat entrypoint for progressive opening balance updates
    Updates both TblPersonalUg and TblOnlineApplication tables
    """
    app = get_flask_app()

    with app.app_context():
        current_app.logger.info("Scheduled opening balance update triggered")

        # Update TblPersonalUg
        async_result_ug = bulk_update_opening_balances_task.delay(
            reg_nos=None,
            batch_size=100,
            reset_offset=False,
            student_table="TblPersonalUg"
        )

        # Update TblOnlineApplication
        async_result_online = bulk_update_opening_balances_task.delay(
            reg_nos=None,
            batch_size=100,
            reset_offset=False,
            student_table="TblOnlineApplication"
        )

        return {
            "success": True,
            "scheduled": True,
            "task_ids": {
                "TblPersonalUg": async_result_ug.id,
                "TblOnlineApplication": async_result_online.id
            },
            "timestamp": datetime.now().isoformat(),
        }


# -------------------------------------------------------------------
# CONVENIENCE TASK: Update specific students
# -------------------------------------------------------------------
@shared_task
def update_specific_students_opening_balance(reg_nos, student_table="TblPersonalUg"):
    """
    Update opening balance for specific students
    
    Args:
        reg_nos (list[str]): List of registration numbers
        student_table (str): Table name
        
    Returns:
        dict: Results of the update
    """
    return bulk_update_opening_balances_task(
        reg_nos=reg_nos,
        batch_size=100,
        reset_offset=False,
        student_table=student_table
    )