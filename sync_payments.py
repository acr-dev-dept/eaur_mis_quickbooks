from application.services.payment_sync import PaymentSyncService
from application import create_app
import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
# Create Flask application instance
app = create_app(os.getenv('FLASK_ENV', 'development'))
app.logger.setLevel(logging.DEBUG)
app.logger.info("Starting payment sync process")

def sync_payments():
    """Sync all unsynchronized payments from MIS to QuickBooks."""
    try:
        with app.app_context():  # <-- push context here
            sync_service = PaymentSyncService()
            results = sync_service.sync_payments_batch(10)
            app.logger.info(
                f"Payment sync process completed successfully: "
                f"{results['total_succeeded']} payments synchronized."
            )
            return results
    except Exception as e:
        app.logger.error(f"Error during payment sync process: {e}")
        return {"error": str(e)}