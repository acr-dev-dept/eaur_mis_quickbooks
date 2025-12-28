"""
This module is used to sync income categories from MIS to QuickBooks.
"""

import sys
import os
import logging

from application import create_app
from application.services.income_sync import IncomeSyncService

# Initialize Flask app
app = create_app(os.getenv("FLASK_ENV", "development"))
app.logger.setLevel(logging.DEBUG)
app.logger.info("Starting income category sync process")


def sync_income_categories(batch_size: int = 10):
    """
    Sync all unsynced income categories to QuickBooks in batches.
    """
    try:
        with app.app_context():
            sync_service = IncomeSyncService()

            results = sync_service.sync_all_unsynced_categories_in_batches(
                batch_size=batch_size
            )

            app.logger.info(
                "Income category sync completed successfully. "
                f"Succeeded: {results['total_succeeded']}, "
                f"Failed: {results['total_failed']}"
            )

            return results

    except Exception as e:
        app.logger.error(f"Error during income category sync process: {e}", exc_info=True)
        return {"error": str(e)}


if __name__ == "__main__":
    try:
        outcome = sync_income_categories(batch_size=15)
        app.logger.info(f"Income category sync script finished execution: {outcome}")

        if "error" in outcome or outcome.get("total_failed", 0) > 0:
            sys.exit(1)

    except Exception as e:
        app.logger.error(f"Unhandled exception in income category sync script: {e}", exc_info=True)
        sys.exit(1)
