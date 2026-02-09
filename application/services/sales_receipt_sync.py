import logging
import os
from typing import Optional
from enum import Enum
from flask import current_app, jsonify
from application.models.mis_models import Payment, TblIncomeCategory, TblPersonalUg, TblStudentWallet, TblBank, TblRegisterProgramUg, TblCampus, TblOnlineApplication, TblStudentWalletLedger
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
        

    def map_sales_receipt_to_quickbooks(self, sales_receipt: TblStudentWalletLedger) -> dict:
        """
        Map MIS sales receipt data to QuickBooks format.
        
        Args:
            is_update: Whether this is an update operation or new record
            sales_receipt: Student wallet transaction record
            
        Returns:
            dict: QuickBooks-formatted sales receipt data
            
        Raises:
            ValueError: If sales_receipt is None or required data is missing
        """
        if not sales_receipt:
            raise ValueError("sales_receipt cannot be None")

        current_app.logger.info("Mapping sales receipt to QuickBooks format...")
        
        # Fetch and validate required data
        item_id = self._get_item_id(os.getenv("PREPAYMENT_ID"))
        customer_id = self._get_customer_id(sales_receipt.student_id)
        bank_qb_id = self._get_bank_id(sales_receipt.bank_id)
        location_id = self._get_location_id(sales_receipt.student_id)
        
        # Build the base line item structure
        amount = float(sales_receipt.original_amount)
        line_item = {
            "DetailType": "SalesItemLineDetail",
            "Amount": amount,
            "SalesItemLineDetail": {
                "ItemRef": {"value": item_id}
            },
            "Description": "Wallet payment for student " + sales_receipt.student_id

        }
        
        # Build base QuickBooks data structure
        quickbooks_data = {"Line": [line_item]}
        quickbooks_data.update({
            "CustomerRef": {"value": customer_id},
            "DepositToAccountRef": {"value": bank_qb_id},
            "DepartmentRef": {"value": location_id},
            "TxnDate": sales_receipt.created_at.strftime("%Y-%m-%d"),
            "DocNumber": f"SR-{sales_receipt.id}"        
            })
        
        current_app.logger.info("Sales receipt mapped to QuickBooks format successfully.")
        return quickbooks_data


    def _get_item_id(self, fee_category_id: int) -> str:
        """
        Get QuickBooks item ID for a fee category.
        
        Args:
            fee_category_id: Fee category identifier
            
        Returns:
            str: QuickBooks item ID
            
        Raises:
            ValueError: If item not found or missing QuickBooks ID
        """
        item = TblIncomeCategory.get_by_id(fee_category_id)
        
        if not item or not item.income_account_qb:
            current_app.logger.error(f"Income category {fee_category_id} not found or missing QuickBooks mapping")
            raise ValueError(f"Income category {fee_category_id} not found in database or missing QuickBooks account")
        
        return item.QuickBk_ctgId


    def _get_customer_id(self, reg_no: str) -> str:
        """
        Get QuickBooks customer ID for a student.
        
        Args:
            reg_no: Student registration number
            
        Returns:
            str: QuickBooks customer ID
            
        Raises:
            ValueError: If customer not found or missing QuickBooks ID
        """
        student = TblPersonalUg.get_student_by_reg_no(reg_no)
        applicant = TblOnlineApplication.get_applicant_by_registration_no(reg_no)
        
        if student:
            customer_id=student.qk_id
        elif applicant:
            customer_id=applicant.quickbooks_id
        else:
            current_app.logger.error(f"Customer {reg_no} not found (neither student nor applicant)")
            raise ValueError(f"Customer {reg_no} not found in database or missing QuickBooks ID")

        if not customer_id:
            current_app.logger.error(
                f"Customer {reg_no} found but missing QuickBooks ID"
            )
            raise ValueError(
                f"Customer {reg_no} not found in database or missing QuickBooks ID"
            )        
        return customer_id


    def _get_bank_id(self, bank_id: int) -> str:
        """
        Get QuickBooks account ID for a bank.
        
        Args:
            bank_id: Bank identifier
            
        Returns:
            str: QuickBooks account ID
            
        Raises:
            ValueError: If bank not found or missing QuickBooks ID
        """
        bank = TblBank.get_bank_details(bank_id)
        
        if not bank or not bank.get("qk_id"):
            current_app.logger.error(f"Bank {bank_id} not found or missing QuickBooks ID")
            raise ValueError(f"Bank {bank_id} not found in database or missing QuickBooks ID")
        
        return bank.get("qk_id")


    def _get_location_id(self, reg_no: str) -> int:
        """
        Get QuickBooks location/department ID for a student's campus.
        
        Args:
            reg_no: Student registration number
            
        Returns:
            int: QuickBooks location ID
            
        Raises:
            ValueError: If campus or location not found
        """
        student_campus_id = TblRegisterProgramUg.get_campus_id_by_reg_no(reg_no)
        applicants_campus_id = TblOnlineApplication.get_campus_id_by_tracking_id(reg_no)

        if student_campus_id:
            campus_id = student_campus_id
        elif applicants_campus_id:
            campus_id = applicants_campus_id
        else:
            raise ValueError(f"Campus ID not found for student {reg_no}")
        

        if not campus_id:
            current_app.logger.error(f"Campus ID not found for student {reg_no}")
            raise ValueError(f"Campus ID not found for student {reg_no}")
        
        location_id = TblCampus.get_location_id_by_camp_id(campus_id)
        
        if not location_id:
            current_app.logger.error(f"Location ID not found for campus {campus_id}")
            raise ValueError(f"QuickBooks location ID not found for campus {campus_id}")
        
        return int(location_id)
        


    def _get_qb_service(self) -> QuickBooks:
        """
        Get QuickBooks service instance
        """
        if not self.qb_service:
            if not QuickBooksConfig.is_connected():
                raise Exception("QuickBooks is not connected. Please authenticate first.")
            self.qb_service = QuickBooks()
        return self.qb_service
    
    def _update_sales_receipt_sync_status(
        sales_receipt_id: int,
        qb_id: str = None,
        sync_token: str = None
    ):
        """
        Update the sync status of a sales_receipt
        """
        current_app.logger.info(
            f"Updating sync status for sales_receipt {sales_receipt_id}"
        )

        update_ledger = TblStudentWalletLedger.update_sync_status(
            id=sales_receipt_id,
            qb_id=qb_id,
            sync_token=sync_token
        )

        if not update_ledger:
            current_app.logger.error(
                f"Failed to update sync status for sales_receipt {sales_receipt_id}"
            )

        return update_ledger

        



    def _update_deleted_sales_receipt(self, sales_receipt_id: int):

        """
        Update the sync status of a deleted sales_receipt
        """
        current_app.logger.info(
            f"Updating sync status for deleted sales_receipt {sales_receipt_id}"
        )
        with db_manager.get_mis_session() as session:
            sales_receipt = session.get(TblStudentWallet, sales_receipt_id)

            if not sales_receipt:
                self.logger.warning(
                    f"Sales receipt {sales_receipt_id} not found while updating sync status"
                )
                return

            sales_receipt.sync_status = 0
            sales_receipt.quickbooks_id = None
            sales_receipt.sync_token = None

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

        


    def sync_single_sales_receipt(self, sales_receipt: TblStudentWalletLedger) -> SalesReceiptSyncResult:
        """
        Synchronize a single sales_receipt to QuickBooks
        """
        map_error = None

        try:
            qb_service = self._get_qb_service()

            # ---- Mapping phase ----
            try:
                qb_sales_receipt_data = self.map_sales_receipt_to_quickbooks(sales_receipt=sales_receipt)
            except Exception as e:
                map_error = str(e)
                qb_sales_receipt_data = None

            if map_error:
                self._update_sales_receipt_sync_status(
                    sales_receipt.id,
                    SalesReceiptSyncStatus.FAILED.value,
                    qb_id=None,
                    sync_token=None
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
                    sales_receipt_id=sales_receipt.id,
                    qb_id=qb_id,
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
                sales_receipt.id
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
                qb_sales_receipt_data = self.map_sales_receipt_to_quickbooks(False,sales_receipt)
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
                    qb_id=qb_id,
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
        
        # fetch sales receipt from QuickBooks to verify existence
        try:
            qb_service = self._get_qb_service()
            existing_sr_response = qb_service.get_sales_receipt(
                qb_service.realm_id,
                sales_receipt.quickbooks_id
            )

            current_app.logger.debug(
                f"Existing SalesReceipt data from QuickBooks for {sales_receipt.id}: {existing_sr_response}, with type: {type(existing_sr_response)}"
            )
            current_app.logger.info(
                f"Existing sr response: {existing_sr_response}, type: {type(existing_sr_response)}"
            )

            if "Fault" in existing_sr_response:
                error_msg = (
                    existing_sr_response.get('Fault', {})
                    .get('Error', [{}])[0]
                    .get('Detail', 'Unknown QuickBooks error')
                )
                self.logger.error(
                    f"SalesReceipt {sales_receipt.id} not found in QuickBooks: {error_msg}"
                )
                return {
                    "status": "FAILED",
                    "success": False,
                    "error_message": f"Sales receipt not found in QuickBooks: {error_msg}",
                    "details": existing_sr_response
                }
            
            qb_amount = existing_sr_response['SalesReceipt'].get('TotalAmt')
            payment_exists = False
            qb_sync_token = existing_sr_response['SalesReceipt'].get('SyncToken')
            if float(sales_receipt.dept) != float(qb_amount):
                # Amounts differ; check in payments table if payment exists
                from application.models.mis_models import Payment
                payment_exists = Payment.get_payment_by_wallet_id(sales_receipt.reference_number) is not None
                if not payment_exists:
                    self.logger.error(
                        f"Cannot update SalesReceipt {sales_receipt.id}: amounts differ and no payment found"
                    )
                    return {
                        "status": "FAILED",
                        "success": False,
                        "error_message": "Cannot update sales receipt: amounts differ and no payment found",
                        "details": None
                    }
                total_paid = Payment.get_total_paid_by_wallet_id(sales_receipt.reference_number)
                
        except Exception as e:
            error_msg = str(e)
            self.logger.exception(
                f"Error verifying existence of SalesReceipt {sales_receipt.id} in QuickBooks"
            )
            return {
                "status": "FAILED",
                "success": False,
                "error_message": error_msg
            }

        try:
            qb_service = self._get_qb_service()

            # ---- Mapping phase ----
            try:
                # update total amount if payment exists
                if payment_exists:
                    sales_receipt.dept = float(sales_receipt.dept) + float(total_paid)
                    sales_receipt.sync_token = qb_sync_token
                else:
                    sales_receipt.dept = float(sales_receipt.dept) + float(qb_amount)

                qb_sales_receipt_data = self.map_sales_receipt_to_quickbooks(
                    True,sales_receipt
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

    def get_sales_receipt_from_quickbooks(self, quickbooks_id: str) -> dict:
        """
        Retrieve sales receipt details from QuickBooks by QuickBooks ID.
        """
        try:
            qb_service = self._get_qb_service()

            self.logger.info(
                f"Retrieving SalesReceipt from QuickBooks ID: {quickbooks_id}"
            )

            response = qb_service.get_sales_receipt(
                qb_service.realm_id,
                quickbooks_id
            )

            self.logger.debug(
                f"QuickBooks retrieval response for SalesReceipt ID {quickbooks_id}: "
                f"{json.dumps(response, cls=EnhancedJSONEncoder)}"
            )

            # ---- Success path ----
            if 'SalesReceipt' in response:
                return {
                    "status": "RETRIEVED_SUCCESSFULLY",
                    "success": True,
                    "error_message": None,
                    "details": response
                }

        except Exception as e:
            # ---- System-level failure ----
            error_msg = str(e)
            self.logger.exception(
                f"Unexpected error retrieving SalesReceipt {quickbooks_id}"
            )

            return {
                "status": "FAILED",
                "success": False,
                "error_message": error_msg
            }
        
    def delete_sales_receipt_in_quickbooks(self, quickbooks_id: str, sync_token: str = None, sales_receipt_id: int = None) -> dict:
        """
        Delete a sales receipt in QuickBooks by QuickBooks ID.
        """
        try:
            qb_service = self._get_qb_service()

            self.logger.info(
                f"Deleting SalesReceipt in QuickBooks ID: {quickbooks_id}"
            )

            response = qb_service.delete_sales_receipt(
                qb_service.realm_id,
                quickbooks_id,
                sync_token

            )

            self.logger.debug(
                f"QuickBooks deletion response for SalesReceipt ID {quickbooks_id}: "
                f"{json.dumps(response, cls=EnhancedJSONEncoder)}"
            )

            # ---- Success path ----
            if 'SalesReceipt' in response:
                # update local DB to reflect deletion if necessary
                TblStudentWallet.delete_quickbooks_id(quickbooks_id)

                return {
                    "status": "DELETED_SUCCESSFULLY",
                    "success": True,
                    "error_message": None,
                    "details": response
                }

        except Exception as e:
            # ---- System-level failure ----
            error_msg = str(e)
            self.logger.exception(
                f"Unexpected error deleting SalesReceipt {quickbooks_id}"
            )

            return {
                "status": "FAILED",
                "success": False,
                "error_message": error_msg
            }