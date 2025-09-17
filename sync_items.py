"""This module will be used to sync students from MIS to QuickBooks."""
import sys
from application.services.customer_sync import CustomerSyncService
from application import create_app
import os
import logging
from application.services.item_sync import ItemSyncService

app = create_app(os.getenv('FLASK_ENV', 'development'))
app.logger.setLevel(logging.DEBUG)
app.logger.info("Starting item sync process")

def sync_items(batch_size: int = 10):
    try:
        with app.app_context():
            sync_service = ItemSyncService()
            results = sync_service.sync_all_unsynced_items_in_batches(batch_size=batch_size)
            app.logger.info(
                f"Item sync process completed successfully: {results['total_succeeded']} items synchronized."
            )
            return results
    except Exception as e:
        app.logger.error(f"Error during item sync process: {e}")
        return {"error": str(e)}

if __name__ == '__main__':
    try:
        outcome = sync_items(batch_size=15)
        app.logger.info(f"Item sync script finished execution: {outcome}")
        if "error" in outcome:
            sys.exit(1)
    except Exception as e:
        app.logger.error(f"Unhandled exception in item sync script: {e}")
        sys.exit(1)
