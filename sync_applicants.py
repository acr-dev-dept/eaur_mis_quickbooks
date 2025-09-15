"""This module handles the synchronization of applicants from MIS to QuickBooks."""
from application.services.customer_sync import CustomerSyncService
from application import create_app
import os
import logging
from flask import current_app

# Create Flask application instance
app = create_app(os.getenv('FLASK_ENV', 'development'))
app.logger.setLevel(logging.DEBUG)
app.logger.info("Starting applicant sync process")

def sync_applicants():
    try:
        with app.app_context():  # <-- push context here
            sync_service = CustomerSyncService()
            results = sync_service.sync_all_unsynchronized_applicants_in_batches(20)
            app.logger.info(
                f"Applicant sync process completed successfully: "
                f"{results['total_succeeded']} applicants synchronized."
            )
            return results
    except Exception as e:
        app.logger.error(f"Error during applicant sync process: {e}")
        return {"error": str(e)}
    
if __name__ == '__main__':
    try:
        outcome = sync_applicants()
        app.logger.info(f"Applicant sync script finished execution: {outcome}")
    except Exception as e:
        app.logger.error(f"Unhandled exception in applicant sync script: {e}")