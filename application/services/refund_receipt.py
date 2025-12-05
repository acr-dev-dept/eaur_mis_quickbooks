from application.models.mis_models import TblIncomeCategory
from application.services.quickbooks import QuickBooks, QuickBooksConfig
from flask import current_app

class RefundReceiptService:
    """Service to create refund receipts in QuickBooks."""

    def __init__(self):
        self.qb = QuickBooks()

    def _get_qb_service(self):
        """Retrieve QuickBooks service instance."""
        if not self.qb_service:
            if not QuickBooksConfig.is_connected():
                raise Exception("QuickBooks is not connected. Please authenticate first.")
            self.qb_service = QuickBooks()
        return self.qb_service
    
    def map_refund_receipt_data(self, refund_data: dict) -> dict:
        """
        Map refund data to QuickBooks refund receipt format.

        Args:
            refund_data (dict): Refund data from MIS

        Returns:
            dict: Mapped refund receipt data for QuickBooks
        """
        mapped_data = {
            "CustomerRef": {
                "value": refund_data['customer_qb_id'],
            },
            "TotalAmt": refund_data['amount'],
            "Line": [
                {
                    "DetailType": "SalesItemLineDetail",
                    "Amount": 10000.00,
                    "SalesItemLineDetail": {
                        "ItemRef": {
                            "value": refund_data['item_qb_id'],
                        },
                        "Qty": 1,
                        "UnitPrice": refund_data['amount'],
                    }
                }
            ],
            "PaymentMethodRef": {
                "value": refund_data['payment_method_qb_id'],
            },
            "TxnDate": refund_data['refund_date'].strftime('%Y-%m-%d'),
            "Memo": refund_data.get('memo', 'Refund Receipt'),
        }
        return mapped_data
    
    def create_refund_receipt(self, refund_data: dict) -> dict:
        """
        Create a refund receipt in QuickBooks.

        Args:
            refund_data (dict): Refund data from MIS
        Returns:
            dict: Result from QuickBooks API
        """
        qb_service = self._get_qb_service()
        mapped_data = self.map_refund_receipt_data(refund_data)
        
        current_app.logger.info(f"Creating refund receipt for customer {refund_data['customer_qb_id']} with amount {refund_data['amount']}")
        
        result = qb_service.create_refund_receipt(qb_service.realm_id, mapped_data)
        
        if 'Fault' in result:
            current_app.logger.error(f"Failed to create refund receipt: {result['Fault']['Error'][0]['Message']}")
        else:
            current_app.logger.info(f"Successfully created refund receipt with ID: {result['RefundReceipt']['Id']}")
        
        return result