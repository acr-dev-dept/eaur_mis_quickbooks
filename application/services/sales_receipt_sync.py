import logging
from typing import Optional
from enum import Enum
from flask import current_app, jsonify
from application.models.mis_models import TblIncomeCategory, TblPersonalUg, TblStudentWallet, TblBank, TblRegisterProgramUg, TblCampus
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

    def __init__(self, status: SalesReceiptSyncStatus, error_message: Optional[str] = None, success: bool = True, traceback: Optional[str] = None, details: Optional[dict] = None, quickbooks_id: Optional[str] = None):
        self.details = details
        self.quickbooks_id = quickbooks_id
        self.status = status
        self.error_message = error_message
        self.success = success
        self.traceback = traceback
        self.details = None

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
        

    def map_sales_receipt_to_quickbooks(self, is_update: bool, sales_receipt: TblStudentWallet) -> dict:
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

        
        
        bank = TblBank.get_bank_details(sales_receipt.bank_id)
        if not bank:
            current_app.logger.info("Bank not found in database")
            raise Exception("Bank not found in database")

        student_camp_id = TblRegisterProgramUg.get_campus_id_by_reg_no(sales_receipt.reg_no)
        
        if not student_camp_id:
            current_app.logger.info("Student campus ID not found in database")
            raise Exception("Student campus ID not found in database")
        
        item_id = item.QuickBk_ctgId
        customer_id = customer.qk_id
        bank_qb_id = bank.get("qk_id")
        location_id = TblCampus.get_location_id_by_camp_id(student_camp_id)

        if is_update == True:
            quickbooks_data = {
                "SyncToken": sales_receipt.sync_token, 
                "Line": [
                    {
                    "DetailType": "SalesItemLineDetail", 
                    "Amount": float(sales_receipt.dept), 
                    "Description": "Updated wallet amount", 
                    "SalesItemLineDetail": {
                        "Qty": 1, 
                        "UnitPrice": float(sales_receipt.dept), 
                        "ItemRef": {
                        "value": item_id
                        }
                    }
                    }
                ], 
                "Id": sales_receipt.quickbooks_id, 
                "sparse": True,
            }
        else:
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

                "TotalAmt":float(sales_receipt.dept),

                "DepositToAccountRef" :{
                    "value": bank_qb_id
                },
                "DepartmentRef": {"value": int(location_id) if location_id else ''}
            
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
        current_app.logger.info(
            f"Updating sync status for sales_receipt {sales_receipt_id} to {status}, quickbooks_id: {quickbooks_id}, sync_token: {sync_token}"
        )
        with db_manager.get_mis_session() as session:
            sales_receipt = session.get(TblStudentWallet, sales_receipt_id)

            if not sales_receipt:
                self.logger.warning(
                    f"Sales receipt {sales_receipt_id} not found while updating sync status"
                )
                return

            sales_receipt.sync_status = status

            if quickbooks_id is not None:
                sales_receipt.quickbooks_id = quickbooks_id

            if sync_token is not None:
                sales_receipt.sync_token = sync_token

            session.commit()
            

    def _log_sync_audit(self, sales_receipt_id: int, status: str, error_message: str):
        try:
            with db_manager.get_mis_session() as session:
                
                audit_log = QuickbooksAuditLog(
                    action_type='sales_receipt',
                    operation_status=status,
                    error_message=error_message,
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
            if 'SalesReceipt' in response:
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
                    error_message=f"SalesReceipt {sales_receipt.id} synchronized successfully",
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
        
    def sync_single_sales_receipt_async(self, wallet_id: int) -> dict:
        """
        Synchronize a single sales_receipt to QuickBooks.
        Returns a JSON-serializable dict for both Celery and Flask consumption.
        """
        sales_receipt = TblStudentWallet.get_sales_data(wallet_id)
        if not sales_receipt:
            return {
                "status": "FAILED",
                "success": False,
                "error_message": "Sales receipt not found",
                "details": None
            }

        if sales_receipt.quickbooks_id:
            return {
                "status": "ALREADY_SYNCED",
                "success": True,
                "error_message": "Sales receipt already synced",
                "details": None,
                "quickbooks_id": sales_receipt.quickbooks_id
            }

        try:
            qb_service = self._get_qb_service()

            # ---- Mapping phase ----
            try:
                qb_sales_receipt_data = self.map_sales_receipt_to_quickbooks(True,sales_receipt)
            except Exception as e:
                map_error = str(e)
                qb_sales_receipt_data = None
                self._update_sales_receipt_sync_status(
                    sales_receipt.id,
                    SalesReceiptSyncStatus.FAILED.value
                )
                self._log_sync_audit(sales_receipt.id, 'ERROR', map_error)
                return {
                    "status": "FAILED",
                    "success": False,
                    "error_message": map_error
                }

            # ---- Send to QuickBooks ----
            self.logger.info(f"Sending SalesReceipt {sales_receipt.id}")

            response = qb_service.update_sales_receipt(
                qb_service.realm_id,
                qb_sales_receipt_data
            )

            self.logger.debug(
                f"QuickBooks response for sales_receipt {sales_receipt.id}: "
                f"{json.dumps(response, cls=EnhancedJSONEncoder)}"
            )

            # ---- Success path ----
            if 'SalesReceipt' in response:
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

                return {
                    "status": "SYNCED_SUCCESSFULLY",
                    "success": True,
                    "error_message": f"SalesReceipt {sales_receipt.id} synchronized successfully",
                    "details": response,
                    "quickbooks_id": qb_id
                }

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

            return {
                "status": "FAILED",
                "success": False,
                "error_message": error_msg,
                "details": response
            }

        except Exception as e:
            # ---- System-level failure ----
            error_msg = str(e)
            self.logger.exception(f"Unexpected error syncing sales_receipt {sales_receipt.id}")

            self._update_sales_receipt_sync_status(
                sales_receipt.id,
                SalesReceiptSyncStatus.FAILED.value
            )
            self._log_sync_audit(sales_receipt.id, 'ERROR', error_msg)

            return {
                "status": "FAILED",
                "success": False,
                "error_message": error_msg
            }

    def update_single_sales_receipt(self,wallet_id: int) -> dict:
        """
        Update an already-synced SalesReceipt in QuickBooks.
        Requires quickbooks_id and sync_token to be present.
        """

        sales_receipt = TblStudentWallet.get_sales_data(wallet_id)
        if not sales_receipt:
            return {
                "status": "FAILED",
                "success": False,
                "error_message": "Sales receipt not found",
                "details": None
            }

        if not sales_receipt.quickbooks_id or not sales_receipt.sync_token:
            return {
                "status": "NOT_SYNCED",
                "success": False,
                "error_message": "Sales receipt has not been synced before",
                "details": None
            }

        try:
            qb_service = self._get_qb_service()

            # ---- Mapping phase ----
            try:
                qb_sales_receipt_data = self.map_sales_receipt_to_quickbooks(
                    sales_receipt,
                    is_update=True
                )

                # Required for QuickBooks update
                qb_sales_receipt_data["Id"] = sales_receipt.quickbooks_id
                qb_sales_receipt_data["SyncToken"] = sales_receipt.sync_token

            except Exception as e:
                map_error = str(e)

                self._update_sales_receipt_sync_status(
                    sales_receipt.id,
                    SalesReceiptSyncStatus.FAILED.value
                )
                self._log_sync_audit(sales_receipt.id, 'ERROR', map_error)

                return {
                    "status": "FAILED",
                    "success": False,
                    "error_message": map_error
                }

            # ---- Send update to QuickBooks ----
            self.logger.info(
                f"Updating SalesReceipt {sales_receipt.id} "
                f"(QB ID: {sales_receipt.quickbooks_id})"
            )

            response = qb_service.update_sales_receipt(
                qb_service.realm_id,
                qb_sales_receipt_data
            )

            self.logger.debug(
                f"QuickBooks update response for sales_receipt {sales_receipt.id}: "
                f"{json.dumps(response, cls=EnhancedJSONEncoder)}"
            )

            # ---- Success path ----
            if 'SalesReceipt' in response:
                qb_id = response['SalesReceipt']['Id']
                new_sync_token = response['SalesReceipt'].get('SyncToken')

                self._update_sales_receipt_sync_status(
                    sales_receipt.id,
                    SalesReceiptSyncStatus.SYNCED.value,
                    quickbooks_id=qb_id,
                    sync_token=new_sync_token
                )

                self._log_sync_audit(
                    sales_receipt.id,
                    'SUCCESS',
                    f"Updated QuickBooks SalesReceipt ID: {qb_id}"
                )

                return {
                    "status": "UPDATED_SUCCESSFULLY",
                    "success": True,
                    "error_message": f"SalesReceipt {sales_receipt.id} updated successfully",
                    "details": response,
                    "quickbooks_id": qb_id
                }

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

            return {
                "status": "FAILED",
                "success": False,
                "error_message": error_msg,
                "details": response
            }

        except Exception as e:
            # ---- System-level failure ----
            error_msg = str(e)
            self.logger.exception(
                f"Unexpected error updating sales_receipt {sales_receipt.id}"
            )

            self._update_sales_receipt_sync_status(
                sales_receipt.id,
                SalesReceiptSyncStatus.FAILED.value
            )
            self._log_sync_audit(sales_receipt.id, 'ERROR', error_msg)

            return {
                "status": "FAILED",
                "success": False,
                "error_message": error_msg
            }
