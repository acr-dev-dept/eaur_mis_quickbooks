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

@celery.task
def sync_payments():
    """This Celery task handles the synchronization of payments from MIS to QuickBooks."""
    try:
        with flask_app.app_context():  # <-- push context here
            sync_service = PaymentSyncService()
            unsynchronized_payments = sync_service.get_unsynchronized_payments()
            flask_app.logger.info(
                f"Payment sync process completed successfully: "
                f"{unsynchronized_payments['total_succeeded']} payments synchronized."
            )
            # get the payment ids and store them in a list
            payment_ids = [payment.id for payment in unsynchronized_payments.get('payments', [])]
            return {
                "total_succeeded": unsynchronized_payments['total_succeeded'],
                "payment_ids": payment_ids
            }
    except Exception as e:
        flask_app.logger.error(f"Error during payment sync process: {e}")
        return {"error": str(e)}