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
    
    def __init__(self, status: SalesReceiptSyncStatus, error_message: Optional[str] = None):
        self.status = status
        self.error_message = error_message

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

    def map_sales_receipt_to_quickbooks(self, sales_receipt: dict):
        """
            Map MIS sales receipt data to quickbooks format.
        """

        if sales_receipt:
            current_app.logger.info("Mapping sales receipt to quickbooks format...")
            item = TblIncomeCategory.get_by_id(sales_receipt.fee_category)
            customer = TblPersonalUg.get_student_by_reg_no(sales_receipt.reg_no)

            if item:
                item_id = item.income_account_qb
            else:
                current_app.logger.info("Item not found in database")
                raise Exception("Item not found in database")

            if customer:
                customer_id = customer.id
            else:
                current_app.logger.info("Customer not found in database")
                raise Exception("Customer not found in database")
            sales_receipt["customer_id"] = customer_id

        try:
            quickbooks_data = {
                "Line": [
                    {
                        "DetailType": "SalesItemLineDetail",
                        "Amount": sales_receipt["amount"],
                        "SalesItemLine": {
                            "ItemRef": {
                                "value": item_id
                            }
                        }
                    }
                ],
                "CustomerRef": {
                    "value": sales_receipt["customer_id"]
                }
            
            }
            current_app.logger.info("Sales receipt mapped to quickbooks format successfully.")
            return quickbooks_data
        except Exception as e:
            current_app.logger.error(f"Error mapping sales receipt to quickbooks format: {e}")
            raise Exception

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
                    id=sales_receipt_id,
                    status=status,
                    message=message
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
        try:
            qb_service = self._get_qb_service()
            qb_sales_receipt_data, map_error = self.map_sales_receipt_to_quickbooks(sales_receipt)

            self.logger.debug(f"Mapped QuickBooks sales_receipt data for sales_receipt {sales_receipt.id}: {json.dumps(qb_sales_receipt_data, cls=EnhancedJSONEncoder)}")

            if map_error:
                self._update_sales_receipt_sync_status(sales_receipt.id, SalesReceiptSyncStatus.FAILED.value)
                self._log_sync_audit(sales_receipt.id, 'ERROR', map_error)
                return SalesReceiptSyncResult(
                    status=SalesReceiptSyncStatus.FAILED,
                    message=f"Failed to synchronize sales_receipt {sales_receipt.id} due to mapping error",
                    success=False,
                    error_message=map_error
                )
            # Log the payload being sent
            self.logger.info(f"sending a sales_receipt with invoice ref {sales_receipt.invoi_ref} to QuickBooks and data mapped is {qb_sales_receipt_data}")
            response = qb_service.create_sales_receipt(qb_service.realm_id, qb_sales_receipt_data)
            # write this response to the log file
            log_path = "/var/log/hrms/quickbooks_response.log"
            try:
                with open(log_path, 'a') as log_file:
                    log_file.write(f"{datetime.now().isoformat()} - Payment ID {sales_receipt.id} Response: {response}\n")
                    log_file.write(f"{datetime.now().isoformat()} - Payment ID {sales_receipt.id} Request: {qb_sales_receipt_data}\n")
            except Exception as e:
                self.logger.error(f"Error writing QuickBooks log for sales_receipt {sales_receipt.id}: {e}")
            self.logger.debug(f"QuickBooks response for sales_receipt {sales_receipt.id}: {json.dumps(response, cls=EnhancedJSONEncoder)}")

            if 'Payment' in response and response['Payment'].get('Id'):
                qb_sales_receipt_id = response['Payment']['Id']
                self._update_sales_receipt_sync_status(
                    sales_receipt.id,
                    SalesReceiptSyncStatus.SYNCED.value,
                    quickbooks_id=qb_sales_receipt_id,
                    sync_token=response['Payment'].get('SyncToken')
                )
                self._log_sync_audit(sales_receipt.id, 'SUCCESS', f"Synced to QuickBooks ID: {qb_sales_receipt_id}")
                result = SalesReceiptSyncResult(
                    status=SalesReceiptSyncStatus.SYNCED,
                    message=f"Payment {sales_receipt.id} synchronized successfully",
                    success=True,
                    details=response,
                    quickbooks_id=qb_sales_receipt_id
                )
                return result.to_dict()
            else:
                error_msg = response.get('Fault', {}).get('Error', [{}])[0].get('Detail', 'Unknown error')
                self._update_sales_receipt_sync_status(sales_receipt.id, SalesReceiptSyncStatus.FAILED.value)
                self._log_sync_audit(sales_receipt.id, 'ERROR', error_msg)
                result = SalesReceiptSyncResult(
                    status=SalesReceiptSyncStatus.FAILED,
                    message=f"Failed to synchronize sales_receipt {sales_receipt.id}",
                    success=False,
                    error_message=error_msg,
                    details=response
                )
                return result.to_dict()

        except Exception as e:
            error_msg = str(e)
            tb = traceback.format_exc()
            self._update_sales_receipt_sync_status(sales_receipt.id, SalesReceiptSyncStatus.FAILED.value)
            self._log_sync_audit(sales_receipt.id, 'ERROR', error_msg)
            result = SalesReceiptSyncResult(
                status=SalesReceiptSyncStatus.FAILED,
                success=False,
                error_message=error_msg,
                traceback=tb
            )
            return result.to_dict()
