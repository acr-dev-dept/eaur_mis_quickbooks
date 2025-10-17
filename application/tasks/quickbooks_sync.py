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
import requests
from flask import current_app as flask_app
from application.models.mis_models import TblOnlineApplication, TblCountry, TblPersonalUg


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
    
@celery.task(bind=True)
def sync_applicants(self):
    """
    Celery task to synchronize applicants from MIS to QuickBooks.
    """
    try:
        sync_service = CustomerSyncService()
        unsynchronized_applicants = sync_service.get_unsynchronized_applicants()
        flask_app.logger.info(
            f"Retrieved {len(unsynchronized_applicants)} unsynchronized applicants "
            f"and the type is {type(unsynchronized_applicants)}"
        )
        succeeded = 0
        tracking_ids = []
        for applicant in unsynchronized_applicants:
            applicant = applicant.to_dict()
            tracking_id = applicant.get('tracking_id')
            try:
                url = f"https://api.eaur.ac.rw/api/v1/sync/customers/applicant/{tracking_id}"
                payload = {"batch_size": 50}
                response = requests.post(url, json=payload, timeout=15)

                if response.status_code == 200:
                    succeeded += 1
                    tracking_ids.append(tracking_id)
                    flask_app.logger.info(
                        f"Successfully synchronized applicant ID {tracking_id}, response: {response.text}"
                    )
                else:
                    flask_app.logger.error(
                        f"Failed to sync applicant ID {tracking_id}, status: {response.status_code}, body: {response.text}"
                    )

            except Exception as e:
                flask_app.logger.error(f"Exception syncing applicant ID {tracking_id}: {e}")
                continue
        flask_app.logger.info(
            f"Applicant sync completed: {succeeded}/{len(unsynchronized_applicants)} succeeded"
        )
        return {
            "total_succeeded": succeeded,
            "total_attempted": len(unsynchronized_applicants),
            "successful_tracking_ids": tracking_ids,
        }
    except Exception as e:
        flask_app.logger.error(f"Error during applicant sync process: {e}")
        return {"error": str(e)}
    
@celery.task(bind=True)
def sync_students(self, batch_size=100):
    """
    Celery task to synchronize unsynchronized students in batches.
    Uses streaming to handle thousands of records efficiently.
    """
    try:
        sync_service = CustomerSyncService()
        
        # Get total count first (fast query)
        total_students = TblPersonalUg.count_unsynced_students()
        flask_app.logger.info(f"Found {total_students} unsynchronized students")

        if total_students == 0:
            return {"message": "No unsynchronized students found."}

        succeeded = 0
        failed = 0
        failed_students = []
        current_batch = []
        
        # Stream students and process in batches
        for idx, student in enumerate(sync_service.get_unsynchronized_students_stream()):
            current_batch.append(student)
            
            # Process batch when full or at end
            if len(current_batch) >= batch_size or idx == total_students - 1:
                # Update progress
                progress = int(((idx + 1) / total_students) * 100)
                self.update_state(
                    state='PROGRESS',
                    meta={
                        'current': idx + 1,
                        'total': total_students,
                        'percent': progress,
                        'succeeded': succeeded,
                        'failed': failed
                    }
                )
                
                # Process current batch
                batch_results = _sync_student_batch(current_batch)
                succeeded += batch_results['succeeded']
                failed += batch_results['failed']
                failed_students.extend(batch_results['failed_students'])
                
                flask_app.logger.info(
                    f"Processed {idx + 1}/{total_students}: "
                    f"{batch_results['succeeded']} succeeded, {batch_results['failed']} failed"
                )
                
                # Clear batch for next iteration
                current_batch = []

        flask_app.logger.info(
            f"Final summary: {succeeded} succeeded, {failed} failed of {total_students}"
        )

        return {
            "total_succeeded": succeeded,
            "total_failed": failed,
            "total_attempted": total_students,
            "failed_count": len(failed_students),
            "failed_students": failed_students[:100]  # Limit in response
        }

    except Exception as e:
        flask_app.logger.error(f"Critical error during student sync: {e}")
        flask_app.logger.debug(traceback.format_exc())
        raise


def _sync_student_batch(students, max_retries=3):
    """Sync a batch of students with retry logic."""
    max_workers = min(20, max(5, len(students) // 5))
    succeeded = 0
    failed = 0
    failed_students = []
    
    def sync_with_retry(student_dict, retries=0):
        """Sync single student with retry logic."""
        try:
            # Call sync service directly instead of HTTP
            sync_service = CustomerSyncService()
            result = sync_service.sync_single_student(student_dict['reg_no'])
            
            if result['success']:
                return (student_dict['student_id'], student_dict['reg_no'], True, None)
            else:
                # Retry on failure
                if retries < max_retries:
                    flask_app.logger.warning(
                        f"Retrying {student_dict['reg_no']} (attempt {retries + 1})"
                    )
                    return sync_with_retry(student_dict, retries + 1)
                return (student_dict['student_id'], student_dict['reg_no'], 
                       False, result.get('error'))
                       
        except Exception as e:
            if retries < max_retries:
                return sync_with_retry(student_dict, retries + 1)
            return (student_dict['student_id'], student_dict['reg_no'], False, str(e))
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(sync_with_retry, student.to_dict()): student
            for student in students
        }
        
        for future in as_completed(futures):
            try:
                student_id, reg_no, success, error = future.result()
                if success:
                    succeeded += 1
                else:
                    failed += 1
                    failed_students.append({"reg_no": reg_no, "error": error})
            except Exception as e:
                failed += 1
                flask_app.logger.error(f"Unexpected future exception: {e}")
    
    return {
        'succeeded': succeeded,
        'failed': failed,
        'failed_students': failed_students
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
    