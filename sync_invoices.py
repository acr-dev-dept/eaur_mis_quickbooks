"""This module will be used to sync invoices from MIS to QuickBooks."""
import sys
import os
import logging
from application import create_app
from application.services.invoice_sync import InvoiceSyncService  # <-- make sure this exists

app = create_app(os.getenv('FLASK_ENV', 'development'))
app.logger.setLevel(logging.DEBUG)
app.logger.info("Starting invoice sync process")


def sync_invoices(batch_size: int = 20):
    with app.app_context():
        sync_service = InvoiceSyncService()
        total_succeeded = 0
        total_failed = 0

        while True:
            results = sync_service.sync_invoices_batch(batch_size=batch_size)

            if results['total_processed'] == 0:  # nothing left
                break

            total_succeeded += results['successful']
            total_failed += results['failed']

        return {"total_succeeded": total_succeeded, "total_failed": total_failed}



if __name__ == '__main__':
    try:
        outcome = sync_invoices(batch_size=20)
        app.logger.info(f"Invoice sync script finished execution: {outcome}")
        if "error" in outcome:
            sys.exit(1)
    except Exception as e:
        app.logger.error(f"Unhandled exception in invoice sync script: {e}")
        sys.exit(1)
