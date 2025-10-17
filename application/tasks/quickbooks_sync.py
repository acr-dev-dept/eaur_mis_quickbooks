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
def sync_students(self):
    """
    Celery task to synchronize unsynchronized students from MIS to QuickBooks
    by calling the /sync_student endpoint for each student in parallel.
    """
    try:
        sync_service = CustomerSyncService()
        unsynchronized_students = sync_service.get_unsynchronized_students()
        total_students = len(unsynchronized_students)
        flask_app.logger.info(
            f"Retrieved {total_students} unsynchronized students "
            f"of type {type(unsynchronized_students)}"
        )

        if total_students == 0:
            flask_app.logger.info("No unsynchronized students found. Exiting sync process.")
            return {"message": "No unsynchronized students found."}

        # Adjust the thread pool size dynamically (max 20 workers)
        max_workers = min(20, max(5, total_students // 5))

        local_sync_url = "https://api.eaur.ac.rw/api/v1/sync/customers/sync_student"
        succeeded = 0
        failed = 0
        successful_students = []
        failed_students = []

        def sync_single_student(student):
            """Helper function for threading — sync one student."""
            try:
                reg_no = student.get("reg_no")
                student_id = student.get("student_id")

                if not reg_no:
                    flask_app.logger.warning(f"Student ID {student_id} has no reg_no; skipping.")
                    return (student_id, reg_no, False, "Missing registration number")

                response = requests.post(local_sync_url, json={"reg_no": reg_no}, timeout=20)

                if response.status_code == 200:
                    res_json = response.json()
                    if res_json.get("success"):
                        flask_app.logger.info(
                            f" Student {reg_no} ({student_id}) synchronized successfully."
                        )
                        return (student_id, reg_no, True, None)
                    else:
                        flask_app.logger.error(
                            f" Student {reg_no} sync failed: {res_json.get('error', 'Unknown error')}"
                        )
                        return (student_id, reg_no, False, res_json.get("error"))
                else:
                    flask_app.logger.error(
                        f" HTTP {response.status_code} while syncing {reg_no}: {response.text}"
                    )
                    return (student_id, reg_no, False, f"HTTP {response.status_code}")
            except requests.exceptions.Timeout:
                flask_app.logger.error(f"⏱ Timeout syncing student {student.get('reg_no')}")
                return (student.get("student_id"), student.get("reg_no"), False, "Timeout")
            except Exception as e:
                flask_app.logger.error(f" Exception syncing student {student.get('reg_no')}: {e}")
                flask_app.logger.debug(traceback.format_exc())
                return (student.get("student_id"), student.get("reg_no"), False, str(e))

        # Run all syncs concurrently
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(sync_single_student, student.to_dict()): student
                for student in unsynchronized_students
            }

            for future in as_completed(futures):
                try:
                    student_id, reg_no, success, error = future.result()
                    if success:
                        succeeded += 1
                        successful_students.append(reg_no)
                    else:
                        failed += 1
                        failed_students.append({"reg_no": reg_no, "error": error})
                except Exception as e:
                    failed += 1
                    flask_app.logger.error(f"Unexpected future exception: {e}")

        flask_app.logger.info(
            f"🎓 Student sync summary: {succeeded} succeeded, {failed} failed, total {total_students}"
        )

        return {
            "total_succeeded": succeeded,
            "total_failed": failed,
            "total_attempted": total_students,
            "successful_reg_nos": successful_students,
            "failed_students": failed_students,
        }

    except Exception as e:
        flask_app.logger.error(f"Critical error during student sync: {e}")
        flask_app.logger.debug(traceback.format_exc())
        return {"error": str(e)}


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
    