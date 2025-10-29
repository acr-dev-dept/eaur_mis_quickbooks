# application/services/item_sync.py
from application.models.mis_models import TblIncomeCategory
from application.services.quickbooks import QuickBooks
from flask import current_app

class ItemSyncService:
    """Service to sync income categories to QuickBooks in batches."""

    def __init__(self):
        self.qb = QuickBooks()

    def sync_all_unsynced_items_in_batches(self, batch_size: int = 10):
        """
        Sync all unsynced income categories to QuickBooks in batches.
        Returns a summary dict with successes, failures, and total processed.
        """
        results = []
        total_succeeded = 0
        total_failed = 0
        total_skipped = 0

        unsynced_categories = TblIncomeCategory.get_unsynced_categories()

        existing_qb_categories = self.qb.get_items(self.qb.realm_id)
        if isinstance(existing_qb_categories, dict):
            items = existing_qb_categories.get('Item', [])
        else:
            items = existing_qb_categories
        existing_names = {item['Name'] for item in items}

        # Process in batches
        for i in range(0, len(unsynced_categories), batch_size):
            batch = unsynced_categories[i:i + batch_size]
            for category in batch:
                try:
                    if category['Quickbk_Status'] == 1:
                        results.append({'id': category['id'], 'status': 'skipped', 'reason': 'Already synced'})
                        continue
                    
                    if category['name'] in existing_names:
                        results.append({'id': category['id'], 'status': 'skipped', 'reason': 'Duplicate name in QuickBooks'})
                        current_app.logger.info(f"Category {category['id']} skipped due to duplicate name")
                        total_skipped += 1
                        continue  

                    item_data = {
                        "Name": category['name'],
                        "Type": "Service",
                        "IncomeAccountRef": category['income_account_qb'],  # customize if needed
                        "Description": category['description'] or "No description",
                        "UnitPrice": 0.0,
                    }

                    current_app.logger.info(f"Syncing category {category['id']} to QuickBooks")

                    result = self.qb.create_item(self.qb.realm_id, item_data)

                    if 'Fault' in result:
                        results.append({'id': category['id'], 'status': 'failed', 'reason': result['Fault']['Error'][0]['Message']})
                        total_failed += 1
                    else:
                        item_id = result.get("Item", {}).get("Id")
                        sync_token = result.get("Item", {}).get("SyncToken")
                        TblIncomeCategory.update_quickbooks_status(
                            category_id=category['id'],
                            quickbooks_id=item_id,
                            pushed_by="ItemSyncService",
                            sync_token=sync_token,
                        )
                        results.append({'id': category['id'], 'status': 'success', 'quickbooks_id': item_id})
                        total_succeeded += 1

                except Exception as e:
                    results.append({'id': category['id'], 'status': 'failed', 'reason': str(e)})
                    total_failed += 1

        summary = {
            'total_processed': len(unsynced_categories),
            'total_succeeded': total_succeeded,
            'total_failed': total_failed,
            'total_skipped': total_skipped,
            'details': results
        }

        return summary
