"""
MIS Database Models for EAUR MIS-QuickBooks Integration

Auto-generated from database analysis on 2025-08-22 13:21:06
These models represent the existing MIS database structure.

DO NOT MODIFY THIS FILE MANUALLY - it will be regenerated when the database schema changes.
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Boolean, Float
from sqlalchemy.types import Numeric
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from application.utils.database import db_manager

# Base class for MIS models
MISBase = declarative_base()

class MISBaseModel(MISBase):
    """Base model for MIS database tables"""
    __abstract__ = True

    @classmethod
    def get_session(cls):
        """Get database session for MIS database"""
        return db_manager.get_mis_session()

    @classmethod
    def get_by_id(cls, id_value):
        """
        Get record by ID with error handling

        Args:
            id_value: The ID to search for

        Returns:
            Model instance or None if not found
        """
        try:
            with cls.get_session() as session:
                # Get the primary key column name
                primary_key = cls.__table__.primary_key.columns.keys()[0]
                return session.query(cls).filter(getattr(cls, primary_key) == id_value).first()
        except Exception as e:
            from flask import current_app
            current_app.logger.error(f"Error getting {cls.__name__} by ID {id_value}: {str(e)}")
            return []

    def to_dict(self):
        """
        Convert model to dictionary for JSON responses

        Returns:
            dict: Model data as dictionary
        """
        result = {}
        for column in self.__table__.columns:
            value = getattr(self, column.name)
            # Handle datetime objects
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
    module_id = Column(Integer, nullable=False, primary_key=True)
    moduleType_Id = Column(String, nullable=False)
    module_categoryId = Column(String, nullable=False)
    acad_cycle_id = Column(String)
    curculum_Id = Column(String, nullable=False)
    level_id = Column(String, nullable=False)
    splz_id = Column(String, nullable=False)
    module_code = Column(String(15), nullable=False)
    module_name = Column(String(70), nullable=False)
    module_credits = Column(String, nullable=False)
    module_hours = Column(String)
    time = Column(String)
    recorded_date = Column(DateTime)
    user_id = Column(String(20), nullable=False)
    status_Id = Column(Integer, nullable=False)
    Situation = Column(String(50))

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
    
    id = Column(Integer, nullable=False, primary_key=True)
    trans_code = Column(String(200))
    reg_no = Column(String(200))
    level_id = Column(Integer)
    bank_id = Column(Integer)
    slip_no = Column(String(200))
    user = Column(String(20))
    acad_cycle_id = Column(String(100))
    date = Column(String(50))
    fee_category = Column(String(50))
    amount = Column(Float)
    description = Column(Text)
    recorded_date = Column(DateTime, default='current_timestamp()')
    Remark = Column(String(200))
    action = Column(String(100))
    external_transaction_id = Column(Text)
    payment_chanel = Column(String(100))
    payment_notifi = Column(String(100))
    invoi_ref = Column(String)
    QuickBk_Status = Column(Integer, default='0')
    pushed_by = Column(String(200))
    pushed_date = Column(DateTime)

    # Relationships will be added after analyzing foreign keys

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
            'level_id': self.level_id,
            'bank_id': self.bank_id,
            'slip_no': self.slip_no,
            'user': self.user,
            'acad_cycle_id': self.acad_cycle_id,
            'date': self.date,
            'fee_category': self.fee_category,
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
            'pushed_date': self.pushed_date.isoformat() if self.pushed_date else None
        }

class TblBank(MISBaseModel):
    """Model for tbl_bank table"""
    __tablename__ = 'tbl_bank'
    
    bank_id = Column(Integer, nullable=False, primary_key=True)
    bank_code = Column(String(10), nullable=False)
    bank_name = Column(String(100), nullable=False)
    bank_branch = Column(String(100), nullable=False)
    account_no = Column(String(30))
    currency = Column(String(10), nullable=False)
    status = Column(String, nullable=False)
    quickbook = Column(String)

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
            'quickbook': self.quickbook
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
    
    camp_id = Column(Integer, nullable=False, primary_key=True)
    camp_full_name = Column(String(50), nullable=False)
    camp_short_name = Column(String(20), nullable=False)
    camp_city = Column(String(30), nullable=False)
    camp_yor = Column(DateTime, nullable=False)
    camp_active = Column(Integer, nullable=False)
    camp_comments = Column(String(255), nullable=False)

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

    id = Column(Integer, nullable=False, primary_key=True)
    reg_no = Column(String(200))
    level_id = Column(Integer, ForeignKey("tbl_level.level_id"))
    fee_category = Column(Integer, ForeignKey("tbl_income_category.id"))
    module_id = Column(Integer, ForeignKey("modules.module_id"))
    Rpt_Id = Column(Integer)
    dept = Column(Float)
    credit = Column(Float)
    balance = Column(String(200))
    invoice_date = Column(DateTime)
    comment = Column(String(900))
    user = Column(String(20))
    date = Column(DateTime)
    intake_id = Column(Integer, ForeignKey("tbl_intake.intake_id"))
    QuickBk_Status = Column(Integer, default='0')
    pushed_by = Column(String(200))
    pushed_date = Column(DateTime)

    # Define relationships between levels, modules, and intakes
    # This is not implemented on database level, we need them for joins
    level = relationship("TblLevel", backref="invoices", lazy='joined')
    module = relationship("Modules", backref="invoices", lazy='joined')
    intake = relationship("TblIntake", backref="invoices", lazy='joined')
    fee_category_rel = relationship("TblIncomeCategory", backref="invoices", lazy='joined')


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
            'user': self.user,
            'date': self.date.isoformat() if self.date else None,
            'intake_id': self.intake_id,
            'intake_details': self.intake.to_dict() if self.intake else [],
            'QuickBk_Status': self.QuickBk_Status,
            'pushed_by': self.pushed_by,
            'pushed_date': self.pushed_date.isoformat() if self.pushed_date else None
        }

class TblIncomeCategory(MISBaseModel):
    """Model for tbl_income_category table"""
    __tablename__ = 'tbl_income_category'

    id = Column(Integer, nullable=False, primary_key=True)
    invTypeId = Column(String, nullable=False)
    camp_id = Column(Integer, ForeignKey("tbl_campus.camp_id"))
    prg_type = Column(String, nullable=False)
    splz_id = Column(Integer, ForeignKey("tbl_specialization.splz_id"))
    name = Column(String(100), nullable=False)
    amount = Column(String, nullable=False)
    description = Column(String, nullable=False)
    recorded_date = Column(DateTime)
    recorded_by = Column(String(100), nullable=False)
    status_Id = Column(Integer, nullable=False)
    category = Column(String(200), nullable=False)
    QuickBk_ctgId = Column(Integer)

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
            'QuickBk_ctgId': self.QuickBk_ctgId
        }

class TblLevel(MISBaseModel):
    """Model for tbl_level table"""
    __tablename__ = 'tbl_level'
    
    level_id = Column(Integer, nullable=False, primary_key=True)
    level_no = Column(String(20), nullable=False)
    level_full_name = Column(String(50), nullable=False)
    level_short_name = Column(String(10), nullable=False)
    amount = Column(String(20), nullable=False)
    level_exit_award = Column(String, nullable=False)
    status = Column(Integer, nullable=False)

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
    
    appl_Id = Column(Integer, nullable=False, primary_key=True)
    tracking_id = Column(String(200))
    reg_no = Column(String(200))
    first_name = Column(String(200))
    middlename = Column(String(200))
    family_name = Column(String(200))
    dob = Column(DateTime)
    sex = Column(String(6))
    phone1 = Column(String(50))
    email1 = Column(String(100))
    country_of_birth = Column(String)
    nation_Id_passPort_no = Column(String(200))
    present_nationality = Column(String)
    sector = Column(String)
    father_name = Column(String(500))
    mother_name = Column(String(500))
    guardian_phone = Column(String(50))
    serious_illness = Column(String(20))
    serious_illness_comment = Column(Text)
    blood_pressure = Column(String(20))
    diabetes = Column(String(20))
    high_school_name = Column(String(500))
    combination = Column(String(500))
    completed_year = Column(String)
    school_categ_Id = Column(String)
    index_number = Column(String(200))
    grade_marks = Column(String(200))
    principle_passes = Column(String(300))
    n_principle_passes = Column(String)
    camp_id = Column(String)
    opt_1 = Column(String)
    opt_2 = Column(String)
    opt_3 = Column(String)
    opt_oriented = Column(String)
    intake_id = Column(String)
    level_id = Column(String)
    prg_mode_id = Column(String)
    spon_id = Column(String)
    StdentTrnsfr = Column(String(20))
    about_Id = Column(String)
    appl_date = Column(DateTime)
    NID_doc = Column(String(1000))
    highSchool_doc = Column(String(1000))
    transcript_doc = Column(String(1000))
    HoD_comment = Column(Text)
    HoD_user = Column(String(200))
    HoD_resp_date = Column(DateTime)
    respont_by = Column(String(100))
    response_date = Column(DateTime)
    response_comment = Column(Text)
    status = Column(Integer)

    # Relationships will be added after analyzing foreign keys

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
            'status': self.status
        }

class TblPersonalUg(MISBaseModel):
    """Model for tbl_personal_ug table"""
    __tablename__ = 'tbl_personal_ug'
    
    per_id_ug = Column(Integer, nullable=False, primary_key=True)
    reg_no = Column(String(200), nullable=False)
    prg_type = Column(String, nullable=False)
    sex = Column(String(6))
    fname = Column(String(250))
    middlename = Column(String(200))
    lname = Column(String(100))
    dob = Column(DateTime)
    marital_status = Column(String(7))
    father_name = Column(String(50))
    mother_name = Column(String(50))
    national_id = Column(String(20))
    cntr_id = Column(String, nullable=False)
    VISA_Expiration_date = Column(DateTime)
    b_province = Column(String(50), nullable=False)
    b_district = Column(String(20), nullable=False)
    b_sector = Column(String(50), nullable=False)
    b_cell = Column(String(50), nullable=False)
    b_village = Column(String(50), nullable=False)
    district = Column(String(50))
    sector = Column(String(50))
    cell = Column(String(200))
    village = Column(String(200))
    province = Column(String(50))
    nationality = Column(String(50))
    phone1 = Column(String(100))
    phone2 = Column(String(20))
    email1 = Column(String(50))
    email2 = Column(String(50))
    combination = Column(String(100))
    principle_passes = Column(String(500))
    no_principle_passes = Column(String, nullable=False)
    year_of_compleshed = Column(String)
    max_or_grad = Column(Float, nullable=False)
    reg_date = Column(DateTime)
    secondary_notes = Column(Text, nullable=False)
    secondary_school = Column(String(50), nullable=False)
    student_updating = Column(String(10))
    registered_by = Column(String(100))
    updated_date = Column(DateTime)
    updated_by = Column(String(100))
    transf_status = Column(String(50))
    about_Id = Column(String)
    certificate_doc = Column(String(150))
    auth_ccs_nnc = Column(String, nullable=False, default='0')
    qk_id = Column(String)
    pushed_by = Column(String(200))
    pushed_date = Column(DateTime)

    # Relationships will be added after analyzing foreign keys

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
            'prg_type': self.prg_type,
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
            'VISA_Expiration_date': self.VISA_Expiration_date.isoformat() if self.VISA_Expiration_date else None,
            'b_province': self.b_province,
            'b_district': self.b_district,
            'b_sector': self.b_sector,
            'b_cell': self.b_cell,
            'b_village': self.b_village,
            'district': self.district,
            'sector': self.sector,
            'cell': self.cell,
            'village': self.village,
            'province': self.province,
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
            'pushed_date': self.pushed_date.isoformat() if self.pushed_date else None
        }

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
                    return student.to_dict()
                return []
        except Exception as e:
            from flask import current_app
            current_app.logger.error(f"Error getting student details for reg_no {reg_no}: {str(e)}")
            return []

class TblRegisterProgramUg(MISBaseModel):
    """Model for tbl_register_program_ug table"""
    __tablename__ = 'tbl_register_program_ug'
    
    reg_prg_id = Column(Integer, nullable=False, primary_key=True)
    reg_no = Column(String(200), nullable=False)
    intake_id = Column(String, nullable=False)
    prg_id = Column(String, nullable=False)
    splz_id = Column(String, nullable=False)
    level_id = Column(String, nullable=False)
    prg_mode_id = Column(String, nullable=False)
    prg_type = Column(String, nullable=False)
    year_id = Column(String)
    sem1 = Column(String)
    sem2 = Column(String)
    sem3 = Column(String)
    camp_id = Column(String, nullable=False)
    reg_date = Column(DateTime)
    reg_comments = Column(String(255))
    spon_id = Column(String)
    reg_active = Column(Integer)
    status_comment = Column(String(400), nullable=False)
    Availability = Column(String, nullable=False)
    pasted_bk = Column(String(11))
    registered_by = Column(String(100))
    updated_date = Column(DateTime)
    updated_by = Column(String(100))
    suspension_date = Column(DateTime)
    suspended_by = Column(String(100))
    auth_ccs_nnc = Column(String)
    qk_id = Column(String)

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
    
    spon_id = Column(Integer, nullable=False, primary_key=True)
    spon_cat_id = Column(String, nullable=False)
    spon_full_name = Column(String(50), nullable=False)
    spon_short_name = Column(String(20), nullable=False)
    sponsor_value = Column(Float)
    reg_fee = Column(Integer)
    tut_fee = Column(Integer)
    indus_fee = Column(Integer)
    tour_fee = Column(Integer)
    thesis_fee = Column(Integer)
    grad_fee = Column(Integer)
    degree_fee = Column(Integer)
    testimony_fee = Column(Integer)
    recorded_date = Column(DateTime)
    user_id = Column(String(100), nullable=False)
    statusId = Column(Integer, nullable=False)

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

    intake_id = Column(Integer, nullable=False, primary_key=True)
    prg_type = Column(String, nullable=False)
    acad_cycle_id = Column(String, nullable=False)
    intake_no = Column(Integer, nullable=False)
    intake_month = Column(String(30), nullable=False)
    intake_start = Column(DateTime, nullable=False)
    intake_end = Column(DateTime, nullable=False)
    app_start = Column(DateTime, nullable=False)
    app_end = Column(DateTime, nullable=False)
    reg_start = Column(DateTime, nullable=False)
    reg_end = Column(DateTime, nullable=False)
    late_reg_end = Column(DateTime, nullable=False)
    late_reg_fee = Column(Integer, nullable=False)
    status = Column(Integer, nullable=False, default='1')

    def __repr__(self):
        """String representation of the TblIntake model"""
        return f'<TblIntake {self.intake_id}>'

class TblSpecialization(MISBaseModel):
    """Model for tbl_specialization table"""
    __tablename__ = 'tbl_specialization'
    
    splz_id = Column(Integer, nullable=False, primary_key=True)
    prg_id = Column(String, nullable=False)
    prg_type = Column(String, nullable=False)
    splz_full_name = Column(String(100), nullable=False)
    splz_short_name = Column(String(50), nullable=False)
    splz_start_level = Column(String, nullable=False)
    degree_name = Column(String(100), nullable=False)
    diploma_name = Column(String(255), nullable=False)
    splz_comments = Column(String(255), nullable=False)
    status = Column(Integer)

    def __repr__(self):
        """String representation of the TblSpecialization model"""
        return f'<TblSpecialization {self.splz_id}>'

       
class TblProgramMode(MISBaseModel):
    """Model for tbl_program_mode table"""
    __tablename__ = 'tbl_program_mode'    
    prg_mode_id = Column(Integer, nullable=False, primary_key=True)
    prg_mode_full_name = Column(String(30), nullable=False)
    prg_mode_short_name = Column(String(10), nullable=False)

    def __repr__(self):
        """String representation of the TblProgramMode model"""
        return f'<TblProgramMode {self.prg_mode_id}>'

