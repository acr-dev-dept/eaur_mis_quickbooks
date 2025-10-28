"""
    Income synchronization service for QuickBooks integration.
"""

import email
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum
import json
import time
import traceback

from flask import current_app
from sqlalchemy import and_, or_, func
from application.models.mis_models import TblIncomeCategory
from application.models.central_models import QuickBooksConfig, QuickbooksAuditLog
from application.services.quickbooks import QuickBooks
from application.utils.database import db_manager
from application import db
from application.helpers.json_field_helper import JSONFieldHelper
from application.helpers.json_encoder import EnhancedJSONEncoder

logger = logging.getLogger(__name__)

class IncomeSyncStatus(Enum):
    """Customer synchronization status enumeration"""
    NOT_SYNCED = 0
    SYNCED = 1
    FAILED = 2
    IN_PROGRESS = 3

@dataclass
class IncomeSyncResult:
    """Data class to hold the result of income synchronization."""
    category_id: int
    qb_account_id: str
    qb_sync_token: int
    status: IncomeSyncStatus

class IncomeSyncService:
    """Service to handle income category synchronization with QuickBooks."""

    def __init__(self):
        self.qb_service = QuickBooks()

    def _get_qb_service(self) -> QuickBooks:
        """Get QuickBooks service instance"""
        if not self.qb_service:
            if not QuickBooksConfig.is_connected():
                raise Exception("QuickBooks is not connected. Please authenticate first.")
            self.qb_service = QuickBooks()
        return self.qb_service


    def _update_income_category_sync_status(self, category_id: int, qb_account_id: str, qb_sync_token: int, status: IncomeSyncStatus):
        """Update the synchronization status of an income category."""
        category = db.session.query(TblIncomeCategory).filter(TblIncomeCategory.id == category_id).first()
        if category:
            category.income_account_qb = qb_account_id
            category.sync_token_income = qb_sync_token
            category.income_account_status = status.value
            category.pushed_date = datetime.utc()
            category.pushed_by = 'IncomeSyncService'
            db.session.commit()
            current_app.logger.info(f"Updated income category {category_id} sync status to {status.name}")
        else:
            current_app.logger.error(f"Income category with ID {category_id} not found for status update.")

    def sync_income_category(self, category: Dict[str, Any]) -> bool:
        """Sync a single income category to QuickBooks."""
        try:
            # Prepare payload for QuickBooks
            payload = {
                "Name": category['name'],
                "Description": category.get('description', ''),
                "AccountType": "Income",
            }
            qb_service = self._get_qb_service()
            # Call QuickBooks API to create income category
            response = qb_service.create_account(account_data=payload, realm_id=qb_service.realm_id)
            current_app.logger.info(f"Income category synced: {response}")

            if 'Account' in response:
                qb_account_id = response['Account']['Id']
                qb_sync_token = response['Account']['SyncToken']
                self._update_income_category_sync_status(
                    category['id'],
                    qb_account_id,
                    qb_sync_token,
                    IncomeSyncStatus.SYNCED
                )

                # Log successful sync
                audit_log = QuickbooksAuditLog(
                    entity_type='IncomeCategory',
                    entity_id=category['id'],
                    action='SYNC',
                    status='SUCCESS',
                    details=json.dumps(response, cls=EnhancedJSONEncoder)
                )
                db.session.add(audit_log)
                db.session.commit()

                return IncomeSyncResult(
                    category_id=category['id'],
                    qb_account_id=qb_account_id,
                    qb_sync_token=qb_sync_token,
                    status=IncomeSyncStatus.SYNCED
                )
            else:
                # handle API error response
                error_message = response.get('Fault', {}).get('Error', [{}])[0].get('Message', 'Unknown error')
                current_app.logger.error(f"Failed to sync income category {category['id']}: {error_message}")
                # Log failed sync
                audit_log = QuickbooksAuditLog(
                    entity_type='IncomeCategory',
                    entity_id=category['id'],
                    action='SYNC',
                    status='FAILED',
                    details=error_message
                )
                db.session.add(audit_log)
                db.session.commit()
                return IncomeSyncResult(
                    category_id=category['id'],
                    qb_account_id=None,
                    qb_sync_token=None,
                    status=IncomeSyncStatus.FAILED
                )
        except Exception as e:
            current_app.logger.error(f"Exception during income category sync for {category['id']}: {str(e)}")
            traceback_str = traceback.format_exc()
            current_app.logger.error(traceback_str)
            # Log exception
            audit_log = QuickbooksAuditLog(
                entity_type='IncomeCategory',
                entity_id=category['id'],
                action='SYNC',
                status='FAILED',
                details=str(e)
            )
            db.session.add(audit_log)
            db.session.commit()
            return IncomeSyncResult(
                category_id=category['id'],
                qb_account_id=None,
                qb_sync_token=None,
                status=IncomeSyncStatus.FAILED
            )
