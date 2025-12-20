import logging
from typing import Optional
from enum import Enum
from flask import current_app
from application.models.mis_models import TblIncomeCategory, TblPersonalUg, TblStudentWallet
from application.services.quickbooks import QuickBooks
import traceback
from application.models.central_models import QuickBooksConfig, QuickbooksAuditLog
from datetime import datetime
import json
from application.helpers.json_encoder import EnhancedJSONEncoder
from application.utils.database import db_manager






class SalesReceiptSyncStatus(Enum):
    """Enumeration for sales_receipt synchronization status."""
    NOT_SYNCED = 0
    SYNCED = 1
    FAILED = 2
    IN_PROGRESS = 3


class SalesReceiptSyncResult:
    """Dataclass to hold the result of a sales_receipt synchronization attempt."""
    status: SalesReceiptSyncStatus
    error_message: Optional[str] = None
    success: bool = True
    details: Optional[dict] = None
    quickbooks_id: Optional[str] = None
    traceback: Optional[str] = None

    def __init__(self, status: SalesReceiptSyncStatus, error_message: Optional[str] = None, success: bool = True, traceback: Optional[str] = None):
        self.status = status
        self.error_message = error_message
        self.success = success
        self.traceback = traceback

    def to_dict(self) -> dict:
        """Convert the object to a dictionary."""
        return {
            "status": self.status.value,
            "error_message": self.error_message
        }
    

class SalesReceiptSyncService:


    def __init__(self):
        self.qb_service = None
        self.batch_size = 50  # Process payments in batches
        self.max_retries = 3
        self.retry_delay = 5  # seconds
        self.logger = logging.getLogger(self.__class__.__name__)
        self.bank_sync_service = None  # Lazy load for bank operations
        self.success = None
        

    def map_sales_receipt_to_quickbooks(self, sales_receipt: TblStudentWallet) -> dict:
        """
            Map MIS sales receipt data to quickbooks format.
        """

        if not sales_receipt:
            raise ValueError("sales_receipt cannot be None")


        current_app.logger.info("Mapping sales receipt to quickbooks format...")
        item = TblIncomeCategory.get_by_id(sales_receipt.fee_category)
        

        if not item or not item.income_account_qb:
            current_app.logger.info("Item not found in database")
            raise Exception("Item not found in database")

        
        customer = TblPersonalUg.get_student_by_reg_no(sales_receipt.reg_no)
        if not customer or not customer.qk_id:
            current_app.logger.info("Customer not found in database")
            raise Exception("Customer not found in database")

        item_id = item.income_account_qb
        customer_id = customer.qk_id
        

        quickbooks_data = {
            "Line": [
                {
                    "DetailType": "SalesItemLineDetail",
                    "Amount": float(sales_receipt.dept),
                    "SalesItemLineDetail": {
                        "ItemRef": {
                            "value": item_id
                        }
                    }
                }
            ],
            "CustomerRef": {
                "value": customer_id
            },
            "TotalAmt":float(sales_receipt.dept)
        
        }
        current_app.logger.info("Sales receipt mapped to quickbooks format successfully.")
        return quickbooks_data
        


    def _get_qb_service(self) -> QuickBooks:
        """
        Get QuickBooks service instance
        """
        if not self.qb_service:
            if not QuickBooksConfig.is_connected():
                raise Exception("QuickBooks is not connected. Please authenticate first.")
            self.qb_service = QuickBooks()
        return self.qb_service
    
    def _update_sales_receipt_sync_status(self, sales_receipt_id: int, status: int, quickbooks_id: Optional[str] = None, sync_token: Optional[str] = None):
        """
        Update the sync status of a sales_receipt
        """
        sales_receipt = TblStudentWallet.get_by_id(sales_receipt_id)
        if sales_receipt:
            with db_manager.get_mis_session() as session:
                sales_receipt.sync_status = status
                sales_receipt.quickbooks_id = quickbooks_id
                sales_receipt.sync_token = sync_token
                session.commit()
                session.close()
            

    def _log_sync_audit(self, sales_receipt_id: int, status: str, message: str):
        try:
            with db_manager.get_mis_session() as session:
                
                audit_log = QuickbooksAuditLog(
                    action_type='sales_receipt',
                    operation_status=status,
                    error_message=message,
                    request_payload=None,
                    response_payload=None,
                    user_id=None,
                )
                session.add(audit_log)
                session.commit()
                session.close()
        except Exception as e:
            self.logger.error(f"Error logging sync audit for sales_receipt {sales_receipt_id}: {e}")

        


    def sync_single_sales_receipt(self, sales_receipt: TblStudentWallet) -> SalesReceiptSyncResult:
        """
        Synchronize a single sales_receipt to QuickBooks
        """
        map_error = None

        try:
            qb_service = self._get_qb_service()

            # ---- Mapping phase ----
            try:
                qb_sales_receipt_data = self.map_sales_receipt_to_quickbooks(sales_receipt)
            except Exception as e:
                map_error = str(e)
                qb_sales_receipt_data = None

            if map_error:
                self._update_sales_receipt_sync_status(
                    sales_receipt.id,
                    SalesReceiptSyncStatus.FAILED.value
                )
                self._log_sync_audit(sales_receipt.id, 'ERROR', map_error)
                return SalesReceiptSyncResult(
                    status=SalesReceiptSyncStatus.FAILED,
                    success=False,
                    error_message=map_error
                )

            # ---- Send to QuickBooks ----
            self.logger.info(
                f"Sending SalesReceipt {sales_receipt.id} "
            )

            response = qb_service.create_sales_receipt(
                qb_service.realm_id,
                qb_sales_receipt_data
            )

            self.logger.debug(
                f"QuickBooks response for sales_receipt {sales_receipt.id}: "
                f"{json.dumps(response, cls=EnhancedJSONEncoder)}"
            )

            # ---- Success path ----
            if response.get('SalesReceipt', {}).get('Id'):
                qb_id = response['SalesReceipt']['Id']
                sync_token = response['SalesReceipt'].get('SyncToken')

                self._update_sales_receipt_sync_status(
                    sales_receipt.id,
                    SalesReceiptSyncStatus.SYNCED.value,
                    quickbooks_id=qb_id,
                    sync_token=sync_token
                )

                self._log_sync_audit(
                    sales_receipt.id,
                    'SUCCESS',
                    f"Synced to QuickBooks ID: {qb_id}"
                )

                return SalesReceiptSyncResult(
                    status=SalesReceiptSyncStatus.SYNCED,
                    success=True,
                    message=f"SalesReceipt {sales_receipt.id} synchronized successfully",
                    details=response,
                    quickbooks_id=qb_id
                )

            # ---- QuickBooks business error ----
            error_msg = (
                response.get('Fault', {})
                .get('Error', [{}])[0]
                .get('Detail', 'Unknown QuickBooks error')
            )

            self._update_sales_receipt_sync_status(
                sales_receipt.id,
                SalesReceiptSyncStatus.FAILED.value
            )
            self._log_sync_audit(sales_receipt.id, 'ERROR', error_msg)

            return SalesReceiptSyncResult(
                status=SalesReceiptSyncStatus.FAILED,
                success=False,
                error_message=error_msg,
                details=response
            )

        except Exception as e:
            # ---- System-level failure ----
            error_msg = str(e)
            self.logger.exception(
                f"Unexpected error syncing sales_receipt {sales_receipt.id}"
            )

            self._update_sales_receipt_sync_status(
                sales_receipt.id,
                SalesReceiptSyncStatus.FAILED.value
            )
            self._log_sync_audit(sales_receipt.id, 'ERROR', error_msg)

            return SalesReceiptSyncResult(
                status=SalesReceiptSyncStatus.FAILED,
                success=False,
                error_message=error_msg
            )
