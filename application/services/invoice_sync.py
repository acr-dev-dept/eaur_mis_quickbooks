"""
Invoice Synchronization Service for EAUR MIS-QuickBooks Integration

This service handles the bulk synchronization of existing invoices from MIS to QuickBooks,
including progress tracking, error handling, and data validation.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum
import json
import time

from flask import current_app
from sqlalchemy import and_, or_, func
from sqlalchemy.orm import joinedload

from application.models.mis_models import TblImvoice, TblPersonalUg, TblLevel, TblIncomeCategory, Payment, TblOnlineApplication
from application.models.central_models import QuickBooksConfig, QuickbooksAuditLog
from application.services.quickbooks import QuickBooks
from application.utils.database import db_manager
from application import db


logger = logging.getLogger(__name__)

class SyncStatus(Enum):
    """Synchronization status enumeration"""
    NOT_SYNCED = 0
    SYNCED = 1
    FAILED = 2
    IN_PROGRESS = 3

@dataclass
class SyncStats:
    """Statistics for synchronization process"""
    total_invoices: int = 0
    not_synced: int = 0
    already_synced: int = 0
    failed: int = 0
    in_progress: int = 0
    
    def to_dict(self) -> Dict:
        return {
            'total_invoices': self.total_invoices,
            'not_synced': self.not_synced,
            'already_synced': self.already_synced,
            'failed': self.failed,
            'in_progress': self.in_progress
        }

@dataclass
class SyncResult:
    """Result of a single invoice synchronization"""
    invoice_id: int
    success: bool
    quickbooks_id: Optional[str] = None
    error_message: Optional[str] = None
    details: Optional[Dict] = None

class InvoiceSyncService:
    """
    Service for synchronizing MIS invoices to QuickBooks
    """
    
    def __init__(self):
        self.qb_service = None
        self.batch_size = 50  # Process invoices in batches
        self.max_retries = 3
        self.retry_delay = 5  # seconds
        
    def _get_qb_service(self) -> QuickBooks:
        """Get QuickBooks service instance"""
        if not self.qb_service:
            if not QuickBooksConfig.is_connected():
                raise Exception("QuickBooks is not connected. Please authenticate first.")
            self.qb_service = QuickBooks()
        return self.qb_service
    
    def analyze_sync_requirements(self) -> SyncStats:
        """
        Analyze current invoice synchronization status
        
        Returns:
            SyncStats: Statistics about invoices requiring synchronization
        """
        try:
            session = db_manager.get_mis_session()
            
            # Get total invoice count
            total_count = session.query(func.count(TblImvoice.id)).scalar()
            
            # Count by sync status
            not_synced = session.query(func.count(TblImvoice.id)).filter(
                or_(TblImvoice.QuickBk_Status == 0, TblImvoice.QuickBk_Status.is_(None))
            ).scalar()
            
            already_synced = session.query(func.count(TblImvoice.id)).filter(
                TblImvoice.QuickBk_Status == 1
            ).scalar()
            
            failed = session.query(func.count(TblImvoice.id)).filter(
                TblImvoice.QuickBk_Status == 2
            ).scalar()
            
            in_progress = session.query(func.count(TblImvoice.id)).filter(
                TblImvoice.QuickBk_Status == 3
            ).scalar()
            
            stats = SyncStats(
                total_invoices=total_count,
                not_synced=not_synced,
                already_synced=already_synced,
                failed=failed,
                in_progress=in_progress
            )
            
            logger.info(f"Invoice sync analysis: {stats.to_dict()}")
            return stats
            
        except Exception as e:
            logger.error(f"Error analyzing sync requirements: {e}")
            raise
        finally:
            if 'session' in locals():
                session.close()
    def fetch_invoice_data(self, invoice_id: int) -> TblImvoice:
        """
        Fetch a single invoice by ID
        
        Args:
            invoice_id: ID of the invoice to fetch
            
        Returns:
            TblImvoice: Invoice object
        """
        try:
            with db_manager.get_mis_session() as session:
                invoice = session.query(TblImvoice).options(
                    joinedload(TblImvoice.level),
                    joinedload(TblImvoice.fee_category_rel),
                    joinedload(TblImvoice.module),
                joinedload(TblImvoice.intake)
            ).filter(TblImvoice.id == invoice_id, TblImvoice.QuickBk_Status != 1).first()
            
            if not invoice:
                raise Exception(f"Invoice with ID {invoice_id} not found")
            
            return invoice
            
        except Exception as e:
            logger.error(f"Error fetching invoice {invoice_id}: {e}")
            raise Exception(f"The invoice with ID {invoice_id} could not be found or is already synchronized.") from e
        finally:
            if 'session' in locals():
                session.close()
    def get_unsynchronized_invoices(self, limit: Optional[int] = None, offset: int = 0) -> List[TblImvoice]:
        """
        Get invoices that haven't been synchronized to QuickBooks
        
        Args:
            limit: Maximum number of invoices to return
            offset: Number of invoices to skip
            
        Returns:
            List of unsynchronized invoice objects
        """
        try:
            with db_manager.get_mis_session() as session:
                query = (
                    session.query(TblImvoice)
                    .join(TblImvoice.fee_category_rel)  # join TblIncomeCategory
                    .filter(
                        or_(
                            TblImvoice.QuickBk_Status != 1,
                            TblImvoice.QuickBk_Status.is_(None),
                        ),
                        TblIncomeCategory.status_Id == 1,  # active category
                    )
                    .order_by(TblImvoice.invoice_date.desc())
                )

            
            if limit:
                query = query.limit(limit)
            if offset:
                query = query.offset(offset)
                
            invoices = query.all()
            logger.info(f"Retrieved {len(invoices)} unsynchronized invoices")
            return invoices
            
        except Exception as e:
            logger.error(f"Error getting unsynchronized invoices: {e}")
            raise
        finally:
            if 'session' in locals():
                session.close()
    
    def get_student_details(self, reg_no: str) -> Optional[Dict]:
        """
        Get student details for invoice customer mapping
        
        Args:
            reg_no: Student registration number
            
        Returns:
            Dictionary with student details or None if not found
        """
        try:
            with db_manager.get_mis_session() as session:
                student = session.query(TblPersonalUg).filter(
                    TblPersonalUg.reg_no == reg_no
                ).first()
            
            if student:
                return {
                    'reg_no': student.reg_no,
                    'first_name': getattr(student, 'first_name', ''),
                    'last_name': getattr(student, 'last_name', ''),
                    'email': getattr(student, 'email', ''),
                    'phone': getattr(student, 'phone', ''),
                    'full_name': f"{getattr(student, 'first_name', '')} {getattr(student, 'last_name', '')}".strip()
                }
            return None
            
        except Exception as e:
            logger.error(f"Error getting student details for {reg_no}: {e}")
            return None
        finally:
            if 'session' in locals():
                session.close()

    def map_invoice_to_quickbooks(self, invoice: TblImvoice) -> Dict:
        """
        Map MIS invoice data to QuickBooks invoice format

        Args:
            invoice: MIS invoice object

        Returns:
            Dictionary formatted for QuickBooks API
        """
        try:
            # Calculate amounts
            amount = float(invoice.dept or 0) - float(invoice.credit or 0)
            if amount <= 0:
                amount = float(invoice.dept or 0)  # Use debit amount if calculation results in zero/negative

            # Get fee category description
            fee_description = "Tuition Fee"  # Default
            if invoice.fee_category_rel:
                fee_description = getattr(invoice.fee_category_rel, 'name', 'Tuition Fee')
                current_app.logger.debug(f"Fee category for invoice {invoice.id}: {fee_description}")
            # Format invoice date
            invoice_date = invoice.invoice_date.strftime('%Y-%m-%d') if invoice.invoice_date else datetime.now().strftime('%Y-%m-%d')

            # Get fee category for item mapping
            if invoice.fee_category:
                category = TblIncomeCategory.get_category_by_id(invoice.fee_category)
                quickbooks_id = category['QuickBk_ctgId'] if category else None
            

            # if no category found
            if not quickbooks_id:
                current_app.logger.warning(f"No QuickBooks category ID found for invoice {invoice.id}, using default item")
                raise ValueError(f"Invoice {invoice.id} has no valid QuickBooks ItemRef mapped.")

            reg_no = invoice.reg_no
            current_app.logger.info(f"Mapping invoice {invoice.id} for student {reg_no}")


            # Attempt to find student or applicant reference by registration number
            student_ref = TblPersonalUg.get_student_by_reg_no(invoice.reg_no)
            applicant_ref = TblOnlineApplication.get_applicant_details(invoice.reg_no)
            customer_id = None
            
            # Check if the student reference exists and extract the QuickBooks customer ID
            if student_ref:
                customer_id = student_ref.qk_id
                current_app.logger.info(f"Found Student customer ID {customer_id} for student {invoice.reg_no}")

            # If no student reference, check the applicant reference
            elif applicant_ref:
                customer_id = applicant_ref.get('quickbooks_id')
                current_app.logger.info(f"Found Applicant customer ID {customer_id} for applicant {invoice.reg_no}")

            # Log a warning if no customer reference is found
            else:
                current_app.logger.warning(f"No QuickBooks customer reference found for student {invoice.reg_no}")
                raise ValueError(f"Invoice {invoice.id} has no valid QuickBooks CustomerRef mapped.")

            # Create QuickBooks invoice structure
            current_app.logger.info(f"Customer ID for invoice {invoice.id}: {customer_id}, QuickBooks Item ID: {quickbooks_id}")
            qb_invoice = {
                "Line": [
                    {
                        "Amount": float(amount),
                        "DetailType": "SalesItemLineDetail",
                        "SalesItemLineDetail": {
                            "ItemRef": {
                                "value": quickbooks_id if quickbooks_id else ''  # must exist in QB
                            },
                            "Qty": 1,
                            "UnitPrice": float(amount)
                        },
                        "Description": f"{fee_description} - {invoice.comment or 'Student Fee'}"
                    }
                ],
                "CustomerRef": {
                    "value": str(customer_id)  #str(invoice.quickbooks_customer_id)  # must exist in QB
                },
                "TxnDate": invoice_date if isinstance(invoice_date, str) else invoice_date.strftime("%Y-%m-%d"),
                "DocNumber": f"MIS-{invoice.id}",
                "PrivateNote": f"Synchronized from MIS - Invoice ID: {invoice.id}, Student: {invoice.reg_no}",
            }


            return qb_invoice, customer_id, quickbooks_id

        except Exception as e:
            logger.error(f"Error mapping invoice {invoice.id} to QuickBooks format: {e}")
            raise

    def map_invoice_to_quickbooks_update(self, invoice: TblImvoice) -> Dict:
        """
        Map MIS invoice data to QuickBooks invoice format

        Args:
            invoice: MIS invoice object

        Returns:
            Dictionary formatted for QuickBooks API
        """
        invoice_id = getattr(invoice, 'id', None) or invoice.get('id')
        if not invoice_id:
            raise ValueError("Invoice ID is required for mapping.")
        current_app.logger.info(f"Mapping invoice for update__: {invoice}")
        try:
            # Calculate amounts
            amount = float(invoice.get('dept') or 0) - float(invoice.get('credit') or 0)
            if amount <= 0:
                amount = float(invoice.get('dept') or 0)  # Use debit amount if calculation results in zero/negative

            # Get fee category description
            fee_description = "Tuition Fee"  # Default
            if invoice.get('fee_category_rel'):
                fee_description = invoice.get('fee_category_rel', {}).get('name', 'Tuition Fee')
                current_app.logger.debug(f"Fee category for invoice {invoice.get('id')}: {fee_description}")
            # Format invoice date
            invoice_date = invoice.get('invoice_date').strftime('%Y-%m-%d') if invoice.get('invoice_date') else datetime.now().strftime('%Y-%m-%d')

            # Get fee category for item mapping
            if invoice.get('fee_category'):
                category = TblIncomeCategory.get_category_by_id(invoice.get('fee_category'))
                quickbooks_id = category.get('QuickBk_ctgId') if category else None
            

            # if no category found
            if not quickbooks_id:
                current_app.logger.warning(f"No QuickBooks category ID found for invoice {invoice.get('id')}, using default item")
                raise ValueError(f"Invoice {invoice.get('id')} has no valid QuickBooks ItemRef mapped.")

            reg_no = invoice.get('reg_no')
            current_app.logger.info(f"Mapping invoice {invoice.get('id')} for student {reg_no}")


            # Attempt to find student or applicant reference by registration number
            student_ref = TblPersonalUg.get_student_by_reg_no(invoice.get('reg_no'))
            applicant_ref = TblOnlineApplication.get_applicant_details(invoice.get('reg_no'))
            customer_id = None
            
            # Check if the student reference exists and extract the QuickBooks customer ID
            if student_ref:
                customer_id = student_ref.qk_id
                current_app.logger.info(f"Found Student customer ID {customer_id} for student {invoice.get('reg_no')}")

            # If no student reference, check the applicant reference
            elif applicant_ref:
                customer_id = applicant_ref.get('quickbooks_id')
                current_app.logger.info(f"Found Applicant customer ID {customer_id} for applicant {invoice.get('reg_no')}")

            # Log a warning if no customer reference is found
            else:
                current_app.logger.warning(f"No QuickBooks customer reference found for student {invoice.get('reg_no')}")
                raise ValueError(f"Invoice {invoice.get('id')} has no valid QuickBooks CustomerRef mapped.")

            sync_token = getattr(invoice, 'sync_token', None)
            # If sync token is missing, pull it from QuickBooks
            if not sync_token:
                invoice_qb = self._get_qb_service().get_invoice(invoice.get('quickbooks_id'))
                current_app.logger.info(f"Fetched invoice {invoice.get('id')} from QuickBooks for SyncToken retrieval: {invoice_qb}")
                sync_token = invoice_qb.get('SyncToken') if invoice_qb else None
                if not sync_token:
                    raise ValueError(f"Could not retrieve SyncToken for invoice {invoice.get('id')} from QuickBooks.")
            # Create QuickBooks invoice structure
            current_app.logger.info(f"Customer ID for invoice {invoice.get('id')}: {customer_id}, QuickBooks Item ID: {quickbooks_id}")
            qb_invoice = {
                "Line": [
                    {
                        "Amount": float(amount),
                        "DetailType": "SalesItemLineDetail",
                        "SalesItemLineDetail": {
                            "ItemRef": {
                                "value": quickbooks_id if quickbooks_id else ''  # must exist in QB
                            },
                            "Qty": 1,
                            "UnitPrice": float(amount)
                        },
                        "Description": f"{fee_description} - {invoice.comment or 'Student Fee'}"
                    }
                ],
                "CustomerRef": {
                    "value": str(customer_id)  #str(invoice.quickbooks_customer_id)  # must exist in QB
                },
                "TxnDate": invoice_date if isinstance(invoice_date, str) else invoice_date.strftime("%Y-%m-%d"),
                "SyncToken": f"{sync_token}",
                "PrivateNote": f"Synchronized from MIS - Invoice ID: {invoice.get('id')}, Student: {invoice.get('reg_no')}",
            }


            return qb_invoice, customer_id, quickbooks_id

        except Exception as e:
            logger.error(f"Error mapping invoice {invoice.get('id')} to QuickBooks format: {e}")
            raise


    def sync_single_invoice(self, invoice: TblImvoice) -> SyncResult:
        """
        Synchronize a single invoice to QuickBooks

        Args:
            invoice: MIS invoice object to synchronize

        Returns:
            SyncResult: Result of the synchronization attempt
        """
        """
        if invoice.quickbooks_id:
            logger.info(f"Invoice {invoice.id} already synced with QuickBooks ID {invoice.quickbooks_id}")
            raise Exception(f"Invoice {invoice.id} is already synchronized with QuickBooks.")
        """
        try:
            # Mark invoice as in progress
            current_app.logger.info(f"Invoice data: {invoice}")
            self._update_invoice_sync_status(invoice.id, SyncStatus.IN_PROGRESS.value)

            # Get QuickBooks service
            qb_service = self._get_qb_service()

            # Map invoice data
            qb_invoice_data = self.map_invoice_to_quickbooks(invoice)[0]

            qb_item_id = self.map_invoice_to_quickbooks(invoice)[2]
            if not qb_item_id:
                raise ValueError(f"Invoice {invoice.id} has no valid QuickBooks ItemRef mapped.")
            
            qb_customer_id = self.map_invoice_to_quickbooks(invoice)[1]
            if not qb_customer_id:
                raise ValueError(f"Invoice {invoice.id} has no valid QuickBooks CustomerRef mapped.")

            

            # Create invoice in QuickBooks
            response = qb_service.create_invoice(qb_service.realm_id, qb_invoice_data)

            if 'Invoice' in response:
                # Success - update sync status
                qb_invoice_id = response['Invoice']['Id']
                self._update_invoice_sync_status(
                    invoice.id,
                    SyncStatus.SYNCED.value,
                    quickbooks_id=qb_invoice_id
                )

                # Log successful sync
                self._log_sync_audit(invoice.id, 'SUCCESS', f"Synced to QuickBooks ID: {qb_invoice_id}")

                return SyncResult(
                    invoice_id=invoice.id,
                    success=True,
                    quickbooks_id=qb_invoice_id,
                    details=response
                )
            else:
                # Handle API error
                error_msg = response.get('Fault', {}).get('Error', [{}])[0].get('Detail', 'Unknown error')
                self._update_invoice_sync_status(invoice.id, SyncStatus.FAILED.value)
                self._log_sync_audit(invoice.id, 'ERROR', error_msg)

                return SyncResult(
                    invoice_id=invoice.id,
                    success=False,
                    error_message=error_msg,
                    details=response
                )

        except Exception as e:
            # Handle exception
            error_msg = str(e)
            self._update_invoice_sync_status(invoice.id, SyncStatus.FAILED.value)
            self._log_sync_audit(invoice.id, 'ERROR', error_msg)

            return SyncResult(
                invoice_id=invoice.id,
                success=False,
                error_message=error_msg
            )

    def update_single_invoice(self, invoice):
        """
        Update a single invoice in QuickBooks

        Args:
            invoice: MIS invoice object to update

        Returns:
            SyncResult: Result of the update attempt
        """
        quickbooks_id = getattr(invoice, 'quickbooks_id', None) or invoice.get('quickbooks_id')
        if not quickbooks_id:
            return SyncResult(False, "Missing QuickBooks ID for update")

        sync_token = getattr(invoice, 'sync_token', None) or invoice.get('sync_token')
        if not sync_token:
            current_app.logger.info(f"Fetching SyncToken for invoice {invoice.get('id')}")
        current_app.logger.info(f"Invoice data for update: {invoice}")
        if not invoice.get('quickbooks_id'):
            logger.info(f"Invoice {invoice.get('id')} has not been synced yet, cannot update.")
            raise Exception(f"Invoice {invoice.get('id')} has not been synchronized with QuickBooks yet.")

        try:
            # Mark invoice as in progress
            current_app.logger.info(f"Invoice data: {invoice}")
            self._update_invoice_sync_status(invoice.get('id'), SyncStatus.IN_PROGRESS.value)
            # Get QuickBooks service
            qb_service = self._get_qb_service()

            # Map invoice data for update
            qb_invoice_data = self.map_invoice_to_quickbooks_update(invoice)[0]
            qb_item_id = self.map_invoice_to_quickbooks_update(invoice)[2]
            if not qb_item_id:
                raise ValueError(f"Invoice {invoice.get('id')} has no valid QuickBooks ItemRef mapped.")
            
            qb_customer_id = self.map_invoice_to_quickbooks_update(invoice)[1]
            if not qb_customer_id:
                raise ValueError(f"Invoice {invoice.get('id')} has no valid QuickBooks CustomerRef mapped.")

            # Update invoice in QuickBooks
            response = qb_service.update_invoice(realm_id=qb_service.realm_id, invoice_data=qb_invoice_data)
            
            if 'Invoice' in response:
                # Success - update sync status
                qb_invoice_id = response['Invoice']['Id']
                self._update_invoice_sync_status(
                    invoice.get('id'),
                    SyncStatus.SYNCED.value,
                    quickbooks_id=qb_invoice_id
                )

                # Log successful sync
                self._log_sync_audit(invoice.get('id'), 'SUCCESS', f"Updated in QuickBooks ID: {qb_invoice_id}")

                return SyncResult(
                    invoice_id=invoice.get('id'),
                    success=True,
                    quickbooks_id=qb_invoice_id,
                    details=response
                )
            else:
                # Handle API error
                error_msg = response.get('Fault', {}).get('Error', [{}])[0].get('Detail', 'Unknown error')
                self._update_invoice_sync_status(invoice.get('id'), SyncStatus.FAILED.value)
                self._log_sync_audit(invoice.get('id'), 'ERROR', error_msg)

                return SyncResult(
                    invoice_id=invoice.get('id'),
                    success=False,
                    error_message=error_msg,
                    details=response
                )
        except Exception as e:
            # Handle exception
            error_msg = str(e)
            self._update_invoice_sync_status(invoice.get('id'), SyncStatus.FAILED.value)
            self._log_sync_audit(invoice.get('id'), 'ERROR', error_msg)

            return SyncResult(
                invoice_id=invoice.get('id'),
                success=False,
                error_message=error_msg
            )

    def sync_invoices_batch(self, batch_size: Optional[int] = None) -> Dict:
        """
        Synchronize invoices in batches

        Args:
            batch_size: Number of invoices to process in each batch

        Returns:
            Dictionary with synchronization results and statistics
        """
        batch_size = batch_size or self.batch_size
        results = {
            'total_processed': 0,
            'successful': 0,
            'failed': 0,
            'errors': [],
            'success_details': []
        }

        try:
            # Get unsynchronized invoices
            invoices = self.get_unsynchronized_invoices(limit=batch_size)

            if not invoices:
                logger.info("No unsynchronized invoices found")
                return results

            logger.info(f"Starting batch synchronization of {len(invoices)} invoices")

            for invoice in invoices:
                try:
                    result = self.sync_single_invoice(invoice)
                    results['total_processed'] += 1

                    if result.success:
                        results['successful'] += 1
                        results['success_details'].append({
                            'invoice_id': result.invoice_id,
                            'quickbooks_id': result.quickbooks_id
                        })
                        logger.info(f"Successfully synced invoice {result.invoice_id}")
                    else:
                        results['failed'] += 1
                        results['errors'].append({
                            'invoice_id': result.invoice_id,
                            'error': result.error_message
                        })
                        logger.error(f"Failed to sync invoice {result.invoice_id}: {result.error_message}")

                    # Add delay between requests to avoid rate limiting
                    time.sleep(0.5)

                except Exception as e:
                    results['failed'] += 1
                    results['errors'].append({
                        'invoice_id': invoice.id,
                        'error': str(e)
                    })
                    logger.error(f"Exception syncing invoice {invoice.id}: {e}")

            logger.info(f"Batch sync completed: {results['successful']} successful, {results['failed']} failed")
            return results

        except Exception as e:
            logger.error(f"Error in batch synchronization: {e}")
            results['errors'].append({'general_error': str(e)})
            return results

    def _update_invoice_sync_status(self, invoice_id: int, status: int, quickbooks_id: Optional[int] = None):
        """
        Update invoice synchronization status in MIS database

        Args:
            invoice_id: MIS invoice ID
            status: Sync status (0=not synced, 1=synced, 2=failed, 3=in progress)
            quickbooks_id: QuickBooks invoice ID if successfully synced
        """
        try:
            with db_manager.get_mis_session() as session:
                invoice = session.query(TblImvoice).filter(TblImvoice.id == invoice_id).first()
                if invoice:
                    invoice.QuickBk_Status = status
                    invoice.pushed_date = datetime.now()
                    invoice.pushed_by = "InvoiceSyncService",
                    invoice.quickbooks_id = quickbooks_id if quickbooks_id else invoice.quickbooks_id

                # Store QuickBooks ID in a custom field or comment if needed
                if quickbooks_id and status == SyncStatus.SYNCED.value:
                    current_comment = invoice.comment or ""
                    if "QB_ID:" not in current_comment:
                        invoice.comment = f"{current_comment} [QB_ID:{quickbooks_id}]".strip()
                session.commit()
                logger.info(f"Updated invoice {invoice_id} sync status to {status}")

        except Exception as e:
            logger.error(f"Error updating invoice sync status: {e}")
            if 'session' in locals():
                session.rollback()
            raise
        finally:
            if 'session' in locals():
                session.close()

    def _log_sync_audit(self, invoice_id: int, action: str, details: str):
        """
        Log synchronization audit trail

        Args:
            invoice_id: MIS invoice ID
            action: Action performed (SUCCESS, ERROR, etc.)
            details: Additional details about the action
        """
        try:
            audit_log = QuickbooksAuditLog(
                action_type=f"INVOICE_SYNC_{action}",
                error_message=f"Invoice ID: {invoice_id} - {details}",
                operation_status="Completed" if action == "SUCCESS" else "Failed",
                request_payload="N/A",
                response_payload="N/A",
            )
            db.session.add(audit_log)
            db.session.commit()

        except Exception as e:
            logger.error(f"Error logging sync audit: {e}")
            if db.session:
                db.session.rollback()

    def sync_all_invoices(self, max_batches: Optional[int] = None) -> Dict:
        """
        Synchronize all unsynchronized invoices in batches

        Args:
            max_batches: Maximum number of batches to process (None for unlimited)

        Returns:
            Dictionary with overall synchronization results
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

        try:
            batch_count = 0
            while True:
                # Check if we've reached max batches
                if max_batches and batch_count >= max_batches:
                    logger.info(f"Reached maximum batch limit: {max_batches}")
                    break

                # Process next batch
                batch_result = self.sync_invoices_batch()

                # If no invoices were processed, we're done
                if batch_result['total_processed'] == 0:
                    logger.info("No more invoices to synchronize")
                    break

                # Update overall results
                batch_count += 1
                overall_results['batches_processed'] = batch_count
                overall_results['total_processed'] += batch_result['total_processed']
                overall_results['total_successful'] += batch_result['successful']
                overall_results['total_failed'] += batch_result['failed']
                overall_results['batch_results'].append({
                    'batch_number': batch_count,
                    'result': batch_result
                })

                logger.info(f"Completed batch {batch_count}: {batch_result['successful']} successful, {batch_result['failed']} failed")

                # Add delay between batches
                time.sleep(2)

            overall_results['end_time'] = datetime.now()
            duration = overall_results['end_time'] - overall_results['start_time']

            logger.info(f"Invoice synchronization completed: {overall_results['total_successful']} successful, "
                       f"{overall_results['total_failed']} failed in {duration}")

            return overall_results

        except Exception as e:
            logger.error(f"Error in full synchronization: {e}")
            overall_results['end_time'] = datetime.now()
            overall_results['error'] = str(e)
            return overall_results
