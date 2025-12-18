"""
Payment synchronization service for Urubuto Pay and QuickBooks integration.

This service handles the synchronization of payment data between
Urubuto Pay and QuickBooks.
"""
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum
import json
import time
import traceback

from flask import app, current_app
from sqlalchemy import and_, or_, func
from sqlalchemy.orm import joinedload

from application.models.mis_models import TblOnlineApplication, TblPersonalUg, Payment
from application.models.central_models import QuickBooksConfig, QuickbooksAuditLog
from application.services.quickbooks import QuickBooks
from application.utils.database import db_manager
from application import db
from application.helpers.json_field_helper import JSONFieldHelper
from application.helpers.json_encoder import EnhancedJSONEncoder
from application.helpers.SafeStringify import safe_stringify

class PaymentSyncStatus(Enum):
    """Enumeration for payment synchronization status."""
    NOT_SYNCED = 0
    SYNCED = 1
    FAILED = 2
    IN_PROGRESS = 3

@dataclass
class PaymentSyncStats:
    """Statistics for payment synchronization process"""
    total_payments: int = 0
    not_synced: int = 0
    synced: int = 0
    failed: int = 0
    in_progress: int = 0

    def to_dict(self) -> Dict:
        return {
            'total_payments': self.total_payments,
            'not_synced': self.not_synced,
            'synced': self.synced,
            'failed': self.failed,
            'in_progress': self.in_progress
        }

@dataclass
class PaymentSyncResult:
    """Dataclass to hold the result of a payment synchronization attempt."""
    status: PaymentSyncStatus
    message: str
    success: bool = False  # Add a success indicator
    quickbooks_id: Optional[str] = None # QuickBooks ID if synced
    details: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None # Standardized error message
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

class PaymentSyncService:
    """
    Service for synchronizing MIS payments to QuickBooks
    """

    def __init__(self):
        self.qb_service = None
        self.batch_size = 50  # Process payments in batches
        self.max_retries = 3
        self.retry_delay = 5  # seconds
        self.logger = logging.getLogger(self.__class__.__name__)
        self.bank_sync_service = None  # Lazy load for bank operations

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

    def analyze_sync_requirements(self) -> PaymentSyncStats:
        """
        Analyze current payment synchronization status
        """
        try:
            with db_manager.get_mis_session() as session:
                total_payments = session.query(func.count(Payment.id)).scalar()
                not_synced = session.query(func.count(Payment.id)).filter(
                    or_(Payment.QuickBk_Status == PaymentSyncStatus.NOT_SYNCED.value, Payment.QuickBk_Status.is_(None))
                ).scalar()
                synced = session.query(func.count(Payment.id)).filter(
                    Payment.QuickBk_Status == PaymentSyncStatus.SYNCED.value
                ).scalar()
                failed = session.query(func.count(Payment.id)).filter(
                    Payment.QuickBk_Status == PaymentSyncStatus.FAILED.value
                ).scalar()
                in_progress = session.query(func.count(Payment.id)).filter(
                    Payment.QuickBk_Status == PaymentSyncStatus.IN_PROGRESS.value
                ).scalar()

                stats = PaymentSyncStats(
                    total_payments=total_payments,
                    not_synced=not_synced,
                    synced=synced,
                    failed=failed,
                    in_progress=in_progress
                )
                self.logger.info(f"Payment sync analysis: {stats.to_dict()}")
                return stats

        except Exception as e:
            self.logger.error(f"Error analyzing payment sync requirements: {e}")
            raise

    def get_unsynchronized_payments(self, limit: Optional[int] = None, offset: int = 0) -> List[Payment]:
        """
        Get payments that haven't been synchronized to QuickBooks
        """
        try:
            with db_manager.get_mis_session() as session:
                query = session.query(Payment).options(
                    joinedload(Payment.level),
                    joinedload(Payment.bank),
                    joinedload(Payment.fee_category_rel),
                    joinedload(Payment.online_application)
                ).filter(
                    or_(Payment.QuickBk_Status == PaymentSyncStatus.NOT_SYNCED.value, Payment.QuickBk_Status.is_(None))
                ).order_by(Payment.recorded_date.desc())

                if limit:
                    query = query.limit(limit)
                if offset:
                    query = query.offset(offset)

                payments = query.all()
                self.logger.info(f"Retrieved {len(payments)} unsynchronized payments")
                return payments

        except Exception as e:
            self.logger.error(f"Error getting unsynchronized payments: {e}")
            raise

    def get_unsynced_payments(self, limit: int = 50, offset: int = 0) -> List[Payment]:
        """
        API method to retrieve unsynchronized payments with pagination
        """
        try:
            payments = self.get_unsynchronized_payments(limit=limit, offset=offset)
            payment_list = [payment.to_dict() for payment in payments]
            total_count = self.analyze_sync_requirements().not_synced

            return {
                'total_unsynced': total_count,
                'returned_count': len(payment_list),
                'payments': payment_list
            }
        except Exception as e:
            self.logger.error(f"Error retrieving unsynced payments: {e}")
            return {'error': str(e)}

    def _get_quickbooks_customer_id(self, mis_customer_id: str, customer_type: str) -> Optional[str]:
        """
        Helper to retrieve QuickBooks Customer ID from local database or QuickBooks API if needed.
        This assumes a mapping exists in your local database (e.g., in TblOnlineApplication or TblPersonalUg qk_id).
        """
        from application.models.mis_models import TblOnlineApplication, TblPersonalUg
        with db_manager.get_mis_session() as session:
            if customer_type == 'applicant':
                applicant = session.query(TblOnlineApplication).filter_by(tracking_id=mis_customer_id).first()
                return applicant.qk_id if applicant else None
            elif customer_type == 'student':
                student = session.query(TblPersonalUg).filter_by(reg_no=mis_customer_id).first()
                return student.qk_id if student else None
        return None

    def _get_deposit_account_id(self, payment: Payment, enable_auto_sync: bool = None) -> Tuple[Optional[str], Optional[str]]:
        """
        Get QuickBooks deposit account ID for payment with dynamic bank lookup and verification

        Args:
            payment (Payment): Payment object with bank relationship
            enable_auto_sync (bool): Whether to auto-sync bank if not synced (defaults to config)

        Returns:
            Tuple[account_id, error_message]: QuickBooks account ID or error message
        """
        try:
            # Step 1: Check if payment has associated bank
            if not payment.bank_id:
                return None, "Payment has no associated bank_id"

            if not payment.bank:
                return None, f"Bank relationship not found for bank_id {payment.bank_id}"

            bank_name = payment.bank.bank_name or f"Bank ID {payment.bank_id}"

            # Step 2: Check if bank is synced to QuickBooks
            if not payment.bank.qk_id or not payment.bank.qk_id.strip():
                # Bank not synced - check if auto-sync is enabled
                if enable_auto_sync is None:
                    enable_auto_sync = current_app.config.get('PAYMENT_SYNC_ENABLE_AUTO_BANK_SYNC', False)

                if enable_auto_sync:
                    self.logger.info(f"Bank '{bank_name}' not synced, attempting auto-sync for payment {payment.id}")

                    # Attempt to auto-sync the bank
                    auto_sync_result = self._auto_sync_bank(payment.bank)

                    if auto_sync_result['success']:
                        # Auto-sync successful, use the new QuickBooks ID
                        qb_account_id = auto_sync_result['quickbooks_id']
                        self.logger.info(f"Auto-sync successful for bank '{bank_name}', using QB account ID: {qb_account_id}")
                        return qb_account_id, None
                    else:
                        # Auto-sync failed
                        return None, f"Bank '{bank_name}' (ID: {payment.bank_id}) auto-sync failed: {auto_sync_result['message']}"
                else:
                    # Auto-sync disabled
                    return None, f"Bank '{bank_name}' (ID: {payment.bank_id}) not synced to QuickBooks"

            # Step 3: Bank has QB ID - verify it still exists (optional verification)
            enable_verification = current_app.config.get('PAYMENT_SYNC_VERIFY_BANK_ACCOUNTS', True)

            if enable_verification:
                verification = self._verify_bank_account_exists(payment.bank.qk_id)

                if not verification['exists']:
                    error_msg = f"QuickBooks account {payment.bank.qk_id} for bank '{bank_name}' no longer exists"
                    if verification.get('error'):
                        error_msg += f": {verification['error']}"

                    # Account doesn't exist - could attempt re-sync here if desired
                    return None, error_msg

            # Step 4: Return verified QuickBooks account ID
            self.logger.info(f"Using dynamic QuickBooks account ID '{payment.bank.qk_id}' for bank '{bank_name}' (ID: {payment.bank_id})")
            return payment.bank.qk_id, None

        except Exception as e:
            error_msg = f"Error retrieving deposit account ID for payment {payment.id}: {str(e)}"
            self.logger.error(error_msg)
            return None, error_msg

    def _get_fallback_account_id(self) -> str:
        """
        Get fallback QuickBooks account ID from configuration

        Returns:
            str: Fallback account ID
        """
        fallback_id = current_app.config.get('QUICKBOOKS_DEFAULT_DEPOSIT_ACCOUNT_ID', "35")
        self.logger.warning(f"Using fallback QuickBooks account ID: {fallback_id}")
        return fallback_id

    def _get_bank_sync_service(self):
        """
        Get bank sync service instance for bank operations

        Returns:
            BankSyncService: Bank sync service instance
        """
        if not self.bank_sync_service:
            from application.services.bank_sync import BankSyncService
            self.bank_sync_service = BankSyncService()
        return self.bank_sync_service

    def _verify_bank_account_exists(self, qb_account_id: str) -> Dict[str, Any]:
        """
        Verify that QuickBooks bank account still exists using bank sync service

        Args:
            qb_account_id (str): QuickBooks Account ID to verify

        Returns:
            Dict containing verification results
        """
        try:
            bank_sync_service = self._get_bank_sync_service()
            verification = bank_sync_service._verify_quickbooks_account_exists(qb_account_id)

            if verification['exists']:
                self.logger.debug(f"Verified QuickBooks account {qb_account_id} exists for payment sync")
            else:
                self.logger.warning(f"QuickBooks account {qb_account_id} not found during payment sync verification")

            return verification

        except Exception as e:
            self.logger.error(f"Error verifying QuickBooks account {qb_account_id}: {e}")
            return {
                'exists': False,
                'error': f"Verification failed: {str(e)}",
                'verified_at': datetime.now().isoformat()
            }

    def _auto_sync_bank(self, bank) -> Dict[str, Any]:
        """
        Automatically sync bank to QuickBooks if not already synced

        Args:
            bank: TblBank object to sync

        Returns:
            Dict containing sync result
        """
        try:
            bank_sync_service = self._get_bank_sync_service()

            self.logger.info(f"Attempting auto-sync for bank {bank.bank_id} ({bank.bank_name}) during payment processing")

            # Perform bank sync
            sync_result = bank_sync_service.sync_single_bank(bank)

            result = {
                'success': sync_result.success,
                'quickbooks_id': sync_result.quickbooks_id,
                'message': sync_result.message,
                'action_taken': getattr(sync_result, 'action_taken', 'UNKNOWN')
            }

            if sync_result.success:
                self.logger.info(f"Auto-sync successful for bank {bank.bank_id}: QB ID {sync_result.quickbooks_id}")
                # Log audit entry for auto-sync
                self._log_sync_audit(f"BANK_AUTO_SYNC_{bank.bank_id}", 'SUCCESS',
                                   f"Auto-synced bank {bank.bank_name} (ID: {bank.bank_id}) to QB ID: {sync_result.quickbooks_id}")
            else:
                self.logger.error(f"Auto-sync failed for bank {bank.bank_id}: {sync_result.error_message}")
                self._log_sync_audit(f"BANK_AUTO_SYNC_{bank.bank_id}", 'ERROR',
                                   f"Auto-sync failed for bank {bank.bank_name} (ID: {bank.bank_id}): {sync_result.error_message}")

            return result

        except Exception as e:
            error_msg = f"Exception during auto-sync for bank {bank.bank_id}: {str(e)}"
            self.logger.error(error_msg)
            self._log_sync_audit(f"BANK_AUTO_SYNC_{bank.bank_id}", 'ERROR', error_msg)
            return {
                'success': False,
                'quickbooks_id': None,
                'message': error_msg,
                'action_taken': 'FAILED_EXCEPTION'
            }

    def map_payment_to_quickbooks(self, payment: Payment) -> Tuple[Optional[Dict], Optional[str]]:
        """
        Map MIS payment data to QuickBooks Payment API format
        """
        try:
            # Determine customer (applicant or student)
            customer_ref_id = None
            customer_name = None

            if payment.appl_Id and payment.online_application:
                # Assuming applicant has been synced as a customer
                customer_ref_id = payment.online_application.tracking_id # Use tracking_id for QuickBooks customer lookup if needed
                # In a real scenario, you'd fetch the QuickBooks Customer ID using the tracking_id
                # For now, let's use a placeholder or attempt to query existing QB customers
                qb_customer_id = self._get_quickbooks_customer_id(customer_ref_id, 'applicant')
                if not qb_customer_id:
                    self.logger.warning(f"QuickBooks customer ID not found for applicant {payment.appl_Id}. This payment will be marked as failed.")
                    # In a full solution, you might trigger customer creation here
                    return None, f"QuickBooks Customer not found for applicant {customer_ref_id}"
                customer_ref_id = qb_customer_id

            elif payment.reg_no:
                # Assuming student has been synced as a customer
                # You'd need to fetch student details and their QuickBooks ID
                from application.models.mis_models import TblPersonalUg, TblOnlineApplication
                with db_manager.get_mis_session() as session:
                    student = session.query(TblPersonalUg).filter_by(reg_no=payment.reg_no).first()
                    online_app = session.query(TblOnlineApplication).filter_by(tracking_id=payment.reg_no).first()
                if student and student.qk_id:
                    customer_ref_id = student.qk_id

                elif online_app and online_app.quickbooks_id:
                    customer_ref_id = online_app.quickbooks_id
                
                elif online_app:
                    self.logger.warning(f"QuickBooks ID not found for online application {payment.reg_no}. This payment will be marked as failed.")
                    # In a full solution, you might trigger customer creation here
                    return None, f"QuickBooks Customer not found for online application {payment.reg_no}"

                elif student:
                    self.logger.warning(f"QuickBooks ID not found for student {payment.reg_no}. This payment will be marked as failed.")
                    # In a full solution, you might trigger customer creation here
                    return None, f"QuickBooks Customer not found for student {payment.reg_no}"
                else:
                    self.logger.warning(f"Student with reg_no {payment.reg_no} not found in MIS. This payment will be marked as failed.")
                    return None, f"Student with reg_no {payment.reg_no} not found in MIS."
            
            if not customer_ref_id:
                self.logger.warning(f"Could not determine QuickBooks Customer ID for payment {payment.id}. This payment will be marked as failed.")
                return None, f"Could not determine QuickBooks Customer ID for payment {payment.id}."

            # Determine payment amount
            amount = float(payment.amount or 0)

            # Determine deposit to account using dynamic bank lookup
            deposit_account_id, bank_error = self._get_deposit_account_id(payment)

            if bank_error:
                # Handle bank sync dependency with fallback strategy
                self.logger.warning(f"Bank lookup failed for payment {payment.id}: {bank_error}")

                # Check if fallback is allowed (configurable)
                allow_fallback = current_app.config.get('PAYMENT_SYNC_ALLOW_FALLBACK_ACCOUNT', True)

                if allow_fallback:
                    deposit_account_id = self._get_fallback_account_id()
                    self.logger.warning(f"Using fallback account {deposit_account_id} for payment {payment.id} due to: {bank_error}")
                else:
                    # Strict mode - fail payment sync if bank not synced
                    return None, f"Payment sync failed: {bank_error}. Fallback account disabled."

            # Reference to an invoice if applicable
            linked_invoices = []
            if payment.invoi_ref:
                # Here you would fetch the QuickBooks Invoice ID using payment.invoi_ref
                from application.models.mis_models import TblImvoice
                with db_manager.get_mis_session() as session:
                    invoice_obj = session.query(TblImvoice).filter_by(reference_number=payment.invoi_ref).first()
                    current_app.logger.info(f"Invoice object for reference {payment.invoi_ref}: {invoice_obj}")
                
                if invoice_obj and invoice_obj.quickbooks_id:
                    linked_invoices.append({
                        "TxnId": str(invoice_obj.quickbooks_id),
                        "TxnType": "Invoice"
                    })
                else:
                    self.logger.warning(f"Associated invoice {payment.invoi_ref} not synced to QuickBooks or not found.")


            # Construct the QuickBooks Payment payload
            qb_payment_data = {
                "CustomerRef": {
                    "value": str(customer_ref_id), # This must be the QuickBooks Customer ID
                },
                "DepositToAccountRef": {
                    "value": deposit_account_id # QuickBooks Account ID
                },
                "PaymentMethodRef": {
                    "value": current_app.config.get('QUICKBOOKS_DEFAULT_PAYMENT_METHOD_ID', "2") # Use configurable default
                                 # This should ideally be dynamically mapped from payment.payment_chanel
                },
                "TotalAmt": amount,
                "PrivateNote": f"MIS Payment ID: {payment.id}, Trans Code: {payment.trans_code}",
                "TxnDate": payment.date if payment.date else datetime.now().strftime('%Y-%m-%d') # Use payment date if available
            }

            if linked_invoices:
                qb_payment_data["Line"] = [{
                    "Amount": amount,
                    "LinkedTxn": linked_invoices
                    }]

            self.logger.debug(f"QuickBooks Payment Payload for payment {payment.id}: {json.dumps(qb_payment_data, cls=EnhancedJSONEncoder)}")
            return qb_payment_data, None # Return payload and no error

        except Exception as e:
            self.logger.error(f"Error mapping payment {payment.id} to QuickBooks format: {e}")
            return None, str(e)

    def sync_single_payment(self, payment: Payment) -> PaymentSyncResult:
        """
        Synchronize a single payment to QuickBooks
        """
        try:
            qb_service = self._get_qb_service()
            qb_payment_data, map_error = self.map_payment_to_quickbooks(payment)

            self.logger.debug(f"Mapped QuickBooks payment data for payment {payment.id}: {json.dumps(qb_payment_data, cls=EnhancedJSONEncoder)}")

            if map_error:
                self._update_payment_sync_status(payment.id, PaymentSyncStatus.FAILED.value)
                self._log_sync_audit(payment.id, 'ERROR', map_error)
                return PaymentSyncResult(
                    status=PaymentSyncStatus.FAILED,
                    message=f"Failed to synchronize payment {payment.id} due to mapping error",
                    success=False,
                    error_message=map_error
                )
            # Log the payload being sent
            self.logger.info(f"sending a payment with invoice ref {payment.invoi_ref} to QuickBooks and data mapped is {qb_payment_data}")
            response = qb_service.create_payment(qb_service.realm_id, qb_payment_data)
            # write this response to the log file
            log_path = "/var/log/hrms/quickbooks_response.log"
            try:
                with open(log_path, 'a') as log_file:
                    log_file.write(f"{datetime.now().isoformat()} - Payment ID {payment.id} Response: {response}\n")
                    log_file.write(f"{datetime.now().isoformat()} - Payment ID {payment.id} Request: {qb_payment_data}\n")
            except Exception as e:
                self.logger.error(f"Error writing QuickBooks log for payment {payment.id}: {e}")
            self.logger.debug(f"QuickBooks response for payment {payment.id}: {json.dumps(response, cls=EnhancedJSONEncoder)}")

            if 'Payment' in response and response['Payment'].get('Id'):
                qb_payment_id = response['Payment']['Id']
                self._update_payment_sync_status(
                    payment.id,
                    PaymentSyncStatus.SYNCED.value,
                    quickbooks_id=qb_payment_id,
                    sync_token=response['Payment'].get('SyncToken')
                )
                self._log_sync_audit(payment.id, 'SUCCESS', f"Synced to QuickBooks ID: {qb_payment_id}")
                result = PaymentSyncResult(
                    status=PaymentSyncStatus.SYNCED,
                    message=f"Payment {payment.id} synchronized successfully",
                    success=True,
                    details=response,
                    quickbooks_id=qb_payment_id
                )
                return result.to_dict()
            else:
                error_msg = response.get('Fault', {}).get('Error', [{}])[0].get('Detail', 'Unknown error')
                self._update_payment_sync_status(payment.id, PaymentSyncStatus.FAILED.value)
                self._log_sync_audit(payment.id, 'ERROR', error_msg)
                result = PaymentSyncResult(
                    status=PaymentSyncStatus.FAILED,
                    message=f"Failed to synchronize payment {payment.id}",
                    success=False,
                    error_message=error_msg,
                    details=response
                )
                return result.to_dict()

        except Exception as e:
            error_msg = str(e)
            tb = traceback.format_exc()
            self._update_payment_sync_status(payment.id, PaymentSyncStatus.FAILED.value)
            self._log_sync_audit(payment.id, 'ERROR', error_msg)
            result = PaymentSyncResult(
                status=PaymentSyncStatus.FAILED,
                message=f"Error synchronizing payment {payment.id}",
                success=False,
                error_message=error_msg,
                traceback=tb
            )
            return result.to_dict()


    def sync_single_payment_async(self, payment_id: int) -> Dict:
        """
        Synchronize a single payment to QuickBooks
        """
        payment = Payment.get_payment_by_id(payment_id)

        if payment.date < datetime(2025, 1, 1):
            return {
                'status': 'ERROR',
                'message': 'Payment date is before 2025-01-01',
                'success': False
            }

        if not payment:
            raise ValueError(f"Payment with ID {payment_id} not found.")
        
        if payment.QuickBk_Status == 1:  # Already synced
            return {
                'status': 'ALREADY_SYNCED',
                'message': f"Payment {payment_id} is already synchronized to QuickBooks.",
                'success': True
            }
        try:
            qb_service = self._get_qb_service()
            qb_payment_data, map_error = self.map_payment_to_quickbooks(payment)

            self.logger.debug(f"Mapped QuickBooks payment data for payment {payment.id}: {json.dumps(qb_payment_data, cls=EnhancedJSONEncoder)}")

            if map_error:
                self._update_payment_sync_status(payment.id, PaymentSyncStatus.FAILED.value)
                self._log_sync_audit(payment.id, 'ERROR', map_error)
                return PaymentSyncResult(
                    status=PaymentSyncStatus.FAILED,
                    message=f"Failed to synchronize payment {payment.id} due to mapping error",
                    success=False,
                    error_message=map_error
                )
            # Log the payload being sent
            self.logger.info(f"sending a payment with invoice ref {payment.invoi_ref} to QuickBooks and data mapped is {qb_payment_data}")
            response = qb_service.create_payment(qb_service.realm_id, qb_payment_data)
            # write this response to the log file
            log_path = "/var/log/hrms/quickbooks_response.log"
            try:
                with open(log_path, 'a') as log_file:
                    log_file.write(f"{datetime.now().isoformat()} - Payment ID {payment.id} Response: {response}\n")
                    log_file.write(f"{datetime.now().isoformat()} - Payment ID {payment.id} Request: {qb_payment_data}\n")
            except Exception as e:
                self.logger.error(f"Error writing QuickBooks log for payment {payment.id}: {e}")
            self.logger.debug(f"QuickBooks response for payment {payment.id}: {json.dumps(response, cls=EnhancedJSONEncoder)}")

            if 'Payment' in response and response['Payment'].get('Id'):
                qb_payment_id = response['Payment']['Id']
                self._update_payment_sync_status(
                    payment.id,
                    PaymentSyncStatus.SYNCED.value,
                    quickbooks_id=qb_payment_id,
                    sync_token=response['Payment'].get('SyncToken')
                )
                self._log_sync_audit(payment.id, 'SUCCESS', f"Synced to QuickBooks ID: {qb_payment_id}")
                result = PaymentSyncResult(
                    status=PaymentSyncStatus.SYNCED,
                    message=f"Payment {payment.id} synchronized successfully",
                    success=True,
                    details=response,
                    quickbooks_id=qb_payment_id
                )
                return result.to_dict()
            else:
                error_msg = response.get('Fault', {}).get('Error', [{}])[0].get('Detail', 'Unknown error')
                self._update_payment_sync_status(payment.id, PaymentSyncStatus.FAILED.value)
                self._log_sync_audit(payment.id, 'ERROR', error_msg)
                current_app.logger.error(f"Failed to sync payment {payment.id}. Error: {error_msg}. Full response: {response}")
                result = PaymentSyncResult(
                    status=PaymentSyncStatus.FAILED,
                    message=f"Failed to synchronize payment {payment.id}",
                    success=False,
                    error_message=error_msg,
                    details=response
                )
                return result.to_dict()

        except Exception as e:
            error_msg = str(e)
            tb = traceback.format_exc()
            self._update_payment_sync_status(payment.id, PaymentSyncStatus.FAILED.value)
            self._log_sync_audit(payment.id, 'ERROR', error_msg)
            result = PaymentSyncResult(
                status=PaymentSyncStatus.FAILED,
                message=f"Error synchronizing payment {payment.id}",
                success=False,
                error_message=error_msg,
                traceback=tb
            )
            return result.to_dict()

    def sync_payments_batch(self, batch_size: Optional[int] = None) -> Dict:
        """
        Synchronize a batch of unsynchronized payments to QuickBooks using the batch API.
        """
        batch_size = batch_size or self.batch_size
        qb_service = self._get_qb_service()
        realm_id = qb_service.realm_id

        payments_batch = self.get_unsynchronized_payments(limit=batch_size)

        if not payments_batch:
            self.logger.info("No unsynchronized payments found for batch sync.")
            return {'total_processed': 0, 'successful': 0, 'failed': 0, 'results': []}

        self.logger.info(f"Processing batch of {len(payments_batch)} unsynchronized payments.")

        batch_operations = []
        payment_id_map = {}

        for i, payment_orm in enumerate(payments_batch):
            try:
                # Mark as IN_PROGRESS immediately
                self._update_payment_sync_status(payment_orm.id, PaymentSyncStatus.IN_PROGRESS.value)

                qb_payment_data, map_error = self.map_payment_to_quickbooks(payment_orm)

                if map_error or not qb_payment_data:
                    self.logger.error(f"Error preparing payment {payment_orm.id} for batch sync: {map_error or 'Mapping returned empty data.'}")
                    self._update_payment_sync_status(payment_orm.id, PaymentSyncStatus.FAILED.value)
                    self._log_sync_audit(payment_orm.id, 'ERROR', map_error or 'Mapping returned empty data.')
                    continue # Skip to the next payment in the batch

                bId = f"payment-{payment_orm.id}"
                payment_id_map[bId] = payment_orm.id # Store original MIS payment ID

                batch_operations.append({
                    "operation": "create",
                    "bId": bId,
                    "Payment": qb_payment_data
                })
            except Exception as e:
                self.logger.error(f"Unexpected error preparing payment {payment_orm.id} for batch sync: {e}")
                self._update_payment_sync_status(payment_orm.id, PaymentSyncStatus.FAILED.value)
                self._log_sync_audit(payment_orm.id, 'ERROR', f"Unexpected error preparing for batch sync: {str(e)}")
                # Continue to next payment if this one fails to map
                
        if not batch_operations:
            self.logger.warning("No payments successfully prepared for batch operations.")
            return {'total_processed': len(payments_batch), 'successful': 0, 'failed': len(payments_batch), 'results': []}

        batch_payload = {
            "BatchItemRequest": batch_operations
        }

        all_results: List[PaymentSyncResult] = []
        total_succeeded = 0
        total_failed = 0

        try:
            quickbooks_batch_response = qb_service.make_batch_request(realm_id, batch_payload)
            self.logger.info(f"QuickBooks batch response for payments: {quickbooks_batch_response}")

            for item_response in quickbooks_batch_response.get("BatchItemResponse", []):
                bId = item_response.get("bId")
                mis_payment_id = payment_id_map.get(bId)

                if not mis_payment_id:
                    self.logger.warning(f"Payment with bId {bId} not found in map. Skipping status update.")
                    continue

                if "Payment" in item_response and item_response['Payment'].get('Id'):
                    qb_payment_id = item_response['Payment']['Id']
                    self._update_payment_sync_status(mis_payment_id, PaymentSyncStatus.SYNCED.value, quickbooks_id=qb_payment_id)
                    self._log_sync_audit(mis_payment_id, 'SUCCESS', f"Synced to QuickBooks ID: {qb_payment_id}")
                    all_results.append(PaymentSyncResult(
                        status=PaymentSyncStatus.SYNCED, message=f"Payment {mis_payment_id} synced successfully",
                        success=True,
                        quickbooks_id=qb_payment_id, details=item_response
                    ))
                    total_succeeded += 1
                else:
                    error_detail = "Unknown error during batch sync."
                    if "Fault" in item_response and "Error" in item_response['Fault']:
                        error_detail = item_response['Fault']['Error'][0].get('Detail', error_detail)
                    
                    self.logger.error(f"Failed to sync payment {mis_payment_id} (bId: {bId}). Error: {error_detail}. Full response: {item_response}")
                    self._update_payment_sync_status(mis_payment_id, PaymentSyncStatus.FAILED.value)
                    self._log_sync_audit(mis_payment_id, 'ERROR', f"Batch sync failed: {error_detail}")
                    all_results.append(PaymentSyncResult(
                        status=PaymentSyncStatus.FAILED, message=f"Failed to sync payment {mis_payment_id}",
                        success=False,
                        error_message=error_detail, details=item_response
                    ))
                    total_failed += 1

        except Exception as e:
            self.logger.error(f"Overall error during QuickBooks batch request for payments: {e}")
            self.logger.error(traceback.format_exc())
            # Mark all payments in the current batch as failed if the entire request fails
            for payment_orm in payments_batch:
                self._update_payment_sync_status(payment_orm.id, PaymentSyncStatus.FAILED.value)
                self._log_sync_audit(payment_orm.id, 'ERROR', f"Overall batch request failed: {str(e)}")
                all_results.append(PaymentSyncResult(
                    status=PaymentSyncStatus.FAILED, message=f"Error during batch sync for payment {payment_orm.id}",
                    success=False,
                    error_message=str(e), traceback=traceback.format_exc()
                ))
                total_failed += 1
        
        return {
            "total_processed": len(payments_batch),
            "successful": total_succeeded,
            "failed": total_failed,
            "results": all_results
        }

    def sync_all_payments(self, max_batches: Optional[int] = None) -> Dict:
        """
        Synchronize all unsynchronized payments in batches
        """
        overall_results = {
            'batches_processed': 0,
            'total_processed': 0,
            'total_successful': 0,
            'total_failed': 0,
            'batch_results': [],
            'start_time': datetime.now(),
            'end_time': None
        }

        batch_count = 0
        while True:
            if max_batches and batch_count >= max_batches:
                self.logger.info(f"Reached maximum batch limit: {max_batches}")
                break

            batch_result = self.sync_payments_batch()

            if batch_result['total_processed'] == 0:
                self.logger.info("No more payments to synchronize.")
                break

            batch_count += 1
            overall_results['batches_processed'] = batch_count
            overall_results['total_processed'] += batch_result['total_processed']
            overall_results['total_successful'] += batch_result['successful']
            overall_results['total_failed'] += batch_result['failed']
            overall_results['batch_results'].append({
                'batch_number': batch_count,
                'result': batch_result
            })

            self.logger.info(f"Completed batch {batch_count}: {batch_result['successful']} successful, {batch_result['failed']} failed")
            time.sleep(2) # Delay between batches to respect API limits

        overall_results['end_time'] = datetime.now()
        duration = overall_results['end_time'] - overall_results['start_time']

        self.logger.info(f"Payment synchronization completed: {overall_results['total_successful']} successful, "
                           f"{overall_results['total_failed']} failed in {duration}")
        return overall_results

    def _update_payment_sync_status(self, payment_id: int, status: int, quickbooks_id: Optional[str] = None, sync_token: Optional[str] = None):
        """
        Update payment synchronization status in MIS database
        """
        try:
            with db_manager.get_mis_session() as session:
                payment = session.query(Payment).filter(Payment.id == payment_id).first()
                if payment:
                    payment.QuickBk_Status = status
                    payment.pushed_date = datetime.now()
                    payment.pushed_by = "PaymentSyncService"
                    if sync_token:
                        payment.sync_token = sync_token
                    if quickbooks_id and status == PaymentSyncStatus.SYNCED.value:
                        payment.qk_id = quickbooks_id # Assuming 'qk_id' field exists in Payment model for QB ID
                    session.commit()
                    self.logger.info(f"Updated payment {payment_id} sync status to {status}")
        except Exception as e:
            self.logger.error(f"Error updating payment sync status for payment {payment_id}: {e}")
            # No need for session.rollback() in finally here, as it's done within db_manager context
            raise

    def _log_sync_audit(self, payment_id: int, action: str, details: str):
        """
        Log synchronization audit trail for payments
        """
        with app.app_context():
            try:
                audit_log = QuickbooksAuditLog(
                    action_type=f"PAYMENT_SYNC_{action}",
                    operation_status=f"{'200' if action == 'SUCCESS' else '500'}",
                    response_payload=f"Payment ID: {payment_id} - {details}",
                )
                db.session.add(audit_log)
                db.session.commit()
            except Exception as e:
                self.logger.error(f"Error logging payment sync audit for payment {payment_id}: {e}")
                if db.session:
                    db.session.rollback()