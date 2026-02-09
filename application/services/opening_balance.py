import logging
import os
from typing import Optional
from enum import Enum
from flask import current_app, jsonify
from application.models.mis_models import Payment, TblIncomeCategory, TblPersonalUg, TblStudentWallet, TblBank, TblRegisterProgramUg,TblImvoice, TblCampus, TblOnlineApplication, TblStudentWalletLedger
from application.services.quickbooks import QuickBooks
import traceback
from application.models.central_models import QuickBooksConfig, QuickbooksAuditLog
from datetime import datetime
import json
from application.helpers.json_encoder import EnhancedJSONEncoder
from application.utils.database import db_manager
import re
from sqlalchemy import extract

from sqlalchemy import extract, func
from flask import jsonify
import traceback

class OpeningBalanceSyncService:
    """
    Service to handle syncing of opening balance to QuickBooks
    """

    def __init__(self, logger=None):
        self.logger = logger or current_app.logger

    def get_outstanding_balance(self, reg_no: str):
        """
        Fetch total amount from 2024 invoices and payments for a given reg_no
        and return a JSON with totals and outstanding balance
        """
        try:
            with db_manager.get_mis_session() as session:
                # Total invoices for 2024
                invoice_total = (
                    session.query(func.coalesce(func.sum(TblImvoice.dept), 0))
                    .filter(
                        TblImvoice.reg_no == reg_no,
                        extract('year', TblImvoice.invoice_date) == 2024
                    )
                    .scalar()
                )

                # Total payments for 2024
                payment_total = (
                    session.query(func.coalesce(func.sum(Payment.amount), 0))
                    .filter(
                        Payment.reg_no == reg_no,
                        extract('year', Payment.recorded_date) == 2024
                    )
                    .scalar()
                )

                outstanding_balance = invoice_total - payment_total
                # update the opening balance in the database for reference
                # Fetch student record using the same session
                student = session.query(TblPersonalUg).filter_by(reg_no=reg_no).first()
                if not student:
                    student = session.query(TblOnlineApplication).filter_by(reg_no=reg_no).first()

                if student:
                    student.opening_balance = outstanding_balance
                    session.commit()  # now this will persist
                    
            result = {
                "reg_no": reg_no,
                "invoice_total_2024": float(invoice_total),
                "payment_total_2024": float(payment_total),
                "outstanding_balance": float(outstanding_balance)
            }

            self.logger.info(
                f"[OpeningBalanceSyncService] Outstanding balance for {reg_no}: {outstanding_balance}"
            )
            return jsonify(result)

        except Exception as e:
            self.logger.error(
                f"[OpeningBalanceSyncService] Error fetching outstanding balance for {reg_no}: {str(e)}\n{traceback.format_exc()}"
            )
            return jsonify({
                "reg_no": reg_no,
                "error": "Failed to fetch outstanding balance"
            }), 500
