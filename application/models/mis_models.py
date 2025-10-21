"""
MIS Database Models for EAUR MIS-QuickBooks Integration

Auto-generated from database analysis on 2025-08-22 13:21:06
These models represent the existing MIS database structure.

DO NOT MODIFY THIS FILE MANUALLY - it will be regenerated when the database schema changes.
"""

from datetime import datetime
from sqlalchemy import  DateTime, ForeignKey, Text, Boolean, Float, func
from sqlalchemy.types import Numeric
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from application.utils.database import db_manager
from application import db
from sqlalchemy import or_, and_
from sqlalchemy.orm import joinedload, foreign
from flask import current_app
from sqlalchemy import cast, String



class MISBaseModel(db.Model):
    """Base model for MIS database tables"""
    __abstract__ = True

    @classmethod
    def get_session(cls):
        """Get database session for MIS database"""
        return db_manager.get_mis_session()

    @classmethod
    def get_by_id(cls, id_value):
        """Get record by primary key"""
        try:
            with cls.get_session() as session:
                pk_col = list(cls.__table__.primary_key.columns)[0]
                return session.query(cls).filter(pk_col == id_value).first()
        except Exception as e:
            from flask import current_app
            current_app.logger.error(
                f"Error getting {cls.__name__} by ID {id_value}: {str(e)}"
            )
            return None

    def to_dict(self):
        """
        Convert model to dictionary for JSON responses
        """
        result = {}
        for column in self.__table__.columns:
            value = getattr(self, column.name)
            if isinstance(value, datetime):
                result[column.name] = value.isoformat()
            else:
                result[column.name] = value
        return result


    @classmethod
    def get_active_records(cls):
        """
        Get only active/valid records

        Returns:
            list: List of active records
        """
        try:
            with cls.get_session() as session:
                query = session.query(cls)
                # Check if model has status or active field
                if hasattr(cls, 'status_Id'):
                    query = query.filter(cls.status_Id == 1)
                elif hasattr(cls, 'statusId'):
                    query = query.filter(cls.statusId == 1)
                elif hasattr(cls, 'is_active'):
                    query = query.filter(cls.is_active == True)
                return query.all()
        except Exception as e:
            from flask import current_app
            current_app.logger.error(f"Error getting active {cls.__name__} records: {str(e)}")
            return []

class Modules(MISBaseModel):
    """Model for modules table"""
    __tablename__ = 'modules'    
    module_id = db.Column(db.Integer, nullable=False, primary_key=True)
    moduleType_Id = db.Column(db.Integer, nullable=False)
    module_categoryId = db.Column(db.Integer, nullable=False)
    acad_cycle_id = db.Column(db.Integer)
    curculum_Id = db.Column(db.Integer, nullable=False)
    level_id = db.Column(db.Integer, nullable=False)
    splz_id = db.Column(db.Integer, nullable=False)
    module_code = db.Column(db.String(15), nullable=False)
    module_name = db.Column(db.String(70), nullable=False)
    module_credits = db.Column(db.String(255), nullable=False)
    module_hours = db.Column(db.String(255))
    time = db.Column(db.String(255))
    recorded_date = db.Column(DateTime)
    user_id = db.Column(db.String(20), nullable=False)
    status_Id = db.Column(db.Integer, nullable=False)
    Situation = db.Column(db.String(50))

    # Relationships will be added after analyzing foreign keys

    def __repr__(self):
        return f'<Modules {self.id if hasattr(self, "id") else "unknown"}>'

    def to_dict(self):
        """
        Convert model to dictionary for JSON responses

        Returns:
            dict: Model data as dictionary
        """
        return {
            'module_id': self.module_id,
            'moduleType_Id': self.moduleType_Id,
            'module_categoryId': self.module_categoryId,
            'acad_cycle_id': self.acad_cycle_id,
            'curculum_Id': self.curculum_Id,
            'level_id': self.level_id,
            'splz_id': self.splz_id,
            'module_code': self.module_code,
            'module_name': self.module_name,
            'module_credits': self.module_credits,
            'module_hours': self.module_hours,
            'time': self.time,
            'recorded_date': self.recorded_date.isoformat() if self.recorded_date else None,
            'user_id': self.user_id,
            'status_Id': self.status_Id,
            'Situation': self.Situation
        }

class Payment(MISBaseModel):
    """Model for payment table"""
    __tablename__ = 'payment'
    
    id = db.Column(db.Integer, nullable=False, primary_key=True)
    trans_code = db.Column(db.String(200), unique=True)
    reg_no = db.Column(db.String(200))
    appl_Id = db.Column(db.Integer, ForeignKey("tbl_online_application.appl_Id"))
    level_id = db.Column(db.Integer, ForeignKey("tbl_level.level_id"))
    bank_id = db.Column(db.Integer, ForeignKey("tbl_bank.bank_id"))
    slip_no = db.Column(db.String(200), unique=True)
    user = db.Column(db.String(20))
    acad_cycle_id = db.Column(db.String(100))
    date = db.Column(db.String(50))
    fee_category = db.Column(db.Integer, ForeignKey("tbl_income_category.id"))
    amount = db.Column(Float)
    description = db.Column(Text)
    recorded_date = db.Column(DateTime, server_default=func.now())
    Remark = db.Column(db.String(200))
    action = db.Column(db.String(100))
    external_transaction_id = db.Column(Text, unique=True)
    payment_chanel = db.Column(db.String(100))
    payment_notifi = db.Column(db.String(100))
    invoi_ref = db.Column(db.String(255))
    QuickBk_status = db.Column(db.Integer, default='0')
    pushed_by = db.Column(db.String(200))
    pushed_date = db.Column(DateTime)
    qk_id = db.Column(db.String(255))  # QuickBooks Payment ID

    # Relationships
    level = relationship("TblLevel", backref="payments", lazy='joined')
    bank = relationship("TblBank", backref="payments", lazy='joined')
    fee_category_rel = relationship("TblIncomeCategory", backref="payments", lazy='joined')
    online_application = relationship("TblOnlineApplication", backref="payments", lazy='joined')


    def __repr__(self):
        return f'<Payment {self.id if hasattr(self, "id") else "unknown"}>'

    def to_dict(self):
        """
        Convert model to dictionary for JSON responses

        Returns:
            dict: Model data as dictionary
        """
        return {
            'id': self.id,
            'trans_code': self.trans_code,
            'reg_no': self.reg_no,
            'appl_Id': self.appl_Id,
            'application_details': self.online_application.to_dict() if self.online_application else [],
            'level_id': self.level_id,
            'level_details': self.level.to_dict() if self.level else [],
            'bank_id': self.bank_id,
            'bank_details': self.bank.to_dict() if self.bank else [],
            'slip_no': self.slip_no,
            'user': self.user,
            'acad_cycle_id': self.acad_cycle_id,
            'date': self.date,
            'fee_category': self.fee_category,
            'fee_category_details': self.fee_category_rel.to_dict() if self.fee_category_rel else [],
            'amount': self.amount,
            'description': self.description,
            'recorded_date': self.recorded_date.isoformat() if self.recorded_date else None,
            'Remark': self.Remark,
            'action': self.action,
            'external_transaction_id': self.external_transaction_id,
            'payment_chanel': self.payment_chanel,
            'payment_notifi': self.payment_notifi,
            'invoi_ref': self.invoi_ref,
            'QuickBk_Status': self.QuickBk_Status,
            'pushed_by': self.pushed_by,
            'pushed_date': self.pushed_date.isoformat() if self.pushed_date else None,
            'qk_id': self.qk_id
        }
    
    @classmethod
    def get_payment_details_by_external_id(cls, external_transaction_id):
        """
        Get detailed payment information by external transaction ID

        Args:
            external_transaction_id (str): External transaction ID

        Returns:
            dict: Payment details or None if not found
        """
        try:
            with cls.get_session() as session:
                payment = session.query(cls).filter(cls.external_transaction_id == external_transaction_id).first()
                if payment:
                    return payment
                return []
        except Exception as e:
            from flask import current_app
            current_app.logger.error(f"Error getting payment details for transaction ID {external_transaction_id}: {str(e)}")
            return None
        

    @classmethod
    def create_payment(cls, **kwargs):
        """
        Create a new payment record

        Args:
            kwargs: Payment fields

        Returns:
            Payment: Created payment record
        """
        try:
            with cls.get_session() as session:
                payment = cls(**kwargs)
                session.add(payment)
                session.commit()
                return payment.to_dict()
        except Exception as e:
            from flask import current_app
            current_app.logger.error(f"Error creating payment: {str(e)}")
            return []
        
    @classmethod
    def get_payment_by_id(cls, payment_id):
        """
        Get payment by ID

        Args:
            payment_id (int): Payment ID

        Returns:
            Payment: Payment record or None if not found
        """
        try:
            with cls.get_session() as session:
                payment = session.query(cls).filter(cls.id == payment_id).first()
                return payment
        except Exception as e:
            from flask import current_app
            current_app.logger.error(f"Error getting payment for ID {payment_id}: {str(e)}")
            return None
    @staticmethod
    def count_payments():
        """Count total payments"""
        try:
            with MISBaseModel.get_session() as session:
                return session.query(func.count(Payment.id)).scalar()
        except Exception as e:
            from flask import current_app
            current_app.logger.error(f"Error counting payments: {str(e)}")
            return 0

    @staticmethod
    def count_synced_payments():
        """Count total payments synced to QuickBooks"""
        try:
            with MISBaseModel.get_session() as session:
                return session.query(func.count(Payment.id)).filter(Payment.QuickBk_Status == 1, Payment.qk_id != None).scalar()
        except Exception as e:
            from flask import current_app
            current_app.logger.error(f"Error counting synced payments: {str(e)}")
            return 0

    @staticmethod
    def fetch_paginated_payments(start: int = 0, length: int = 50, search=None):
        """Fetch payments with pagination for DataTables server-side"""
        try:
            with MISBaseModel.get_session() as session:
                query = session.query(
                    Payment.id,
                    Payment.reg_no,
                    Payment.amount,
                    Payment.external_transaction_id,
                    Payment.date,
                    Payment.QuickBk_Status,
                    Payment.pushed_by,
                    Payment.pushed_date,
                    Payment.invoi_ref,
                    Payment.qk_id
                )

                total_payments = session.query(func.count(Payment.id)).scalar()

                # Status mapping
                mapping = {
                    "synced": {
                        "QuickBk_Status": 1,
                        "qk_id_not_null": True
                    },
                    "unsynced": {
                        "qk_id_not_null": False,
                    },
                    "failed": {
                        "QuickBk_Status": [2, 3],
                        "qk_id_not_null": False
                    }
                }

                # Optional search filter
                if search:
                    search_str = str(search).strip().lower()

                    if search_str in mapping:  
                        status_filter = mapping[search_str]
                        cond = []

                        if isinstance(status_filter["QuickBk_Status"], list):
                            cond.append(Payment.QuickBk_Status.in_(status_filter["QuickBk_Status"]))
                        else:
                            cond.append(Payment.QuickBk_Status == status_filter["QuickBk_Status"])
                        
                        # Handle qk_id null/not null
                        if status_filter.get("qk_id_not_null") is True:
                            cond.append(Payment.qk_id.isnot(None))
                        elif status_filter.get("qk_id_not_null") is False:
                            cond.append(Payment.qk_id.is_(None))

                        query = query.filter(and_(*cond))

                    elif search_str.isdigit():
                        # Direct numeric search on QuickBk_Status
                        query = query.filter(Payment.QuickBk_Status == int(search_str))
                    else:
                        # Free-text search
                        query = query.filter(
                            or_(
                                Payment.reg_no.ilike(f"%{search_str}%"),
                                Payment.external_transaction_id.ilike(f"%{search_str}%"),
                                Payment.invoi_ref.ilike(f"%{search_str}%")
                            )
                        )

                filtered_payments = query.count()
                payments = query.order_by(Payment.pushed_date.desc()).offset(start).limit(length).all()

                data = [
                    {
                        "id": pay.id,
                        "reg_no": pay.reg_no,
                        "amount": pay.amount or 0,
                        "external_transaction_id": pay.external_transaction_id or "-",
                        "date": pay.date or "-",
                        "invoi_ref": pay.invoi_ref or "-",
                        "QuickBk_Status": pay.QuickBk_Status,
                        "pushed_by": pay.pushed_by or "-",
                        "pushed_date": pay.pushed_date.isoformat() if pay.pushed_date else "-",
                        "status": (
                            "Synced" if pay.QuickBk_Status == 1 and pay.qk_id
                            else "Unsynced" if (pay.QuickBk_Status in [0, None])
                            else "Failed" if (pay.QuickBk_Status in [2, 3])
                            else "Unknown"
                        )
                    } for pay in payments
                ]
                return total_payments, filtered_payments, data

        except Exception as e:
            from flask import current_app
            current_app.logger.error(f"Error fetching paginated payments: {str(e)}")
            return 0, 0, []

class TblBank(MISBaseModel):
    """Model for tbl_bank table"""
    __tablename__ = 'tbl_bank'

    bank_id = db.Column(db.Integer, nullable=False, primary_key=True)
    bank_code = db.Column(db.String(10), nullable=False)
    bank_name = db.Column(db.String(100), nullable=False)
    bank_branch = db.Column(db.String(100), nullable=False)
    account_no = db.Column(db.String(30))
    currency = db.Column(db.String(10), nullable=False)
    status = db.Column(db.String(10), nullable=False)
    qk_id = db.Column(db.String(255))  # QuickBooks Account ID

    # QuickBooks sync tracking fields (using existing status field)
    pushed_by = db.Column(db.String(200), default='System Auto Push')
    pushed_date = db.Column(DateTime)

    # Relationships will be added after analyzing foreign keys

    def __repr__(self):
        return f'<TblBank {self.id if hasattr(self, "id") else "unknown"}>'

    def to_dict(self):
        """
        Convert model to dictionary for JSON responses

        Returns:
            dict: Model data as dictionary
        """
        return {
            'bank_id': self.bank_id,
            'bank_code': self.bank_code,
            'bank_name': self.bank_name,
            'bank_branch': self.bank_branch,
            'account_no': self.account_no,
            'currency': self.currency,
            'status': self.status,
            'qk_id': self.qk_id,
            'pushed_by': self.pushed_by,
            'pushed_date': self.pushed_date.isoformat() if self.pushed_date else None
        }

    @classmethod
    def get_bank_details(cls, bank_id):
        """
        Get detailed bank information for QuickBooks custom fields

        Args:
            bank_id (str): Bank ID

        Returns:
            dict: Bank details or None if not found
        """
        try:
            with cls.get_session() as session:
                bank = session.query(cls).filter(cls.bank_id == bank_id).first()
                return bank.to_dict() if bank else []
        except Exception as e:
            from flask import current_app
            current_app.logger.error(f"Error getting bank details for ID {bank_id}: {str(e)}")
            return []

class TblCampus(MISBaseModel):
    """Model for tbl_campus table"""
    __tablename__ = 'tbl_campus'
    
    camp_id = db.Column(db.Integer, nullable=False, primary_key=True)
    camp_full_name = db.Column(db.String(50), nullable=False)
    camp_short_name = db.Column(db.String(20), nullable=False)
    camp_city = db.Column(db.String(30), nullable=False)
    camp_yor = db.Column(DateTime, nullable=False)
    camp_active = db.Column(db.Integer, nullable=False)
    camp_comments = db.Column(db.String(255), nullable=False)

    # Relationships will be added after analyzing foreign keys

    def __repr__(self):
        return f'<TblCampus {self.camp_id}>'

    def to_dict(self):
        """
        Convert model to dictionary for JSON responses

        Returns:
            dict: Model data as dictionary
        """
        return {
            'camp_id': self.camp_id,
            'camp_full_name': self.camp_full_name,
            'camp_short_name': self.camp_short_name,
            'camp_city': self.camp_city,
            'camp_yor': self.camp_yor.isoformat() if self.camp_yor else None,
            'camp_active': self.camp_active,
            'camp_comments': self.camp_comments
        }

    @classmethod
    def get_campus_name(cls, camp_id):
        """
        Get campus name by ID

        Args:
            camp_id (str): Campus ID

        Returns:
            str: Campus full name or None if not found
        """
        try:
            with cls.get_session() as session:
                campus = session.query(cls).filter(cls.camp_id == camp_id).first()
                return campus.camp_full_name if campus else None
        except Exception as e:
            from flask import current_app
            current_app.logger.error(f"Error getting campus name for ID {camp_id}: {str(e)}")
            return None

    @classmethod
    def get_campus_details(cls, camp_id):
        """
        Get detailed campus information for QuickBooks custom fields

        Args:
            camp_id (str): Campus ID

        Returns:
            dict: Campus details or None if not found
        """
        try:
            with cls.get_session() as session:
                campus = session.query(cls).filter(cls.camp_id == camp_id).first()
                if campus:
                    return {
                        'id': campus.camp_id,
                        'full_name': campus.camp_full_name,
                        'short_name': campus.camp_short_name,
                        'city': campus.camp_city,
                        'year_opened': campus.camp_yor.isoformat() if campus.camp_yor else None,
                        'is_active': campus.camp_active == 1,
                        'comments': campus.camp_comments,
                        'display_name': f"{campus.camp_full_name} ({campus.camp_city})"
                    }
                return None
        except Exception as e:
            from flask import current_app
            current_app.logger.error(f"Error getting campus details for ID {camp_id}: {str(e)}")
            return None

    def to_quickbooks_format(self):
        """
        Format campus data for QuickBooks custom fields

        Returns:
            dict: Formatted data for QB
        """
        return {
            'Campus': self.camp_full_name,
            'CampusCity': self.camp_city,
            'CampusCode': self.camp_short_name
        }

class TblImvoice(MISBaseModel):
    """Model for tbl_imvoice table"""
    __tablename__ = 'tbl_imvoice'
    id = db.Column(db.Integer, nullable=False, primary_key=True)
    reg_no = db.Column(db.String(200))
    level_id = db.Column(db.Integer, ForeignKey("tbl_level.level_id"))
    fee_category = db.Column(db.Integer, ForeignKey("tbl_income_category.id"))
    module_id = db.Column(db.Integer, ForeignKey("modules.module_id"))
    Rpt_Id = db.Column(db.Integer)
    appl_Id = db.Column(db.Integer)
    dept = db.Column(Float)
    credit = db.Column(Float)
    balance = db.Column(db.Float, nullable=True)
    invoice_date = db.Column(DateTime)
    reference_number = db.Column(db.String(255))
    comment = db.Column(db.String(900))
    user = db.Column(db.String(20))
    date = db.Column(DateTime)
    intake_id = db.Column(db.Integer, ForeignKey("tbl_intake.intake_id"))
    QuickBk_Status = db.Column(db.Integer, default='0')
    pushed_by = db.Column(db.String(200))
    pushed_date = db.Column(DateTime)
    quickbooks_id = db.Column(db.String(255))  # To store QuickBooks Invoice ID
    sync_token = db.Column(db.String(10))  # To store QuickBooks SyncToken
    # Define relationships between levels, modules, and intakes
    # This is not implemented on database level, we need them for joins
    level = relationship("TblLevel", backref="invoices", lazy='joined')
    module = relationship("Modules", backref="invoices", lazy='joined')
    intake = relationship("TblIntake", backref="invoices", lazy='joined')
    fee_category_rel = relationship("TblIncomeCategory", backref="invoices", lazy='joined')
    online_application = relationship("TblOnlineApplication", backref="invoices", lazy='joined', primaryjoin="TblImvoice.reg_no==foreign(TblOnlineApplication.tracking_id)")
    student = relationship("TblPersonalUg", backref="invoices", lazy='joined', primaryjoin="TblImvoice.reg_no==foreign(TblPersonalUg.reg_no)")


    def __repr__(self):
        return f'<TblImvoice {self.id if hasattr(self, "id") else "unknown"}>'

    def to_dict(self):
        """
        Convert model to dictionary for JSON responses

        Returns:
            dict: Model data as dictionary
        """
        return {
            'id': self.id,
            'reg_no': self.reg_no,
            'level_id': self.level_id,
            'level_details': self.level.to_dict() if self.level else [],
            'fee_category': self.fee_category,
            'fee_category_details': self.fee_category_rel.to_dict() if self.fee_category_rel else [],
            'module_id': self.module_id,
            'module_details': self.module.to_dict() if self.module else [],
            'Rpt_Id': self.Rpt_Id,
            'dept': self.dept,
            'credit': self.credit,
            'balance': self.balance,
            'invoice_date': self.invoice_date.isoformat() if self.invoice_date else None,
            'comment': self.comment,
            'reference_number': self.reference_number,
            'appl_Id': self.appl_Id,
            'user': self.user,
            'date': self.date.isoformat() if self.date else None,
            'intake_id': self.intake_id,
            'intake_details': self.intake.to_dict() if self.intake else [],
            'QuickBk_Status': self.QuickBk_Status,
            'pushed_by': self.pushed_by,
            'pushed_date': self.pushed_date.isoformat() if self.pushed_date else None,
            'quickbooks_id': self.quickbooks_id
        }
    
    @classmethod
    def get_invoice_details(cls, reference_number):
        """
        Get detailed invoice information by reference number

        Args:
            reference_number (str): Invoice reference number

        Returns:
            dict: Invoice details or None if not found
        """
        try:
            with cls.get_session() as session:
                invoice = session.query(cls).filter(cls.reference_number == reference_number).first()
                return invoice
        except Exception as e:
            from flask import current_app
            current_app.logger.error(f"Error getting invoice details for reference {reference_number}: {str(e)}")
            return []
        
    @classmethod
    def get_invoice_balance(cls, reference_number):
        """
        Get invoice balance by reference number

        Args:
            reference_number (str): Invoice reference number

        Returns:
            float: Invoice balance or None if not found
        """
        try:
            with cls.get_session() as session:
                invoice = session.query(cls).filter(cls.reference_number == reference_number).first()
                return invoice.balance if invoice else None
        except Exception as e:
            from flask import current_app
            current_app.logger.error(f"Error getting invoice balance for reference {reference_number}: {str(e)}")
            return None
    
    @classmethod
    def update_invoice_balance(cls, reference_number, amount_paid):
        """
        Update invoice balance by reference number

        Args:
            reference_number (str): Invoice reference number
            amount_paid (float): Amount paid to deduct from balance
        Returns:
            new_balance (float): Updated invoice balance or None if not found/error
        """
        try:
            with cls.get_session() as session:
                invoice = session.query(cls).filter(cls.reference_number == reference_number).first()
                if invoice:
                    # The balance cannot be negative
                    new_balance = max(0, (invoice.balance or 0) - amount_paid)
                    invoice.balance = new_balance
                    session.commit()
                    return new_balance, invoice
                return None, None
        except Exception as e:
            from flask import current_app
            current_app.logger.error(f"Error updating invoice balance for reference {reference_number}: {str(e)}")
            return None, None
        
    @classmethod
    def get_all_invoices_associated_with_student(cls, reg_no):
        """
        Get all invoices associated with a student by registration number

        Args:
            reg_no (str): Student registration number

        Returns:
            list: List of invoice records
        """
        try:
            # get the invoices with the balance greater than zero
            with cls.get_session() as session:
                invoices = session.query(cls).filter(
                    cls.reg_no == reg_no
                ).all()
                return [invoice.to_dict() for invoice in invoices] if invoices else []
        except Exception as e:
            from flask import current_app
            current_app.logger.error(f"Error getting invoices for student {reg_no}: {str(e)}")
            return []
        
    @classmethod
    def get_all_invoices_associated_with_application(cls, appl_Id):
        """
        Get all invoices associated with an application by application ID

        Args:
            appl_Id (int): Application ID

        Returns:
            list: List of invoice records
        """
        try:
            with cls.get_session() as session:
                invoices = session.query(cls).filter(cls.appl_Id == appl_Id).all()
                return [invoice.to_dict() for invoice in invoices] if invoices else []
        except Exception as e:
            from flask import current_app
            current_app.logger.error(f"Error getting invoices for application {appl_Id}: {str(e)}")
            return []
        
    @classmethod
    def get_payer_details(cls, reference_number):
        """
        Get payer details for an invoice by reference number

        Args:
            reference_number (str): Invoice reference number
        Returns:
            dict: Payer details or None if not found
        """ 
        try:
            with cls.get_session() as session:
                invoice = session.query(cls).filter(cls.reference_number == reference_number).first()
                if invoice and invoice.online_application:
                    app = invoice.online_application
                    payer_name = f"{app.first_name} {app.middlename} {app.family_name}".strip()
                    return {
                        'payer_name': payer_name if payer_name else "Unknown Student",
                        'payer_email': app.email1 if app.email1 else "",
                    }
                return {}
        except Exception as e:
            from flask import current_app
            current_app.logger.error(f"Error getting payer details for invoice {reference_number}: {str(e)}")
            return {}
    @staticmethod
    def update_invoice_quickbooks_status(invoice_id,quickbooks_id, pushed_by, pushed_date, QuickBk_Status):
        """
        Update QuickBooks sync status for an invoice

        Args:
            invoice_id (int): Invoice ID
            quickbooks_id (str): QuickBooks invoice ID
            pushed_by (str): User who pushed the data
            pushed_date (datetime): Date when data was pushed
            QuickBk_Status (int): Sync status (0=not synced, 1=synced)
        Returns:
            bool: True if update was successful, False otherwise
        """
        try:
            with MISBaseModel.get_session() as session:
                invoice = session.query(TblImvoice).filter(TblImvoice.id == invoice_id).first()
                if invoice:
                    invoice.quickbooks_id = quickbooks_id
                    invoice.pushed_by = pushed_by
                    invoice.pushed_date = pushed_date
                    invoice.QuickBk_Status = QuickBk_Status
                    session.commit()
                    return True
                return False
        except Exception as e:
            from flask import current_app
            current_app.logger.error(f"Error updating QuickBooks status for invoice {invoice_id}: {str(e)}")
            return False
    @staticmethod
    def fetch_paginated_invoices(start: int = 0, length: int = 50, search= None):
        """Fetch invoices with pagination for DataTables server-side"""
        try:
            with MISBaseModel.get_session() as session:
                query = session.query(
                    TblImvoice.id,
                    TblImvoice.reg_no,
                    TblImvoice.balance,
                    TblImvoice.dept,
                    TblImvoice.reference_number,
                    TblImvoice.invoice_date,
                    TblImvoice.QuickBk_Status,
                    TblImvoice.pushed_by,
                    TblImvoice.pushed_date
                )
                total_records = session.query(func.count(TblImvoice.id)).scalar()
                # Optional search filter
                if search:
                    mapping = {
                        "synced": {
                            "nbr": 1,
                            "quickbooks_id_not_null": True
                        },
                        "unsynced": {
                            "nbr": 0,
                            "quickbooks_id_not_null": False
                        },
                        "failed": {
                            "nbr": 2,
                            "quickbooks_id_not_null": False
                        }
                    }

                    # normalize search
                    search_str = str(search).strip().lower()

                    if search_str in mapping:  
                        status_filter = mapping[search_str]
                        cond = [TblImvoice.QuickBk_Status == status_filter["nbr"]]

                        if status_filter["quickbooks_id_not_null"]:
                            cond.append(TblImvoice.quickbooks_id.isnot(None))
                        elif status_filter["quickbooks_id_not_null"] is False:
                            cond.append(TblImvoice.quickbooks_id.is_(None))

                        query = query.filter(*cond)
                    elif search_str.isdigit():
                        query = query.filter(TblImvoice.QuickBk_Status == int(search_str))

                    else:
                        query = query.filter(
                            TblImvoice.reg_no.ilike(f"%{search}%") |
                            TblImvoice.reference_number.ilike(f"%{search}%") |
                            cast(TblImvoice.balance, String).ilike(f"%{search}%")
                        )

                total_records = db.session.query(func.count(TblImvoice.id)).scalar()
                filtered_records = query.count()

                invoices = (
                    query.order_by(TblImvoice.id.desc())
                    .offset(start)
                    .limit(length)
                    .all()
                )

                data = [
                    {
                        "id": inv.id,
                        "reg_no": inv.reg_no,
                        "reference_number": inv.reference_number or "-",
                        "balance": inv.balance or 0,
                        "dept": inv.dept or 0,
                        "invoice_date": inv.invoice_date.isoformat() if inv.invoice_date else "-",
                        "QuickBk_Status": inv.QuickBk_Status,
                        "pushed_by": inv.pushed_by or "-",
                        "pushed_date": inv.pushed_date.isoformat() if inv.pushed_date else "-"
                    }
                    for inv in invoices
                ]

                return total_records, filtered_records, data

        except Exception as e:
            from flask import current_app
            current_app.logger.error(f"Error fetching paginated invoices: {str(e)}")
            return 0, 0, []
    @staticmethod
    def count_invoices():
        """Count total number of invoices in the database"""
        try:
            with MISBaseModel.get_session() as session:
                total_invoices = session.query(TblImvoice).count()
                return total_invoices
        except Exception as e:
            from flask import current_app
            current_app.logger.error(f"Error counting total invoices: {str(e)}")
            return 0

    @staticmethod
    def count_synced_invoices():
        """Count total number of invoices synced to QuickBooks"""
        try:
            with MISBaseModel.get_session() as session:
                synced_invoices = session.query(TblImvoice).filter(TblImvoice.QuickBk_Status == 1, TblImvoice.quickbooks_id != None).count()
                return synced_invoices
        except Exception as e:
            from flask import current_app
            current_app.logger.error(f"Error counting synced invoices: {str(e)}")
            return 0
    @staticmethod
    def get_invoice_by_id(invoice_id):
        """
        Get invoice by ID

        Args:
            invoice_id (int): Invoice ID

        Returns:
            TblImvoice: Invoice record or None if not found
        """
        try:
            with MISBaseModel.get_session() as session:
                invoice = (
                    session.query(TblImvoice)
                    .filter(TblImvoice.id == invoice_id)
                    .first()
                )
                if not invoice:
                    return None
                return invoice.to_dict()
        except Exception as e:
            from flask import current_app
            current_app.logger.error(f"Error getting invoice for ID {invoice_id}: {str(e)}")
            return None

class TblIncomeCategory(MISBaseModel):
    """Model for tbl_income_category table"""
    __tablename__ = 'tbl_income_category'

    id = db.Column(db.Integer, nullable=False, primary_key=True)
    invTypeId = db.Column(db.String, nullable=False)
    camp_id = db.Column(db.Integer, ForeignKey("tbl_campus.camp_id"))
    prg_type = db.Column(db.String, nullable=False)
    splz_id = db.Column(db.Integer, ForeignKey("tbl_specialization.splz_id"))
    name = db.Column(db.String(100), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    description = db.Column(db.String(255), nullable=False)
    recorded_date = db.Column(DateTime)
    recorded_by = db.Column(db.String(100), nullable=False)
    status_Id = db.Column(db.Integer, nullable=False)
    category = db.Column(db.String(200), nullable=False)
    QuickBk_ctgId = db.Column(db.Integer)
    Quickbk_Status = db.Column(db.Integer, default='0')
    pushed_date = db.Column(DateTime)
    pushed_by = db.Column(db.String(200))

    # Relationships 
    camp = relationship("TblCampus", backref="income_categories", lazy='joined')
    splz = relationship("TblSpecialization", backref="income_categories", lazy='joined')


    def __repr__(self):
        return f'<TblIncomeCategory {self.id if hasattr(self, "id") else "unknown"}>'

    def to_dict(self):
        """
        Convert model to dictionary for JSON responses

        Returns:
            dict: Model data as dictionary
        """
        return {
            'id': self.id,
            'invTypeId': self.invTypeId,
            'camp_id': self.camp_id,
            'camp_details': self.camp.to_dict() if self.camp else [],
            'prg_type': self.prg_type,
            'splz_id': self.splz_id,
            'splz_details': self.splz.to_dict() if self.splz else [],
            'name': self.name,
            'amount': self.amount,
            'description': self.description,
            'recorded_date': self.recorded_date.isoformat() if self.recorded_date else None,
            'recorded_by': self.recorded_by,
            'status_Id': self.status_Id,
            'category': self.category,
            'QuickBk_ctgId': self.QuickBk_ctgId,
            'Quickbk_Status': self.Quickbk_Status,
            'pushed_date': self.pushed_date.isoformat() if self.pushed_date else None,
            'pushed_by': self.pushed_by
        }
    @staticmethod
    def get_category_by_id(category_id):
        """
        Get income category by ID

        Args:
            category_id (int): Income category ID

        Returns:
            TblIncomeCategory: Income category record or None if not found
        """
        try:
            with MISBaseModel.get_session() as session:
                cat_data_obj=session.query(TblIncomeCategory).filter(TblIncomeCategory.id == category_id, TblIncomeCategory.status_Id == 1, TblIncomeCategory.Quickbk_Status == 1).first()
                cat_data_dict=cat_data_obj.to_dict() if cat_data_obj else None
                return cat_data_dict
        except Exception as e:
            from flask import current_app
            current_app.logger.error(f"Error getting income category for ID {category_id}: {str(e)}")
            return None

    @staticmethod
    def get_category_by_id_not_synced(category_id):
        """
        Get income category by ID only if not yet synced

        Args:
            category_id (int): Income category ID
        Returns:
            TblIncomeCategory: Income category record or None if not found or already synced
        """
        try:
            with MISBaseModel.get_session() as session:
                cat_data_obj=session.query(TblIncomeCategory).filter(TblIncomeCategory.id == category_id, TblIncomeCategory.status_Id == 1, or_(TblIncomeCategory.Quickbk_Status != 1, TblIncomeCategory.Quickbk_Status.is_(None))).first()
                cat_data_dict=cat_data_obj.to_dict() if cat_data_obj else None
                return cat_data_dict
        except Exception as e:
            from flask import current_app
            current_app.logger.error(f"Error getting unsynced income category for ID {category_id}: {str(e)}")
            return None

    @staticmethod
    def get_active_categories():
        """
        Get income categories with status_id = 1
        """
        try:
            with MISBaseModel.get_session() as session:
                categories = session.query(TblIncomeCategory).filter(TblIncomeCategory.status_Id == 1).all()
                return [c.to_dict() for c in categories] if categories else []
        except Exception as e:
            from flask import current_app
            current_app.logger.error(f"Error getting active income categories: {str(e)}")
            return []

    @staticmethod
    def count_active_categories():
        """
        Count income categories with status_id = 1
        """
        try:
            with MISBaseModel.get_session() as session:
                count = session.query(TblIncomeCategory).filter(TblIncomeCategory.status_Id == 1).count()
                return count
        except Exception as e:
            from flask import current_app
            current_app.logger.error(f"Error counting active income categories: {str(e)}")
            return 0
    @staticmethod
    def update_quickbooks_status(category_id, quickbooks_id, pushed_by):
        """
        Update QuickBooks sync status for an income category

        Args:
            category_id (int): Income category ID
            quickbooks_id (int): QuickBooks category ID
            pushed_by (str): User who pushed the data
        Returns:
            bool: True if update was successful, False otherwise
        """
        try:
            with MISBaseModel.get_session() as session:
                category = session.query(TblIncomeCategory).filter(TblIncomeCategory.id == category_id).first()
                if category:
                    category.QuickBk_ctgId = quickbooks_id
                    category.Quickbk_Status = 1  # Mark as synced
                    category.pushed_by = pushed_by
                    category.pushed_date = datetime.utcnow()
                    session.commit()
                    return True
                return False
        except Exception as e:
            from flask import current_app
            current_app.logger.error(f"Error updating QuickBooks status for income category {category_id}: {str(e)}")
            return False
    @staticmethod
    def get_unsynced_categories():
        try:
            with MISBaseModel.get_session() as session:
                # Fetch categories that are active and not yet synced
                unsynced_categories = session.query(TblIncomeCategory).filter(
                    or_(
                        TblIncomeCategory.Quickbk_Status != 1,  # not pushed
                        TblIncomeCategory.Quickbk_Status.is_(None),  # not synced
                    ),
                    TblIncomeCategory.status_Id == 1        # active
                ).all()
                
                return [c.to_dict() for c in unsynced_categories] if unsynced_categories else []
        except Exception as e:
            from flask import current_app
            current_app.logger.error(f"Error getting unsynced income categories: {str(e)}")
            return []
    @staticmethod
    def count_synced_categories():
        """Count income categories that have been synced to QuickBooks"""
        try:
            with MISBaseModel.get_session() as session:
                count = session.query(TblIncomeCategory).filter(TblIncomeCategory.Quickbk_Status == 1).count()
                return count
        except Exception as e:
            from flask import current_app
            current_app.logger.error(f"Error counting synced income categories: {str(e)}")
            return 0

    @staticmethod
    def fetch_paginated_categories(start: int = 0, length: int = 50, search: str = None):
        """Fetch income categories with pagination for DataTables server-side"""
        try:
            with MISBaseModel.get_session() as session:
                query = session.query(
                    TblIncomeCategory.id,
                    TblIncomeCategory.name,
                    TblIncomeCategory.amount,
                    TblIncomeCategory.status_Id,
                    TblIncomeCategory.Quickbk_Status,
                    TblIncomeCategory.pushed_by,
                    TblIncomeCategory.pushed_date
                )

                if search:
                    query = query.filter(
                        TblIncomeCategory.name.ilike(f"%{search}%") |
                        TblIncomeCategory.description.ilike(f"%{search}%")
                    )
                total_categories = session.query(TblIncomeCategory.id).count()
                filtered_categories = query.count()
                categories = query.order_by(TblIncomeCategory.name.asc()).offset(start).limit(length).all()
                data = [
                    {
                        "id": cat.id,
                        "name": cat.name,
                        "amount": cat.amount or 0,
                        "status_Id": cat.status_Id,
                        "Quickbk_Status": cat.Quickbk_Status,
                        "pushed_by": cat.pushed_by or "-",
                        "pushed_date": cat.pushed_date.isoformat() if cat.pushed_date else "-"
                    } for cat in categories
                ]
                return total_categories, filtered_categories, data

        except Exception as e:
            from flask import current_app
            current_app.logger.error(f"Error fetching paginated income categories: {str(e)}")
            return 0, 0, []

class TblLevel(MISBaseModel):
    """Model for tbl_level table"""
    __tablename__ = 'tbl_level'
    
    level_id = db.Column(db.Integer, nullable=False, primary_key=True)
    level_no = db.Column(db.String(20), nullable=False)
    level_full_name = db.Column(db.String(50), nullable=False)
    level_short_name = db.Column(db.String(10), nullable=False)
    amount = db.Column(db.String(20), nullable=False)
    level_exit_award = db.Column(db.String(255), nullable=False)
    status = db.Column(db.Integer, nullable=False)

    # Relationships will be added after analyzing foreign keys

    def __repr__(self):
        return f'<TblLevel {self.id if hasattr(self, "id") else "unknown"}>'

    def to_dict(self):
        """
        Convert model to dictionary for JSON responses

        Returns:
            dict: Model data as dictionary
        """
        return {
            'level_id': self.level_id,
            'level_no': self.level_no,
            'level_full_name': self.level_full_name,
            'level_short_name': self.level_short_name,
            'amount': self.amount,
            'level_exit_award': self.level_exit_award,
            'status': self.status
        }

class TblOnlineApplication(MISBaseModel):
    """Model for tbl_online_application table"""
    __tablename__ = 'tbl_online_application'

    appl_Id = db.Column(db.Integer, nullable=False, primary_key=True)
    tracking_id = db.Column(db.String(200))
    reg_no = db.Column(db.String(200))
    first_name = db.Column(db.String(200))
    middlename = db.Column(db.String(200))
    family_name = db.Column(db.String(200))
    dob = db.Column(DateTime)
    sex = db.Column(db.String(6))
    phone1 = db.Column(db.String(50))
    email1 = db.Column(db.String(100))
    country_of_birth = db.Column(db.String)
    nation_Id_passPort_no = db.Column(db.String(200))
    present_nationality = db.Column(db.String(255))
    sector = db.Column(db.String(255))
    father_name = db.Column(db.String(500))
    mother_name = db.Column(db.String(500))
    guardian_phone = db.Column(db.String(50))
    serious_illness = db.Column(db.String(20))
    serious_illness_comment = db.Column(Text)

    # QuickBooks sync tracking fields
    QuickBk_status = db.Column(db.Integer, default=0, nullable=True)  # 0=not synced, 1=synced, 2=failed, 3=in progress
    pushed_by = db.Column(db.String(200), default='System Auto Push', nullable=True)
    pushed_date = db.Column(DateTime, nullable=True)
    blood_pressure = db.Column(db.String(20))
    diabetes = db.Column(db.String(20))
    high_school_name = db.Column(db.String(500))
    combination = db.Column(db.String(500))
    completed_year = db.Column(db.String(155))
    school_categ_Id = db.Column(db.String(155))
    index_number = db.Column(db.String(200))
    grade_marks = db.Column(db.String(200))
    principle_passes = db.Column(db.String(300))
    n_principle_passes = db.Column(db.String(155))
    camp_id = db.Column(db.String(155))
    opt_1 = db.Column(db.String(155))
    opt_2 = db.Column(db.String(155))
    opt_3 = db.Column(db.String(155))
    opt_oriented = db.Column(db.String(155))
    intake_id = db.Column(db.Integer, ForeignKey("tbl_intake.intake_id"))
    level_id = db.Column(db.Integer)
    prg_mode_id = db.Column(db.Integer)
    spon_id = db.Column(db.Integer)
    StdentTrnsfr = db.Column(db.String(20))
    about_Id = db.Column(db.String(100))
    appl_date = db.Column(DateTime)
    NID_doc = db.Column(db.String(1000))
    highSchool_doc = db.Column(db.String(1000))
    transcript_doc = db.Column(db.String(1000))
    HoD_comment = db.Column(Text)
    HoD_user = db.Column(db.String(200))
    HoD_resp_date = db.Column(DateTime)
    respont_by = db.Column(db.String(100))
    response_date = db.Column(DateTime)
    response_comment = db.Column(Text)
    status = db.Column(db.Integer)
    quickbooks_id = db.Column(db.String(255))  # To store QuickBooks Customer ID
    sync_token = db.Column(db.String(10))  # To store QuickBooks SyncToken

    # Relationships for performance optimization
    intake = relationship("TblIntake", backref="applications", lazy='select')

    def __repr__(self):
        return f'<TblOnlineApplication {self.id if hasattr(self, "id") else "unknown"}>'

    def to_dict(self):
        """
        Convert model to dictionary for JSON responses

        Returns:
            dict: Model data as dictionary
        """
        return {
            'appl_Id': self.appl_Id,
            'tracking_id': self.tracking_id,
            'reg_no': self.reg_no,
            'first_name': self.first_name,
            'middlename': self.middlename,
            'family_name': self.family_name,
            'dob': self.dob.isoformat() if self.dob else None,
            'sex': self.sex,
            'phone1': self.phone1,
            'email1': self.email1,
            'country_of_birth': self.country_of_birth,
            'nation_Id_passPort_no': self.nation_Id_passPort_no,
            'present_nationality': self.present_nationality,
            'sector': self.sector,
            'father_name': self.father_name,
            'mother_name': self.mother_name,
            'guardian_phone': self.guardian_phone,
            'serious_illness': self.serious_illness,
            'serious_illness_comment': self.serious_illness_comment,
            'blood_pressure': self.blood_pressure,
            'diabetes': self.diabetes,
            'high_school_name': self.high_school_name,
            'combination': self.combination,
            'completed_year': self.completed_year,
            'school_categ_Id': self.school_categ_Id,
            'index_number': self.index_number,
            'grade_marks': self.grade_marks,
            'principle_passes': self.principle_passes,
            'n_principle_passes': self.n_principle_passes,
            'camp_id': self.camp_id,
            'opt_1': self.opt_1,
            'opt_2': self.opt_2,
            'opt_3': self.opt_3,
            'opt_oriented': self.opt_oriented,
            'intake_id': self.intake_id,
            'level_id': self.level_id,
            'prg_mode_id': self.prg_mode_id,
            'spon_id': self.spon_id,
            'StdentTrnsfr': self.StdentTrnsfr,
            'about_Id': self.about_Id,
            'appl_date': self.appl_date.isoformat() if self.appl_date else None,
            'NID_doc': self.NID_doc,
            'highSchool_doc': self.highSchool_doc,
            'transcript_doc': self.transcript_doc,
            'HoD_comment': self.HoD_comment,
            'HoD_user': self.HoD_user,
            'HoD_resp_date': self.HoD_resp_date.isoformat() if self.HoD_resp_date else None,
            'respont_by': self.respont_by,
            'response_date': self.response_date.isoformat() if self.response_date else None,
            'response_comment': self.response_comment,
            'status': self.status,
            'quickbooks_status': self.QuickBk_status,
            'pushed_by': self.pushed_by,
            'pushed_date': self.pushed_date.isoformat() if self.pushed_date else None,
            'quickbooks_id': self.quickbooks_id,
            'sync_token': self.sync_token

        }

    def to_dict_for_quickbooks(self):
        """
        Enhanced serialization for QuickBooks customer sync with fallback handling

        Returns:
            dict: QuickBooks-ready applicant data with enriched information
        """
        try:
            # Get enriched data with fallbacks
            campus_name = self._get_enriched_campus_name()
            intake_details = self._get_enriched_intake_details()
            program_name = self._get_enriched_program_name()
            program_mode = self._get_enriched_program_mode()
            country_name = self._get_enriched_country_name()

            return {
                # Primary identifiers
                'appl_Id': self.appl_Id,
                'tracking_id': self.tracking_id or '',
                'customer_type': 'Applicant',

                # Display name (real name only)
                'display_name': f"{self.first_name or ''} {self.family_name or ''}".strip() or f"Applicant {self.appl_Id}",
                'first_name': self.first_name or '',
                'last_name': self.family_name or '',
                'middle_name': self.middlename or '',

                # Contact information
                'phone': self.phone1 or '',
                'email': self.email1 or '',

                # Personal information
                'sex': self.sex or '',
                'dob': self.dob.isoformat() if self.dob else '',
                'country_of_birth': country_name,
                'national_id': self.nation_Id_passPort_no or '',
                'present_nationality': self.present_nationality or '',

                # Academic information (enriched with fallbacks)
                'campus_name': campus_name,
                'intake_details': intake_details,
                'program_name': program_name,
                'program_mode': program_mode,

                # Family information
                'father_name': self.father_name or '',
                'mother_name': self.mother_name or '',
                'guardian_phone': self.guardian_phone or '',

                # Application details
                'application_date': self.appl_date.isoformat() if self.appl_date else '',

                # Sync tracking
                'quickbooks_status': self.QuickBk_status or 0,
                'pushed_by': self.pushed_by or 'System Auto Push',
                'pushed_date': self.pushed_date.isoformat() if self.pushed_date else None,
                'quickbooks_id': self.quickbooks_id or '',
                'sync_token': self.sync_token or ''
            }
        except Exception as e:
            # Fallback to basic data if enrichment fails
            from flask import current_app
            if current_app:
                current_app.logger.warning(f"Error in to_dict_for_quickbooks for applicant {self.appl_Id}: {e}")

            return {
                'appl_Id': self.appl_Id,
                'tracking_id': self.tracking_id or '',
                'customer_type': 'Applicant',
                'display_name': f"{self.first_name or ''} {self.family_name or ''}".strip() or f"Applicant {self.appl_Id}",
                'first_name': self.first_name or '',
                'family_name': self.family_name or '',
                'phone': self.phone1 or '',
                'email': self.email1 or '',
                'sex': self.sex or '',
                'campus_name': str(self.camp_id) if self.camp_id else '',
                'intake_details': str(self.intake_id) if self.intake_id else '',
                'program_name': str(self.opt_1) if self.opt_1 else '',
                'quickbooks_status': self.QuickBk_status or 0
            }

    def _get_enriched_campus_name(self):
        """Get enriched campus name with fallback"""
        if not self.camp_id:
            return ''
        try:
            from application.models.mis_models import TblCampus
            campus = TblCampus.get_by_id(self.camp_id)
            if campus:
                return getattr(campus, 'camp_full_name', '') or getattr(campus, 'camp_short_name', '') or str(self.camp_id)
            return str(self.camp_id)
        except:
            return str(self.camp_id)

    def _get_enriched_intake_details(self):
        """Get enriched intake details with fallback"""
        if not self.intake_id:
            return ''
        try:
            from application.models.mis_models import TblIntake
            intake = TblIntake.get_by_id(self.intake_id)
            if intake:
                return intake.to_dict()
                 #getattr(intake, 'intake_name', '') or getattr(intake, 'intake_details', '') or str(self.intake_id)
            return str(self.intake_id)
        except:
            return str(self.intake_id)

    def _get_enriched_program_name(self):
        """Get enriched program name with fallback"""
        if not self.opt_1:  # Primary option
            return ''
        try:
            from application.models.mis_models import TblSpecialization
            program = TblSpecialization.get_by_id(self.opt_1)
            if program:
                return getattr(program, 'splz_full_name', '') or getattr(program, 'splz_short_name', '') or str(self.opt_1)
            return str(self.opt_1)
        except:
            return str(self.opt_1)

    def _get_enriched_program_mode(self):
        """Get enriched program mode with fallback - optimized with cached data"""
        if not self.prg_mode_id:
            return ''
        try:
            from flask import current_app

            # Strategy 1: Use cached program mode data (from batch loading)
            if hasattr(self, '_cached_program_mode') and self._cached_program_mode:
                mode = self._cached_program_mode
                mode_name = getattr(mode, 'prg_mode_full_name', '') or getattr(mode, 'prg_mode_short_name', '') or str(self.prg_mode_id)
                if current_app:
                    current_app.logger.debug(f"Enriched program mode for applicant {self.appl_Id} (cached): {mode_name}")
                return mode_name

            # Strategy 2: Fallback to database lookup (for non-batch scenarios)
            from application.models.mis_models import TblProgramMode
            mode = TblProgramMode.get_by_id(self.prg_mode_id)
            if mode:
                mode_name = getattr(mode, 'prg_mode_full_name', '') or getattr(mode, 'prg_mode_short_name', '') or str(self.prg_mode_id)
                if current_app:
                    current_app.logger.debug(f"Enriched program mode for applicant {self.appl_Id} (db lookup): {mode_name}")
                return mode_name
            else:
                if current_app:
                    current_app.logger.warning(f"Program mode {self.prg_mode_id} not found for applicant {self.appl_Id}")
                return str(self.prg_mode_id)
        except Exception as e:
            from flask import current_app
            if current_app:
                current_app.logger.error(f"Error getting enriched program mode for applicant {self.appl_Id}: {e}")
            return str(self.prg_mode_id)

    def _get_enriched_country_name(self):
        """Get enriched country name with fallback - optimized with cached data"""
        try:
            from flask import current_app

            # Strategy 1: Use cached country data (from batch loading)
            if hasattr(self, '_cached_country') and self._cached_country:
                country = self._cached_country
                country_name = getattr(country, 'cntr_name', '') or getattr(country, 'cntr_nationality', '') or str(self.country_of_birth)
                if current_app:
                    current_app.logger.debug(f"Enriched country for applicant {self.appl_Id} (cached): {country_name}")
                return country_name

            # Strategy 2: Fallback to database lookup (for non-batch scenarios)
            if self.country_of_birth and str(self.country_of_birth).isdigit():
                from application.models.mis_models import TblCountry
                with self.get_session() as session:
                    country = session.query(TblCountry).filter_by(cntr_id=int(self.country_of_birth)).first()
                    if country:
                        country_name = getattr(country, 'cntr_name', '') or getattr(country, 'cntr_nationality', '') or str(self.country_of_birth)
                        if current_app:
                            current_app.logger.debug(f"Enriched country for applicant {self.appl_Id} (db lookup): {country_name}")
                        return country_name
                    else:
                        if current_app:
                            current_app.logger.warning(f"Country ID {self.country_of_birth} not found for applicant {self.appl_Id}")
                        return f"Country ID: {self.country_of_birth}"

            # Strategy 3: Return country_of_birth as-is if it's already a name
            if self.country_of_birth and not str(self.country_of_birth).isdigit():
                return str(self.country_of_birth)

            # Final fallback
            return str(self.country_of_birth) if self.country_of_birth else ''

        except Exception as e:
            from flask import current_app
            if current_app:
                current_app.logger.error(f"Error getting enriched country name for applicant {self.appl_Id}: {e}")
            return str(self.country_of_birth) if self.country_of_birth else ''

    def get_applicant_details(tracking_id):
        """
        Get detailed applicant information by tracking ID

        Args:
            tracking_id (str): Applicant tracking ID

        Returns:
            dict: Applicant details or None if not found
        """
        try:
            with TblOnlineApplication.get_session() as session:
                applicant = session.query(TblOnlineApplication).filter(TblOnlineApplication.tracking_id == tracking_id).first()
                return applicant.to_dict_for_quickbooks() if applicant else None
        except Exception as e:
            from flask import current_app
            current_app.logger.error(f"Error getting applicant details for tracking ID {tracking_id}: {str(e)}")
            return False
    @staticmethod
    def get_applicant_by_reg_no(reg_no):
        """
        Get detailed applicant information by registration number

        Args:
            reg_no (str): Applicant registration number

        Returns:
            dict: Applicant details or None if not found
        """
        try:
            with TblOnlineApplication.get_session() as session:
                applicant = session.query(TblOnlineApplication).filter(TblOnlineApplication.tracking_id == reg_no).first()
                return applicant.to_dict() if applicant else None
        except Exception as e:
            from flask import current_app
            current_app.logger.error(f"Error getting applicant details for reg no {reg_no}: {str(e)}")
            return []
    @classmethod
    def update_applicant_quickbooks_status(cls, tracking_id, quickbooks_id, pushed_by, QuickBk_status, sync_token=None):
        """
        Update QuickBooks sync status for an applicant

        Args:
            appl_Id (int): Applicant ID
            quickbooks_id (str): QuickBooks Customer ID
            pushed_by (str): User who pushed the data
            pushed_date (datetime): Date when data was pushed
            QuickBk_Status (int): Sync status (0=not pushed, 1=pushed)
        Returns:
            bool: True if update was successful, False otherwise
        """
        try:
            with cls.get_session() as session:
                applicant = session.query(cls).filter(cls.tracking_id == tracking_id).first()
                if applicant:
                    applicant.QuickBk_status = QuickBk_status
                    applicant.quickbooks_id = quickbooks_id
                    applicant.pushed_by = pushed_by
                    applicant.pushed_date = datetime.now()
                    applicant.sync_token = sync_token
                    session.commit()
                    return True
                return False
        except Exception as e:
            from flask import current_app
            current_app.logger.error(f"Error updating QuickBooks status for applicant {tracking_id}: {str(e)}")
            return False
    @staticmethod
    def count_applicants():
        """
        Count total number of applicants
        """
        try:
            with MISBaseModel.get_session() as session:
                count = session.query(TblOnlineApplication).count()
                return count
        except Exception as e:
            from flask import current_app
            current_app.logger.error(f"Error counting applicants: {str(e)}")
            return 0

    @staticmethod
    def count_synced_applicants():
        """
        Count total number of applicants synced to QuickBooks
        """
        try:
            with MISBaseModel.get_session() as session:
                count = session.query(TblOnlineApplication).filter(TblOnlineApplication.QuickBk_Status == 1, TblOnlineApplication.quickbooks_id != None).count()
                return count
        except Exception as e:
            from flask import current_app
            current_app.logger.error(f"Error counting synced applicants: {str(e)}")
            return 0


class TblPersonalUg(MISBaseModel):
    """Model for tbl_personal_ug table"""
    __tablename__ = 'tbl_personal_ug'
    
    per_id_ug = db.Column(db.Integer, nullable=False, primary_key=True)
    reg_no = db.Column(db.String(200), nullable=False)
    prg_type = db.Column(db.Integer, ForeignKey("tbl_program_type.prg_type_id"))
    sex = db.Column(db.String(6))
    fname = db.Column(db.String(250))
    middlename = db.Column(db.String(200))
    lname = db.Column(db.String(100))
    dob = db.Column(DateTime)
    marital_status = db.Column(db.String(7))
    father_name = db.Column(db.String(50))
    mother_name = db.Column(db.String(50))
    national_id = db.Column(db.String(20))
    cntr_id = db.Column(db.Integer, ForeignKey("tbl_country.cntr_id"))
    VISA_Expiration_date = db.Column(DateTime)
    b_province = db.Column(db.Integer, ForeignKey("tbl_province.province_id"))
    b_district = db.Column(db.Integer, ForeignKey("tbl_district.district_id"))
    b_sector = db.Column(db.Integer, ForeignKey("tbl_sector.sector_id"))
    b_cell = db.Column(db.Integer, ForeignKey("tbl_cell.cell_id"))
    b_village = db.Column(db.Integer, ForeignKey("tbl_village.village_id"))
    district = db.Column(db.Integer, ForeignKey("tbl_district.district_id"))
    sector = db.Column(db.Integer, ForeignKey("tbl_sector.sector_id"))
    cell = db.Column(db.Integer, ForeignKey("tbl_cell.cell_id"))
    village = db.Column(db.Integer, ForeignKey("tbl_village.village_id"))
    province = db.Column(db.Integer, ForeignKey("tbl_province.province_id"))
    nationality = db.Column(db.String(50))
    phone1 = db.Column(db.String(100))
    phone2 = db.Column(db.String(20))
    email1 = db.Column(db.String(50))
    email2 = db.Column(db.String(50))
    combination = db.Column(db.String(100))
    principle_passes = db.Column(db.String(500))
    no_principle_passes = db.Column(db.String, nullable=False)
    year_of_compleshed = db.Column(db.String)
    max_or_grad = db.Column(Float, nullable=False)
    reg_date = db.Column(DateTime)
    secondary_notes = db.Column(Text, nullable=False)
    secondary_school = db.Column(db.String(50), nullable=False)
    student_updating = db.Column(db.String(10))
    registered_by = db.Column(db.String(100))
    updated_date = db.Column(DateTime)
    updated_by = db.Column(db.String(100))
    transf_status = db.Column(db.String(50))
    about_Id = db.Column(db.String)
    certificate_doc = db.Column(db.String(150))
    auth_ccs_nnc = db.Column(db.String, nullable=False, default='0')
    qk_id = db.Column(db.String)
    pushed_by = db.Column(db.String(200), default='System Auto Push')
    pushed_date = db.Column(DateTime)
    sync_token = db.Column(db.String(50))
    

    # QuickBooks sync tracking field (additional to existing fields)
    QuickBk_status = db.Column(db.Integer, default=0, nullable=True)  # 0=not synced, 1=synced, 2=failed, 3=in progress

    # Relationships will be added after analyzing foreign keys
    country = relationship("TblCountry", backref="personal_ugs", lazy='joined')
    district = relationship("TblDistrict", backref="personal_ugs", lazy='joined')
    sector = relationship("TblSector", backref="personal_ugs", lazy='joined')
    cell = relationship("TblCell", backref="personal_ugs", lazy='joined')
    village = relationship("TblVillage", backref="personal_ugs", lazy='joined')
    province = relationship("Province", backref="personal_ugs", lazy='joined')
    prgtype = relationship("TblProgramType", backref="personal_ugs", lazy='joined')


    def __repr__(self):
        return f'<TblPersonalUg {self.id if hasattr(self, "id") else "unknown"}>'

    def to_dict(self):
        """
        Convert model to dictionary for JSON responses

        Returns:
            dict: Model data as dictionary
        """
        return {
            'per_id_ug': self.per_id_ug,
            'reg_no': self.reg_no,
            'prg_type': self.prg_type if self.prg_type else None,
            'sex': self.sex,
            'fname': self.fname,
            'middlename': self.middlename,
            'lname': self.lname,
            'dob': self.dob.isoformat() if self.dob else None,
            'marital_status': self.marital_status,
            'father_name': self.father_name,
            'mother_name': self.mother_name,
            'national_id': self.national_id,
            'cntr_id': self.cntr_id,
            'VISA_Expiration_date': self.VISA_Expiration_date.isoformat()
            if self.VISA_Expiration_date and hasattr(self.VISA_Expiration_date, 'isoformat') else self.VISA_Expiration_date,
            'b_province': self.b_province.to_dict() if self.b_province else [],

            'b_district': self.b_district.to_dict() if self.b_district else [],
            'b_sector': self.b_sector.to_dict() if self.b_sector else [],
            'b_cell': self.b_cell.to_dict() if self.b_cell else [],
            'b_village': self.b_village.to_dict() if self.b_village else [],
            'district': self.district.to_dict() if self.district else [],
            'sector': self.sector.to_dict() if self.sector else [],
            'cell': self.cell.to_dict() if self.cell else [],
            'village': self.village.to_dict() if self.village else [],
            'province': self.province.to_dict() if self.province else [],
            'nationality': self.nationality,
            'phone1': self.phone1,
            'phone2': self.phone2,
            'email1': self.email1,
            'email2': self.email2,
            'combination': self.combination,
            'principle_passes': self.principle_passes,
            'no_principle_passes': self.no_principle_passes,
            'year_of_compleshed': self.year_of_compleshed,
            'max_or_grad': self.max_or_grad,
            'reg_date': self.reg_date.isoformat() if self.reg_date else None,
            'secondary_notes': self.secondary_notes,
            'secondary_school': self.secondary_school,
            'student_updating': self.student_updating,
            'registered_by': self.registered_by,
            'updated_date': self.updated_date.isoformat() if self.updated_date else None,
            'updated_by': self.updated_by,
            'transf_status': self.transf_status,
            'about_Id': self.about_Id,
            'certificate_doc': self.certificate_doc,
            'auth_ccs_nnc': self.auth_ccs_nnc,
            'qk_id': self.qk_id,
            'pushed_by': self.pushed_by,
            'pushed_date': self.pushed_date.isoformat() if self.pushed_date else None,
            'quickbooks_status': self.QuickBk_status,
            'sync_token': self.sync_token
        }

    def to_dict_for_quickbooks(self):
        """
        Enhanced serialization for QuickBooks customer sync with fallback handling

        Returns:
            dict: QuickBooks-ready student data with enriched information
        """
        try:
            # Get enriched data with fallbacks
            level_name = self._get_enriched_level_name()
            campus_name = self._get_enriched_campus_name()
            program_name = self._get_enriched_program_name()
            intake_details = self._get_enriched_intake_details()
            country_name = self._get_enriched_country_name()

            return {
                # Primary identifiers
                'per_id_ug': self.per_id_ug,
                'reg_no': self.reg_no or '',
                'customer_type': 'Student',

                # Display name (real name only)
                'display_name': f"{self.fname or ''} {self.lname or ''}".strip() or f"Student {self.reg_no}",
                'first_name': self.fname or '',
                'last_name': self.lname or '',
                'middle_name': self.middlename or '',

                # Contact information
                'phone': self.phone1 or self.phone2 or '',
                'email': self.email1 or self.email2 or '',

                # Personal information
                'sex': self.sex or '',
                'dob': self.dob.isoformat() if self.dob else '',
                'national_id': self.national_id or '',
                'nationality': country_name,
                'marital_status': self.marital_status or '',

                # Academic information (enriched with fallbacks)
                'level_name': level_name,
                'campus_name': campus_name,
                'program_name': program_name,
                'intake_details': intake_details,
                'program_type': self.prgtype.prg_type_full_name if self.prgtype else '',

                # Family information
                'father_name': self.father_name or '',
                'mother_name': self.mother_name or '',

                # Address information
                'province': self.province or '',
                'district': self.district or '',
                'sector': self.sector or '',
                'cell': self.cell or '',
                'village': self.village or '',

                # Academic background
                'secondary_school': self.secondary_school or '',
                'combination': self.combination or '',
                'principle_passes': self.principle_passes or '',
                'year_completed': self.year_of_compleshed or '',

                # Registration details
                'registration_date': self.reg_date.isoformat() if self.reg_date else '',

                # Sync tracking
                'quickbooks_status': self.QuickBk_status or 0,
                'pushed_by': self.pushed_by or 'System Auto Push',
                'pushed_date': self.pushed_date.isoformat() if self.pushed_date else None,
                'qk_id': self.qk_id or '',
                'sync_token': self.sync_token
            }
        except Exception as e:
            # Fallback to basic data if enrichment fails
            from flask import current_app
            import traceback
            if current_app:
                current_app.logger.error(f"Error in to_dict_for_quickbooks for student {self.reg_no}: {e}")
                current_app.logger.error(f"Traceback: {traceback.format_exc()}")

            return {
                'per_id_ug': self.per_id_ug,
                'reg_no': self.reg_no or '',
                'customer_type': 'Student',
                'display_name': f"{self.fname or ''} {self.lname or ''}".strip() or f"Student {self.reg_no}",
                'first_name': self.fname or '',
                'last_name': self.lname or '',
                'phone': self.phone1 or '',
                'email': self.email1 or '',
                'sex': self.sex or '',
                'national_id': self.national_id or '',
                'nationality': self.nationality or '',
                'level_name': '',
                'campus_name': '',
                'program_name': '',
                'intake_details': '',
                'program_type': '',
                'quickbooks_status': self.QuickBk_Status or 0,
                'error_occurred': True,
                'error_message': str(e)
            }

    def _get_enriched_level_name(self):
        """Get enriched level name with fallback - optimized with cached data"""
        try:
            from flask import current_app

            # Strategy 1: Use cached level data (from batch loading)
            if hasattr(self, '_cached_level') and self._cached_level:
                level = self._cached_level
                level_name = getattr(level, 'level_full_name', '') or getattr(level, 'level_short_name', '') or 'Unknown Level'
                if current_app:
                    current_app.logger.debug(f"Enriched level for student {self.reg_no} (cached): {level_name}")
                return level_name

            # Strategy 2: Use cached registration program data
            if hasattr(self, '_cached_reg_program') and self._cached_reg_program:
                reg_program = self._cached_reg_program
                if reg_program.level_id:
                    if current_app:
                        current_app.logger.debug(f"Level ID for student {self.reg_no} (cached reg program): {reg_program.level_id}")
                    return str(reg_program.level_id)

            # Strategy 3: Fallback to database lookup (for non-batch scenarios)
            from application.models.mis_models import TblRegisterProgramUg, TblLevel
            with self.get_session() as session:
                reg_program = session.query(TblRegisterProgramUg).filter_by(reg_no=self.reg_no).first()
                if reg_program and reg_program.level_id:
                    level = session.query(TblLevel).filter_by(level_id=reg_program.level_id).first()
                    if level:
                        level_name = getattr(level, 'level_full_name', '') or getattr(level, 'level_short_name', '') or str(reg_program.level_id)
                        if current_app:
                            current_app.logger.debug(f"Enriched level for student {self.reg_no} (db lookup): {level_name}")
                        return level_name
                    else:
                        if current_app:
                            current_app.logger.warning(f"Level {reg_program.level_id} not found for student {self.reg_no}")
                        return str(reg_program.level_id)
                else:
                    if current_app:
                        current_app.logger.warning(f"No registration program found for student {self.reg_no}")
                    return ''
        except Exception as e:
            from flask import current_app
            if current_app:
                current_app.logger.error(f"Error getting enriched level name for student {self.reg_no}: {e}")
            return ''

    def _get_enriched_campus_name(self):
        """Get enriched campus name with fallback - optimized with cached data"""
        try:
            from flask import current_app

            # Strategy 1: Use cached campus data (from batch loading)
            if hasattr(self, '_cached_campus') and self._cached_campus:
                campus = self._cached_campus
                campus_name = getattr(campus, 'camp_full_name', '') or getattr(campus, 'camp_short_name', '') or 'Unknown Campus'
                if current_app:
                    current_app.logger.debug(f"Enriched campus for student {self.reg_no} (cached): {campus_name}")
                return campus_name

            # Strategy 2: Use cached registration program data
            if hasattr(self, '_cached_reg_program') and self._cached_reg_program:
                reg_program = self._cached_reg_program
                if hasattr(reg_program, 'camp_id') and reg_program.camp_id:
                    if current_app:
                        current_app.logger.debug(f"Campus ID for student {self.reg_no} (cached reg program): {reg_program.camp_id}")
                    return str(reg_program.camp_id)

            # Strategy 3: Fallback to database lookup (for non-batch scenarios)
            from application.models.mis_models import TblRegisterProgramUg, TblCampus
            with self.get_session() as session:
                reg_program = session.query(TblRegisterProgramUg).filter_by(reg_no=self.reg_no).first()
                if reg_program and hasattr(reg_program, 'camp_id') and reg_program.camp_id:
                    campus = session.query(TblCampus).filter_by(camp_id=reg_program.camp_id).first()
                    if campus:
                        campus_name = getattr(campus, 'camp_full_name', '') or getattr(campus, 'camp_short_name', '') or str(reg_program.camp_id)
                        if current_app:
                            current_app.logger.debug(f"Enriched campus for student {self.reg_no} (db lookup): {campus_name}")
                        return campus_name
                    else:
                        if current_app:
                            current_app.logger.warning(f"Campus {reg_program.camp_id} not found for student {self.reg_no}")
                        return str(reg_program.camp_id)
                else:
                    if current_app:
                        current_app.logger.warning(f"No registration program or campus ID found for student {self.reg_no}")
                    return ''
        except Exception as e:
            from flask import current_app
            if current_app:
                current_app.logger.error(f"Error getting enriched campus name for student {self.reg_no}: {e}")
            return ''

    def _get_enriched_program_name(self):
        """Get enriched program name with fallback - optimized with cached data"""
        try:
            from flask import current_app

            # Strategy 1: Use cached specialization data (from batch loading)
            if hasattr(self, '_cached_specialization') and self._cached_specialization:
                program = self._cached_specialization
                program_name = getattr(program, 'splz_full_name', '') or getattr(program, 'splz_short_name', '') or 'Unknown Program'
                if current_app:
                    current_app.logger.debug(f"Enriched program for student {self.reg_no} (cached): {program_name}")
                return program_name

            # Strategy 2: Use cached registration program data
            if hasattr(self, '_cached_reg_program') and self._cached_reg_program:
                reg_program = self._cached_reg_program
                if reg_program.splz_id:
                    if current_app:
                        current_app.logger.debug(f"Program ID for student {self.reg_no} (cached reg program): {reg_program.splz_id}")
                    return str(reg_program.splz_id)

            # Strategy 3: Fallback to database lookup (for non-batch scenarios)
            from application.models.mis_models import TblRegisterProgramUg, TblSpecialization
            with self.get_session() as session:
                reg_program = session.query(TblRegisterProgramUg).filter_by(reg_no=self.reg_no).first()
                if reg_program and reg_program.splz_id:
                    program = session.query(TblSpecialization).filter_by(splz_id=reg_program.splz_id).first()
                    if program:
                        program_name = getattr(program, 'splz_full_name', '') or getattr(program, 'splz_short_name', '') or str(reg_program.splz_id)
                        if current_app:
                            current_app.logger.debug(f"Enriched program for student {self.reg_no} (db lookup): {program_name}")
                        return program_name
                    else:
                        if current_app:
                            current_app.logger.warning(f"Program {reg_program.splz_id} not found for student {self.reg_no}")
                        return str(reg_program.splz_id)
                else:
                    if current_app:
                        current_app.logger.warning(f"No registration program or specialization ID found for student {self.reg_no}")
                    return ''
        except Exception as e:
            from flask import current_app
            if current_app:
                current_app.logger.error(f"Error getting enriched program name for student {self.reg_no}: {e}")
            return ''

    def _get_enriched_intake_details(self):
        """Get enriched intake details with fallback - optimized with cached data"""
        try:
            from flask import current_app

            # Strategy 1: Use cached intake data (from batch loading)
            if hasattr(self, '_cached_intake') and self._cached_intake:
                intake = self._cached_intake
                intake_details = f"{intake.intake_month} {intake.intake_no}" if intake.intake_month else 'Unknown Intake'
                if current_app:
                    current_app.logger.debug(f"Enriched intake for student {self.reg_no} (cached): {intake_details}")
                return intake_details

            # Strategy 2: Use cached registration program data
            if hasattr(self, '_cached_reg_program') and self._cached_reg_program:
                reg_program = self._cached_reg_program
                if reg_program.intake_id:
                    if current_app:
                        current_app.logger.debug(f"Intake ID for student {self.reg_no} (cached reg program): {reg_program.intake_id}")
                    return str(reg_program.intake_id)

            # Strategy 3: Fallback to database lookup (for non-batch scenarios)
            from application.models.mis_models import TblRegisterProgramUg, TblIntake
            with self.get_session() as session:
                reg_program = session.query(TblRegisterProgramUg).filter_by(reg_no=self.reg_no).first()
                if reg_program and reg_program.intake_id:
                    intake = session.query(TblIntake).filter_by(intake_id=reg_program.intake_id).first()
                    if intake:
                        intake_details = f"{intake.intake_month} {intake.intake_no}" if intake.intake_month else str(reg_program.intake_id)
                        if current_app:
                            current_app.logger.debug(f"Enriched intake for student {self.reg_no} (db lookup): {intake_details}")
                        return intake_details
                    else:
                        if current_app:
                            current_app.logger.warning(f"Intake {reg_program.intake_id} not found for student {self.reg_no}")
                        return str(reg_program.intake_id)
                else:
                    if current_app:
                        current_app.logger.warning(f"No registration program or intake ID found for student {self.reg_no}")
                    return ''
        except Exception as e:
            from flask import current_app
            if current_app:
                current_app.logger.error(f"Error getting enriched intake details for student {self.reg_no}: {e}")
            return ''

    def _get_enriched_country_name(self):
        """Get enriched country name with fallback - optimized with cached data"""
        try:
            from flask import current_app

            # Strategy 1: Use cached country data (from batch loading)
            if hasattr(self, '_cached_country') and self._cached_country:
                country = self._cached_country
                country_name = getattr(country, 'cntr_name', '') or getattr(country, 'cntr_nationality', '') or 'Unknown Country'
                if current_app:
                    current_app.logger.debug(f"Enriched country for student {self.reg_no} (cached): {country_name}")
                return country_name

            # Strategy 2: Use existing country relationship if available
            if hasattr(self, 'country') and self.country:
                country_name = getattr(self.country, 'cntr_name', '') or getattr(self.country, 'cntr_nationality', '')
                if country_name:
                    if current_app:
                        current_app.logger.debug(f"Enriched country for student {self.reg_no} via relationship: {country_name}")
                    return country_name

            # Strategy 3: Fallback to database lookup (for non-batch scenarios)
            from application.models.mis_models import TblCountry

            # Try cntr_id field first
            if self.cntr_id:
                with self.get_session() as session:
                    country = session.query(TblCountry).filter_by(cntr_id=self.cntr_id).first()
                    if country:
                        country_name = getattr(country, 'cntr_name', '') or getattr(country, 'cntr_nationality', '') or str(self.cntr_id)
                        if current_app:
                            current_app.logger.debug(f"Enriched country for student {self.reg_no} via cntr_id (db lookup): {country_name}")
                        return country_name

            # Try nationality field as country ID
            if self.nationality and self.nationality.isdigit():
                with self.get_session() as session:
                    country = session.query(TblCountry).filter_by(cntr_id=int(self.nationality)).first()
                    if country:
                        country_name = getattr(country, 'cntr_name', '') or getattr(country, 'cntr_nationality', '') or self.nationality
                        if current_app:
                            current_app.logger.debug(f"Enriched country for student {self.reg_no} via nationality field (db lookup): {country_name}")
                        return country_name
                    else:
                        if current_app:
                            current_app.logger.warning(f"Country ID {self.nationality} not found for student {self.reg_no}")
                        return f"Country ID: {self.nationality}"

            # Return nationality as-is if it's already a name
            if self.nationality and not self.nationality.isdigit():
                return self.nationality

            # Final fallback
            return self.nationality or ''

        except Exception as e:
            from flask import current_app
            if current_app:
                current_app.logger.error(f"Error getting enriched country name for student {self.reg_no}: {e}")
            return self.nationality or ''

    def debug_enrichment(self):
        """
        Debug method to test enrichment methods individually

        Returns:
            dict: Results of all enrichment methods for debugging
        """
        from flask import current_app

        debug_results = {
            'reg_no': self.reg_no,
            'enrichment_results': {},
            'errors': []
        }

        # Test each enrichment method
        enrichment_methods = [
            ('level_name', self._get_enriched_level_name),
            ('campus_name', self._get_enriched_campus_name),
            ('program_name', self._get_enriched_program_name),
            ('intake_details', self._get_enriched_intake_details),
            ('country_name', self._get_enriched_country_name)
        ]

        for method_name, method in enrichment_methods:
            try:
                result = method()
                debug_results['enrichment_results'][method_name] = result
                if current_app:
                    current_app.logger.info(f"Enrichment {method_name} for {self.reg_no}: '{result}'")
            except Exception as e:
                error_msg = f"Error in {method_name}: {e}"
                debug_results['errors'].append(error_msg)
                debug_results['enrichment_results'][method_name] = f"ERROR: {e}"
                if current_app:
                    current_app.logger.error(f"Enrichment {method_name} failed for {self.reg_no}: {e}")

        return debug_results
    @staticmethod
    def get_student_by_reg_no(reg_no):
        """
        Get detailed student information by registration number

        Args:
            reg_no (str): Student registration number

        Returns:
            dict: Student details or None if not found
        """
        try:
            with TblPersonalUg.get_session() as session:
                student = session.query(TblPersonalUg).filter(TblPersonalUg.reg_no == reg_no).first()
                return student
        except Exception as e:
            from flask import current_app
            current_app.logger.error(f"Error getting student details for reg no {reg_no}: {str(e)}")
            return False
    @classmethod
    def get_student_details(cls, reg_no):
        """
        Get detailed student information for QuickBooks custom fields

        Args:
            reg_no (str): Student registration number

        Returns:
            dict: Student details or None if not found
        """
        try:
            with cls.get_session() as session:
                student = session.query(cls).filter(cls.reg_no == reg_no).first()
                if student:
                    # return the data formatted with quickbooks fields
                    return student.to_dict_for_quickbooks()
                return []
        except Exception as e:
            from flask import current_app
            current_app.logger.error(f"Error getting student details for reg_no {reg_no}: {str(e)}")
            return []

    @staticmethod
    def count_students():
        """
        Count total number of students in tbl_personal_ug

        Returns:
            int: Total number of students
        """
        try:
            with TblPersonalUg.get_session() as session:
                count = session.query(func.count(TblPersonalUg.per_id_ug)).scalar()
                return count
        except Exception as e:
            from flask import current_app
            current_app.logger.error(f"Error counting students: {str(e)}")
            return 0

    @staticmethod
    def fetch_paginated_students(start: int = 0, length: int = 50, search: str = None):
        """
        Fetch paginated student records with optional search filter

        """
        try:
            with TblPersonalUg.get_session() as session:
                query = session.query(
                    TblPersonalUg.per_id_ug,
                    TblPersonalUg.reg_no,
                    TblPersonalUg.fname,
                    TblPersonalUg.lname,
                    TblPersonalUg.email1,
                    TblPersonalUg.phone1,
                    TblPersonalUg.QuickBk_status,
                    TblPersonalUg.qk_id,
                    TblPersonalUg.pushed_by,
                    TblPersonalUg.pushed_date
                )

                if search:
                    search_pattern = f"%{search}%"
                    query = query.filter(
                        or_(
                            TblPersonalUg.reg_no.ilike(search_pattern),
                            TblPersonalUg.fname.ilike(search_pattern),
                            TblPersonalUg.lname.ilike(search_pattern),
                            TblPersonalUg.email1.ilike(search_pattern),
                            TblPersonalUg.phone1.ilike(search_pattern)
                        )
                    )
                total_records = session.query(func.count(TblPersonalUg.per_id_ug)).scalar()
                filtered_records = query.count()

                students = query.order_by(TblPersonalUg.per_id_ug).offset(start).limit(length).all()
                data = [
                    {
                        'per_id_ug': s.per_id_ug,
                        'reg_no': s.reg_no,
                        'fname': s.fname,
                        'lname': s.lname,
                        'email1': s.email1,
                        'phone1': s.phone1,
                        'quickbooks_status': s.QuickBk_status,
                        'qk_id': s.qk_id,
                        'pushed_by': s.pushed_by,
                        'pushed_date': s.pushed_date.isoformat() if s.pushed_date else None
                    }
                    for s in students
                ]
                return total_records, filtered_records, data
        except Exception as e:
            from flask import current_app
            current_app.logger.error(f"Error fetching paginated students: {str(e)}")
            return 0, 0, []
    @staticmethod
    def count_synced_students():
        """
        Count total number of students synced to QuickBooks

        Returns:
            int: Total number of synced students
        """
        try:
            with TblPersonalUg.get_session() as session:
                count = session.query(func.count(TblPersonalUg.per_id_ug)).filter(TblPersonalUg.qk_id.isnot(None)).scalar()
                return count
        except Exception as e:
            from flask import current_app
            current_app.logger.error(f"Error counting synced students: {str(e)}")
            return 0

    @staticmethod
    def count_unsynced_students():
        """
        Count total number of students not yet synced to QuickBooks.

        Returns:
            int: Total number of unsynced students
        """
        try:
            with TblPersonalUg.get_session() as session:
                count = (
                    session.query(func.count(TblPersonalUg.per_id_ug))
                    .filter(TblPersonalUg.QuickBk_status.is_(None))
                    .scalar()
                )
                return int(count or 0)
        except Exception as e:
            current_app.logger.error(f"Error counting NULL QuickBk_status: {str(e)}")
            return 0

    @staticmethod
    def get_unsynced_students(limit: int = 100):
        """
        Get a list of students not yet synced to QuickBooks.

        Args:
            limit (int): Maximum number of records to retrieve

        Returns:
            list: List of unsynced student records
        """
        try:
            students = TblPersonalUg.query.filter(TblPersonalUg.QuickBk_status.is_(None)).limit(limit).all()
            return students.to_dict_for_quickbooks() if students else []
        
        except Exception as e:
            from flask import current_app
            current_app.logger.error(f"Error fetching unsynced students: {str(e)}")
            return []
        
    def get_all_students():
        """
        Get all student records from tbl_personal_ug

        Returns:
            list: List of all student records
        """
        try:
            with TblPersonalUg.get_session() as session:
                students = session.query(TblPersonalUg).all()
                return students.to_dict_for_quickbooks() if students else []
        except Exception as e:
            from flask import current_app
            current_app.logger.error(f"Error fetching all students: {str(e)}")
            return []

class TblRegisterProgramUg(MISBaseModel):
    """Model for tbl_register_program_ug table"""
    __tablename__ = 'tbl_register_program_ug'
    
    reg_prg_id = db.Column(db.Integer, nullable=False, primary_key=True)
    reg_no = db.Column(db.String(200), nullable=False)
    intake_id = db.Column(db.Integer, nullable=False)
    prg_id = db.Column(db.Integer, nullable=False)
    splz_id = db.Column(db.Integer, nullable=False)
    level_id = db.Column(db.Integer, nullable=False)
    prg_mode_id = db.Column(db.Integer, nullable=False)
    prg_type = db.Column(db.String(20), nullable=False)
    year_id = db.Column(db.Integer)
    sem1 = db.Column(db.String(10))
    sem2 = db.Column(db.String(10))
    sem3 = db.Column(db.String(10))
    camp_id = db.Column(db.Integer, nullable=False)
    reg_date = db.Column(DateTime)
    reg_comments = db.Column(db.String(255))
    spon_id = db.Column(db.Integer)
    reg_active = db.Column(db.Integer)
    status_comment = db.Column(db.String(400), nullable=False)
    Availability = db.Column(db.String(10), nullable=False)
    pasted_bk = db.Column(db.String(11))
    registered_by = db.Column(db.String(100))
    updated_date = db.Column(DateTime)
    updated_by = db.Column(db.String(100))
    suspension_date = db.Column(DateTime)
    suspended_by = db.Column(db.String(100))
    auth_ccs_nnc = db.Column(db.String(100))
    qk_id = db.Column(db.Integer)

    # Relationships will be added after analyzing foreign keys

    def __repr__(self):
        return f'<TblRegisterProgramUg {self.id if hasattr(self, "id") else "unknown"}>'

    def to_dict(self):
        """
        Convert model to dictionary for JSON responses

        Returns:
            dict: Model data as dictionary
        """
        return {
            'reg_prg_id': self.reg_prg_id,
            'reg_no': self.reg_no,
            'intake_id': self.intake_id,
            'prg_id': self.prg_id,
            'splz_id': self.splz_id,
            'level_id': self.level_id,
            'prg_mode_id': self.prg_mode_id,
            'prg_type': self.prg_type,
            'year_id': self.year_id,
            'sem1': self.sem1,
            'sem2': self.sem2,
            'sem3': self.sem3,
            'camp_id': self.camp_id,
            'reg_date': self.reg_date.isoformat() if self.reg_date else None,
            'reg_comments': self.reg_comments,
            'spon_id': self.spon_id,
            'reg_active': self.reg_active,
            'status_comment': self.status_comment,
            'Availability': self.Availability,
            'pasted_bk': self.pasted_bk,
            'registered_by': self.registered_by,
            'updated_date': self.updated_date.isoformat() if self.updated_date else None,
            'updated_by': self.updated_by,
            'suspension_date': self.suspension_date.isoformat() if self.suspension_date else None,
            'suspended_by': self.suspended_by,
            'auth_ccs_nnc': self.auth_ccs_nnc,
            'qk_id': self.qk_id
        }

class TblSponsor(MISBaseModel):
    """Model for tbl_sponsor table"""
    __tablename__ = 'tbl_sponsor'
    
    spon_id = db.Column(db.Integer, nullable=False, primary_key=True)
    spon_cat_id = db.Column(db.String, nullable=False)
    spon_full_name = db.Column(db.String(50), nullable=False)
    spon_short_name = db.Column(db.String(20), nullable=False)
    sponsor_value = db.Column(Float)
    reg_fee = db.Column(db.Integer)
    tut_fee = db.Column(db.Integer)
    indus_fee = db.Column(db.Integer)
    tour_fee = db.Column(db.Integer)
    thesis_fee = db.Column(db.Integer)
    grad_fee = db.Column(db.Integer)
    degree_fee = db.Column(db.Integer)
    testimony_fee = db.Column(db.Integer)
    recorded_date = db.Column(DateTime)
    user_id = db.Column(db.String(100), nullable=False)
    statusId = db.Column(db.Integer, nullable=False)

    # Relationships will be added after analyzing foreign keys

    def __repr__(self):
        return f'<TblSponsor {self.spon_id}>'

    def to_dict(self):
        """
        Convert model to dictionary for JSON responses

        Returns:
            dict: Model data as dictionary
        """
        return {
            'spon_id': self.spon_id,
            'spon_cat_id': self.spon_cat_id,
            'spon_full_name': self.spon_full_name,
            'spon_short_name': self.spon_short_name,
            'sponsor_value': self.sponsor_value,
            'reg_fee': self.reg_fee,
            'tut_fee': self.tut_fee,
            'indus_fee': self.indus_fee,
            'tour_fee': self.tour_fee,
            'thesis_fee': self.thesis_fee,
            'grad_fee': self.grad_fee,
            'degree_fee': self.degree_fee,
            'testimony_fee': self.testimony_fee,
            'recorded_date': self.recorded_date.isoformat() if self.recorded_date else None,
            'user_id': self.user_id,
            'statusId': self.statusId
        }

    @classmethod
    def get_sponsor_name(cls, spon_id):
        """
        Get sponsor name by ID

        Args:
            spon_id (str): Sponsor ID

        Returns:
            str: Sponsor full name or None if not found
        """
        try:
            with cls.get_session() as session:
                sponsor = session.query(cls).filter(cls.spon_id == spon_id).first()
                return sponsor.spon_full_name if sponsor else None
        except Exception as e:
            from flask import current_app
            current_app.logger.error(f"Error getting sponsor name for ID {spon_id}: {str(e)}")
            return None

    @classmethod
    def get_sponsor_details(cls, spon_id):
        """
        Get detailed sponsor information for QuickBooks custom fields

        Args:
            spon_id (str): Sponsor ID

        Returns:
            dict: Sponsor details or None if not found
        """
        try:
            with cls.get_session() as session:
                sponsor = session.query(cls).filter(cls.spon_id == spon_id).first()
                if sponsor:
                    return {
                        'id': sponsor.spon_id,
                        'full_name': sponsor.spon_full_name,
                        'short_name': sponsor.spon_short_name,
                        'sponsor_value': float(sponsor.sponsor_value) if sponsor.sponsor_value else 0.0,
                        'fee_structure': {
                            'registration': sponsor.reg_fee,
                            'tuition': sponsor.tut_fee,
                            'industrial': sponsor.indus_fee,
                            'tour': sponsor.tour_fee,
                            'thesis': sponsor.thesis_fee,
                            'graduation': sponsor.grad_fee,
                            'degree': sponsor.degree_fee,
                            'testimony': sponsor.testimony_fee
                        },
                        'is_active': sponsor.statusId == 1,
                        'display_name': f"{sponsor.spon_full_name} ({sponsor.sponsor_value}%)" if sponsor.sponsor_value else sponsor.spon_full_name
                    }
                return None
        except Exception as e:
            from flask import current_app
            current_app.logger.error(f"Error getting sponsor details for ID {spon_id}: {str(e)}")
            return None

    def calculate_sponsored_amount(self, base_amount):
        """
        Calculate sponsored amount based on sponsor value

        Args:
            base_amount (float): Base fee amount

        Returns:
            float: Sponsored amount
        """
        if self.sponsor_value:
            return base_amount * (self.sponsor_value / 100)
        return 0.0

    def to_quickbooks_format(self):
        """
        Format sponsor data for QuickBooks custom fields

        Returns:
            dict: Formatted data for QB
        """
        return {
            'Sponsor': self.spon_full_name,
            'SponsorCode': self.spon_short_name,
            'SponsorValue': f"{self.sponsor_value}%" if self.sponsor_value else "0%"
        }
    
class TblIntake(MISBaseModel):
    """Model for tbl_intake table"""
    __tablename__ = 'tbl_intake'  

    intake_id = db.Column(db.Integer, nullable=False, primary_key=True)
    prg_type = db.Column(db.String(255), nullable=False)
    acad_cycle_id = db.Column(db.Integer, nullable=False)
    intake_no = db.Column(db.Integer, nullable=False)
    intake_month = db.Column(db.String(30), nullable=False)
    intake_start = db.Column(DateTime, nullable=False)
    intake_end = db.Column(DateTime, nullable=False)
    app_start = db.Column(DateTime, nullable=False)
    app_end = db.Column(DateTime, nullable=False)
    reg_start = db.Column(DateTime, nullable=False)
    reg_end = db.Column(DateTime, nullable=False)
    late_reg_end = db.Column(DateTime, nullable=False)
    late_reg_fee = db.Column(db.Integer, nullable=False)
    status = db.Column(db.Integer, nullable=False, default='1')

    def __repr__(self):
        """db.String representation of the TblIntake model"""
        return f'<TblIntake {self.intake_id}>'

class TblSpecialization(MISBaseModel):
    """Model for tbl_specialization table"""
    __tablename__ = 'tbl_specialization'
    
    splz_id = db.Column(db.Integer, nullable=False, primary_key=True)
    prg_id = db.Column(db.Integer, nullable=False)
    prg_type = db.Column(db.String(255), nullable=False)
    splz_full_name = db.Column(db.String(100), nullable=False)
    splz_short_name = db.Column(db.String(50), nullable=False)
    splz_start_level = db.Column(db.String(255), nullable=False)
    degree_name = db.Column(db.String(100), nullable=False)
    diploma_name = db.Column(db.String(255), nullable=False)
    splz_comments = db.Column(db.String(255), nullable=False)
    status = db.Column(db.Integer)

    def __repr__(self):
        """db.String representation of the TblSpecialization model"""
        return f'<TblSpecialization {self.splz_id}>'

       
class TblProgramMode(MISBaseModel):
    """Model for tbl_program_mode table"""
    __tablename__ = 'tbl_program_mode'    
    prg_mode_id = db.Column(db.Integer, nullable=False, primary_key=True)
    prg_mode_full_name = db.Column(db.String(30), nullable=False)
    prg_mode_short_name = db.Column(db.String(10), nullable=False)

    def __repr__(self):
        """db.String representation of the TblProgramMode model"""
        return f'<TblProgramMode {self.prg_mode_id}>'


class TblAcadCycle(MISBaseModel):
    """Model for tbl_acad_cycle table"""
    __tablename__ = 'tbl_acad_cycle'
    
    acad_cycle_id = db.Column(db.Integer, nullable=False, primary_key=True)
    curculum_Id = db.Column(db.Integer, ForeignKey("tbl_curriculum.curculum_Id"))
    no_of_intakes = db.Column(db.Integer, nullable=False)
    intakes_months = db.Column(db.String(255), nullable=False)
    no_of_cohorts = db.Column(db.Integer, nullable=False)
    cohort_months = db.Column(db.String(255), nullable=False)
    acad_year = db.Column(db.String(9), nullable=False)
    active = db.Column(db.Integer, nullable=False)
    status = db.Column(db.Integer, nullable=False)

    # Relationship with TblCurriculum
    curriculum = relationship(
        "TblCurriculum",
        backref="acad_cycles",
        lazy='joined',
        foreign_keys=[curculum_Id]  # <-- explicitly specify FK
    )

    def __repr__(self):
        """db.String representation of the TblAcadCycle model"""
        return f'<TblAcadCycle {self.acad_cycle_id}>'

    def to_dict(self):
        """
        Convert model to dictionary for JSON responses

        Returns:
            dict: Model data as dictionary
        """
        return {
            'acad_cycle_id': self.acad_cycle_id,
            'curculum_Id': self.curculum_Id,
            'curriculum_details': self.curriculum.to_dict() if self.curriculum else [],
            'no_of_intakes': self.no_of_intakes,
            'intakes_months': self.intakes_months,
            'no_of_cohorts': self.no_of_cohorts,
            'cohort_months': self.cohort_months,
            'acad_year': self.acad_year,
            'active': self.active,
            'status': self.status
        }

  
class TblCurriculum(MISBaseModel):
    """Model for tbl_curriculum table"""
    __tablename__ = 'tbl_curriculum'
    
    curculum_Id = db.Column(db.Integer, nullable=False, primary_key=True)
    acad_cycle_id = db.Column(db.Integer,ForeignKey("tbl_acad_cycle.acad_cycle_id"))
    recorded_date = db.Column(DateTime, nullable=False)
    recorded_by = db.Column(db.String(200), nullable=False)
    status_Id = db.Column(db.Integer, nullable=False)
    graduation_status = db.Column(db.String(15), nullable=False)

    # Relationship with TblAcadCycle
    acad_cycle = relationship(
        "TblAcadCycle",
        backref="curriculums",
        lazy='joined',
        foreign_keys=[acad_cycle_id]  # <-- explicitly specify FK
    )


    def __repr__(self):
        """db.String representation of the TblCurriculum model"""
        return f'<TblCurriculum {self.curculum_Id}>'

    def to_dict(self):
        """
        Convert model to dictionary for JSON responses

        Returns:
            dict: Model data as dictionary
        """
        return {
            'curculum_Id': self.curculum_Id,
            'acad_cycle_id': self.acad_cycle_id,
            'acad_cycle_details': self.acad_cycle.to_dict() if self.acad_cycle else [],
            'recorded_date': self.recorded_date.isoformat() if self.recorded_date else None,
            'recorded_by': self.recorded_by,
            'status_Id': self.status_Id,
            'graduation_status': self.graduation_status
        }

class Province(MISBaseModel):
    __tablename__ = 'tbl_province'

    province_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    province_name = db.Column(db.String(20), nullable=False)

    def __repr__(self):
        return f"<Province {self.province_name}>"

    def to_dict(self):
        return {
            'province_id': self.province_id,
            'province_name': self.province_name
        }

class TblDistrict(MISBaseModel):
    """Model for tbl_district table"""
    __tablename__ = 'tbl_district'
    
    district_id = db.Column(db.Integer, nullable=False, primary_key=True)
    district_name = db.Column(db.String(50), nullable=False)
    province_id = db.Column(db.Integer, ForeignKey("tbl_province.province_id"))

    # Relationship with Province
    province = relationship(
        "Province",
        backref="districts",
        lazy='joined',
        foreign_keys=[province_id]  # <-- explicitly specify FK
    )

    def __repr__(self):
        """db.String representation of the TblDistrict model"""
        return f'<TblDistrict {self.district_id}>'

    def to_dict(self):
        """
        Convert model to dictionary for JSON responses

        Returns:
            dict: Model data as dictionary
        """
        return {
            'district_id': self.district_id,
            'district_name': self.district_name,
            'province_id': self.province_id,    
            'province_details': self.province.to_dict() if self.province else []
        }

class TblSector(MISBaseModel):
    """Model for tbl_sector table"""
    __tablename__ = 'tbl_sector'
    
    sector_id = db.Column(db.Integer, nullable=False, primary_key=True)
    sector_name = db.Column(db.String(50), nullable=False)
    district_id = db.Column(db.Integer, ForeignKey("tbl_district.district_id"))

    # Relationship with TblDistrict
    district = relationship(
        "TblDistrict",
        backref="sectors",
        lazy='joined',
        foreign_keys=[district_id]  # <-- explicitly specify FK
    )

    def __repr__(self):
        """db.String representation of the TblSector model"""
        return f'<TblSector {self.sector_id}>'

    def to_dict(self):
        """
        Convert model to dictionary for JSON responses

        Returns:
            dict: Model data as dictionary
        """
        return {
            'sector_id': self.sector_id,
            'sector_name': self.sector_name,
            'district_id': self.district_id,    
            'district_details': self.district.to_dict() if self.district else []
        }

class TblCell(MISBaseModel):
    """Model for tbl_cell table"""
    __tablename__ = 'tbl_cell'
    
    cell_id = db.Column(db.Integer, nullable=False, primary_key=True)
    cell_name = db.Column(db.String(50), nullable=False)
    sector_id = db.Column(db.Integer, ForeignKey("tbl_sector.sector_id"))

    # Relationship with TblSector
    sector = relationship(
        "TblSector",
        backref="cells",
        lazy='joined',
        foreign_keys=[sector_id]  # <-- explicitly specify FK
    )

    def __repr__(self):
        """db.String representation of the TblCell model"""
        return f'<TblCell {self.cell_id}>'

    def to_dict(self):
        """
        Convert model to dictionary for JSON responses

        Returns:
            dict: Model data as dictionary
        """
        return {
            'cell_id': self.cell_id,
            'cell_name': self.cell_name,
            'sector_id': self.sector_id,    
            'sector_details': self.sector.to_dict() if self.sector else []
        }

class TblVillage(MISBaseModel):
    """Model for tbl_village table"""
    __tablename__ = 'tbl_village'
    
    village_id = db.Column(db.Integer, nullable=False, primary_key=True)
    village_name = db.Column(db.String(50), nullable=False)
    cell_id = db.Column(db.Integer, ForeignKey("tbl_cell.cell_id"))

    # Relationship with TblCell 
    cell = relationship(
        "TblCell",
        backref="villages",
        lazy='joined',
        foreign_keys=[cell_id]  # <-- explicitly specify FK
    )

    def __repr__(self):
        """db.String representation of the TblVillage model"""
        return f'<TblVillage {self.village_id}>'

    def to_dict(self):
        """
        Convert model to dictionary for JSON responses

        Returns:
            dict: Model data as dictionary
        """
        return {
            'village_id': self.village_id,
            'village_name': self.village_name,
            'cell_id': self.cell_id,    
            'cell_details': self.cell.to_dict() if self.cell else []
        }

class TblCountry(MISBaseModel):
    """Model for tbl_country table"""
    __tablename__ = 'tbl_country'

    cntr_id = db.Column(db.Integer, nullable=False, primary_key=True)
    cntr_code = db.Column(db.String(50), nullable=True)
    cntr_name = db.Column(db.String(50), nullable=True)
    cntr_nationality = db.Column(db.String(50), nullable=True)
    com_cntr_code = db.Column(db.String(50), nullable=True)

class TblProgramType(MISBaseModel):
    """Model for tbl_program_type table"""
    __tablename__ = 'tbl_program_type'
    
    prg_type_id = db.Column(db.Integer, nullable=False, primary_key=True)
    prg_type_full_name = db.Column(db.String(20), nullable=False)
    prg_type_short_name = db.Column(db.String(20), nullable=False)

    def __repr__(self):
        """db.String representation of the TblProgramType model"""
        return f'<TblProgramType {self.prg_type_id}>'

    def to_dict(self):
        """
        Convert model to dictionary for JSON responses

        Returns:
            dict: Model data as dictionary
        """
        return {
            'prg_type_id': self.prg_type_id,
            'prg_type_full_name': self.prg_type_full_name,
            'prg_type_short_name': self.prg_type_short_name
        }