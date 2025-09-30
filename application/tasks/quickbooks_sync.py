from application.utils.celery_utils import make_celery
from application import create_app
import os
import logging
from flask import current_app
from application.services.payment_sync import PaymentSyncService
import requests
from application.services.customer_sync import CustomerSyncService

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
    Celery task to synchronize students from MIS to QuickBooks.
    """
    try:
        sync_service = CustomerSyncService()
        unsynchronized_students = sync_service.get_unsynchronized_students()
        flask_app.logger.info(
            f"Retrieved {len(unsynchronized_students)} unsynchronized students "
            f"and the type is {type(unsynchronized_students)}"
        )
        succeeded = 0
        student_ids = []
        for student in unsynchronized_students:
            student = student.to_dict()
            student_id = student.get('student_id')
            try:
                url = f"https://api.eaur.ac.rw/api/v1/sync/customers/student/{student_id}"
                payload = {"batch_size": 50}
                response = requests.post(url, json=payload, timeout=15)

                if response.status_code == 200:
                    succeeded += 1
                    student_ids.append(student_id)
                    flask_app.logger.info(
                        f"Successfully synchronized student ID {student_id}, response: {response.text}"
                    )
                else:
                    flask_app.logger.error(
                        f"Failed to sync student ID {student_id}, status: {response.status_code}, body: {response.text}"
                    )

            except Exception as e:
                flask_app.logger.error(f"Exception syncing student ID {student_id}: {e}")
                continue
        flask_app.logger.info(
            f"Student sync completed: {succeeded}/{len(unsynchronized_students)} succeeded"
        )
        return {
            "total_succeeded": succeeded,
            "total_attempted": len(unsynchronized_students),
            "successful_student_ids": student_ids,
        }
    except Exception as e:
        flask_app.logger.error(f"Error during student sync process: {e}")
        return {"error": str(e)}

@celery.task(bind=True)
def sync_invoices(self, batch_size=20):
    """
    Celery task to synchronize unsynchronized invoices from MIS to QuickBooks.
    """
    sync_service = InvoiceSyncService()
    total_succeeded = 0
    total_failed = 0

    try:
        
        while True:
            results = sync_service.sync_invoices_batch(batch_size=batch_size)

            total_succeeded += results.get('total_succeeded', 0)
            total_failed += results.get('total_failed', 0)

            if results['total_processed'] == 0:  # nothing left
                break
            # Sleep or wait before the next batch if needed
        flask_app.logger.info(
            f"Invoice sync completed: {total_succeeded} succeeded, {total_failed} failed"
        )
        return {"total_succeeded": total_succeeded, "total_failed": total_failed}
    except Exception as e:
        flask_app.logger.error(f"Error during invoice sync process: {e}")
        return {"error": str(e)}

        