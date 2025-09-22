"""This module will be used to sync invoices from MIS to QuickBooks."""
import sys
import os
import logging
from application import create_app
from application.services.invoice_sync import InvoiceSyncService  # <-- make sure this exists

app = create_app(os.getenv('FLASK_ENV', 'development'))
app.logger.setLevel(logging.DEBUG)
app.logger.info("Starting invoice sync process")


def sync_invoices(batch_size: int = 10):
    """Sync unsynced invoices from MIS to QuickBooks in batches."""
    try:
        with app.app_context():
            sync_service = InvoiceSyncService()
            results = sync_service.sync_invoices_batch(batch_size=batch_size)
            app.logger.info(
                f"Invoice sync process completed successfully: "
                f"{results['total_succeeded']} invoices synchronized, "
                f"{results['total_failed']} failed."
            )
            return results
    except Exception as e:
        app.logger.error(f"Error during invoice sync process: {e}")
        return {"error": str(e)}


if __name__ == '__main__':
    try:
        outcome = sync_invoices(batch_size=15)
        app.logger.info(f"Invoice sync script finished execution: {outcome}")
        if "error" in outcome:
            sys.exit(1)
    except Exception as e:
        app.logger.error(f"Unhandled exception in invoice sync script: {e}")
        sys.exit(1)
