from application.utils.celery_utils import make_celery
from application import create_app
import os
import logging
from flask import current_app
from application.services.payment_sync import PaymentSyncService

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
        flask_app.logger.info(f"Retrieved {len(unsynchronized_payments)} unsynchronized payments and the type is {type(unsynchronized_payments)}")
        succeeded = 0
        payment_ids = []

        for payment in unsynchronized_payments:
            payment = payment.to_dict()
            try:
                result = sync_service.sync_single_payment(payment)
                flask_app.logger.info(
                    f"Payment {payment['id']} sync result: {result}"
                )
                succeeded += 1
                payment_ids.append(payment['id'])
            except Exception as e:
                flask_app.logger.error(
                    f"Failed to sync payment {payment['id']}: {e}"
                )

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