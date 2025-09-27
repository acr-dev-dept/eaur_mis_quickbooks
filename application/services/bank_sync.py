"""
Bank synchronization service for MIS-QuickBooks integration.

This service handles the synchronization of bank data from MIS to QuickBooks Chart of Accounts.
"""
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
from sqlalchemy.orm import joinedload

from application.models.mis_models import TblBank
from application.models.central_models import QuickBooksConfig, QuickbooksAuditLog
from application.services.quickbooks import QuickBooks
from application.utils.database import db_manager
from application import db
from application.helpers.json_encoder import EnhancedJSONEncoder
from application.helpers.SafeStringify import safe_stringify


class BankSyncStatus(Enum):
    """
    Enumeration for bank synchronization status.

    These values are stored in the tbl_bank.status field:
    - 0: Bank not synchronized to QuickBooks
    - 1: Bank successfully synchronized to QuickBooks
    - 2: Bank synchronization failed
    - 3: Bank synchronization in progress

    Note: The status field serves dual purpose - original bank status AND sync status
    """
    NOT_SYNCED = 0
    SYNCED = 1
    FAILED = 2
    IN_PROGRESS = 3


@dataclass
class BankSyncStats:
    """Dataclass to hold bank synchronization statistics."""
    total_banks: int
    not_synced: int
    synced: int
    failed: int
    in_progress: int


@dataclass
class BankSyncResult:
    """Dataclass to hold the result of a bank synchronization attempt."""
    status: BankSyncStatus
    message: str
    success: bool = False
    quickbooks_id: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    traceback: Optional[str] = None
    duration: Optional[float] = None

    def __init__(self, status, message, success, quickbooks_id=None, details=None,
                 error_message=None, traceback=None, duration=None):
        self.status = status
        self.message = message
        self.success = success
        self.quickbooks_id = quickbooks_id
        self.details = details or {}
        self.error_message = error_message
        self.traceback = traceback
        self.duration = duration

    def to_dict(self) -> Dict:
        return {
            'status': self.status.name,
            'message': self.message,
            'success': self.success,
            'quickbooks_id': self.quickbooks_id,
            'details': self.details,
            'error_message': self.error_message,
            'traceback': self.traceback,
            'duration': self.duration
        }


class BankSyncService:
    """
    Service for synchronizing MIS banks to QuickBooks Chart of Accounts
    """

    def __init__(self):
        self.qb_service = None
        self.batch_size = 20  # Banks are fewer, smaller batches
        self.max_retries = 3
        self.retry_delay = 5  # seconds
        self.logger = logging.getLogger(self.__class__.__name__)

    def to_dict(self) -> Dict:
        return {
            'qb_service': safe_stringify(self.qb_service),
            'batch_size': self.batch_size,
            'max_retries': self.max_retries,
            'retry_delay': self.retry_delay
        }

    def _get_qb_service(self) -> QuickBooks:
        """
        Get QuickBooks service instance
        """
        if not self.qb_service:
            if not QuickBooksConfig.is_connected():
                raise Exception("QuickBooks is not connected. Please authenticate first.")
            self.qb_service = QuickBooks()
        return self.qb_service

    def analyze_sync_requirements(self) -> BankSyncStats:
        """
        Analyze current bank synchronization status
        """
        try:
            with db_manager.get_mis_session() as session:
                total_banks = session.query(func.count(TblBank.bank_id)).scalar()
                not_synced = session.query(func.count(TblBank.bank_id)).filter(
                    or_(TblBank.status == BankSyncStatus.NOT_SYNCED.value, TblBank.status.is_(None))
                ).scalar()
                synced = session.query(func.count(TblBank.bank_id)).filter(
                    TblBank.status == BankSyncStatus.SYNCED.value
                ).scalar()
                failed = session.query(func.count(TblBank.bank_id)).filter(
                    TblBank.status == BankSyncStatus.FAILED.value
                ).scalar()
                in_progress = session.query(func.count(TblBank.bank_id)).filter(
                    TblBank.status == BankSyncStatus.IN_PROGRESS.value
                ).scalar()

                return BankSyncStats(
                    total_banks=total_banks,
                    not_synced=not_synced,
                    synced=synced,
                    failed=failed,
                    in_progress=in_progress
                )

        except Exception as e:
            self.logger.error(f"Error analyzing bank sync requirements: {e}")
            raise

    def get_unsynchronized_banks(self, limit: Optional[int] = None, offset: int = 0) -> List[TblBank]:
        """
        Get banks that haven't been synchronized to QuickBooks
        """
        try:
            with db_manager.get_mis_session() as session:
                query = session.query(TblBank).filter(
                    or_(TblBank.status == BankSyncStatus.NOT_SYNCED.value, TblBank.status.is_(None))
                ).order_by(TblBank.bank_id.asc())

                if limit:
                    query = query.limit(limit)
                if offset:
                    query = query.offset(offset)

                banks = query.all()
                self.logger.info(f"Retrieved {len(banks)} unsynchronized banks")
                return banks

        except Exception as e:
            self.logger.error(f"Error getting unsynchronized banks: {e}")
            raise

    def get_bank_by_id(self, bank_id: int) -> Optional[TblBank]:
        """
        Get bank by ID
        """
        try:
            with db_manager.get_mis_session() as session:
                bank = session.query(TblBank).filter(TblBank.bank_id == bank_id).first()
                return bank
        except Exception as e:
            self.logger.error(f"Error getting bank for ID {bank_id}: {e}")
            return None

    def _map_currency(self, mis_currency: str) -> str:
        """
        Map MIS currency codes to QuickBooks currency codes
        """
        currency_map = {
            'RWF': 'RWF',
            'USD': 'USD',
            'EUR': 'EUR',
            'GBP': 'GBP'
        }
        return currency_map.get(mis_currency.upper(), 'RWF')  # Default to RWF

    def _safe_get_sync_status(self, status_value) -> BankSyncStatus:
        """
        Safely convert database status value to BankSyncStatus enum

        Args:
            status_value: The status value from database (could be int, str, or None)

        Returns:
            BankSyncStatus: The corresponding enum value, defaults to NOT_SYNCED
        """
        try:
            # Handle None or empty values
            if status_value is None or status_value == '':
                return BankSyncStatus.NOT_SYNCED

            # Convert to integer if it's a string
            if isinstance(status_value, str):
                try:
                    status_value = int(status_value)
                except ValueError:
                    # If string can't be converted to int, check for known string values
                    status_map = {
                        'active': BankSyncStatus.NOT_SYNCED,
                        'inactive': BankSyncStatus.NOT_SYNCED,
                        'synced': BankSyncStatus.SYNCED,
                        'failed': BankSyncStatus.FAILED,
                        'in_progress': BankSyncStatus.IN_PROGRESS
                    }
                    return status_map.get(status_value.lower(), BankSyncStatus.NOT_SYNCED)

            # Try to create enum from integer value
            if isinstance(status_value, int):
                try:
                    return BankSyncStatus(status_value)
                except ValueError:
                    # If integer is not a valid enum value, default to NOT_SYNCED
                    return BankSyncStatus.NOT_SYNCED

            # Default fallback
            return BankSyncStatus.NOT_SYNCED

        except Exception as e:
            self.logger.warning(f"Error converting status value '{status_value}' to BankSyncStatus: {e}")
            return BankSyncStatus.NOT_SYNCED

    def map_bank_to_quickbooks_account(self, bank: TblBank) -> Tuple[Optional[Dict], Optional[str]]:
        """
        Map MIS bank to QuickBooks Account format
        
        Args:
            bank (TblBank): MIS bank object
            
        Returns:
            Tuple[Optional[Dict], Optional[str]]: (account_data, error_message)
        """
        try:
            if not bank.bank_name:
                return None, "Bank name is required"

            # Create account name combining bank name and branch
            account_name = f"{bank.bank_name}"
            if bank.bank_branch and bank.bank_branch.strip():
                account_name += f" - {bank.bank_branch}"

            account_data = {
                "Name": account_name,
                "AccountType": "Bank",
                "AccountSubType": "Checking",  # Default to Checking account
                "AcctNum": bank.account_no or "",
                "Description": f"MIS Bank ID: {bank.bank_id} - {bank.bank_name} {bank.bank_branch or ''}".strip(),
                "CurrencyRef": {
                    "value": self._map_currency(bank.currency)
                }
            }

            return account_data, None

        except Exception as e:
            error_msg = f"Error mapping bank {bank.bank_id} to QuickBooks format: {str(e)}"
            self.logger.error(error_msg)
            return None, error_msg

    def sync_single_bank(self, bank: TblBank) -> BankSyncResult:
        """
        Synchronize a single bank to QuickBooks Chart of Accounts
        """
        start_time = time.time()

        try:
            self._update_bank_sync_status(bank.bank_id, BankSyncStatus.IN_PROGRESS.value)
            qb_service = self._get_qb_service()
            account_data, map_error = self.map_bank_to_quickbooks_account(bank)

            self.logger.debug(f"Mapped QuickBooks account data for bank {bank.bank_id}: {json.dumps(account_data, cls=EnhancedJSONEncoder)}")

            if map_error:
                self._update_bank_sync_status(bank.bank_id, BankSyncStatus.FAILED.value)
                self._log_sync_audit(bank.bank_id, 'ERROR', map_error)
                return BankSyncResult(
                    status=BankSyncStatus.FAILED,
                    message=f"Failed to synchronize bank {bank.bank_id} due to mapping error",
                    success=False,
                    error_message=map_error,
                    duration=time.time() - start_time
                )

            response = qb_service.create_account(qb_service.realm_id, account_data)
            self.logger.debug(f"QuickBooks response for bank {bank.bank_id}: {json.dumps(response, cls=EnhancedJSONEncoder)}")

            if 'Account' in response and response['Account'].get('Id'):
                qb_account_id = response['Account']['Id']
                self._update_bank_sync_status(
                    bank.bank_id,
                    BankSyncStatus.SYNCED.value,
                    quickbooks_id=qb_account_id
                )
                self._log_sync_audit(bank.bank_id, 'SUCCESS', f"Synced to QuickBooks Account ID: {qb_account_id}")
                result = BankSyncResult(
                    status=BankSyncStatus.SYNCED,
                    message=f"Bank {bank.bank_id} synchronized successfully",
                    success=True,
                    details=response,
                    quickbooks_id=qb_account_id,
                    duration=time.time() - start_time
                )
                return result
            else:
                error_detail = "Unknown error during bank sync."
                if "Fault" in response and "Error" in response['Fault']:
                    error_detail = response['Fault']['Error'][0].get('Detail', error_detail)

                self._update_bank_sync_status(bank.bank_id, BankSyncStatus.FAILED.value)
                self._log_sync_audit(bank.bank_id, 'ERROR', error_detail)
                return BankSyncResult(
                    status=BankSyncStatus.FAILED,
                    message=f"Failed to synchronize bank {bank.bank_id}",
                    success=False,
                    error_message=error_detail,
                    details=response,
                    duration=time.time() - start_time
                )

        except Exception as e:
            duration = time.time() - start_time
            tb = traceback.format_exc()
            error_msg = f"Exception during bank sync for bank {bank.bank_id}: {str(e)}"
            self.logger.error(error_msg)
            self.logger.error(f"Traceback: {tb}")

            self._update_bank_sync_status(bank.bank_id, BankSyncStatus.FAILED.value)
            self._log_sync_audit(bank.bank_id, 'ERROR', error_msg)

            result = BankSyncResult(
                status=BankSyncStatus.FAILED,
                message=f"Exception during bank sync for bank {bank.bank_id}",
                success=False,
                error_message=error_msg,
                traceback=tb,
                duration=duration
            )
            return result

    def get_bank_status(self, bank_id: int) -> Dict:
        """
        Get synchronization status for a specific bank
        """
        try:
            bank = self.get_bank_by_id(bank_id)
            if not bank:
                return {
                    'error': f'Bank with ID {bank_id} not found',
                    'bank_id': bank_id
                }

            sync_status_enum = self._safe_get_sync_status(bank.status)
            return {
                'bank_id': bank.bank_id,
                'bank_name': bank.bank_name,
                'bank_branch': bank.bank_branch,
                'sync_status': bank.status,
                'sync_status_name': sync_status_enum.name,
                'sync_status_value': sync_status_enum.value,
                'quickbooks_id': bank.qk_id,
                'pushed_by': bank.pushed_by,
                'pushed_date': bank.pushed_date.isoformat() if bank.pushed_date else None,
                'last_updated': datetime.now().isoformat()
            }

        except Exception as e:
            self.logger.error(f"Error getting bank status for bank {bank_id}: {e}")
            return {
                'error': f'Error retrieving status for bank {bank_id}: {str(e)}',
                'bank_id': bank_id
            }

    def _update_bank_sync_status(self, bank_id: int, status: int, quickbooks_id: Optional[str] = None):
        """
        Update bank synchronization status in MIS database
        """
        try:
            with db_manager.get_mis_session() as session:
                bank = session.query(TblBank).filter(TblBank.bank_id == bank_id).first()
                if bank:
                    bank.status = status
                    bank.pushed_date = datetime.now()
                    bank.pushed_by = "BankSyncService"
                    if quickbooks_id and status == BankSyncStatus.SYNCED.value:
                        bank.qk_id = quickbooks_id
                    session.commit()
                    self.logger.info(f"Updated bank {bank_id} sync status to {status}")
        except Exception as e:
            self.logger.error(f"Error updating bank sync status for bank {bank_id}: {e}")
            raise

    def _log_sync_audit(self, bank_id: int, action: str, details: str):
        """
        Log synchronization audit trail for banks
        """
        try:
            audit_log = QuickbooksAuditLog(
                action_type=f"BANK_SYNC_{action}",
                operation_status=f"{'200' if action == 'SUCCESS' else '500'}",
                response_payload=f"Bank ID: {bank_id} - {details}",
            )
            db.session.add(audit_log)
            db.session.commit()
        except Exception as e:
            self.logger.error(f"Error logging bank sync audit for bank {bank_id}: {e}")
            if db.session:
                db.session.rollback()
