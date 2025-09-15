"""This module will be used to sync students from MIS to QuickBooks."""
from application.services.customer_sync import CustomerSyncService
from  application import create_app
import os
import logging

# Create Flask application instance
app = create_app(os.getenv('FLASK_ENV', 'development'))
app.logger.setLevel(logging.DEBUG)
app.logger.info("Starting student sync process")

def sync_students():
    try:
        sync_service = CustomerSyncService()
        sync_service.sync_all_unsynchronized_students_in_batches(15)
        app.logger.info(f"Student sync process completed successfully: {sync_service.synced_count} students synchronized.")
        message = f"Student sync process completed successfully: {sync_service} students synchronized."
        return message
    except Exception as e:
        message = f"Error during student sync process: {e}"
        app.logger.error(f"Error during student sync process: {e}")
        return message

if __name__ == '__main__':
    try:
        operation = sync_students()
        app.logger.info(f"Student sync script finished execution: {operation}")
    except Exception as e:
        app.logger.error(f"Unhandled exception in student sync script: {e}")
    