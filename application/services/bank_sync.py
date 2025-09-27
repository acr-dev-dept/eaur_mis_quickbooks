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
from application.config.bank_sync_config import BankSyncConfig, DEFAULT_CONFIG


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
    already_synced: bool = False  # New field to indicate if bank was already synced
    action_taken: Optional[str] = None  # What action was taken (created, skipped, verified, etc.)

    def __init__(self, status, message, success, quickbooks_id=None, details=None,
                 error_message=None, traceback=None, duration=None, already_synced=False, action_taken=None):
        self.status = status
        self.message = message
        self.success = success
        self.quickbooks_id = quickbooks_id
        self.details = details or {}
        self.error_message = error_message
        self.traceback = traceback
        self.duration = duration
        self.already_synced = already_synced
        self.action_taken = action_taken

    def to_dict(self) -> Dict:
        return {
            'status': self.status.name,
            'message': self.message,
            'success': self.success,
            'quickbooks_id': self.quickbooks_id,
            'details': self.details,
            'error_message': self.error_message,
            'traceback': self.traceback,
            'duration': self.duration,
            'already_synced': self.already_synced,
            'action_taken': self.action_taken
        }


class BankSyncService:
    """
    Service for synchronizing MIS banks to QuickBooks Chart of Accounts
    """

    def __init__(self, config=None):
        self.qb_service = None
        self.batch_size = 20  # Banks are fewer, smaller batches
        self.max_retries = 3
        self.retry_delay = 5  # seconds
        self.logger = logging.getLogger(self.__class__.__name__)

        # Load configuration (defaults to current environment setting)
        self.config = config or DEFAULT_CONFIG
        self.environment = self.config.get('environment', 'SANDBOX')
        self.qb_base_currency = self.config.get('qb_base_currency', 'USD')
        self.mis_primary_currency = self.config.get('mis_primary_currency', 'RWF')
        self.currency_strategy = self.config.get('currency_strategy', 'AUTO_DETECT')
        self.enable_multi_currency_detection = self.config.get('enable_multi_currency_detection', True)

        self.logger.info(f"BankSyncService initialized for {self.environment} environment")
        self.logger.info(f"QB base currency: {self.qb_base_currency}, MIS primary: {self.mis_primary_currency}")
        self.logger.info(f"Currency strategy: {self.currency_strategy}")

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

    def _is_multicurrency_enabled(self) -> bool:
        """
        DEPRECATED: Not needed for single-currency EAUR environment
        Kept for backward compatibility if needed in future
        """
        """
        Check if QuickBooks company has multi-currency enabled

        Returns:
            bool: True if multi-currency is enabled, False otherwise
        """
        try:
            # First try the simple currency query method
            if self._test_multicurrency_support():
                return True

            # Fallback: Try company info method
            qb_service = self._get_qb_service()

            # Get company information to check multi-currency status
            endpoint = f"{qb_service.realm_id}/companyinfo/{qb_service.realm_id}"
            response = qb_service.make_request(endpoint, method="GET")

            if 'CompanyInfo' in response:
                company_info = response['CompanyInfo'][0] if isinstance(response['CompanyInfo'], list) else response['CompanyInfo']
                # Check for multi-currency preference
                multicurrency_enabled = company_info.get('QBORealmID') is not None and \
                                      company_info.get('Country') != 'US'  # Basic heuristic

                self.logger.info(f"Multi-currency enabled from company info: {multicurrency_enabled}")
                return multicurrency_enabled

            # Final fallback: Try to get preferences
            prefs_endpoint = f"{qb_service.realm_id}/preferences"
            prefs_response = qb_service.make_request(prefs_endpoint, method="GET")

            if 'Preferences' in prefs_response:
                # Look for currency preferences
                preferences = prefs_response['Preferences']
                if 'CurrencyPrefs' in preferences:
                    multicurrency = preferences['CurrencyPrefs'].get('MultiCurrencyEnabled', False)
                    self.logger.info(f"Multi-currency from preferences: {multicurrency}")
                    return multicurrency

            # Default to False (single currency) to avoid errors
            self.logger.warning("Could not determine multi-currency status, defaulting to False")
            return False

        except Exception as e:
            self.logger.warning(f"Error checking multi-currency status: {e}. Defaulting to False")
            return False

    def _test_multicurrency_support(self) -> bool:
        """
        DEPRECATED: Not needed for single-currency EAUR environment
        Alternative method: Test multi-currency support by attempting to query currencies

        Returns:
            bool: True if multi-currency is supported, False otherwise
        """
        try:
            qb_service = self._get_qb_service()

            # Try to query available currencies - this will fail if multi-currency is disabled
            endpoint = f"{qb_service.realm_id}/query"
            query = "SELECT * FROM Currency MAXRESULTS 1"

            response = qb_service.make_request(
                endpoint,
                method="POST",
                data=query,
                headers={"Content-Type": "application/text"}
            )

            # If we get currencies back, multi-currency is enabled
            if 'Currency' in response:
                self.logger.info("Multi-currency detected via Currency query")
                return True

            return False

        except Exception as e:
            # If currency query fails, multi-currency is likely disabled
            self.logger.info(f"Currency query failed (multi-currency likely disabled): {e}")
            return False

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

    def _is_bank_already_synced_status_based(self, bank: TblBank) -> Dict[str, Any]:
        """
        Check sync state using status field as primary indicator with qk_id validation

        This is the robust hybrid approach that provides operational intelligence
        and maintains consistency with existing payment/customer sync patterns.

        Args:
            bank (TblBank): Bank to check

        Returns:
            Dict containing sync status analysis
        """
        sync_status_enum = self._safe_get_sync_status(bank.status)

        analysis = {
            'is_synced': False,
            'has_qb_id': bool(bank.qk_id and bank.qk_id.strip()),
            'sync_status': sync_status_enum,
            'sync_status_value': bank.status,
            'qb_id': bank.qk_id,
            'pushed_date': bank.pushed_date,
            'data_consistent': False,
            'issues': [],
            'recommendation': None
        }

        # Primary check: Status field indicates sync state
        if sync_status_enum == BankSyncStatus.SYNCED:
            analysis['is_synced'] = True

            # Secondary validation: Ensure qk_id exists for data consistency
            if analysis['has_qb_id']:
                analysis['data_consistent'] = True
                analysis['recommendation'] = 'SKIP_ALREADY_SYNCED'
            else:
                analysis['issues'].append('Bank marked as synced but missing QuickBooks ID')
                analysis['recommendation'] = 'VERIFY_OR_RESYNC'

        elif sync_status_enum == BankSyncStatus.IN_PROGRESS:
            analysis['issues'].append('Bank sync appears to be in progress')
            analysis['recommendation'] = 'CHECK_PROGRESS_OR_RETRY'

        elif sync_status_enum == BankSyncStatus.FAILED:
            analysis['issues'].append('Previous sync attempt failed')
            analysis['recommendation'] = 'RETRY_SYNC'

        else:  # NOT_SYNCED
            analysis['recommendation'] = 'PROCEED_WITH_SYNC'

        return analysis

    def _is_bank_already_synced(self, bank: TblBank) -> Dict[str, Any]:
        """
        Check if bank is already synchronized using the hybrid status-based approach

        This is the primary method that uses status field as primary indicator
        with qk_id validation for robust duplicate detection.

        Args:
            bank (TblBank): Bank to check

        Returns:
            Dict containing sync status analysis
        """
        # Use the status-based approach as the primary/default method
        return self._is_bank_already_synced_status_based(bank)

    def _verify_quickbooks_account_exists(self, qb_account_id: str) -> Dict[str, Any]:
        """
        Verify that a QuickBooks account actually exists

        Args:
            qb_account_id (str): QuickBooks Account ID to verify

        Returns:
            Dict containing verification results
        """
        verification = {
            'exists': False,
            'account_data': None,
            'error': None,
            'verified_at': datetime.now().isoformat()
        }

        try:
            qb_service = self._get_qb_service()

            # Query specific account by ID
            endpoint = f"{qb_service.realm_id}/account/{qb_account_id}"
            response = qb_service.make_request(endpoint, method="GET")

            if 'Account' in response:
                verification['exists'] = True
                verification['account_data'] = response['Account']
                self.logger.info(f"Verified QuickBooks account {qb_account_id} exists")
            else:
                verification['error'] = 'Account not found in QuickBooks'
                self.logger.warning(f"QuickBooks account {qb_account_id} not found")

        except Exception as e:
            verification['error'] = f"Error verifying account: {str(e)}"
            self.logger.error(f"Error verifying QuickBooks account {qb_account_id}: {e}")

        return verification

    def _decide_currency_handling(self, bank: TblBank) -> Dict[str, Any]:
        """
        Intelligently decide how to handle currency for this bank

        Args:
            bank (TblBank): The bank being synchronized

        Returns:
            Dict containing currency decision and rationale
        """
        decision = {
            'include_currency_ref': False,
            'currency_value': None,
            'strategy_used': None,
            'rationale': None
        }

        bank_currency = (bank.currency or self.mis_primary_currency).upper()

        if self.currency_strategy == 'OMIT':
            # Always omit CurrencyRef - QB will use base currency
            decision.update({
                'include_currency_ref': False,
                'strategy_used': 'OMIT',
                'rationale': f'Omitting CurrencyRef - QB will use base currency ({self.qb_base_currency})'
            })

        elif self.currency_strategy == 'FORCE_BASE':
            # Always use QB base currency
            decision.update({
                'include_currency_ref': True,
                'currency_value': self.qb_base_currency,
                'strategy_used': 'FORCE_BASE',
                'rationale': f'Forcing QB base currency ({self.qb_base_currency})'
            })

        elif self.currency_strategy == 'MATCH_BANK':
            # Use bank's actual currency
            decision.update({
                'include_currency_ref': True,
                'currency_value': self._map_currency(bank_currency),
                'strategy_used': 'MATCH_BANK',
                'rationale': f'Using bank currency ({bank_currency})'
            })

        elif self.currency_strategy == 'AUTO_DETECT':
            # Intelligent decision based on environment and currencies
            if bank_currency == self.qb_base_currency:
                # Perfect match - omit CurrencyRef
                decision.update({
                    'include_currency_ref': False,
                    'strategy_used': 'AUTO_DETECT_MATCH',
                    'rationale': f'Bank currency ({bank_currency}) matches QB base ({self.qb_base_currency}) - omitting CurrencyRef'
                })
            else:
                # Currency mismatch - check if multi-currency is enabled
                if self.enable_multi_currency_detection and self._is_multicurrency_enabled():
                    # Multi-currency enabled - use bank's currency
                    decision.update({
                        'include_currency_ref': True,
                        'currency_value': self._map_currency(bank_currency),
                        'strategy_used': 'AUTO_DETECT_MULTI',
                        'rationale': f'Multi-currency enabled - using bank currency ({bank_currency})'
                    })
                else:
                    # Multi-currency disabled - omit CurrencyRef (QB will use base currency)
                    decision.update({
                        'include_currency_ref': False,
                        'strategy_used': 'AUTO_DETECT_FALLBACK',
                        'rationale': f'Multi-currency disabled - omitting CurrencyRef, QB will use base currency ({self.qb_base_currency})'
                    })

        return decision

    def _map_currency(self, mis_currency: str) -> str:
        """
        Map MIS currency codes to QuickBooks currency codes
        """
        currency_map = {
            'RWF': 'RWF',
            'USD': 'USD',
            'EUR': 'EUR',
            'GBP': 'GBP',
            'KES': 'KES',  # Kenyan Shilling
            'TZS': 'TZS',  # Tanzanian Shilling
            'UGX': 'UGX'   # Ugandan Shilling
        }
        return currency_map.get(mis_currency.upper(), self.qb_base_currency)

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
        Map MIS bank to QuickBooks Account format with intelligent currency handling

        Args:
            bank (TblBank): MIS bank object

        Returns:
            Tuple[Optional[Dict], Optional[str]]: (account_data, error_message)
        """
        try:
            if not bank.bank_name:
                return None, "Bank name is required"

            # Make currency decision
            currency_decision = self._decide_currency_handling(bank)

            # Create account name using template
            name_template = self.config.get('account_name_template', '{bank_name} - {bank_branch}')
            account_name = name_template.format(
                bank_name=bank.bank_name,
                bank_branch=bank.bank_branch or '',
                currency=bank.currency or self.mis_primary_currency
            ).strip(' -')

            # Create description using template
            desc_template = self.config.get('description_template', 'MIS Bank ID: {bank_id} - {bank_name} {bank_branch}')
            description = desc_template.format(
                bank_id=bank.bank_id,
                bank_name=bank.bank_name,
                bank_branch=bank.bank_branch or '',
                currency=bank.currency or self.mis_primary_currency
            ).strip()

            # Base account data
            account_data = {
                "Name": account_name,
                "AccountType": "Bank",
                "AccountSubType": "Checking",
                "AcctNum": bank.account_no or "",
                "Description": description
            }

            # Add currency reference if decision says to include it
            if currency_decision['include_currency_ref'] and currency_decision['currency_value']:
                account_data["CurrencyRef"] = {
                    "value": currency_decision['currency_value']
                }

            # Log the decision
            log_prefix = self.config.get('log_prefix', '[BANK_SYNC]')
            self.logger.info(f"{log_prefix} Bank {bank.bank_id} mapping: {currency_decision['rationale']}")

            return account_data, None

        except Exception as e:
            error_msg = f"Error mapping bank {bank.bank_id} to QuickBooks format: {str(e)}"
            self.logger.error(error_msg)
            return None, error_msg

    def sync_single_bank(self, bank: TblBank, force_resync: bool = False) -> BankSyncResult:
        """
        Synchronize a single bank to QuickBooks Chart of Accounts with duplicate handling

        Args:
            bank (TblBank): Bank to synchronize
            force_resync (bool): If True, bypass duplicate checks and force re-sync

        Returns:
            BankSyncResult: Result of synchronization attempt
        """
        start_time = time.time()
        log_prefix = self.config.get('log_prefix', '[BANK_SYNC]')

        try:
            # Step 1: Check if bank is already synchronized (unless forced)
            if not force_resync:
                sync_analysis = self._is_bank_already_synced(bank)

                if sync_analysis['recommendation'] == 'SKIP_ALREADY_SYNCED':
                    # Bank is properly synced - verify QB account still exists
                    verification = self._verify_quickbooks_account_exists(sync_analysis['qb_id'])

                    if verification['exists']:
                        # Perfect - bank is synced and QB account exists
                        self.logger.info(f"{log_prefix} Bank {bank.bank_id} already synchronized (QB ID: {sync_analysis['qb_id']})")
                        self._log_sync_audit(bank.bank_id, 'SKIPPED', f"Already synced to QB Account ID: {sync_analysis['qb_id']}")

                        return BankSyncResult(
                            status=BankSyncStatus.SYNCED,
                            message=f"Bank {bank.bank_id} ({bank.bank_name}) is already synchronized",
                            success=True,
                            quickbooks_id=sync_analysis['qb_id'],
                            duration=time.time() - start_time,
                            already_synced=True,
                            action_taken='SKIPPED_ALREADY_SYNCED',
                            details={
                                'sync_date': sync_analysis['pushed_date'].isoformat() if sync_analysis['pushed_date'] else None,
                                'quickbooks_account': verification['account_data']
                            }
                        )
                    else:
                        # Data inconsistency - QB account missing
                        self.logger.warning(f"{log_prefix} Bank {bank.bank_id} marked as synced but QB account {sync_analysis['qb_id']} not found")
                        self._log_sync_audit(bank.bank_id, 'WARNING', f"QB Account {sync_analysis['qb_id']} not found - will re-sync")
                        # Continue with sync to fix inconsistency

                elif sync_analysis['recommendation'] == 'VERIFY_OR_RESYNC':
                    # Bank marked as synced but missing QB ID - data inconsistency
                    self.logger.warning(f"{log_prefix} Bank {bank.bank_id} has inconsistent sync state: {sync_analysis['issues']}")
                    self._log_sync_audit(bank.bank_id, 'WARNING', f"Inconsistent sync state: {', '.join(sync_analysis['issues'])}")
                    # Continue with sync to fix inconsistency

                elif sync_analysis['recommendation'] == 'CHECK_PROGRESS_OR_RETRY':
                    # Bank is in progress - check how long it's been
                    if sync_analysis['pushed_date']:
                        time_since_start = datetime.now() - sync_analysis['pushed_date']
                        if time_since_start.total_seconds() < 300:  # Less than 5 minutes
                            return BankSyncResult(
                                status=BankSyncStatus.IN_PROGRESS,
                                message=f"Bank {bank.bank_id} sync is already in progress (started {time_since_start.total_seconds():.0f}s ago)",
                                success=False,
                                duration=time.time() - start_time,
                                already_synced=False,
                                action_taken='SKIPPED_IN_PROGRESS',
                                error_message="Sync already in progress - try again later"
                            )
                    # If too much time has passed, continue with sync
                    self.logger.info(f"{log_prefix} Bank {bank.bank_id} sync appears stalled - proceeding with fresh sync")

            # Step 2: Proceed with synchronization
            self.logger.info(f"{log_prefix} Starting synchronization for bank {bank.bank_id} ({bank.bank_name})")
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
                    duration=time.time() - start_time,
                    action_taken='FAILED_MAPPING'
                )

            # Step 3: Create account in QuickBooks
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

                action = 'CREATED_NEW' if not force_resync else 'FORCE_RESYNCED'
                return BankSyncResult(
                    status=BankSyncStatus.SYNCED,
                    message=f"Bank {bank.bank_id} ({bank.bank_name}) synchronized successfully",
                    success=True,
                    details=response,
                    quickbooks_id=qb_account_id,
                    duration=time.time() - start_time,
                    action_taken=action
                )
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
                    duration=time.time() - start_time,
                    action_taken='FAILED_QB_CREATE'
                )

        except Exception as e:
            duration = time.time() - start_time
            tb = traceback.format_exc()
            error_msg = f"Exception during bank sync for bank {bank.bank_id}: {str(e)}"
            self.logger.error(error_msg)
            self.logger.error(f"Traceback: {tb}")

            self._update_bank_sync_status(bank.bank_id, BankSyncStatus.FAILED.value)
            self._log_sync_audit(bank.bank_id, 'ERROR', error_msg)

            return BankSyncResult(
                status=BankSyncStatus.FAILED,
                message=f"Exception during bank sync for bank {bank.bank_id}",
                success=False,
                error_message=error_msg,
                traceback=tb,
                duration=duration,
                action_taken='FAILED_EXCEPTION'
            )

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
