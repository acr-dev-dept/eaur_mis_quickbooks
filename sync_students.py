#!/home/alex/eaur_mis_quickbooks/venv/bin/python3
"""This module will be used to sync students from MIS to QuickBooks."""
import sys
from application.services.customer_sync import CustomerSyncService
from application import create_app
import os
import logging

# Create Flask application instance
app = create_app(os.getenv('FLASK_ENV', 'development'))
app.logger.setLevel(logging.DEBUG)
app.logger.info("Starting student sync process")

def sync_students():
    try:
        with app.app_context():  # <-- push context here
            sync_service = CustomerSyncService()
            results = sync_service.sync_all_unsynchronized_students_in_batches(15)
            app.logger.info(
                f"Student sync process completed successfully: "
                f"{results['total_succeeded']} students synchronized."
            )
            return results
    except Exception as e:
        app.logger.error(f"Error during student sync process: {e}")
        return {"error": str(e)}

if __name__ == '__main__':
    try:
        outcome = sync_students()
        app.logger.info(f"Student sync script finished execution: {outcome}")
        if "error" in outcome:
            sys.exit(1)
    except Exception as e:
        app.logger.error(f"Unhandled exception in student sync script: {e}")
        sys.exit(1)