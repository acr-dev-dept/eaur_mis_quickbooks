"""
MIS Database Models for EAUR MIS-QuickBooks Integration

Auto-generated from database analysis on 2025-08-25 14:59:35
These models represent the existing MIS database structure.

DO NOT MODIFY THIS FILE MANUALLY - it will be regenerated when the database schema changes.
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Decimal, ForeignKey, Text, Boolean, Float
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

class Auth2Quickbook(MISBaseModel):
        """Model for Auth_2_quickbook table"""
        __tablename__ = 'Auth_2_quickbook'
        
        id = Column(String, nullable=False)
    auth_mode = Column(String(250), nullable=False)
    client_id = Column(String, nullable=False)
    client_secret = Column(String, nullable=False)
    authorizationRequestUrl = Column(String, nullable=False)
    tokenEndPointUrl = Column(String, nullable=False)
    oauth_scope = Column(String, nullable=False)
    openID_scope = Column(String, nullable=False)
    oauth_redirect_uri = Column(String, nullable=False)
    openID_redirect_uri = Column(String, nullable=False)
    mainPage = Column(String, nullable=False)
    refreshTokenPage = Column(String, nullable=False)
    access_token = Column(String, nullable=False)
    refresh_token = Column(String, nullable=False)
    QBORealmID = Column(String, nullable=False)
    baseUrl = Column(String, nullable=False)
    get_time = Column(DateTime, nullable=False, default='current_timestamp() ON UPDATE current_timestamp()')

        def __repr__(self):
            return f'<Auth2Quickbook (no primary key)>'
    
class ApiAuthorization(MISBaseModel):
        """Model for api_authorization table"""
        __tablename__ = 'api_authorization'
        
        id = Column(String, nullable=False)
    merchant_code = Column(String(200), nullable=False)
    apps = Column(String(200), nullable=False)
    email = Column(String, nullable=False)
    username = Column(String, nullable=False)
    password = Column(String, nullable=False)
    token = Column(String, nullable=False)

        def __repr__(self):
            return f'<ApiAuthorization (no primary key)>'
    
class ApiUserBank(MISBaseModel):
        """Model for api_user_bank table"""
        __tablename__ = 'api_user_bank'
        
        id = Column(String, nullable=False)
    bank_name = Column(String(200), nullable=False)
    Api_token = Column(String(200), nullable=False)
    Option_act = Column(String, nullable=False)

        def __repr__(self):
            return f'<ApiUserBank (no primary key)>'
    
class BankApiPayment(MISBaseModel):
        """Model for bank_api_payment table"""
        __tablename__ = 'bank_api_payment'
        
        id = Column(String, nullable=False)
    regNumber = Column(String(20), nullable=False)
    creditedAccount = Column(String(50), nullable=False)
    bankSlip = Column(String(100), nullable=False)
    amount = Column(Float, nullable=False)
    paymentDate = Column(String(300), nullable=False)
    paymentDescription = Column(String(300), nullable=False)
    currency = Column(String(300), nullable=False)
    transaction_number = Column(String(100), nullable=False)
    Remarks = Column(String(200), nullable=False)
    dates = Column(DateTime, nullable=False, default='current_timestamp()')
    bank_id = Column(String)
    feecategory = Column(String)

        def __repr__(self):
            return f'<BankApiPayment (no primary key)>'
    
class Cron(MISBaseModel):
        """Model for cron table"""
        __tablename__ = 'cron'
        
        id = Column(String, nullable=False)
    created_date = Column(DateTime, nullable=False)

        def __repr__(self):
            return f'<Cron (no primary key)>'
    
class FeeCategory(MISBaseModel):
        """Model for fee_category table"""
        __tablename__ = 'fee_category'
        
        id = Column(String, nullable=False)
    name = Column(String(50), nullable=False)
    description = Column(String(200), nullable=False)
    status = Column(String, nullable=False)

        def __repr__(self):
            return f'<FeeCategory (no primary key)>'
    
class FeeCategoryApi(MISBaseModel):
        """Model for fee_category_api table"""
        __tablename__ = 'fee_category_api'
        
        id = Column(String, nullable=False)
    name = Column(String(200), nullable=False)
    Category = Column(String(200), nullable=False)
    status = Column(String, nullable=False)

        def __repr__(self):
            return f'<FeeCategoryApi (no primary key)>'
    
class Groups(MISBaseModel):
        """Model for groups table"""
        __tablename__ = 'groups'
        
        id = Column(String, nullable=False)
    name = Column(String(20), nullable=False)
    description = Column(String(100), nullable=False)

        def __repr__(self):
            return f'<Groups (no primary key)>'
    
class Intake(MISBaseModel):
        """Model for intake table"""
        __tablename__ = 'intake'
        
        intake_id = Column(String, nullable=False)
    name = Column(String(20), nullable=False)

        def __repr__(self):
            return f'<Intake (no primary key)>'
    
class KeytokenUse(MISBaseModel):
        """Model for keytoken_use table"""
        __tablename__ = 'keytoken_use'
        
        id = Column(String, nullable=False)
    bank_name = Column(String(200), nullable=False)
    Api_token = Column(String(200), nullable=False)
    Option_act = Column(String, nullable=False)

        def __repr__(self):
            return f'<KeytokenUse (no primary key)>'
    
class LoginAttempts(MISBaseModel):
        """Model for login_attempts table"""
        __tablename__ = 'login_attempts'
        
        id = Column(String, nullable=False)
    ip_address = Column(String(15), nullable=False)
    login = Column(String(100), nullable=False)
    time = Column(String)

        def __repr__(self):
            return f'<LoginAttempts (no primary key)>'
    
class Messages(MISBaseModel):
        """Model for messages table"""
        __tablename__ = 'messages'
        
        msg_id = Column(String, nullable=False)
    incoming_msg_id = Column(String, nullable=False)
    outgoing_msg_id = Column(String, nullable=False)
    msg = Column(String(1000), nullable=False)

        def __repr__(self):
            return f'<Messages (no primary key)>'
    
class Modules(MISBaseModel):
        """Model for modules table"""
        __tablename__ = 'modules'
        
        module_id = Column(String, nullable=False)
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

        def __repr__(self):
            return f'<Modules (no primary key)>'
    
class Payment(MISBaseModel):
        """Model for payment table"""
        __tablename__ = 'payment'
        
        id = Column(String, nullable=False)
    trans_code = Column(String(200))
    reg_no = Column(String(200))
    appl_Id = Column(String)
    level_id = Column(String)
    bank_id = Column(String)
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

        def __repr__(self):
            return f'<Payment (no primary key)>'
    
class PaymentAudit(MISBaseModel):
        """Model for payment_audit table"""
        __tablename__ = 'payment_audit'
        
        audit_id = Column(String, nullable=False)
    action_type = Column(String)
    action_time = Column(DateTime, default='current_timestamp()')
    payment_id = Column(String)
    user = Column(String(100))
    old_data = Column(Text)
    new_data = Column(Text)

        def __repr__(self):
            return f'<PaymentAudit (no primary key)>'
    
class PaymentBackUp0704(MISBaseModel):
        """Model for payment_back_up_07_04 table"""
        __tablename__ = 'payment_back_up_07_04'
        
        id = Column(String, nullable=False)
    trans_code = Column(String(200), nullable=False)
    reg_no = Column(String(30), nullable=False)
    level_id = Column(String)
    bank_id = Column(String, nullable=False)
    slip_no = Column(String(200), nullable=False)
    user = Column(String(20), nullable=False)
    acad_cycle_id = Column(String(100))
    date = Column(String(50), nullable=False)
    fee_category = Column(String(50), nullable=False)
    amount = Column(Float, nullable=False)
    description = Column(Text, nullable=False)
    recorded_date = Column(DateTime, nullable=False, default='current_timestamp()')
    Remark = Column(String(200), nullable=False)
    action = Column(String(100))
    external_transaction_id = Column(Text)
    payment_chanel = Column(String(100))
    payment_notifi = Column(String(100))
    invoi_ref = Column(String)

        def __repr__(self):
            return f'<PaymentBackUp0704 (no primary key)>'
    
class PaymentMonitor(MISBaseModel):
        """Model for payment_monitor table"""
        __tablename__ = 'payment_monitor'
        
        id = Column(String, nullable=False)
    ref = Column(String, nullable=False)
    reg_new = Column(String(100), nullable=False)
    reg_old = Column(String(100), nullable=False)
    bank_new = Column(String, nullable=False)
    bank_old = Column(String, nullable=False)
    amount_new = Column(Float, nullable=False)
    amount_old = Column(Float, nullable=False)
    date_new = Column(String(100), nullable=False)
    date_old = Column(String(100), nullable=False)
    user_new = Column(String(100), nullable=False)
    user_old = Column(String(100), nullable=False)
    remark = Column(String(100), nullable=False)

        def __repr__(self):
            return f'<PaymentMonitor (no primary key)>'
    
class Permissions(MISBaseModel):
        """Model for permissions table"""
        __tablename__ = 'permissions'
        
        id = Column(String, nullable=False)
    group_id = Column(String, nullable=False)
    books-index = Column(Integer, default='0')
    books-add = Column(Integer, default='0')
    books-edit = Column(Integer, default='0')
    books-delete = Column(Integer, default='0')
    books-read = Column(Integer, default='0')
    books-getBookDetails = Column(Integer, default='0')
    books-import_csv = Column(Integer, default='0')
    book-print_barcodes = Column(Integer, nullable=False, default='0')
    settings-index = Column(Integer, default='0')
    issued-index = Column(Integer, default='0')
    books-categories = Column(Integer, default='0')
    books-authors = Column(Integer, default='0')
    borrow-index = Column(Integer, default='0')
    borrow-bookreturn = Column(Integer, default='0')
    borrow-borrowed = Column(Integer, default='0')
    settings-sms = Column(Integer, default='0')
    settings-list_db = Column(Integer, default='0')
    settings-backup_db = Column(Integer, default='0')
    settings-restore_db = Column(Integer, default='0')
    settings-remove_db = Column(Integer, default='0')
    auth-index = Column(Integer, default='0')
    auth-create_user = Column(Integer, default='0')
    auth-groups = Column(Integer, default='0')
    auth-edit_group = Column(Integer, default='0')
    auth-member_types = Column(Integer, default='0')
    auth-occupations = Column(Integer, default='0')
    reports-index = Column(Integer, default='0')
    reports-quick_inventory = Column(Integer, default='0')
    delayed-index = Column(Integer, nullable=False, default='0')
    delayed-due_books_json = Column(Integer, nullable=False, default='0')
    delayed-email_templates = Column(Integer, nullable=False, default='0')
    delayed-notify_delayed = Column(Integer, nullable=False, default='0')
    request-index = Column(Integer, nullable=False)
    request-add_requested_books = Column(Integer, nullable=False)
    request-delete_request = Column(Integer, nullable=False)
    request-edit_request = Column(Integer, nullable=False)
    requested_books-index = Column(Integer, nullable=False)
    requested_books-email_templates = Column(Integer, nullable=False)

        def __repr__(self):
            return f'<Permissions (no primary key)>'
    
class Section(MISBaseModel):
        """Model for section table"""
        __tablename__ = 'section'
        
        section_id = Column(String, nullable=False)
    section_name = Column(String(50), nullable=False)

        def __repr__(self):
            return f'<Section (no primary key)>'
    
class Settings(MISBaseModel):
        """Model for settings table"""
        __tablename__ = 'settings'
        
        id = Column(String, nullable=False)
    title = Column(String(50), nullable=False)
    issue_conf = Column(String, nullable=False)
    fine = Column(String, nullable=False)
    issue_limit_days = Column(String, nullable=False)
    issue_limit_books = Column(String, nullable=False)
    language = Column(String(100), nullable=False, default=''english'')
    toggle_rtl = Column(Integer, nullable=False, default='0')
    currency = Column(String(10), nullable=False)
    email = Column(String(30), nullable=False)
    logo = Column(String(50), nullable=False)
    favicon = Column(String(40), nullable=False)
    address = Column(Text, nullable=False)
    phone = Column(String(20), nullable=False)
    title_small = Column(String(10), nullable=False)
    terms_conditions = Column(Text, nullable=False)
    books_custom_fields = Column(Text, nullable=False)
    smtp_host = Column(String(100), nullable=False)
    smtp_user = Column(String(100), nullable=False)
    smtp_pass = Column(String(255), nullable=False)
    smtp_port = Column(String(10), nullable=False, default=''25'')
    version = Column(Decimal)
    issue_limit_days_extendable = Column(Integer, nullable=False)
    notify_delayed_no_days_limit_toggle = Column(Integer, nullable=False)
    email_request = Column(Integer, nullable=False)
    sms_request = Column(Integer, nullable=False)
    front_per_page = Column(String, nullable=False)

        def __repr__(self):
            return f'<Settings (no primary key)>'
    
class SmsSettings(MISBaseModel):
        """Model for sms_settings table"""
        __tablename__ = 'sms_settings'
        
        id = Column(String, nullable=False)
    sms_gateway = Column(String(100), nullable=False)
    auth_id = Column(String(100), nullable=False)
    auth_token = Column(String(255), nullable=False)
    api_id = Column(String(100), nullable=False)
    phone_number = Column(String(50), nullable=False)

        def __repr__(self):
            return f'<SmsSettings (no primary key)>'
    
class TblAboutEaur(MISBaseModel):
        """Model for tbl_about_eaur table"""
        __tablename__ = 'tbl_about_eaur'
        
        about_Id = Column(String, nullable=False)
    info_from = Column(String(300), nullable=False)
    status = Column(Integer, nullable=False)

        def __repr__(self):
            return f'<TblAboutEaur (no primary key)>'
    
class TblAcadCycle(MISBaseModel):
        """Model for tbl_acad_cycle table"""
        __tablename__ = 'tbl_acad_cycle'
        
        acad_cycle_id = Column(String, nullable=False)
    curculum_Id = Column(String, nullable=False)
    no_of_intakes = Column(String, nullable=False)
    intakes_months = Column(String(255), nullable=False)
    no_of_cohorts = Column(String, nullable=False)
    cohort_months = Column(String(255), nullable=False)
    acad_year = Column(String(9), nullable=False)
    active = Column(String, nullable=False)
    status = Column(String, nullable=False)

        def __repr__(self):
            return f'<TblAcadCycle (no primary key)>'
    
class TblAcadGrade(MISBaseModel):
        """Model for tbl_acad_grade table"""
        __tablename__ = 'tbl_acad_grade'
        
        acad_grad_id = Column(String, nullable=False)
    acad_grad_short_name = Column(String(25), nullable=False)
    acad_grad_full_name = Column(String(70), nullable=False)

        def __repr__(self):
            return f'<TblAcadGrade (no primary key)>'
    
class TblAccounts(MISBaseModel):
        """Model for tbl_accounts table"""
        __tablename__ = 'tbl_accounts'
        
        id = Column(String, nullable=False)
    name = Column(String(100), nullable=False)
    balance = Column(String(100), nullable=False)
    account = Column(String(200), nullable=False)
    description = Column(String(250), nullable=False)

        def __repr__(self):
            return f'<TblAccounts (no primary key)>'
    
class TblAdmission(MISBaseModel):
        """Model for tbl_admission table"""
        __tablename__ = 'tbl_admission'
        
        adm_id = Column(String, nullable=False)
    admission_type = Column(String, default='0')
    tracking_id = Column(String(200), nullable=False)
    reg_no = Column(String(200))
    acc_controle_no = Column(String(20))
    intake_id = Column(String, nullable=False)
    adm_date = Column(DateTime)
    family_name = Column(String(50), nullable=False)
    middlename = Column(String(200))
    first_name = Column(String(50), nullable=False)
    sex = Column(String(10))
    amount = Column(String(20), nullable=False)
    deadline_date = Column(DateTime)
    comments = Column(String(255))
    get_Api_reg = Column(String(200), nullable=False)

        def __repr__(self):
            return f'<TblAdmission (no primary key)>'
    
class TblAmountToPay(MISBaseModel):
        """Model for tbl_amount_to_pay table"""
        __tablename__ = 'tbl_amount_to_pay'
        
        m_to_pay_id = Column(String, nullable=False)
    camp_id = Column(String, nullable=False)
    prg_type_Id = Column(String, nullable=False)
    splz_id = Column(String, nullable=False)
    intake_id = Column(String, nullable=False)
    amount = Column(Float, nullable=False)
    tolerance_balance = Column(Float, nullable=False)
    tolerance_expiration_date = Column(DateTime, nullable=False, default=''2019-01-21'')
    date = Column(DateTime, nullable=False)

        def __repr__(self):
            return f'<TblAmountToPay (no primary key)>'
    
class TblAnnoucemt(MISBaseModel):
        """Model for tbl_annoucemt table"""
        __tablename__ = 'tbl_annoucemt'
        
        id = Column(String, nullable=False)
    annoucement = Column(String)
    intake = Column(String(100))
    app_from = Column(DateTime)
    app_to = Column(DateTime)
    reg_from = Column(DateTime)
    reg_to = Column(DateTime)
    late_from = Column(DateTime)
    late_to = Column(DateTime)
    installment = Column(DateTime)
    on_date = Column(DateTime, nullable=False)
    expare_date = Column(DateTime, nullable=False)
    type = Column(Integer, nullable=False)

        def __repr__(self):
            return f'<TblAnnoucemt (no primary key)>'
    
class TblApplicationDegree(MISBaseModel):
        """Model for tbl_application_degree table"""
        __tablename__ = 'tbl_application_degree'
        
        appl_deg_id = Column(String, nullable=False)
    reg_no = Column(String(10), nullable=False)
    intake_id = Column(String, nullable=False)
    applied_for = Column(String, nullable=False)
    date_ = Column(DateTime, nullable=False)

        def __repr__(self):
            return f'<TblApplicationDegree (no primary key)>'
    
class TblAssessmentTimetable(MISBaseModel):
        """Model for tbl_assessment_timetable table"""
        __tablename__ = 'tbl_assessment_timetable'
        
        assessment_Id = Column(String, nullable=False)
    assessment_type = Column(String(150), nullable=False)
    time_table_Id = Column(String, nullable=False)
    att_room_Id = Column(String, nullable=False)
    assessment_date = Column(DateTime, nullable=False)
    assessment_day = Column(String(50))
    assessment_time = Column(String)
    recorded_date = Column(DateTime, nullable=False)
    recorded_by = Column(String(100), nullable=False)
    status_Id = Column(Integer, nullable=False)

        def __repr__(self):
            return f'<TblAssessmentTimetable (no primary key)>'
    
class TblAttCatAverage(MISBaseModel):
        """Model for tbl_att_cat_average table"""
        __tablename__ = 'tbl_att_cat_average'
        
        average_Id = Column(String, nullable=False)
    camp_id = Column(String)
    prg_mode_id = Column(String)
    average = Column(String, nullable=False)
    recorded_by = Column(String(200), nullable=False)
    recorded_date = Column(DateTime, nullable=False)
    status_Id = Column(Integer, nullable=False)

        def __repr__(self):
            return f'<TblAttCatAverage (no primary key)>'
    
class TblAttExamAverage(MISBaseModel):
        """Model for tbl_att_exam_average table"""
        __tablename__ = 'tbl_att_exam_average'
        
        average_Id = Column(String, nullable=False)
    camp_id = Column(String)
    prg_mode_id = Column(String)
    average = Column(String, nullable=False)
    recorded_by = Column(String(200), nullable=False)
    recorded_date = Column(DateTime, nullable=False)
    status_Id = Column(Integer, nullable=False)

        def __repr__(self):
            return f'<TblAttExamAverage (no primary key)>'
    
class TblAttExamBalance(MISBaseModel):
        """Model for tbl_att_exam_balance table"""
        __tablename__ = 'tbl_att_exam_balance'
        
        balance_Id = Column(String, nullable=False)
    camp_id = Column(String, nullable=False)
    balance = Column(String, nullable=False)
    recorded_by = Column(String(200), nullable=False)
    recorded_date = Column(DateTime, nullable=False)
    status_Id = Column(Integer, nullable=False)

        def __repr__(self):
            return f'<TblAttExamBalance (no primary key)>'
    
class TblAttRooms(MISBaseModel):
        """Model for tbl_att_rooms table"""
        __tablename__ = 'tbl_att_rooms'
        
        att_room_Id = Column(String, nullable=False)
    room_name = Column(String(200), nullable=False)
    alwd_nmbr = Column(String, nullable=False)
    camp_id = Column(String)
    status_Id = Column(Integer, nullable=False)

        def __repr__(self):
            return f'<TblAttRooms (no primary key)>'
    
class TblAttSessionAsign(MISBaseModel):
        """Model for tbl_att_session_asign table"""
        __tablename__ = 'tbl_att_session_asign'
        
        att_sess_assig_Id = Column(String, nullable=False)
    att_modl_assig_Id = Column(String, nullable=False)
    att_session_Id = Column(String, nullable=False)
    att_room_Id = Column(String, nullable=False)
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)
    att_days = Column(String, nullable=False)
    user_ID = Column(String(100), nullable=False)
    recorded_date = Column(DateTime, nullable=False)
    status_Id = Column(Integer, nullable=False)

        def __repr__(self):
            return f'<TblAttSessionAsign (no primary key)>'
    
class TblAttSessionTime(MISBaseModel):
        """Model for tbl_att_session_time table"""
        __tablename__ = 'tbl_att_session_time'
        
        att_session_time_Id = Column(String, nullable=False)
    time_in = Column(String, nullable=False)
    time_out = Column(String)
    status_Id = Column(Integer)

        def __repr__(self):
            return f'<TblAttSessionTime (no primary key)>'
    
class TblAttSessionType(MISBaseModel):
        """Model for tbl_att_session_type table"""
        __tablename__ = 'tbl_att_session_type'
        
        att_session_type_Id = Column(String, nullable=False)
    att_session_Id = Column(String, nullable=False)
    prg_mode_id = Column(String, nullable=False)
    status_Id = Column(Integer, nullable=False)
    recorded_date = Column(DateTime, nullable=False)
    recorded_by = Column(String(100), nullable=False)

        def __repr__(self):
            return f'<TblAttSessionType (no primary key)>'
    
class TblAttSessions(MISBaseModel):
        """Model for tbl_att_sessions table"""
        __tablename__ = 'tbl_att_sessions'
        
        att_session_Id = Column(String, nullable=False)
    att_session_name = Column(String(200), nullable=False)
    status_Id = Column(Integer, nullable=False)

        def __repr__(self):
            return f'<TblAttSessions (no primary key)>'
    
class TblAttSessionsTime(MISBaseModel):
        """Model for tbl_att_sessions_time table"""
        __tablename__ = 'tbl_att_sessions_time'
        
        att_sessions_time_Id = Column(String, nullable=False)
    att_session_Id = Column(String, nullable=False)
    time_in = Column(String, nullable=False)
    time_out = Column(String, nullable=False)
    recorded_date = Column(DateTime, nullable=False)
    recorded_by = Column(String(100), nullable=False)
    status_Id = Column(Integer, nullable=False)

        def __repr__(self):
            return f'<TblAttSessionsTime (no primary key)>'
    
class TblAttStudMdlReg(MISBaseModel):
        """Model for tbl_att_stud_mdl_reg table"""
        __tablename__ = 'tbl_att_stud_mdl_reg'
        
        att_stud_mdl_reg_Id = Column(String, nullable=False)
    det_Id = Column(String, nullable=False)
    reg_prg_id = Column(String)
    reg_no = Column(String(50), nullable=False)
    att_session_time_Id = Column(String)
    recorded_date = Column(DateTime, nullable=False)
    recorded_by = Column(String(100))
    status_Id = Column(Integer, nullable=False)
    mdl_status = Column(String(20), default=''1st Time'')
    mdl_comment = Column(Text)

        def __repr__(self):
            return f'<TblAttStudMdlReg (no primary key)>'
    
class TblAttendance(MISBaseModel):
        """Model for tbl_attendance table"""
        __tablename__ = 'tbl_attendance'
        
        att_Id = Column(String, nullable=False)
    att_stud_mdl_reg_Id = Column(String, nullable=False)
    att_Date = Column(DateTime, nullable=False)

        def __repr__(self):
            return f'<TblAttendance (no primary key)>'
    
class TblAttendanceAudit(MISBaseModel):
        """Model for tbl_attendance_audit table"""
        __tablename__ = 'tbl_attendance_audit'
        
        audit_id = Column(String, nullable=False)
    action_type = Column(String)
    attendance_id = Column(String)
    action_time = Column(DateTime, default='current_timestamp()')
    old_data = Column(Text)
    new_data = Column(Text)

        def __repr__(self):
            return f'<TblAttendanceAudit (no primary key)>'
    
class TblAutoInvoiceSettings(MISBaseModel):
        """Model for tbl_auto_invoice_settings table"""
        __tablename__ = 'tbl_auto_invoice_settings'
        
        id = Column(String, nullable=False)
    invoice_date = Column(DateTime, nullable=False)
    user = Column(String(100))

        def __repr__(self):
            return f'<TblAutoInvoiceSettings (no primary key)>'
    
class TblBank(MISBaseModel):
        """Model for tbl_bank table"""
        __tablename__ = 'tbl_bank'
        
        bank_id = Column(String, nullable=False)
    bank_code = Column(String(10), nullable=False)
    bank_name = Column(String(100), nullable=False)
    bank_branch = Column(String(100), nullable=False)
    account_no = Column(String(30))
    currency = Column(String(10), nullable=False)
    status = Column(String, nullable=False)
    quickbook = Column(String)

        def __repr__(self):
            return f'<TblBank (no primary key)>'
    
class TblBankAmount(MISBaseModel):
        """Model for tbl_bank_amount table"""
        __tablename__ = 'tbl_bank_amount'
        
        bankAmountId = Column(String, nullable=False)
    bankId = Column(String, nullable=False)
    bankAmount = Column(String, nullable=False)

        def __repr__(self):
            return f'<TblBankAmount (no primary key)>'
    
class TblBnkSlipRequest(MISBaseModel):
        """Model for tbl_bnk_slip_request table"""
        __tablename__ = 'tbl_bnk_slip_request'
        
        request_Id = Column(String, nullable=False)
    reg_no = Column(String(20), nullable=False)
    reg_prg_id = Column(String, nullable=False)
    student_comment = Column(Text, nullable=False)
    fnc_comment = Column(Text)
    fnc_user = Column(String(100))
    request_date = Column(DateTime, nullable=False)
    request_stus_Id = Column(String)
    statusId = Column(Integer, nullable=False)
    dcsn_Id = Column(String, nullable=False)
    response_date = Column(DateTime)

        def __repr__(self):
            return f'<TblBnkSlipRequest (no primary key)>'
    
class TblBnkSlipRequestDocs(MISBaseModel):
        """Model for tbl_bnk_slip_request_docs table"""
        __tablename__ = 'tbl_bnk_slip_request_docs'
        
        request_doc_Id = Column(String, nullable=False)
    request_Id = Column(String, nullable=False)
    reg_no = Column(String(20), nullable=False)
    reg_prg_id = Column(String, nullable=False)
    doc = Column(String(200))
    statusId = Column(Integer)

        def __repr__(self):
            return f'<TblBnkSlipRequestDocs (no primary key)>'
    
class TblBnkSlipRequestStatus(MISBaseModel):
        """Model for tbl_bnk_slip_request_status table"""
        __tablename__ = 'tbl_bnk_slip_request_status'
        
        stus_Id = Column(String, nullable=False)
    request_stus_name = Column(String(100))

        def __repr__(self):
            return f'<TblBnkSlipRequestStatus (no primary key)>'
    
class TblBookingBooks(MISBaseModel):
        """Model for tbl_booking_books table"""
        __tablename__ = 'tbl_booking_books'
        
        booking_Id = Column(String, nullable=False)
    book_Id = Column(String, nullable=False)
    Qty = Column(String)
    reg_prg_id = Column(String, nullable=False)
    taken_date = Column(DateTime, nullable=False)
    return_date = Column(DateTime, nullable=False)
    real_return_date = Column(DateTime)
    recorded_by = Column(String(100))
    recorded_date = Column(DateTime)
    status = Column(Integer)
    situation = Column(String(50))

        def __repr__(self):
            return f'<TblBookingBooks (no primary key)>'
    
class TblCampus(MISBaseModel):
        """Model for tbl_campus table"""
        __tablename__ = 'tbl_campus'
        
        camp_id = Column(String, nullable=False)
    camp_full_name = Column(String(50), nullable=False)
    camp_short_name = Column(String(20), nullable=False)
    camp_city = Column(String(30), nullable=False)
    camp_yor = Column(DateTime, nullable=False)
    camp_active = Column(Integer, nullable=False)
    camp_comments = Column(String(255), nullable=False)

        def __repr__(self):
            return f'<TblCampus (no primary key)>'
    
class TblCertificate(MISBaseModel):
        """Model for tbl_certificate table"""
        __tablename__ = 'tbl_certificate'
        
        certificate_id = Column(String, nullable=False)
    certificate_no = Column(String(20), nullable=False)
    old_reg_no = Column(String(20), nullable=False)
    reg_no = Column(String(20), nullable=False)
    acad_cycle_id = Column(String, nullable=False)
    grad_cycle_id = Column(String, nullable=False)
    l1_marks = Column(Float, nullable=False)
    cum_marks = Column(Float, nullable=False)
    prg_id = Column(String, nullable=False)
    splz_id = Column(String, nullable=False)
    cont_level = Column(String, nullable=False)
    prg_mode_id = Column(String, nullable=False)
    prg_award_id = Column(String, nullable=False)
    grade_class = Column(String(100), nullable=False)
    issue_date = Column(DateTime, nullable=False)

        def __repr__(self):
            return f'<TblCertificate (no primary key)>'
    
class TblClearanceDocs(MISBaseModel):
        """Model for tbl_clearance_docs table"""
        __tablename__ = 'tbl_clearance_docs'
        
        clrnc_doc_Id = Column(String, nullable=False)
    clrnc_Id = Column(String, nullable=False)
    reg_no = Column(String(20), nullable=False)
    reg_prg_id = Column(String, nullable=False)
    doc = Column(String(200))
    statusId = Column(Integer)

        def __repr__(self):
            return f'<TblClearanceDocs (no primary key)>'
    
class TblClearanceStatus(MISBaseModel):
        """Model for tbl_clearance_status table"""
        __tablename__ = 'tbl_clearance_status'
        
        clrnc_stus_Id = Column(String, nullable=False)
    clrnc_stus_name = Column(String(100))

        def __repr__(self):
            return f'<TblClearanceStatus (no primary key)>'
    
class TblContractType(MISBaseModel):
        """Model for tbl_contract_type table"""
        __tablename__ = 'tbl_contract_type'
        
        contr_type_id = Column(String, nullable=False)
    contr_name = Column(String(50), nullable=False)

        def __repr__(self):
            return f'<TblContractType (no primary key)>'
    
class TblCountry(MISBaseModel):
        """Model for tbl_country table"""
        __tablename__ = 'tbl_country'
        
        cntr_id = Column(String, nullable=False)
    cntr_code = Column(String(50))
    cntr_name = Column(String(50))
    cntr_nationality = Column(String(50))
    com_cntr_code = Column(String(50))

        def __repr__(self):
            return f'<TblCountry (no primary key)>'
    
class TblCumTranscripts(MISBaseModel):
        """Model for tbl_cum_transcripts table"""
        __tablename__ = 'tbl_cum_transcripts'
        
        cum_trans_no = Column(String, nullable=False)
    reg_no = Column(String(100), nullable=False)
    issue_date = Column(DateTime, nullable=False)
    re_issue_date = Column(DateTime)
    comments = Column(String)
    user_Id = Column(String(100))
    recorded_date = Column(DateTime)

        def __repr__(self):
            return f'<TblCumTranscripts (no primary key)>'
    
class TblCurriculum(MISBaseModel):
        """Model for tbl_curriculum table"""
        __tablename__ = 'tbl_curriculum'
        
        curculum_Id = Column(String, nullable=False)
    acad_cycle_id = Column(String, nullable=False)
    curculum_name = Column(String(300))
    recorded_date = Column(DateTime, nullable=False)
    recorded_by = Column(String(200), nullable=False)
    status_Id = Column(Integer, nullable=False)
    graduation_status = Column(String(15), nullable=False)

        def __repr__(self):
            return f'<TblCurriculum (no primary key)>'
    
class TblCutAccount(MISBaseModel):
        """Model for tbl_cut_account table"""
        __tablename__ = 'tbl_cut_account'
        
        roll_id = Column(String, nullable=False)
    account_cut = Column(String(100), nullable=False)
    bank_id = Column(String, nullable=False)
    roll_name = Column(String(100), nullable=False)
    status = Column(String, nullable=False, default='1')
    time = Column(DateTime, nullable=False, default='current_timestamp() ON UPDATE current_timestamp()')

        def __repr__(self):
            return f'<TblCutAccount (no primary key)>'
    
class TblDedAllowType(MISBaseModel):
        """Model for tbl_ded_allow_type table"""
        __tablename__ = 'tbl_ded_allow_type'
        
        type_Id = Column(String, nullable=False)
    type_name = Column(String(100), nullable=False)
    status = Column(Integer, nullable=False)

        def __repr__(self):
            return f'<TblDedAllowType (no primary key)>'
    
class TblDeductionAllowances(MISBaseModel):
        """Model for tbl_deduction_allowances table"""
        __tablename__ = 'tbl_deduction_allowances'
        
        ded_allow_Id = Column(String, nullable=False)
    type_Id = Column(String, nullable=False)
    name = Column(String(200), nullable=False)
    status = Column(Integer, nullable=False)

        def __repr__(self):
            return f'<TblDeductionAllowances (no primary key)>'
    
class TblDeductionsAllowancePercentages(MISBaseModel):
        """Model for tbl_deductions_allowance_percentages table"""
        __tablename__ = 'tbl_deductions_allowance_percentages'
        
        percentage_Id = Column(String, nullable=False)
    ded_allow_Id = Column(String, nullable=False)
    percentage_rssb_employer = Column(String(50), nullable=False)
    percentage_rssb_employee = Column(String(50), nullable=False)
    percentage_rssb_maternity_employer = Column(String(50), nullable=False)
    percentage_rssb_maternity_employee = Column(String(50), nullable=False)
    percentage_transport_allowance = Column(String(50), nullable=False)
    percentage_house_allowance = Column(String(50), nullable=False)
    percentage_basic_salary = Column(String(50), nullable=False)
    status = Column(Integer, nullable=False)
    active_date = Column(DateTime, nullable=False)
    user_Id = Column(String(100), nullable=False)

        def __repr__(self):
            return f'<TblDeductionsAllowancePercentages (no primary key)>'
    
class TblDepartment(MISBaseModel):
        """Model for tbl_department table"""
        __tablename__ = 'tbl_department'
        
        dept_id = Column(String, nullable=False)
    fac_id = Column(String, nullable=False)
    dept_full_name = Column(String(100), nullable=False)
    dept_short_name = Column(String(20), nullable=False)
    dept_comments = Column(String(255), nullable=False)
    status_Id = Column(String, nullable=False)

        def __repr__(self):
            return f'<TblDepartment (no primary key)>'
    
class TblDiploma(MISBaseModel):
        """Model for tbl_diploma table"""
        __tablename__ = 'tbl_diploma'
        
        diploma_id = Column(String, nullable=False)
    diploma_no = Column(String(20), nullable=False)
    old_reg_no = Column(String(20), nullable=False)
    reg_no = Column(String(20), nullable=False)
    acad_cycle_id = Column(String, nullable=False)
    grad_cycle_id = Column(String, nullable=False)
    l1_marks = Column(Float, nullable=False)
    l2_marks = Column(Float, nullable=False)
    l3_marks = Column(Float, nullable=False)
    cum_marks = Column(Float, nullable=False)
    prg_id = Column(String, nullable=False)
    splz_id = Column(String, nullable=False)
    cont_level = Column(String, nullable=False)
    prg_award_id = Column(String, nullable=False)
    grade_class = Column(String(100), nullable=False)
    issue_date = Column(DateTime, nullable=False)

        def __repr__(self):
            return f'<TblDiploma (no primary key)>'
    
class TblDiplomaCourse(MISBaseModel):
        """Model for tbl_diploma_course table"""
        __tablename__ = 'tbl_diploma_course'
        
        dp_id = Column(String, nullable=False)
    no = Column(String, nullable=False)
    prg_type = Column(String, nullable=False)
    fac_id = Column(String, nullable=False)
    dp_full_name = Column(String(100), nullable=False)
    dp_short_name = Column(String(30), nullable=False)
    dp_yor = Column(DateTime, nullable=False)
    duration_months = Column(String(11), nullable=False)
    partner_id = Column(String, nullable=False)
    id = Column(String, nullable=False)

        def __repr__(self):
            return f'<TblDiplomaCourse (no primary key)>'
    
class TblDistrict(MISBaseModel):
        """Model for tbl_district table"""
        __tablename__ = 'tbl_district'
        
        district_id = Column(String, nullable=False)
    district_name = Column(String(50), nullable=False)
    province_id = Column(String, nullable=False)

        def __repr__(self):
            return f'<TblDistrict (no primary key)>'
    
class TblEmploymentProgress(MISBaseModel):
        """Model for tbl_employment_progress table"""
        __tablename__ = 'tbl_employment_progress'
        
        progress_Id = Column(String, nullable=False)
    empl_type_Id = Column(String, nullable=False)
    user_Id = Column(String, nullable=False)
    acad_cycle_id = Column(String, nullable=False)
    recorded_date = Column(DateTime, nullable=False)
    recorded_by = Column(String(200), nullable=False)
    updated_date = Column(DateTime)
    updated_by = Column(String(200))
    status_Id = Column(Integer, nullable=False)

        def __repr__(self):
            return f'<TblEmploymentProgress (no primary key)>'
    
class TblEmploymentType(MISBaseModel):
        """Model for tbl_employment_type table"""
        __tablename__ = 'tbl_employment_type'
        
        empl_type_Id = Column(String, nullable=False)
    empl_name = Column(String(200))
    empl_status = Column(Integer, nullable=False)

        def __repr__(self):
            return f'<TblEmploymentType (no primary key)>'
    
class TblEmploymentWorkload(MISBaseModel):
        """Model for tbl_employment_workload table"""
        __tablename__ = 'tbl_employment_workload'
        
        empl_worload_Id = Column(String, nullable=False)
    empl_workload_name = Column(String(200))
    empl_workload_hours = Column(String, nullable=False)
    empl_workload_status = Column(Integer, nullable=False)

        def __repr__(self):
            return f'<TblEmploymentWorkload (no primary key)>'
    
class TblExpense(MISBaseModel):
        """Model for tbl_expense table"""
        __tablename__ = 'tbl_expense'
        
        id = Column(String, nullable=False)
    name = Column(String(100), nullable=False)
    amount = Column(String(100), nullable=False)
    reference = Column(String(100), nullable=False)
    expense_date = Column(DateTime, nullable=False)
    account = Column(String(100), nullable=False)
    category = Column(String(100), nullable=False)
    description = Column(String(100), nullable=False)
    file = Column(String(100), nullable=False)

        def __repr__(self):
            return f'<TblExpense (no primary key)>'
    
class TblExpenseCategory(MISBaseModel):
        """Model for tbl_expense_category table"""
        __tablename__ = 'tbl_expense_category'
        
        id = Column(String, nullable=False)
    name = Column(String(50), nullable=False)
    description = Column(String, nullable=False)

        def __repr__(self):
            return f'<TblExpenseCategory (no primary key)>'
    
class TblFaculty(MISBaseModel):
        """Model for tbl_faculty table"""
        __tablename__ = 'tbl_faculty'
        
        fac_id = Column(String, nullable=False)
    prg_type = Column(String, nullable=False)
    fac_full_name = Column(String(100), nullable=False)
    fac_short_name = Column(String(30), nullable=False)
    fac_title = Column(String(10), nullable=False)
    fac_comments = Column(String(255), nullable=False)
    status_Id = Column(String, nullable=False)

        def __repr__(self):
            return f'<TblFaculty (no primary key)>'
    
class TblFeeStructure(MISBaseModel):
        """Model for tbl_fee_structure table"""
        __tablename__ = 'tbl_fee_structure'
        
        fee_struct_id = Column(String, nullable=False)
    acad_cycle_id = Column(String, nullable=False)
    service_code = Column(String, nullable=False)
    currency = Column(String(10), nullable=False)
    amount = Column(String, nullable=False)
    comments = Column(Text, nullable=False)

        def __repr__(self):
            return f'<TblFeeStructure (no primary key)>'
    
class TblFinanceRecords(MISBaseModel):
        """Model for tbl_finance_records table"""
        __tablename__ = 'tbl_finance_records'
        
        id = Column(String, nullable=False)
    reg_no = Column(String(20), nullable=False)
    debit_id = Column(String)
    credit_id = Column(String)
    debit_amount = Column(Float)
    credit_amount = Column(Float)
    level_id = Column(String, nullable=False)
    fee_category = Column(String, nullable=False)
    bank_id = Column(String)
    slip_no = Column(String(100))
    date = Column(DateTime)

        def __repr__(self):
            return f'<TblFinanceRecords (no primary key)>'
    
class TblFormAcReference(MISBaseModel):
        """Model for tbl_form_ac_reference table"""
        __tablename__ = 'tbl_form_ac_reference'
        
        acReference_Id = Column(String, nullable=False)
    reg_no = Column(String(20), nullable=False)
    reg_prg_id = Column(String, nullable=False)
    student_comment = Column(Text)
    exm_comment = Column(Text)
    exm_user = Column(String(200))
    rgstr_comment = Column(Text)
    rgstr_user = Column(String(200))
    lbry_comment = Column(Text)
    lbry_user = Column(String(100))
    fnc_comment = Column(Text)
    fnc_user = Column(String(200))
    request_date = Column(DateTime, nullable=False)
    reg_request_stus_Id = Column(String, nullable=False)
    statusId = Column(String, nullable=False)
    dcsn_Id = Column(String, nullable=False)

        def __repr__(self):
            return f'<TblFormAcReference (no primary key)>'
    
class TblFormAcReferenceCategory(MISBaseModel):
        """Model for tbl_form_ac_reference_category table"""
        __tablename__ = 'tbl_form_ac_reference_category'
        
        refCateg_Id = Column(String, nullable=False)
    acReference_Id = Column(String, nullable=False)
    reg_no = Column(String(100), nullable=False)
    reg_prg_id = Column(String, nullable=False)
    fee_category_Id = Column(String, nullable=False)

        def __repr__(self):
            return f'<TblFormAcReferenceCategory (no primary key)>'
    
class TblFormAcReferenceDocs(MISBaseModel):
        """Model for tbl_form_ac_reference_docs table"""
        __tablename__ = 'tbl_form_ac_reference_docs'
        
        docId = Column(String, nullable=False)
    refCateg_Id = Column(String, nullable=False)
    reg_no = Column(String(200), nullable=False)
    reg_prg_id = Column(String, nullable=False)
    doc = Column(Text, nullable=False)
    statusId = Column(String, nullable=False)

        def __repr__(self):
            return f'<TblFormAcReferenceDocs (no primary key)>'
    
class TblFormAdmission(MISBaseModel):
        """Model for tbl_form_admission table"""
        __tablename__ = 'tbl_form_admission'
        
        FrmAdm_Id = Column(String, nullable=False)
    reg_prg_id = Column(String, nullable=False)
    reg_no = Column(String(100), nullable=False)
    Student_comment = Column(Text)
    request_date = Column(DateTime, nullable=False)
    status = Column(String(50))
    decision = Column(Integer)

        def __repr__(self):
            return f'<TblFormAdmission (no primary key)>'
    
class TblFormCampProgr(MISBaseModel):
        """Model for tbl_form_camp_progr table"""
        __tablename__ = 'tbl_form_camp_progr'
        
        formCampProgram_Id = Column(String, nullable=False)
    reg_no = Column(String(20), nullable=False)
    reg_prg_id = Column(String, nullable=False)
    campRequested_Id = Column(String, nullable=False)
    progRequested_Id = Column(String, nullable=False)
    student_comment = Column(Text)
    lbry_comment = Column(Text)
    lbry_user = Column(String(100))
    exm_comment = Column(Text)
    exm_user = Column(String(200))
    fnc_comment = Column(Text)
    fnc_user = Column(String(200))
    hod_comment = Column(Text, nullable=False)
    hod_user = Column(String(100), nullable=False)
    rgstr_comment = Column(Text)
    rgstr_user = Column(String(200))
    request_date = Column(DateTime, nullable=False)
    reg_request_stus_Id = Column(String, nullable=False)
    statusId = Column(String, nullable=False)
    dcsn_Id = Column(String, nullable=False)

        def __repr__(self):
            return f'<TblFormCampProgr (no primary key)>'
    
class TblFormCampProgrDocs(MISBaseModel):
        """Model for tbl_form_camp_progr_docs table"""
        __tablename__ = 'tbl_form_camp_progr_docs'
        
        docId = Column(String, nullable=False)
    formCampProgram_Id = Column(String, nullable=False)
    reg_no = Column(String(200), nullable=False)
    reg_prg_id = Column(String, nullable=False)
    doc = Column(Text, nullable=False)
    statusId = Column(String, nullable=False)

        def __repr__(self):
            return f'<TblFormCampProgrDocs (no primary key)>'
    
class TblFormDefense(MISBaseModel):
        """Model for tbl_form_defense table"""
        __tablename__ = 'tbl_form_defense'
        
        FrmDfns_Id = Column(String, nullable=False)
    reg_prg_id = Column(String, nullable=False)
    acad_cycle_id = Column(String)
    reg_no = Column(String(100), nullable=False)
    request_date = Column(DateTime, nullable=False)
    hod_user = Column(String(200))
    hod_comment = Column(Text)
    hod_response_date = Column(DateTime)
    Fn_user = Column(String(200))
    Fn_comment = Column(Text)
    Fn_resp_date = Column(DateTime)
    Rg_user = Column(String(100))
    Rg_comment = Column(Text)
    Rg_resp_date = Column(DateTime)
    status = Column(String(50))
    decision = Column(Integer, nullable=False, default='0')

        def __repr__(self):
            return f'<TblFormDefense (no primary key)>'
    
class TblFormGraduation(MISBaseModel):
        """Model for tbl_form_graduation table"""
        __tablename__ = 'tbl_form_graduation'
        
        FrmGrdtn_Id = Column(String, nullable=False)
    reg_prg_id = Column(String, nullable=False)
    reg_no = Column(String(100), nullable=False)
    request_date = Column(DateTime, nullable=False)
    library_user = Column(String(200))
    library_comment = Column(Text)
    library_response_date = Column(DateTime)
    Fn_user = Column(String(200))
    Fn_comment = Column(Text)
    Fn_resp_date = Column(DateTime)
    Rg_user = Column(String(100))
    Rg_comment = Column(Text)
    Rg_resp_date = Column(DateTime)
    status = Column(String(50))
    decision = Column(Integer, nullable=False, default='0')

        def __repr__(self):
            return f'<TblFormGraduation (no primary key)>'
    
class TblFormGraduationGown(MISBaseModel):
        """Model for tbl_form_graduation_gown table"""
        __tablename__ = 'tbl_form_graduation_gown'
        
        FrmGrdtnGwn_Id = Column(String, nullable=False)
    grad_cycle_id = Column(String, nullable=False)
    camp_id = Column(String, nullable=False)
    reg_prg_id = Column(String, nullable=False)
    reg_no = Column(String(100), nullable=False)
    Student_comment = Column(Text)
    request_date = Column(DateTime, nullable=False)
    status = Column(String(50))
    Gown_status = Column(String(30))
    taken_date = Column(DateTime)
    recorded_by = Column(String(100))
    Gown_returned_status = Column(String(50))
    returned_date = Column(DateTime)
    return_recorded_by = Column(String(100))
    Degree_status = Column(String(50))
    Degree_taken_date = Column(DateTime)
    Degree_recorded_by = Column(String(100))
    decision = Column(Integer)

        def __repr__(self):
            return f'<TblFormGraduationGown (no primary key)>'
    
class TblFormInternship(MISBaseModel):
        """Model for tbl_form_internship table"""
        __tablename__ = 'tbl_form_internship'
        
        FrmIntrnshp_Id = Column(String, nullable=False)
    reg_prg_id = Column(String, nullable=False)
    reg_no = Column(String(100), nullable=False)
    ExpInstitution = Column(String(200))
    Institution_person_contact_name = Column(String(200))
    Institution_contact_phone = Column(String(200))
    sector_id = Column(String, nullable=False)
    Student_comment = Column(Text)
    StrtDate = Column(DateTime)
    EndDate = Column(DateTime)
    request_date = Column(DateTime, nullable=False)
    Sprvsn_Id = Column(String(200))
    Institution_marks = Column(Float)
    Vstng_Sprvsn_marks = Column(Float)
    Intrnshp_report_marks = Column(Float)
    HoD_user = Column(String(200))
    HoD_comment = Column(Text)
    HoD_resp_date = Column(DateTime)
    Career_user = Column(String(100))
    Career_comment = Column(Text)
    Career_resp_date = Column(DateTime)
    status = Column(String(50))
    decision = Column(Integer, nullable=False, default='0')

        def __repr__(self):
            return f'<TblFormInternship (no primary key)>'
    
class TblFormMultiRequest(MISBaseModel):
        """Model for tbl_form_multi_request table"""
        __tablename__ = 'tbl_form_multi_request'
        
        form_req_Id = Column(String, nullable=False)
    request_type_Id = Column(String, nullable=False)
    reg_prg_id = Column(String, nullable=False)
    reg_no = Column(String(100), nullable=False)
    level_id = Column(String)
    att_stud_mdl_reg_Id = Column(String)
    module_id = Column(String, nullable=False)
    student_comment = Column(Text)
    request_date = Column(DateTime, nullable=False)
    library_user = Column(String(100))
    library_date = Column(DateTime)
    library_comment = Column(Text)
    hod_user = Column(String(100))
    hod_date = Column(DateTime)
    hod_comment = Column(Text)
    registration_user = Column(String(100))
    registration_date = Column(DateTime)
    registration_comment = Column(Text)
    finance_user = Column(String(100))
    finance_date = Column(DateTime)
    finance_comment = Column(Text)
    dvca_user = Column(String(100))
    dvca_date = Column(DateTime)
    dvca_comment = Column(Text)
    status_Id = Column(Integer)
    doc_status = Column(String(100))
    printed_date = Column(DateTime)
    printed_by = Column(String(100))

        def __repr__(self):
            return f'<TblFormMultiRequest (no primary key)>'
    
class TblFormRecommendation(MISBaseModel):
        """Model for tbl_form_recommendation table"""
        __tablename__ = 'tbl_form_recommendation'
        
        FrmRecm_Id = Column(String, nullable=False)
    reg_prg_id = Column(String, nullable=False)
    reg_no = Column(String(100), nullable=False)
    recom_type_Id = Column(String)
    Student_comment = Column(Text)
    request_date = Column(DateTime, nullable=False)
    status = Column(String(50))
    decision = Column(Integer)

        def __repr__(self):
            return f'<TblFormRecommendation (no primary key)>'
    
class TblFormRemarkingExam(MISBaseModel):
        """Model for tbl_form_remarking_exam table"""
        __tablename__ = 'tbl_form_remarking_exam'
        
        Rmrk_exam_Id = Column(String, nullable=False)
    reg_no = Column(String(20), nullable=False)
    reg_prg_id = Column(String, nullable=False)
    module_id = Column(String)
    unity_title = Column(Text)
    intake_id = Column(String)
    lecturer_id = Column(String)
    student_comment = Column(Text)
    fnc_comment = Column(Text)
    fnc_user = Column(String(200))
    cfo_comment = Column(Text)
    cfo_user = Column(String(200))
    dean_hod_comment = Column(Text)
    dean_hod_user = Column(String(200))
    dvca_comment = Column(Text)
    dvca_user = Column(String(200))
    request_date = Column(DateTime, nullable=False)
    reg_request_stus_Id = Column(String, nullable=False)
    statusId = Column(String, nullable=False)
    dcsn_Id = Column(String, nullable=False)
    response_date = Column(DateTime, nullable=False)

        def __repr__(self):
            return f'<TblFormRemarkingExam (no primary key)>'
    
class TblFormRemarkingExamDocs(MISBaseModel):
        """Model for tbl_form_remarking_exam_docs table"""
        __tablename__ = 'tbl_form_remarking_exam_docs'
        
        docId = Column(String, nullable=False)
    Rmrk_exam_Id = Column(String, nullable=False)
    reg_no = Column(String(200), nullable=False)
    reg_prg_id = Column(String, nullable=False)
    doc = Column(Text, nullable=False)
    statusId = Column(String, nullable=False)

        def __repr__(self):
            return f'<TblFormRemarkingExamDocs (no primary key)>'
    
class TblFormRequestType(MISBaseModel):
        """Model for tbl_form_request_type table"""
        __tablename__ = 'tbl_form_request_type'
        
        request_type_Id = Column(String, nullable=False)
    request_type_name = Column(String(200))
    status_Id = Column(Integer)

        def __repr__(self):
            return f'<TblFormRequestType (no primary key)>'
    
class TblFormSessionTransfer(MISBaseModel):
        """Model for tbl_form_session_transfer table"""
        __tablename__ = 'tbl_form_session_transfer'
        
        SessnTransf_Id = Column(String, nullable=False)
    reg_no = Column(String(20), nullable=False)
    reg_prg_id = Column(String, nullable=False)
    prg_mode_id = Column(String, nullable=False)
    student_comment = Column(Text)
    fnc_comment = Column(Text)
    fnc_user = Column(String(200))
    rgstr_comment = Column(Text)
    rgstr_user = Column(String(200))
    request_date = Column(DateTime, nullable=False)
    reg_request_stus_Id = Column(String, nullable=False)
    statusId = Column(String, nullable=False)
    dcsn_Id = Column(String, nullable=False)
    response_date = Column(DateTime, nullable=False)

        def __repr__(self):
            return f'<TblFormSessionTransfer (no primary key)>'
    
class TblFormSessnTransfDocs(MISBaseModel):
        """Model for tbl_form_sessn_transf_docs table"""
        __tablename__ = 'tbl_form_sessn_transf_docs'
        
        docId = Column(String, nullable=False)
    SessnTransf_Id = Column(String, nullable=False)
    reg_no = Column(String(200), nullable=False)
    reg_prg_id = Column(String, nullable=False)
    doc = Column(Text, nullable=False)
    statusId = Column(String, nullable=False)

        def __repr__(self):
            return f'<TblFormSessnTransfDocs (no primary key)>'
    
class TblFormSpecialCat(MISBaseModel):
        """Model for tbl_form_special_cat table"""
        __tablename__ = 'tbl_form_special_cat'
        
        Spec_cat_Id = Column(String, nullable=False)
    att_stud_mdl_reg_Id = Column(String, nullable=False)
    student_comment = Column(Text)
    doc = Column(String(300))
    fnc_comment = Column(Text)
    fnc_user = Column(String(200))
    request_date = Column(DateTime, nullable=False)
    reg_request_stus_Id = Column(String, nullable=False)
    statusId = Column(String, nullable=False)
    dcsn_Id = Column(String, nullable=False)
    response_date = Column(DateTime, nullable=False)

        def __repr__(self):
            return f'<TblFormSpecialCat (no primary key)>'
    
class TblFormSpecialExams(MISBaseModel):
        """Model for tbl_form_special_exams table"""
        __tablename__ = 'tbl_form_special_exams'
        
        Spec_exam_Id = Column(String, nullable=False)
    mark_id = Column(String)
    reg_prg_id = Column(String)
    att_stud_mdl_reg_Id = Column(String, nullable=False)
    student_comment = Column(Text)
    doc = Column(String(300))
    fnc_comment = Column(Text)
    fnc_user = Column(String(200))
    request_date = Column(DateTime, nullable=False)
    reg_request_stus_Id = Column(String, nullable=False)
    statusId = Column(String, nullable=False)
    dcsn_Id = Column(String, nullable=False)
    response_date = Column(DateTime, nullable=False)

        def __repr__(self):
            return f'<TblFormSpecialExams (no primary key)>'
    
class TblFormStatementResult(MISBaseModel):
        """Model for tbl_form_statement_result table"""
        __tablename__ = 'tbl_form_statement_result'
        
        result_Id = Column(String, nullable=False)
    reg_prg_id = Column(String, nullable=False)
    Req_level_id = Column(String, nullable=False)
    Stdnt_comment = Column(Text)
    request_date = Column(DateTime, nullable=False)
    Fin_user = Column(String(100))
    Fin_comment = Column(Text)
    Fin_response_date = Column(DateTime)
    registration_user = Column(String(200), nullable=False)
    registration_comment = Column(Text)
    registration_response_date = Column(DateTime)
    printed_by = Column(String(200))
    printed_date = Column(DateTime)
    status_Id = Column(Integer)
    FinalStatus = Column(Integer, default='0')

        def __repr__(self):
            return f'<TblFormStatementResult (no primary key)>'
    
class TblFormStatementResultDoc(MISBaseModel):
        """Model for tbl_form_statement_result_doc table"""
        __tablename__ = 'tbl_form_statement_result_doc'
        
        doc_Id = Column(String, nullable=False)
    result_Id = Column(String, nullable=False)
    doc = Column(String(500))

        def __repr__(self):
            return f'<TblFormStatementResultDoc (no primary key)>'
    
class TblFormStudiesResuming(MISBaseModel):
        """Model for tbl_form_studies_resuming table"""
        __tablename__ = 'tbl_form_studies_resuming'
        
        formRsmng_Id = Column(String, nullable=False)
    reg_no = Column(String(20), nullable=False)
    reg_prg_id = Column(String, nullable=False)
    lastAttndce = Column(String(200))
    joiningIntak_Id = Column(String)
    joiningLvl_Id = Column(String)
    student_comment = Column(Text)
    fnc_comment = Column(Text)
    fnc_user = Column(String(200))
    cfo_comment = Column(Text)
    cfo_user = Column(String(200))
    dean_hod_comment = Column(Text)
    dean_hod_user = Column(String(100))
    exm_comment = Column(Text)
    exm_user = Column(String(200))
    rgstr_comment = Column(Text)
    rgstr_user = Column(String(200))
    dvca_comment = Column(Text)
    dvca_user = Column(String(200))
    request_date = Column(DateTime, nullable=False)
    reg_request_stus_Id = Column(String, nullable=False)
    statusId = Column(String, nullable=False)
    dcsn_Id = Column(String, nullable=False)
    response_date = Column(DateTime)

        def __repr__(self):
            return f'<TblFormStudiesResuming (no primary key)>'
    
class TblFormSupervision(MISBaseModel):
        """Model for tbl_form_supervision table"""
        __tablename__ = 'tbl_form_supervision'
        
        Sprvsn_Id = Column(String, nullable=False)
    reg_no = Column(String(20), nullable=False)
    reg_prg_id = Column(String, nullable=False)
    topic_1 = Column(Text)
    topic_2 = Column(Text)
    topic_3 = Column(Text)
    lbry_comment = Column(Text)
    lbry_user = Column(String(200))
    approved_topic = Column(Text)
    approved_supervisor = Column(Text)
    approved_co_supervisor = Column(Text)
    student_comment = Column(Text)
    fnc_comment = Column(Text)
    fnc_user = Column(String(200))
    cfo_comment = Column(Text)
    cfo_user = Column(String(200))
    dean_hod_comment = Column(Text)
    dean_hod_user = Column(String(200))
    request_date = Column(DateTime, nullable=False)
    reg_request_stus_Id = Column(String, nullable=False)
    statusId = Column(String, nullable=False)
    dcsn_Id = Column(String, nullable=False)
    response_date = Column(DateTime, nullable=False)

        def __repr__(self):
            return f'<TblFormSupervision (no primary key)>'
    
class TblFormSupervisionDocs(MISBaseModel):
        """Model for tbl_form_supervision_docs table"""
        __tablename__ = 'tbl_form_supervision_docs'
        
        docId = Column(String, nullable=False)
    Sprvsn_Id = Column(String, nullable=False)
    reg_no = Column(String(200), nullable=False)
    reg_prg_id = Column(String, nullable=False)
    doc = Column(Text, nullable=False)
    statusId = Column(String, nullable=False)

        def __repr__(self):
            return f'<TblFormSupervisionDocs (no primary key)>'
    
class TblFormSupplementary(MISBaseModel):
        """Model for tbl_form_supplementary table"""
        __tablename__ = 'tbl_form_supplementary'
        
        Suppl_Id = Column(String, nullable=False)
    mark_id = Column(String)
    reg_prg_id = Column(String)
    att_stud_mdl_reg_Id = Column(String, nullable=False)
    student_comment = Column(Text)
    doc = Column(String(300))
    fnc_comment = Column(Text)
    fnc_user = Column(String(200))
    request_date = Column(DateTime, nullable=False)
    reg_request_stus_Id = Column(String, nullable=False)
    statusId = Column(String, nullable=False)
    dcsn_Id = Column(String, nullable=False)
    response_date = Column(DateTime, nullable=False)

        def __repr__(self):
            return f'<TblFormSupplementary (no primary key)>'
    
class TblFormSuspensionWithdrawal(MISBaseModel):
        """Model for tbl_form_suspension_withdrawal table"""
        __tablename__ = 'tbl_form_suspension_withdrawal'
        
        Sspnsn_Id = Column(String, nullable=False)
    reg_no = Column(String(20), nullable=False)
    reg_prg_id = Column(String, nullable=False)
    student_comment = Column(Text)
    lbry_comment = Column(Text)
    lbry_user = Column(String(200))
    exm_comment = Column(Text)
    exm_user = Column(String(200))
    dean_hod_comment = Column(Text)
    dean_hod_user = Column(String(200))
    fnc_comment = Column(Text)
    fnc_user = Column(String(200))
    cfo_comment = Column(Text)
    cfo_user = Column(String(200))
    rgstr_comment = Column(Text)
    rgstr_user = Column(String(200))
    dvca_comment = Column(Text)
    dvca_user = Column(String(200))
    request_date = Column(DateTime, nullable=False)
    reg_request_stus_Id = Column(String, nullable=False)
    statusId = Column(String, nullable=False)
    dcsn_Id = Column(String, nullable=False)
    response_date = Column(DateTime, nullable=False)
    reintegration_status = Column(String(10), default=''No'')
    reintegration_date = Column(DateTime)
    reintegration_user = Column(String(200))

        def __repr__(self):
            return f'<TblFormSuspensionWithdrawal (no primary key)>'
    
class TblFormTowhom(MISBaseModel):
        """Model for tbl_form_towhom table"""
        __tablename__ = 'tbl_form_towhom'
        
        formTowhom_Id = Column(String, nullable=False)
    reg_no = Column(String(20), nullable=False)
    reg_prg_id = Column(String, nullable=False)
    towhomType_Id = Column(String, nullable=False)
    student_comment = Column(Text)
    exm_comment = Column(Text)
    exm_user = Column(String(200))
    rgstr_comment = Column(Text)
    rgstr_user = Column(String(200))
    lbry_comment = Column(Text)
    lbry_user = Column(String(100))
    fnc_comment = Column(Text)
    fnc_user = Column(String(200))
    request_date = Column(DateTime, nullable=False)
    reg_request_stus_Id = Column(String, nullable=False)
    statusId = Column(String, nullable=False)
    dcsn_Id = Column(String, nullable=False)
    response_date = Column(DateTime)

        def __repr__(self):
            return f'<TblFormTowhom (no primary key)>'
    
class TblFormTowhomDocs(MISBaseModel):
        """Model for tbl_form_towhom_docs table"""
        __tablename__ = 'tbl_form_towhom_docs'
        
        docId = Column(String, nullable=False)
    formTowhom_Id = Column(String, nullable=False)
    reg_no = Column(String(200), nullable=False)
    reg_prg_id = Column(String, nullable=False)
    doc = Column(Text, nullable=False)
    statusId = Column(String, nullable=False)

        def __repr__(self):
            return f'<TblFormTowhomDocs (no primary key)>'
    
class TblFormTowhomRef(MISBaseModel):
        """Model for tbl_form_towhom_ref table"""
        __tablename__ = 'tbl_form_towhom_ref'
        
        detail_Id = Column(String, nullable=False)
    ref_number = Column(String(200))
    formTowhom_Id = Column(String, nullable=False)
    status_Id = Column(String, nullable=False)
    printed_date = Column(DateTime)
    printed_by = Column(String(100))

        def __repr__(self):
            return f'<TblFormTowhomRef (no primary key)>'
    
class TblFormTowhomType(MISBaseModel):
        """Model for tbl_form_towhom_type table"""
        __tablename__ = 'tbl_form_towhom_type'
        
        towhomType_Id = Column(String, nullable=False)
    towhomType = Column(String(100), nullable=False)
    status_Id = Column(String, nullable=False)

        def __repr__(self):
            return f'<TblFormTowhomType (no primary key)>'
    
class TblFormTranscript(MISBaseModel):
        """Model for tbl_form_transcript table"""
        __tablename__ = 'tbl_form_transcript'
        
        formTrans_Id = Column(String, nullable=False)
    reg_no = Column(String(20), nullable=False)
    reg_prg_id = Column(String, nullable=False)
    TransRequested_Id = Column(String, nullable=False)
    student_comment = Column(Text)
    rgstr_comment = Column(Text)
    rgstr_user = Column(String(200))
    fnc_comment = Column(Text)
    fnc_user = Column(String(200))
    exm_comment = Column(Text)
    exm_user = Column(String(200))
    request_date = Column(DateTime, nullable=False)
    reg_request_stus_Id = Column(String, nullable=False)
    statusId = Column(String, nullable=False)
    dcsn_Id = Column(String, nullable=False)
    response_date = Column(DateTime)

        def __repr__(self):
            return f'<TblFormTranscript (no primary key)>'
    
class TblFormTranscriptCategory(MISBaseModel):
        """Model for tbl_form_transcript_category table"""
        __tablename__ = 'tbl_form_transcript_category'
        
        TransRequested_Id = Column(String, nullable=False)
    TransRequested = Column(String(200), nullable=False)
    status_Id = Column(String, nullable=False)

        def __repr__(self):
            return f'<TblFormTranscriptCategory (no primary key)>'
    
class TblFormTranscriptDocs(MISBaseModel):
        """Model for tbl_form_transcript_docs table"""
        __tablename__ = 'tbl_form_transcript_docs'
        
        docId = Column(String, nullable=False)
    formTrans_Id = Column(String, nullable=False)
    reg_no = Column(String(200), nullable=False)
    reg_prg_id = Column(String, nullable=False)
    doc = Column(Text, nullable=False)
    statusId = Column(String, nullable=False)

        def __repr__(self):
            return f'<TblFormTranscriptDocs (no primary key)>'
    
class TblFormTranscriptType(MISBaseModel):
        """Model for tbl_form_transcript_type table"""
        __tablename__ = 'tbl_form_transcript_type'
        
        TransType_Id = Column(String, nullable=False)
    TypeName = Column(String(200), nullable=False)
    status_Id = Column(Integer, nullable=False)

        def __repr__(self):
            return f'<TblFormTranscriptType (no primary key)>'
    
class TblGeneralSetting(MISBaseModel):
        """Model for tbl_general_setting table"""
        __tablename__ = 'tbl_general_setting'
        
        id = Column(String, nullable=False)
    university_name = Column(String(150), nullable=False)
    university_abrv = Column(String(50), nullable=False)
    post_code = Column(String(50), nullable=False)
    footer_message = Column(String(255), nullable=False)
    sms_header_message = Column(String(500), nullable=False)
    logo_img = Column(String(20), nullable=False)
    logo_img2 = Column(String(50), nullable=False)
    watermark = Column(String(70), nullable=False)
    phone = Column(String(20), nullable=False)
    moto = Column(String(50), nullable=False)
    color1 = Column(String(20), nullable=False)
    color2 = Column(String(20), nullable=False)
    header = Column(String(255), nullable=False)
    address = Column(String(255), nullable=False)
    url = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False)

        def __repr__(self):
            return f'<TblGeneralSetting (no primary key)>'
    
class TblGradCycle(MISBaseModel):
        """Model for tbl_grad_cycle table"""
        __tablename__ = 'tbl_grad_cycle'
        
        grad_cycle_id = Column(String, nullable=False)
    acad_cycle_id = Column(String, nullable=False)
    grad_date = Column(DateTime, nullable=False)

        def __repr__(self):
            return f'<TblGradCycle (no primary key)>'
    
class TblGrade(MISBaseModel):
        """Model for tbl_grade table"""
        __tablename__ = 'tbl_grade'
        
        gid = Column(Integer, nullable=False)
    marks_from = Column(Float, nullable=False)
    marks_upto = Column(Float, nullable=False)
    grade_letter = Column(String(50), nullable=False)

        def __repr__(self):
            return f'<TblGrade (no primary key)>'
    
class TblGraduants(MISBaseModel):
        """Model for tbl_graduants table"""
        __tablename__ = 'tbl_graduants'
        
        grad_id = Column(String, nullable=False)
    Grd_number = Column(String)
    degree_no = Column(String(20), nullable=False)
    old_reg_no = Column(String(100), nullable=False)
    reg_no = Column(String(100), nullable=False)
    grad_cycle_id = Column(String, nullable=False)
    l1_marks = Column(Float, nullable=False)
    l2_marks = Column(Float, nullable=False)
    l3_marks = Column(Float, nullable=False)
    l4_marks = Column(Float, nullable=False)
    l5_marks = Column(Float, nullable=False)
    cum_marks = Column(Float, nullable=False)
    prg_id = Column(String, nullable=False)
    splz_id = Column(String, nullable=False)
    level_id = Column(String, nullable=False)
    prg_mode_id = Column(String, nullable=False)
    prg_award_id = Column(String, nullable=False)
    class_id = Column(String(100), nullable=False)
    issue_date = Column(DateTime, nullable=False)
    campus_id = Column(String, nullable=False)
    user_Id = Column(String(100))
    recorded_date = Column(DateTime)
    printed_status = Column(String(15))

        def __repr__(self):
            return f'<TblGraduants (no primary key)>'
    
class TblGraduantsCertificate1year(MISBaseModel):
        """Model for tbl_graduants_certificate_1year table"""
        __tablename__ = 'tbl_graduants_certificate_1year'
        
        grad_id = Column(String, nullable=False)
    Grd_number = Column(String)
    degree_no = Column(String(20), nullable=False)
    old_reg_no = Column(String(100), nullable=False)
    reg_no = Column(String(100), nullable=False)
    grad_cycle_id = Column(String, nullable=False)
    l1_marks = Column(Float, nullable=False)
    cum_marks = Column(Float, nullable=False)
    prg_id = Column(String, nullable=False)
    splz_id = Column(String, nullable=False)
    level_id = Column(String, nullable=False)
    prg_mode_id = Column(String, nullable=False)
    prg_award_id = Column(String, nullable=False)
    class_id = Column(String(100), nullable=False)
    issue_date = Column(DateTime, nullable=False)
    campus_id = Column(String, nullable=False)
    user_Id = Column(String(100))
    recorded_date = Column(DateTime)
    printed_status = Column(String(15))

        def __repr__(self):
            return f'<TblGraduantsCertificate1year (no primary key)>'
    
class TblGraduantsCertificate6m(MISBaseModel):
        """Model for tbl_graduants_certificate_6m table"""
        __tablename__ = 'tbl_graduants_certificate_6m'
        
        grad_id = Column(String, nullable=False)
    Grd_number = Column(String)
    degree_no = Column(String(20), nullable=False)
    old_reg_no = Column(String(100), nullable=False)
    reg_no = Column(String(100), nullable=False)
    grad_cycle_id = Column(String, nullable=False)
    l1_marks = Column(Float, nullable=False)
    cum_marks = Column(Float, nullable=False)
    prg_id = Column(String, nullable=False)
    splz_id = Column(String, nullable=False)
    level_id = Column(String, nullable=False)
    prg_mode_id = Column(String, nullable=False)
    prg_award_id = Column(String, nullable=False)
    class_id = Column(String(100), nullable=False)
    issue_date = Column(DateTime, nullable=False)
    campus_id = Column(String, nullable=False)
    user_Id = Column(String(100))
    recorded_date = Column(DateTime)
    printed_status = Column(String(15))

        def __repr__(self):
            return f'<TblGraduantsCertificate6m (no primary key)>'
    
class TblGraduantsDiploma(MISBaseModel):
        """Model for tbl_graduants_diploma table"""
        __tablename__ = 'tbl_graduants_diploma'
        
        grad_id = Column(String, nullable=False)
    Grd_number = Column(String)
    degree_no = Column(String(20), nullable=False)
    old_reg_no = Column(String(100), nullable=False)
    reg_no = Column(String(100), nullable=False)
    grad_cycle_id = Column(String, nullable=False)
    l1_marks = Column(Float, nullable=False)
    l2_marks = Column(Float, nullable=False)
    l3_marks = Column(Float, nullable=False)
    l4_marks = Column(Float, nullable=False)
    l5_marks = Column(Float, nullable=False)
    cum_marks = Column(Float, nullable=False)
    prg_id = Column(String, nullable=False)
    splz_id = Column(String, nullable=False)
    level_id = Column(String, nullable=False)
    prg_mode_id = Column(String, nullable=False)
    prg_award_id = Column(String, nullable=False)
    class_id = Column(String(100), nullable=False)
    issue_date = Column(DateTime, nullable=False)
    campus_id = Column(String, nullable=False)
    user_Id = Column(String(100))
    recorded_date = Column(DateTime)
    printed_status = Column(String(15))

        def __repr__(self):
            return f'<TblGraduantsDiploma (no primary key)>'
    
class TblGraduationDate(MISBaseModel):
        """Model for tbl_graduation_date table"""
        __tablename__ = 'tbl_graduation_date'
        
        gradDate_Id = Column(String, nullable=False)
    grad_date = Column(DateTime, nullable=False)
    status_Id = Column(Integer, nullable=False)

        def __repr__(self):
            return f'<TblGraduationDate (no primary key)>'
    
class TblGraduationIntakes(MISBaseModel):
        """Model for tbl_graduation_intakes table"""
        __tablename__ = 'tbl_graduation_intakes'
        
        GrdIntk_Id = Column(String, nullable=False)
    intake_id = Column(String, nullable=False)
    gradDate_Id = Column(String, nullable=False)
    recorded_by = Column(String(200))
    recorded_date = Column(DateTime)
    status_Id = Column(Integer, nullable=False)

        def __repr__(self):
            return f'<TblGraduationIntakes (no primary key)>'
    
class TblGraduationRepeats(MISBaseModel):
        """Model for tbl_graduation_repeats table"""
        __tablename__ = 'tbl_graduation_repeats'
        
        GrdRpt_Id = Column(String, nullable=False)
    FrmGrd_Id = Column(String, nullable=False)
    module_id = Column(String, nullable=False)
    recorded_by = Column(String(100), nullable=False)
    recorded_date = Column(DateTime, nullable=False)
    removed_by = Column(String(100))
    removed_date = Column(DateTime)
    status_Id = Column(Integer, nullable=False)

        def __repr__(self):
            return f'<TblGraduationRepeats (no primary key)>'
    
class TblHighSchool(MISBaseModel):
        """Model for tbl_high_school table"""
        __tablename__ = 'tbl_high_school'
        
        high_school_id = Column(String, nullable=False)
    high_school_short_name = Column(String(15), nullable=False)
    high_school_full_name = Column(String(250), nullable=False)
    high_school_country_id = Column(String, nullable=False)
    high_school_status = Column(Integer, nullable=False)

        def __repr__(self):
            return f'<TblHighSchool (no primary key)>'
    
class TblImvoice(MISBaseModel):
        """Model for tbl_imvoice table"""
        __tablename__ = 'tbl_imvoice'
        
        id = Column(String, nullable=False)
    reg_no = Column(String(200))
    appl_Id = Column(String)
    level_id = Column(String)
    fee_category = Column(String)
    module_id = Column(String)
    Rpt_Id = Column(String)
    dept = Column(Float)
    credit = Column(Float)
    balance = Column(String(200))
    invoice_date = Column(DateTime)
    comment = Column(String(900))
    user = Column(String(20))
    date = Column(DateTime)
    intake_id = Column(String)
    QuickBk_Status = Column(Integer, default='0')
    pushed_by = Column(String(200))
    pushed_date = Column(DateTime)

        def __repr__(self):
            return f'<TblImvoice (no primary key)>'
    
class TblIncome(MISBaseModel):
        """Model for tbl_income table"""
        __tablename__ = 'tbl_income'
        
        id = Column(String, nullable=False)
    name = Column(String(100), nullable=False)
    amount = Column(String(100), nullable=False)
    piece = Column(String(200), nullable=False)
    facture = Column(String(200), nullable=False)
    reference = Column(String(100), nullable=False)
    income_date = Column(DateTime)
    account = Column(String(200), nullable=False)
    category = Column(String(100), nullable=False)
    note = Column(String(100), nullable=False)
    file = Column(String(100), nullable=False)

        def __repr__(self):
            return f'<TblIncome (no primary key)>'
    
class TblIncomeCategory(MISBaseModel):
        """Model for tbl_income_category table"""
        __tablename__ = 'tbl_income_category'
        
        id = Column(String, nullable=False)
    invTypeId = Column(String, nullable=False)
    camp_id = Column(String, nullable=False)
    prg_type = Column(String, nullable=False)
    splz_id = Column(String, nullable=False)
    name = Column(String(100), nullable=False)
    amount = Column(String, nullable=False)
    description = Column(String, nullable=False)
    recorded_date = Column(DateTime)
    recorded_by = Column(String(100), nullable=False)
    status_Id = Column(Integer, nullable=False)
    category = Column(String(200), nullable=False)
    QuickBk_ctgId = Column(Integer)

        def __repr__(self):
            return f'<TblIncomeCategory (no primary key)>'
    
class TblIndustrialAttachment(MISBaseModel):
        """Model for tbl_industrial_attachment table"""
        __tablename__ = 'tbl_industrial_attachment'
        
        industrial_Id = Column(String, nullable=False)
    starting_period = Column(String, nullable=False)
    reg_no = Column(String(20), nullable=False)
    reg_prg_id = Column(String, nullable=False)
    n_credit = Column(String)
    student_comment = Column(Text, nullable=False)
    hod_comment = Column(Text)
    hod_user = Column(String(200))
    fnc_comment = Column(Text)
    fnc_user = Column(String(200))
    career_comment = Column(Text)
    career_user = Column(String(200))
    request_date = Column(DateTime, nullable=False)
    industrial_stus_Id = Column(String)
    statusId = Column(Integer, nullable=False)
    dcsn_Id = Column(String, nullable=False)
    response_date = Column(DateTime)
    plcmnt_status = Column(Integer)

        def __repr__(self):
            return f'<TblIndustrialAttachment (no primary key)>'
    
class TblIndustrialAttachmentRecommendations(MISBaseModel):
        """Model for tbl_industrial_attachment_recommendations table"""
        __tablename__ = 'tbl_industrial_attachment_recommendations'
        
        rec_Id = Column(String, nullable=False)
    industrial_Id = Column(String, nullable=False)
    rec_reference = Column(String(200), nullable=False)

        def __repr__(self):
            return f'<TblIndustrialAttachmentRecommendations (no primary key)>'
    
class TblIndustrialDocs(MISBaseModel):
        """Model for tbl_industrial_docs table"""
        __tablename__ = 'tbl_industrial_docs'
        
        industrial_doc_Id = Column(String, nullable=False)
    industrial_Id = Column(String, nullable=False)
    reg_no = Column(String(20), nullable=False)
    reg_prg_id = Column(String, nullable=False)
    doc = Column(String(200))
    statusId = Column(Integer)

        def __repr__(self):
            return f'<TblIndustrialDocs (no primary key)>'
    
class TblIndustrialPlacement(MISBaseModel):
        """Model for tbl_industrial_placement table"""
        __tablename__ = 'tbl_industrial_placement'
        
        placement_Id = Column(String, nullable=False)
    industrial_Id = Column(String, nullable=False)
    company_name = Column(String(200), nullable=False)
    company_sector_Id = Column(String, nullable=False)
    physical_address = Column(Text, nullable=False)
    company_contact_phone = Column(String(50), nullable=False)
    company_contact_email = Column(String(100), nullable=False)
    camp_marks = Column(Float)
    UTB_sup_marks = Column(Float)
    report_marks = Column(Float)
    reporting_date = Column(DateTime, nullable=False)
    started_date = Column(DateTime, nullable=False)
    ending_date = Column(DateTime)
    status = Column(Integer, nullable=False)
    placed_by = Column(String(100), nullable=False)
    marked_by = Column(String(100))
    visited = Column(String(10), nullable=False, default=''no'')
    visited_by = Column(Text)
    visited_date = Column(DateTime)

        def __repr__(self):
            return f'<TblIndustrialPlacement (no primary key)>'
    
class TblIndustrialStatus(MISBaseModel):
        """Model for tbl_industrial_status table"""
        __tablename__ = 'tbl_industrial_status'
        
        industrial_stus_Id = Column(String, nullable=False)
    industrial_stus_name = Column(String(100))

        def __repr__(self):
            return f'<TblIndustrialStatus (no primary key)>'
    
class TblInstalment(MISBaseModel):
        """Model for tbl_instalment table"""
        __tablename__ = 'tbl_instalment'
        
        id = Column(String, nullable=False)
    camp_id = Column(String, nullable=False)
    intake_id = Column(String, nullable=False)
    dept_id = Column(String, nullable=False)
    level = Column(String, nullable=False)
    instalment = Column(String(20), nullable=False)
    amout = Column(String, nullable=False)
    amount_tobepay = Column(String, nullable=False)
    starting_date = Column(DateTime, nullable=False)
    ending_date = Column(DateTime, nullable=False)
    Date_ = Column(DateTime, nullable=False)
    Availability = Column(String, nullable=False)

        def __repr__(self):
            return f'<TblInstalment (no primary key)>'
    
class TblInstitutions(MISBaseModel):
        """Model for tbl_institutions table"""
        __tablename__ = 'tbl_institutions'
        
        inst_id = Column(String, nullable=False)
    inst_short_name = Column(String(20), nullable=False)
    inst_full_name = Column(String(50), nullable=False)
    inst_country_id = Column(String, nullable=False)
    status = Column(Integer, nullable=False)

        def __repr__(self):
            return f'<TblInstitutions (no primary key)>'
    
class TblIntake(MISBaseModel):
        """Model for tbl_intake table"""
        __tablename__ = 'tbl_intake'
        
        intake_id = Column(String, nullable=False)
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
            return f'<TblIntake (no primary key)>'
    
class TblInvoiceAudit(MISBaseModel):
        """Model for tbl_invoice_audit table"""
        __tablename__ = 'tbl_invoice_audit'
        
        audit_id = Column(String, nullable=False)
    action_type = Column(String)
    invoice_id = Column(String)
    user = Column(String(100))
    action_time = Column(DateTime, default='current_timestamp()')
    old_data = Column(Text)
    new_data = Column(Text)

        def __repr__(self):
            return f'<TblInvoiceAudit (no primary key)>'
    
class TblInvoiceNegociation(MISBaseModel):
        """Model for tbl_invoice_negociation table"""
        __tablename__ = 'tbl_invoice_negociation'
        
        negociate_id = Column(String, nullable=False)
    neg_balance_Id = Column(String, nullable=False)
    acad_cycle_id = Column(String, nullable=False)
    reg_no = Column(String(100), nullable=False)
    amount = Column(Float, nullable=False)
    negociation = Column(String(10), nullable=False, default=''no'')
    negociation_due_date = Column(DateTime, nullable=False)
    user_Id = Column(String(100), nullable=False)
    recorded_date = Column(DateTime)
    status_Id = Column(Integer)

        def __repr__(self):
            return f'<TblInvoiceNegociation (no primary key)>'
    
class TblInvoiceNegociationBalance(MISBaseModel):
        """Model for tbl_invoice_negociation_balance table"""
        __tablename__ = 'tbl_invoice_negociation_balance'
        
        neg_balance_Id = Column(String, nullable=False)
    acad_cycle_id = Column(String, nullable=False)
    intake_id = Column(String, nullable=False)
    reg_prg_id = Column(String, nullable=False)
    reg_no = Column(String(100), nullable=False)
    neg_balance_amnt = Column(Float, nullable=False)
    recorded_date = Column(DateTime, nullable=False)
    recorded_by = Column(String(100), nullable=False)
    status_Id = Column(Integer, nullable=False)

        def __repr__(self):
            return f'<TblInvoiceNegociationBalance (no primary key)>'
    
class TblInvoiceType(MISBaseModel):
        """Model for tbl_invoice_type table"""
        __tablename__ = 'tbl_invoice_type'
        
        invTypeId = Column(String, nullable=False)
    invTypeName = Column(String(100), nullable=False)
    status_Id = Column(Integer, nullable=False)

        def __repr__(self):
            return f'<TblInvoiceType (no primary key)>'
    
class TblLbryBook(MISBaseModel):
        """Model for tbl_lbry_book table"""
        __tablename__ = 'tbl_lbry_book'
        
        book_Id = Column(String, nullable=False)
    camp_id = Column(String, nullable=False)
    book_category_Id = Column(String, nullable=False)
    Book_title = Column(String(700))
    book_author = Column(String(700))
    call_number = Column(String(700))
    publication_date = Column(DateTime)
    edition = Column(String(700))
    ISBN = Column(String(700))
    quantity = Column(String)
    publishing_house = Column(String(700))
    recorded_date = Column(DateTime, nullable=False)
    recorded_by = Column(String(100), nullable=False)
    status_Id = Column(String, nullable=False)

        def __repr__(self):
            return f'<TblLbryBook (no primary key)>'
    
class TblLbryBookCategory(MISBaseModel):
        """Model for tbl_lbry_book_category table"""
        __tablename__ = 'tbl_lbry_book_category'
        
        book_category_Id = Column(String, nullable=False)
    category_name = Column(String(500))
    status_Id = Column(String, nullable=False)

        def __repr__(self):
            return f'<TblLbryBookCategory (no primary key)>'
    
class TblLeaveType(MISBaseModel):
        """Model for tbl_leave_type table"""
        __tablename__ = 'tbl_leave_type'
        
        leave_type_id = Column(String, nullable=False)
    leave_full_name = Column(String(100), nullable=False)
    status = Column(Integer, nullable=False)
    Allowed_days = Column(String, nullable=False)
    Description = Column(String(200), nullable=False)

        def __repr__(self):
            return f'<TblLeaveType (no primary key)>'
    
class TblLevel(MISBaseModel):
        """Model for tbl_level table"""
        __tablename__ = 'tbl_level'
        
        level_id = Column(String, nullable=False)
    level_no = Column(String(20), nullable=False)
    level_full_name = Column(String(50), nullable=False)
    level_short_name = Column(String(10), nullable=False)
    amount = Column(String(20), nullable=False)
    level_exit_award = Column(String, nullable=False)
    status = Column(Integer, nullable=False)

        def __repr__(self):
            return f'<TblLevel (no primary key)>'
    
class TblLevelYear(MISBaseModel):
        """Model for tbl_level_year table"""
        __tablename__ = 'tbl_level_year'
        
        level_id = Column(String, nullable=False)
    level_no = Column(String(20), nullable=False)
    level_full_name = Column(String(50), nullable=False)
    level_short_name = Column(String(10), nullable=False)
    amount = Column(String(20), nullable=False)
    level_exit_award = Column(String, nullable=False)
    status = Column(Integer, nullable=False)

        def __repr__(self):
            return f'<TblLevelYear (no primary key)>'
    
class TblMarkbyModuleNew(MISBaseModel):
        """Model for tbl_markby_module_new table"""
        __tablename__ = 'tbl_markby_module_new'
        
        mark_id = Column(String, nullable=False)
    module_id = Column(String, nullable=False)
    module_code = Column(String(100))
    acad_cycle_id = Column(String, nullable=False)
    old_reg_no = Column(String(100))
    reg_no = Column(String(100), nullable=False)
    marks = Column(Float, nullable=False)
    mark_status = Column(String(3), nullable=False, default=''no'')
    exam_marks = Column(Float, nullable=False)
    exam_mark_status = Column(String(3), nullable=False, default=''no'')
    retake = Column(String, nullable=False)
    retake_marks = Column(Float)
    repeat_mark = Column(Float, nullable=False)
    repeat_m_status = Column(String(3), nullable=False)
    repeat_exam = Column(Float, nullable=False)
    repeat_exam_status = Column(String(3), nullable=False)
    user_id = Column(String(30), nullable=False)
    cat_1 = Column(Float, nullable=False)
    cat_1_status = Column(String(3), nullable=False, default=''no'')
    cat_2 = Column(Float, nullable=False)
    cat_2_status = Column(String(3), nullable=False, default=''no'')
    cat_3 = Column(Float, nullable=False)
    cat_3_status = Column(String(3), nullable=False, default=''no'')
    cat_4 = Column(Float, nullable=False)
    cat_4_status = Column(String(3), nullable=False, default=''no'')
    exemption = Column(Float, nullable=False)
    exemption_status = Column(String(5), nullable=False, default=''no'')
    sup = Column(Float, nullable=False)
    sup_status = Column(String(5), nullable=False)
    special = Column(Float)
    special_status = Column(String(5))
    lctr_usr = Column(String(100), nullable=False)
    lctr_recorded_date = Column(DateTime)
    exm_usr = Column(String(100), nullable=False)
    exm_recorded_date = Column(DateTime)
    status_Id = Column(Integer, nullable=False)
    H_A = Column(String(100))

        def __repr__(self):
            return f'<TblMarkbyModuleNew (no primary key)>'
    
class TblMarkbyModuleNextLevel(MISBaseModel):
        """Model for tbl_markby_module_next_level table"""
        __tablename__ = 'tbl_markby_module_next_level'
        
        mark_id = Column(String, nullable=False)
    module_id = Column(String, nullable=False)
    module_code = Column(String(100))
    reg_prg_id = Column(String, nullable=False)
    marks = Column(Float, nullable=False)
    mark_status = Column(String(3), nullable=False, default=''no'')
    exam_marks = Column(Float, nullable=False)
    exam_mark_status = Column(String(3), nullable=False, default=''no'')
    retake = Column(String, nullable=False)
    retake_marks = Column(Float)
    repeat_mark = Column(Float, nullable=False)
    repeat_m_status = Column(String(3), nullable=False)
    repeat_exam = Column(Float, nullable=False)
    repeat_exam_status = Column(String(3), nullable=False)
    user_id = Column(String(30), nullable=False)
    cat_1 = Column(Float, nullable=False)
    cat_1_status = Column(String(3), nullable=False, default=''no'')
    cat_2 = Column(Float, nullable=False)
    cat_2_status = Column(String(3), nullable=False, default=''no'')
    cat_3 = Column(Float, nullable=False)
    cat_3_status = Column(String(3), nullable=False, default=''no'')
    cat_4 = Column(Float, nullable=False)
    cat_4_status = Column(String(3), nullable=False, default=''no'')
    exemption = Column(Float, nullable=False)
    exemption_status = Column(String(5), nullable=False, default=''no'')
    sup = Column(Float, nullable=False)
    sup_status = Column(String(5), nullable=False)
    special = Column(Float)
    special_status = Column(String(5))
    lctr_usr = Column(String(100), nullable=False)
    lctr_recorded_date = Column(DateTime)
    exm_usr = Column(String(100), nullable=False)
    exm_recorded_date = Column(DateTime)
    status_Id = Column(Integer, nullable=False)

        def __repr__(self):
            return f'<TblMarkbyModuleNextLevel (no primary key)>'
    
class TblMissingStudent(MISBaseModel):
        """Model for tbl_missing_student table"""
        __tablename__ = 'tbl_missing_student'
        
        stud_Id = Column(String, nullable=False)
    reg_no = Column(String(100))
    status = Column(String(70))
    recorded_by = Column(String(100))
    recorded_date = Column(DateTime)

        def __repr__(self):
            return f'<TblMissingStudent (no primary key)>'
    
class TblModueType(MISBaseModel):
        """Model for tbl_modue_type table"""
        __tablename__ = 'tbl_modue_type'
        
        id = Column(String, nullable=False)
    module_type_name = Column(String(100), nullable=False)
    status = Column(Integer, nullable=False, default='1')

        def __repr__(self):
            return f'<TblModueType (no primary key)>'
    
class TblModuleCategory(MISBaseModel):
        """Model for tbl_module_category table"""
        __tablename__ = 'tbl_module_category'
        
        module_categoryId = Column(String, nullable=False)
    category_name = Column(String(100), nullable=False)

        def __repr__(self):
            return f'<TblModuleCategory (no primary key)>'
    
class TblModuleTimeTable(MISBaseModel):
        """Model for tbl_module_time_table table"""
        __tablename__ = 'tbl_module_time_table'
        
        time_table_Id = Column(String, nullable=False)
    camp_id = Column(String)
    module_Id = Column(String, nullable=False)
    acad_cycle_id = Column(String, nullable=False)
    lecturer_Id = Column(String(100), nullable=False)
    att_room_Id = Column(String, nullable=False, default='0')
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)
    module_day = Column(String(30))
    att_days = Column(String, nullable=False)
    recorded_date = Column(DateTime, nullable=False)
    recorded_by = Column(String(100), nullable=False)
    transfrd_date = Column(DateTime)
    transfrd_by = Column(String(100))
    status_Id = Column(String, nullable=False)

        def __repr__(self):
            return f'<TblModuleTimeTable (no primary key)>'
    
class TblModuleTimeTableDetails(MISBaseModel):
        """Model for tbl_module_time_table_details table"""
        __tablename__ = 'tbl_module_time_table_details'
        
        det_Id = Column(String, nullable=False)
    time_table_Id = Column(String, nullable=False)
    camp_id = Column(String, nullable=False)
    prg_mode_id = Column(String, nullable=False)
    intake_id = Column(String, nullable=False)
    recorded_date = Column(DateTime, nullable=False)
    recorded_by = Column(String(100), nullable=False)

        def __repr__(self):
            return f'<TblModuleTimeTableDetails (no primary key)>'
    
class TblModuleTimeTableShift(MISBaseModel):
        """Model for tbl_module_time_table_shift table"""
        __tablename__ = 'tbl_module_time_table_shift'
        
        time_table_shift_Id = Column(String, nullable=False)
    time_table_Id = Column(String, nullable=False)
    att_session_time_Id = Column(String, nullable=False)
    recorded_date = Column(DateTime, nullable=False)
    status_Id = Column(Integer, nullable=False)

        def __repr__(self):
            return f'<TblModuleTimeTableShift (no primary key)>'
    
class TblModulesType(MISBaseModel):
        """Model for tbl_modules_type table"""
        __tablename__ = 'tbl_modules_type'
        
        moduleType_Id = Column(String, nullable=False)
    moduleTypeName = Column(String(200), nullable=False)
    status_Id = Column(Integer, nullable=False)

        def __repr__(self):
            return f'<TblModulesType (no primary key)>'
    
class TblMonth(MISBaseModel):
        """Model for tbl_month table"""
        __tablename__ = 'tbl_month'
        
        id_month = Column(String, nullable=False)
    Name = Column(String(50), nullable=False)

        def __repr__(self):
            return f'<TblMonth (no primary key)>'
    
class TblNewAdmission(MISBaseModel):
        """Model for tbl_new_admission table"""
        __tablename__ = 'tbl_new_admission'
        
        new_id = Column(String, nullable=False)
    old_reg_no = Column(String(20), nullable=False)
    reg_no = Column(String(20), nullable=False)
    family_name = Column(String(50), nullable=False)
    first_name = Column(String(50), nullable=False)
    sex = Column(String(1), nullable=False)
    camp_id = Column(String, nullable=False)
    intake_id = Column(String, nullable=False)
    prg_mode_id = Column(String, nullable=False)
    prg_type_id = Column(String, nullable=False)
    prg_id = Column(String, nullable=False)
    splz_id = Column(String, nullable=False)
    level_id = Column(String, nullable=False)
    reg_decision = Column(String, nullable=False)
    spon_id = Column(String, nullable=False)
    institution = Column(String(100), nullable=False)
    comments = Column(String(255), nullable=False)

        def __repr__(self):
            return f'<TblNewAdmission (no primary key)>'
    
class TblNewExamBalance(MISBaseModel):
        """Model for tbl_new_exam_balance table"""
        __tablename__ = 'tbl_new_exam_balance'
        
        blnc_Id = Column(String, nullable=False)
    blnc_amnt = Column(Float, nullable=False)
    campus_Id = Column(String, nullable=False)
    Datefrom = Column(DateTime)
    Dateto = Column(DateTime)
    status = Column(Integer, nullable=False)
    recorded_date = Column(DateTime, nullable=False)
    recorded_by = Column(String(100), nullable=False)

        def __repr__(self):
            return f'<TblNewExamBalance (no primary key)>'
    
class TblOnlineApplication(MISBaseModel):
        """Model for tbl_online_application table"""
        __tablename__ = 'tbl_online_application'
        
        appl_Id = Column(String, nullable=False)
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

        def __repr__(self):
            return f'<TblOnlineApplication (no primary key)>'
    
class TblOnlineApplicationDocs(MISBaseModel):
        """Model for tbl_online_application_docs table"""
        __tablename__ = 'tbl_online_application_docs'
        
        appl_doc_Id = Column(String, nullable=False)
    appl_Id = Column(String, nullable=False)
    applications_docs = Column(String(300))

        def __repr__(self):
            return f'<TblOnlineApplicationDocs (no primary key)>'
    
class TblOnlineApplicationTransDoc(MISBaseModel):
        """Model for tbl_online_application_trans_doc table"""
        __tablename__ = 'tbl_online_application_trans_doc'
        
        appl_trans_doc = Column(String, nullable=False)
    appl_Id = Column(String, nullable=False)
    trans_doc = Column(String(200))

        def __repr__(self):
            return f'<TblOnlineApplicationTransDoc (no primary key)>'
    
class TblPasswordReset(MISBaseModel):
        """Model for tbl_password_reset table"""
        __tablename__ = 'tbl_password_reset'
        
        reset_Id = Column(String, nullable=False)
    identification = Column(String(100), nullable=False)
    reset_type = Column(String(50))
    reset_by = Column(String(100), nullable=False)
    reset_date = Column(DateTime, nullable=False)

        def __repr__(self):
            return f'<TblPasswordReset (no primary key)>'
    
class TblPaymentPlan(MISBaseModel):
        """Model for tbl_payment_plan table"""
        __tablename__ = 'tbl_payment_plan'
        
        plan_id = Column(String, nullable=False)
    plan_name = Column(String(50), nullable=False)
    plan_installments = Column(String, nullable=False)

        def __repr__(self):
            return f'<TblPaymentPlan (no primary key)>'
    
class TblPaymentReverse(MISBaseModel):
        """Model for tbl_payment_reverse table"""
        __tablename__ = 'tbl_payment_reverse'
        
        Rvrs_id = Column(String, nullable=False)
    trans_code = Column(String(200), nullable=False)
    reg_no = Column(String(30), nullable=False)
    level_id = Column(String, nullable=False)
    bank_id = Column(String, nullable=False)
    slip_no = Column(String(30), nullable=False)
    user = Column(String(20), nullable=False)
    acad_cycle_id = Column(String(100), nullable=False)
    date = Column(String(50), nullable=False)
    fee_category = Column(String(50), nullable=False)
    amount = Column(Float, nullable=False)
    description = Column(String(100), nullable=False)
    recorded_date = Column(DateTime, nullable=False, default='current_timestamp()')
    Remark = Column(String, nullable=False)

        def __repr__(self):
            return f'<TblPaymentReverse (no primary key)>'
    
class TblPaymentStatus(MISBaseModel):
        """Model for tbl_payment_status table"""
        __tablename__ = 'tbl_payment_status'
        
        payment_status_Id = Column(String, nullable=False)
    reg_prg_id = Column(String, nullable=False)
    reg_no = Column(String(100), nullable=False)
    invoice_balance = Column(String, nullable=False)
    payment_balance = Column(String, nullable=False)
    user = Column(String(100), nullable=False)
    user_comment = Column(Text, nullable=False)
    recorded_date = Column(DateTime, nullable=False)

        def __repr__(self):
            return f'<TblPaymentStatus (no primary key)>'
    
class TblPayroll(MISBaseModel):
        """Model for tbl_payroll table"""
        __tablename__ = 'tbl_payroll'
        
        payroll_Id = Column(String, nullable=False)
    staff_Id = Column(String(100), nullable=False)
    pers_chrg = Column(String, nullable=False, default='0')
    Reim_advance = Column(String, nullable=False, default='0')
    Special_monthly_adv = Column(String, nullable=False, default='0')
    tutuition_fee = Column(String, nullable=False, default='0')
    SONARWA = Column(String, nullable=False, default='0')
    SORAS = Column(String, nullable=False, default='0')
    support_vollebal = Column(String, nullable=False, default='0')
    warefare = Column(String, nullable=False, default='0')
    cemu_contrib = Column(String, nullable=False, default='0')
    cemu_loan_rep = Column(String, nullable=False, default='0')
    ICDL = Column(String, nullable=False, default='0')
    salary_month = Column(String, nullable=False, default='0')
    salary_year = Column(String, nullable=False, default='0')

        def __repr__(self):
            return f'<TblPayroll (no primary key)>'
    
class TblPayrollCut(MISBaseModel):
        """Model for tbl_payroll_cut table"""
        __tablename__ = 'tbl_payroll_cut'
        
        payroll_Id = Column(String, nullable=False)
    staff_Id = Column(String(100), nullable=False)
    pers_chrg = Column(String, nullable=False, default='0')
    Reim_advance = Column(String, nullable=False, default='0')
    Special_monthly_adv = Column(String, nullable=False, default='0')
    tutuition_fee = Column(String, nullable=False, default='0')
    SONARWA = Column(String, nullable=False, default='0')
    SORAS = Column(String, nullable=False, default='0')
    support_vollebal = Column(String, nullable=False, default='0')
    warefare = Column(String, nullable=False, default='0')
    cemu_contrib = Column(String, nullable=False, default='0')
    cemu_loan_rep = Column(String, nullable=False, default='0')
    ICDL = Column(String, nullable=False, default='0')
    salary_month = Column(String, nullable=False, default='0')
    salary_year = Column(String, nullable=False, default='0')

        def __repr__(self):
            return f'<TblPayrollCut (no primary key)>'
    
class TblPendingPayment(MISBaseModel):
        """Model for tbl_pending_payment table"""
        __tablename__ = 'tbl_pending_payment'
        
        pend_id = Column(String, nullable=False)
    reg_no = Column(String(20), nullable=False)
    acad_cycle_id = Column(String, nullable=False)
    amount = Column(String, nullable=False)
    reason = Column(String(255), nullable=False)
    comments = Column(String(255), nullable=False)

        def __repr__(self):
            return f'<TblPendingPayment (no primary key)>'
    
class TblPersonalUg(MISBaseModel):
        """Model for tbl_personal_ug table"""
        __tablename__ = 'tbl_personal_ug'
        
        per_id_ug = Column(String, nullable=False)
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
    brought_By = Column(String(500))
    certificate_doc = Column(String(150))
    auth_ccs_nnc = Column(String, nullable=False, default='0')
    qk_id = Column(String)
    pushed_by = Column(String(200))
    pushed_date = Column(DateTime)

        def __repr__(self):
            return f'<TblPersonalUg (no primary key)>'
    
class TblPettyCashEntry(MISBaseModel):
        """Model for tbl_petty_cash_entry table"""
        __tablename__ = 'tbl_petty_cash_entry'
        
        id = Column(String, nullable=False)
    Amount = Column(Float, nullable=False)
    Date_ = Column(DateTime, nullable=False)
    Availability = Column(Integer, nullable=False)

        def __repr__(self):
            return f'<TblPettyCashEntry (no primary key)>'
    
class TblPettyCashExit(MISBaseModel):
        """Model for tbl_petty_cash_exit table"""
        __tablename__ = 'tbl_petty_cash_exit'
        
        Id = Column(String, nullable=False)
    Amount = Column(Float, nullable=False)
    Item = Column(Text, nullable=False)
    Description = Column(Text, nullable=False)
    Date_ = Column(DateTime, nullable=False)

        def __repr__(self):
            return f'<TblPettyCashExit (no primary key)>'
    
class TblPgCertificate(MISBaseModel):
        """Model for tbl_pg_certificate table"""
        __tablename__ = 'tbl_pg_certificate'
        
        certificate_id = Column(String, nullable=False)
    certificate_no = Column(String(20), nullable=False)
    old_reg_no = Column(String(20), nullable=False)
    reg_no = Column(String(20), nullable=False)
    grad_cycle_id = Column(String, nullable=False)
    l1_marks = Column(Float, nullable=False)
    prg_id = Column(String, nullable=False)
    splz_id = Column(String, nullable=False)
    cont_level = Column(String, nullable=False)
    pg_award = Column(String(100), nullable=False)
    grade_class = Column(String(100), nullable=False)
    issue_date = Column(DateTime, nullable=False)

        def __repr__(self):
            return f'<TblPgCertificate (no primary key)>'
    
class TblPictureUg(MISBaseModel):
        """Model for tbl_picture_ug table"""
        __tablename__ = 'tbl_picture_ug'
        
        pic_id_pg = Column(String, nullable=False)
    reg_no = Column(String(200), nullable=False)
    pic_ext = Column(String(200))
    pic_content = Column(String)
    image_time = Column(String(100))
    pic_date = Column(DateTime)
    number = Column(String)

        def __repr__(self):
            return f'<TblPictureUg (no primary key)>'
    
class TblPosition(MISBaseModel):
        """Model for tbl_position table"""
        __tablename__ = 'tbl_position'
        
        staff_pos_id = Column(String, nullable=False)
    staff_id = Column(String, nullable=False)
    staff_pos_start = Column(DateTime, nullable=False)
    staff_pos_active = Column(String, nullable=False)
    staff_pos_end = Column(DateTime, nullable=False)
    staff_pos_comments = Column(String(250), nullable=False)

        def __repr__(self):
            return f'<TblPosition (no primary key)>'
    
class TblPreInvoice(MISBaseModel):
        """Model for tbl_pre_invoice table"""
        __tablename__ = 'tbl_pre_invoice'
        
        id = Column(String, nullable=False)
    reg_no = Column(String(100), nullable=False)
    level_id = Column(String, nullable=False)
    fee_category = Column(String, nullable=False)
    dept = Column(String(100), nullable=False)
    credit = Column(String(200))
    balance = Column(String(200))
    invoice_date = Column(DateTime)
    comment = Column(String(200), nullable=False)
    user = Column(String(20))
    date = Column(DateTime, nullable=False)
    status_Id = Column(Integer, default='0')

        def __repr__(self):
            return f'<TblPreInvoice (no primary key)>'
    
class TblProgram(MISBaseModel):
        """Model for tbl_program table"""
        __tablename__ = 'tbl_program'
        
        prg_id = Column(String, nullable=False)
    no = Column(String, nullable=False)
    camp_id = Column(String, nullable=False)
    dept_id = Column(String, nullable=False)
    prg_type = Column(String, nullable=False)
    prg_full_name = Column(String(100), nullable=False)
    prg_short_name = Column(String(20), nullable=False)
    prg_award_id = Column(String, nullable=False)
    partner_id = Column(String, nullable=False)
    amount = Column(String(20), nullable=False)
    deadline_date = Column(DateTime)
    status_Id = Column(String, nullable=False)

        def __repr__(self):
            return f'<TblProgram (no primary key)>'
    
class TblProgramAmount(MISBaseModel):
        """Model for tbl_program_amount table"""
        __tablename__ = 'tbl_program_amount'
        
        prog_amount_Id = Column(String, nullable=False)
    level_id = Column(String, nullable=False)
    prg_id = Column(String, nullable=False)
    amount = Column(Float, nullable=False)
    deadline_date = Column(DateTime, nullable=False)
    status = Column(Integer, nullable=False)

        def __repr__(self):
            return f'<TblProgramAmount (no primary key)>'
    
class TblProgramAward(MISBaseModel):
        """Model for tbl_program_award table"""
        __tablename__ = 'tbl_program_award'
        
        prg_award_id = Column(String, nullable=False)
    prg_award_full_name = Column(String(100), nullable=False)
    prg_award_short_name = Column(String(50), nullable=False)
    prg_award_years = Column(Float, nullable=False)
    level_id = Column(String, nullable=False)

        def __repr__(self):
            return f'<TblProgramAward (no primary key)>'
    
class TblProgramBlock(MISBaseModel):
        """Model for tbl_program_block table"""
        __tablename__ = 'tbl_program_block'
        
        prg_block_id = Column(String, nullable=False)
    prg_block_full_name = Column(String(50), nullable=False)
    prg_block_short_name = Column(String(20), nullable=False)
    prg_mode_id = Column(String, nullable=False)

        def __repr__(self):
            return f'<TblProgramBlock (no primary key)>'
    
class TblProgramFee(MISBaseModel):
        """Model for tbl_program_fee table"""
        __tablename__ = 'tbl_program_fee'
        
        prg_fee_id = Column(String, nullable=False)
    acad_cycle_id = Column(String, nullable=False)
    prg_id = Column(String, nullable=False)
    fee_struct_id_reg = Column(String, nullable=False)
    fee_struct_id_others = Column(String, nullable=False)
    fee_struct_id_tuition = Column(String, nullable=False)
    fee_sruct_id_indus = Column(String, nullable=False)
    fee_sruct_id_tour = Column(String, nullable=False)
    fee_struct_id_thesis = Column(String, nullable=False)
    fee_struct_id_grad = Column(String, nullable=False)
    comments = Column(String(255), nullable=False)

        def __repr__(self):
            return f'<TblProgramFee (no primary key)>'
    
class TblProgramMode(MISBaseModel):
        """Model for tbl_program_mode table"""
        __tablename__ = 'tbl_program_mode'
        
        prg_mode_id = Column(String, nullable=False)
    prg_mode_full_name = Column(String(30), nullable=False)
    prg_mode_short_name = Column(String(10), nullable=False)

        def __repr__(self):
            return f'<TblProgramMode (no primary key)>'
    
class TblProgramRun(MISBaseModel):
        """Model for tbl_program_run table"""
        __tablename__ = 'tbl_program_run'
        
        prg_run_id = Column(String, nullable=False)
    acad_cycle_id = Column(String, nullable=False)
    prg_id = Column(String, nullable=False)
    prg_mode_short_names = Column(String(30), nullable=False)
    camp_ids = Column(String(20), nullable=False)

        def __repr__(self):
            return f'<TblProgramRun (no primary key)>'
    
class TblProgramType(MISBaseModel):
        """Model for tbl_program_type table"""
        __tablename__ = 'tbl_program_type'
        
        prg_type_id = Column(String, nullable=False)
    prg_type_full_name = Column(String(20), nullable=False)
    prg_type_short_name = Column(String(20), nullable=False)

        def __repr__(self):
            return f'<TblProgramType (no primary key)>'
    
class TblProvince(MISBaseModel):
        """Model for tbl_province table"""
        __tablename__ = 'tbl_province'
        
        province_id = Column(String, nullable=False)
    province_name = Column(String(20), nullable=False)

        def __repr__(self):
            return f'<TblProvince (no primary key)>'
    
class TblPtySpecialExam(MISBaseModel):
        """Model for tbl_pty_special_exam table"""
        __tablename__ = 'tbl_pty_special_exam'
        
        pty_special_exam_Id = Column(String, nullable=False)
    camp_id = Column(String, nullable=False)
    start_date = Column(DateTime)
    end_date = Column(DateTime)
    attendance_average = Column(Float)
    exam_date = Column(DateTime)
    recorded_date = Column(DateTime)
    recorded_by = Column(String(100))
    status_Id = Column(Integer, nullable=False)

        def __repr__(self):
            return f'<TblPtySpecialExam (no primary key)>'
    
class TblPtySpecialExams(MISBaseModel):
        """Model for tbl_pty_special_exams table"""
        __tablename__ = 'tbl_pty_special_exams'
        
        pty_special_exam_Id = Column(String, nullable=False)
    intake_id = Column(String, nullable=False)
    start_date = Column(DateTime)
    end_date = Column(DateTime)
    recorded_date = Column(DateTime)
    recorded_by = Column(String(100))
    status_Id = Column(Integer, nullable=False)

        def __repr__(self):
            return f'<TblPtySpecialExams (no primary key)>'
    
class TblPtySpecialMidTermExams(MISBaseModel):
        """Model for tbl_pty_special_mid_term_exams table"""
        __tablename__ = 'tbl_pty_special_mid_term_exams'
        
        pty_special_exam_Id = Column(String, nullable=False)
    camp_id = Column(String, nullable=False)
    start_date = Column(DateTime)
    end_date = Column(DateTime)
    recorded_date = Column(DateTime)
    recorded_by = Column(String(100))
    status_Id = Column(Integer, nullable=False)

        def __repr__(self):
            return f'<TblPtySpecialMidTermExams (no primary key)>'
    
class TblPtySupplementaryExam(MISBaseModel):
        """Model for tbl_pty_supplementary_exam table"""
        __tablename__ = 'tbl_pty_supplementary_exam'
        
        pty_suppl_exam_Id = Column(String, nullable=False)
    camp_id = Column(String, nullable=False)
    start_date = Column(DateTime)
    end_date = Column(DateTime)
    attendance_average = Column(Float)
    exam_date = Column(DateTime)
    recorded_date = Column(DateTime)
    recorded_by = Column(String(100))
    status_Id = Column(Integer, nullable=False)

        def __repr__(self):
            return f'<TblPtySupplementaryExam (no primary key)>'
    
class TblRecommendationTypes(MISBaseModel):
        """Model for tbl_recommendation_types table"""
        __tablename__ = 'tbl_recommendation_types'
        
        recom_type_Id = Column(String, nullable=False)
    recom_type_name = Column(String(500), nullable=False)
    status_Id = Column(Integer, nullable=False)

        def __repr__(self):
            return f'<TblRecommendationTypes (no primary key)>'
    
class TblReconciliationClosing(MISBaseModel):
        """Model for tbl_reconciliation_closing table"""
        __tablename__ = 'tbl_reconciliation_closing'
        
        closing_Id = Column(String, nullable=False)
    closing_period = Column(DateTime, nullable=False)
    recorded_date = Column(DateTime, nullable=False)
    recorded_by = Column(String(100), nullable=False)
    status_Id = Column(Integer, nullable=False)

        def __repr__(self):
            return f'<TblReconciliationClosing (no primary key)>'
    
class TblRefunds(MISBaseModel):
        """Model for tbl_refunds table"""
        __tablename__ = 'tbl_refunds'
        
        refund_Id = Column(String, nullable=False)
    payment_Id = Column(String, nullable=False)
    paid_amount = Column(String, nullable=False)
    payment_slip_no = Column(String(100), nullable=False)
    payment_bank_Id = Column(String, nullable=False)
    paymnt_fee_category_Id = Column(String, nullable=False)
    paid_date = Column(DateTime, nullable=False)
    reg_no = Column(String(50))
    names = Column(String(200), nullable=False)
    refund_amount = Column(String, nullable=False)
    refund_bank_Id = Column(String, nullable=False)
    checque_number = Column(String(30), nullable=False)
    refund_descr = Column(Text, nullable=False)
    refund_date = Column(DateTime, nullable=False)
    user = Column(String(100), nullable=False)

        def __repr__(self):
            return f'<TblRefunds (no primary key)>'
    
class TblRegisterProgramUg(MISBaseModel):
        """Model for tbl_register_program_ug table"""
        __tablename__ = 'tbl_register_program_ug'
        
        reg_prg_id = Column(String, nullable=False)
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

        def __repr__(self):
            return f'<TblRegisterProgramUg (no primary key)>'
    
class TblRegisterProgramUgSpnsr(MISBaseModel):
        """Model for tbl_register_program_ug_spnsr table"""
        __tablename__ = 'tbl_register_program_ug_spnsr'
        
        SpnsrUpdateId = Column(String, nullable=False)
    reg_prg_id = Column(String, nullable=False)
    previous_spnsrId = Column(String, nullable=False)
    current_spnsrId = Column(String, nullable=False)
    updated_date = Column(DateTime, nullable=False)
    updated_by = Column(String(100), nullable=False)

        def __repr__(self):
            return f'<TblRegisterProgramUgSpnsr (no primary key)>'
    
class TblRegistrationNumber(MISBaseModel):
        """Model for tbl_registration_number table"""
        __tablename__ = 'tbl_registration_number'
        
        reg_id = Column(String, nullable=False)
    reg_no = Column(String(200), nullable=False)
    existing = Column(String(20), nullable=False)
    recorded_date = Column(DateTime)
    recorded_by = Column(String(100))

        def __repr__(self):
            return f'<TblRegistrationNumber (no primary key)>'
    
class TblRegistrationRequest(MISBaseModel):
        """Model for tbl_registration_request table"""
        __tablename__ = 'tbl_registration_request'
        
        reg_request_Id = Column(String, nullable=False)
    reg_no = Column(String(20), nullable=False)
    reg_prg_id = Column(String, nullable=False)
    requested_level_Id = Column(String, nullable=False)
    requested_splz_Id = Column(String, nullable=False)
    student_comment = Column(Text, nullable=False)
    exm_comment = Column(Text)
    exm_user = Column(String(100))
    fnc_comment = Column(Text)
    fnc_user = Column(String(100))
    rgstr_comment = Column(Text)
    rgstr_user = Column(String(100))
    request_date = Column(DateTime, nullable=False)
    reg_request_stus_Id = Column(String)
    statusId = Column(Integer, nullable=False)
    dcsn_Id = Column(String, nullable=False)
    response_date = Column(DateTime)

        def __repr__(self):
            return f'<TblRegistrationRequest (no primary key)>'
    
class TblRegistrationRequestDocs(MISBaseModel):
        """Model for tbl_registration_request_docs table"""
        __tablename__ = 'tbl_registration_request_docs'
        
        reg_request_doc_Id = Column(String, nullable=False)
    reg_request_Id = Column(String, nullable=False)
    reg_no = Column(String(20), nullable=False)
    reg_prg_id = Column(String, nullable=False)
    doc = Column(String(200))
    statusId = Column(Integer)

        def __repr__(self):
            return f'<TblRegistrationRequestDocs (no primary key)>'
    
class TblRegistrationRequestStatus(MISBaseModel):
        """Model for tbl_registration_request_status table"""
        __tablename__ = 'tbl_registration_request_status'
        
        stus_Id = Column(String, nullable=False)
    request_stus_name = Column(String(100))

        def __repr__(self):
            return f'<TblRegistrationRequestStatus (no primary key)>'
    
class TblReplaceDegree(MISBaseModel):
        """Model for tbl_replace_degree table"""
        __tablename__ = 'tbl_replace_degree'
        
        replace_degree_id = Column(String, nullable=False)
    degree_no = Column(String(20), nullable=False)
    request_date = Column(DateTime, nullable=False)
    reason = Column(String(255), nullable=False)

        def __repr__(self):
            return f'<TblReplaceDegree (no primary key)>'
    
class TblRequestStatus(MISBaseModel):
        """Model for tbl_request_status table"""
        __tablename__ = 'tbl_request_status'
        
        stus_Id = Column(String, nullable=False)
    request_stus_name = Column(String(100))

        def __repr__(self):
            return f'<TblRequestStatus (no primary key)>'
    
class TblRequirement(MISBaseModel):
        """Model for tbl_requirement table"""
        __tablename__ = 'tbl_requirement'
        
        req_id = Column(String, nullable=False)
    req_full_name = Column(String(100), nullable=False)
    req_level_limit = Column(String, nullable=False)

        def __repr__(self):
            return f'<TblRequirement (no primary key)>'
    
class TblRequirementsSub(MISBaseModel):
        """Model for tbl_requirements_sub table"""
        __tablename__ = 'tbl_requirements_sub'
        
        req_sub_id = Column(String, nullable=False)
    tracking_id = Column(String(25), nullable=False)
    reg_no = Column(String(20), nullable=False)
    req_id = Column(String, nullable=False)
    req_sub_date = Column(DateTime, nullable=False)

        def __repr__(self):
            return f'<TblRequirementsSub (no primary key)>'
    
class TblReturns(MISBaseModel):
        """Model for tbl_returns table"""
        __tablename__ = 'tbl_returns'
        
        returnId = Column(String, nullable=False)
    bankId = Column(String, nullable=False)
    fee_category = Column(String, nullable=False)
    slipNumber = Column(String(100), nullable=False)
    amount = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    date = Column(DateTime, nullable=False)
    user = Column(String(100), nullable=False)

        def __repr__(self):
            return f'<TblReturns (no primary key)>'
    
class TblScholarshipApplication(MISBaseModel):
        """Model for tbl_scholarship_application table"""
        __tablename__ = 'tbl_scholarship_application'
        
        ap_Id = Column(String, nullable=False)
    apl_code = Column(String(100), nullable=False)
    frst_name = Column(String(200))
    fmly_name = Column(String(200))
    Gndr = Column(String(100))
    Ntnl_ID = Column(String(50))
    Phn = Column(String(100))
    Eml = Column(String(100))
    cntr_id = Column(String, nullable=False)
    level_id = Column(String, nullable=False)
    Intk = Column(Text, nullable=False)
    sector_id = Column(String, nullable=False)
    splz_id = Column(String, nullable=False)
    camp_id = Column(String, nullable=False)
    appl_date = Column(DateTime, nullable=False)
    NID_doc = Column(String(1000))
    highSchool_doc = Column(String(1000))
    bankSlip_doc = Column(String(1000))
    EAUR_comment = Column(Text)
    rspnt_by = Column(String(100), nullable=False)
    rspnt_dte = Column(DateTime, nullable=False)
    stats = Column(Integer)

        def __repr__(self):
            return f'<TblScholarshipApplication (no primary key)>'
    
class TblScholarshipApplicationDocs(MISBaseModel):
        """Model for tbl_scholarship_application_docs table"""
        __tablename__ = 'tbl_scholarship_application_docs'
        
        appl_doc_Id = Column(String, nullable=False)
    appl_Id = Column(String, nullable=False)
    applications_docs = Column(String(300))

        def __repr__(self):
            return f'<TblScholarshipApplicationDocs (no primary key)>'
    
class TblScholarshipIntake(MISBaseModel):
        """Model for tbl_scholarship_intake table"""
        __tablename__ = 'tbl_scholarship_intake'
        
        Scholarship_intake_Id = Column(String, nullable=False)
    Intk_name = Column(String(200), nullable=False)
    status = Column(Integer, nullable=False)

        def __repr__(self):
            return f'<TblScholarshipIntake (no primary key)>'
    
class TblSchoolCateg(MISBaseModel):
        """Model for tbl_school_categ table"""
        __tablename__ = 'tbl_school_categ'
        
        school_categ_Id = Column(String, nullable=False)
    categ_name = Column(String(100))
    status = Column(Integer)

        def __repr__(self):
            return f'<TblSchoolCateg (no primary key)>'
    
class TblSector(MISBaseModel):
        """Model for tbl_sector table"""
        __tablename__ = 'tbl_sector'
        
        sector_id = Column(String, nullable=False)
    sector_name = Column(String(50), nullable=False)
    district_id = Column(String, nullable=False)

        def __repr__(self):
            return f'<TblSector (no primary key)>'
    
class TblSemester(MISBaseModel):
        """Model for tbl_semester table"""
        __tablename__ = 'tbl_semester'
        
        sem_id = Column(String, nullable=False)
    sem_full_name = Column(String(50), nullable=False)
    Availability = Column(String, nullable=False)

        def __repr__(self):
            return f'<TblSemester (no primary key)>'
    
class TblShortCourse(MISBaseModel):
        """Model for tbl_short_course table"""
        __tablename__ = 'tbl_short_course'
        
        sc_id = Column(String, nullable=False)
    no = Column(String, nullable=False)
    prg_type = Column(String, nullable=False)
    fac_id = Column(String, nullable=False)
    sc_full_name = Column(String(100), nullable=False)
    sc_short_name = Column(String(30), nullable=False)
    sc_yor = Column(DateTime, nullable=False)
    duration_months = Column(String, nullable=False)
    partner_id = Column(String, nullable=False)
    id = Column(String, nullable=False)

        def __repr__(self):
            return f'<TblShortCourse (no primary key)>'
    
class TblSpecialExamsPeriod(MISBaseModel):
        """Model for tbl_special_exams_period table"""
        __tablename__ = 'tbl_special_exams_period'
        
        period_Id = Column(String, nullable=False)
    start_date = Column(DateTime)
    end_date = Column(DateTime)
    recorded_date = Column(DateTime, nullable=False)
    status_Id = Column(Integer, nullable=False)

        def __repr__(self):
            return f'<TblSpecialExamsPeriod (no primary key)>'
    
class TblSpecialization(MISBaseModel):
        """Model for tbl_specialization table"""
        __tablename__ = 'tbl_specialization'
        
        splz_id = Column(String, nullable=False)
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
            return f'<TblSpecialization (no primary key)>'
    
class TblSpennPendingPayment(MISBaseModel):
        """Model for tbl_spenn_pending_payment table"""
        __tablename__ = 'tbl_spenn_pending_payment'
        
        Pending_Id = Column(String, nullable=False)
    reg_prg_id = Column(String, nullable=False)
    reg_no = Column(String(100), nullable=False)
    req_Id = Column(String(100), nullable=False)
    req_ref = Column(String(100))
    fee_Id = Column(String, nullable=False)
    paidAmnt = Column(Float, nullable=False)
    req_status = Column(String(30), nullable=False)
    req_date = Column(DateTime, nullable=False)

        def __repr__(self):
            return f'<TblSpennPendingPayment (no primary key)>'
    
class TblSponsor(MISBaseModel):
        """Model for tbl_sponsor table"""
        __tablename__ = 'tbl_sponsor'
        
        spon_id = Column(String, nullable=False)
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

        def __repr__(self):
            return f'<TblSponsor (no primary key)>'
    
class TblSponsorCategory(MISBaseModel):
        """Model for tbl_sponsor_category table"""
        __tablename__ = 'tbl_sponsor_category'
        
        spon_cat_id = Column(String, nullable=False)
    spon_cat_full_name = Column(String(50), nullable=False)
    spon_cat_short_name = Column(String(20), nullable=False)

        def __repr__(self):
            return f'<TblSponsorCategory (no primary key)>'
    
class TblSponsorTolerance(MISBaseModel):
        """Model for tbl_sponsor_tolerance table"""
        __tablename__ = 'tbl_sponsor_tolerance'
        
        spon_tol_id = Column(String, nullable=False)
    spon_id = Column(String, nullable=False)
    tolerance_balance = Column(Float, nullable=False)
    tolerance_expiration_date = Column(DateTime, nullable=False)
    date = Column(DateTime, nullable=False)

        def __repr__(self):
            return f'<TblSponsorTolerance (no primary key)>'
    
class TblStaff(MISBaseModel):
        """Model for tbl_staff table"""
        __tablename__ = 'tbl_staff'
        
        id = Column(String, nullable=False)
    staff_id = Column(String(11), nullable=False)
    is_acadmic = Column(String, nullable=False)
    staff_grade_id = Column(String, nullable=False)
    acad_grad_id = Column(String, nullable=False)
    staff_family_name = Column(String(50), nullable=False)
    staff_first_name = Column(String(50), nullable=False)
    PhoneNumber = Column(String(15), nullable=False)
    email = Column(String, nullable=False)
    nid = Column(String(50), nullable=False)
    Country = Column(String(15), nullable=False)
    Province = Column(String(15), nullable=False)
    District = Column(String(15), nullable=False)
    Sector = Column(String(15), nullable=False)
    Cell = Column(String(15), nullable=False)
    Village = Column(String(15), nullable=False)
    Department = Column(String, nullable=False)
    Post = Column(String, nullable=False)
    probation_period = Column(String, nullable=False)
    Nationality = Column(String(15), nullable=False)
    staff_sex = Column(String(1), nullable=False)
    MartialStatus = Column(String(6), nullable=False)
    staff_dob = Column(DateTime)
    staff_doj = Column(DateTime)
    staff_active = Column(String, nullable=False)
    Bank = Column(String(100), nullable=False)
    AccountNumber = Column(String(100), nullable=False)
    basic_salary = Column(String(150), nullable=False)
    rssb = Column(String(15), nullable=False)
    staff_dol = Column(DateTime)
    staff_comments = Column(String(250), nullable=False)
    mother_name = Column(String(100), nullable=False)
    father_name = Column(String(100), nullable=False)
    fulltime = Column(String, nullable=False)
    Status_Employment = Column(String(20), nullable=False)
    campus = Column(String, nullable=False)
    user_Id = Column(String(100), nullable=False)
    Leave_days_allowed = Column(String, nullable=False)

        def __repr__(self):
            return f'<TblStaff (no primary key)>'
    
class TblStaffAcademicInfo(MISBaseModel):
        """Model for tbl_staff_academic_info table"""
        __tablename__ = 'tbl_staff_academic_info'
        
        ac_inf_id = Column(String, nullable=False)
    staff_id = Column(String(15), nullable=False)
    a1_degree = Column(String(50), nullable=False)
    a1_institution = Column(String(50), nullable=False)
    a0_degree = Column(String(50), nullable=False)
    a0_institution = Column(String(50), nullable=False)
    master_degree = Column(String(50), nullable=False)
    master_institution = Column(String(50), nullable=False)
    phd_degree = Column(String(50), nullable=False)
    phd_institution = Column(String(50), nullable=False)
    other_degree = Column(String(50), nullable=False)
    other_institution = Column(String(50), nullable=False)

        def __repr__(self):
            return f'<TblStaffAcademicInfo (no primary key)>'
    
class TblStaffAppointment(MISBaseModel):
        """Model for tbl_staff_appointment table"""
        __tablename__ = 'tbl_staff_appointment'
        
        staff_app_id = Column(String, nullable=False)
    staff_id = Column(String, nullable=False)
    staff_app_date = Column(DateTime, nullable=False)
    staff_dept_id = Column(String, nullable=False)
    staff_probation_yes = Column(String, nullable=False)
    staff_probation_start = Column(DateTime, nullable=False)
    staff_probation_end = Column(DateTime, nullable=False)
    staff_probation_result_id = Column(String, nullable=False)
    staff_app_comments = Column(String(250), nullable=False)

        def __repr__(self):
            return f'<TblStaffAppointment (no primary key)>'
    
class TblStaffBank(MISBaseModel):
        """Model for tbl_staff_bank table"""
        __tablename__ = 'tbl_staff_bank'
        
        bank_id = Column(String, nullable=False)
    bank_code = Column(String(10), nullable=False)
    bank_name = Column(String(100), nullable=False)
    bank_branch = Column(String(100), nullable=False)
    account_no = Column(String(30), nullable=False)
    currency = Column(String(10), nullable=False)

        def __repr__(self):
            return f'<TblStaffBank (no primary key)>'
    
class TblStaffDept(MISBaseModel):
        """Model for tbl_staff_dept table"""
        __tablename__ = 'tbl_staff_dept'
        
        staff_dept_id = Column(String, nullable=False)
    staff_dept_full_name = Column(String(100), nullable=False)
    staff_dept_short_name = Column(String(100), nullable=False)

        def __repr__(self):
            return f'<TblStaffDept (no primary key)>'
    
class TblStaffDocType(MISBaseModel):
        """Model for tbl_staff_doc_type table"""
        __tablename__ = 'tbl_staff_doc_type'
        
        staff_doc_type_id = Column(String, nullable=False)
    staff_doc_type_name = Column(String(50), nullable=False)

        def __repr__(self):
            return f'<TblStaffDocType (no primary key)>'
    
class TblStaffEvaluation(MISBaseModel):
        """Model for tbl_staff_evaluation table"""
        __tablename__ = 'tbl_staff_evaluation'
        
        staff_eval_id = Column(String, nullable=False)
    staff_id = Column(String, nullable=False)
    academic_cycle_id = Column(String, nullable=False)
    self_eval_marks = Column(String, nullable=False)
    line_mgr1_marks = Column(String, nullable=False)
    line_mgr1_comments = Column(String(250), nullable=False)
    line_mgr2_marks = Column(String, nullable=False)
    line_mgr2_comments = Column(String(250), nullable=False)
    line_mgr3_marks = Column(String, nullable=False)
    line_mgr3_comments = Column(String(250), nullable=False)
    final_marks = Column(String, nullable=False)
    staff_approval = Column(String, nullable=False)
    staff_approval_date = Column(String, nullable=False)
    staff_eval_comments = Column(String(250), nullable=False)

        def __repr__(self):
            return f'<TblStaffEvaluation (no primary key)>'
    
class TblStaffGrade(MISBaseModel):
        """Model for tbl_staff_grade table"""
        __tablename__ = 'tbl_staff_grade'
        
        staff_grade_id = Column(String, nullable=False)
    staff_type_id = Column(String, nullable=False)
    staff_grade_full_name = Column(String(255), nullable=False)
    staff_grade_short_name = Column(String(50), nullable=False)
    staff_managerial_role = Column(String, nullable=False)
    staff_managerial_grade_id = Column(String, nullable=False)

        def __repr__(self):
            return f'<TblStaffGrade (no primary key)>'
    
class TblStaffHrsCredits(MISBaseModel):
        """Model for tbl_staff_hrs_credits table"""
        __tablename__ = 'tbl_staff_hrs_credits'
        
        id = Column(String, nullable=False)
    face_to_face = Column(Float, nullable=False)

        def __repr__(self):
            return f'<TblStaffHrsCredits (no primary key)>'
    
class TblStaffHrsWorkload(MISBaseModel):
        """Model for tbl_staff_hrs_workload table"""
        __tablename__ = 'tbl_staff_hrs_workload'
        
        id = Column(String, nullable=False)
    credits = Column(String, nullable=False)
    hours = Column(String, nullable=False)
    status = Column(String, nullable=False, default='1')

        def __repr__(self):
            return f'<TblStaffHrsWorkload (no primary key)>'
    
class TblStaffOtherHours(MISBaseModel):
        """Model for tbl_staff_other_hours table"""
        __tablename__ = 'tbl_staff_other_hours'
        
        id = Column(String, nullable=False)
    name = Column(String(250), nullable=False)
    staff_id = Column(String(30), nullable=False)
    hours = Column(String, nullable=False)
    ac_year = Column(String(100), nullable=False)

        def __repr__(self):
            return f'<TblStaffOtherHours (no primary key)>'
    
class TblStaffPlace(MISBaseModel):
        """Model for tbl_staff_place table"""
        __tablename__ = 'tbl_staff_place'
        
        staff_place_id = Column(String, nullable=False)
    staff_id = Column(String, nullable=False)
    staff_campus_id = Column(String, nullable=False)
    staff_place_type_id = Column(String, nullable=False)
    staff_place_date = Column(DateTime, nullable=False)
    staff_place_active = Column(String, nullable=False)
    staff_place_comments = Column(String(250), nullable=False)

        def __repr__(self):
            return f'<TblStaffPlace (no primary key)>'
    
class TblStaffPlaceType(MISBaseModel):
        """Model for tbl_staff_place_type table"""
        __tablename__ = 'tbl_staff_place_type'
        
        staff_place_type = Column(String, nullable=False)
    staff_place_type_name = Column(String(50), nullable=False)
    staff_place_type_comments = Column(String(250), nullable=False)

        def __repr__(self):
            return f'<TblStaffPlaceType (no primary key)>'
    
class TblStaffProbationResult(MISBaseModel):
        """Model for tbl_staff_probation_result table"""
        __tablename__ = 'tbl_staff_probation_result'
        
        prob_result_id = Column(String, nullable=False)
    prob_result_name = Column(String(50), nullable=False)

        def __repr__(self):
            return f'<TblStaffProbationResult (no primary key)>'
    
class TblStaffPromotionType(MISBaseModel):
        """Model for tbl_staff_promotion_type table"""
        __tablename__ = 'tbl_staff_promotion_type'
        
        staff_promo_type_id = Column(String, nullable=False)
    staff_promo_type_name = Column(String(50), nullable=False)
    staff_promo_type_approve_by = Column(String(11), nullable=False)
    staff_promo_type_comments = Column(String(250), nullable=False)

        def __repr__(self):
            return f'<TblStaffPromotionType (no primary key)>'
    
class TblStaffQualification(MISBaseModel):
        """Model for tbl_staff_qualification table"""
        __tablename__ = 'tbl_staff_qualification'
        
        staff_qual_id = Column(String, nullable=False)
    staff_id = Column(String, nullable=False)
    staff_current_grade_id = Column(String, nullable=False)
    staff_current_grade_from = Column(String(50), nullable=False)
    degree_type = Column(String(50), nullable=False)
    degree_name = Column(String(50), nullable=False)
    university_obtain_from = Column(String(50), nullable=False)
    country_obtain_from = Column(String, nullable=False)
    date_obtain = Column(DateTime, nullable=False)
    equivalence_from_hec = Column(String(50), nullable=False)
    staff_qual_comments = Column(String(250), nullable=False)

        def __repr__(self):
            return f'<TblStaffQualification (no primary key)>'
    
class TblStaffStartingSalary(MISBaseModel):
        """Model for tbl_staff_starting_salary table"""
        __tablename__ = 'tbl_staff_starting_salary'
        
        salary_Id = Column(String, nullable=False)
    staff_Id = Column(String(100), nullable=False)
    gross_salary = Column(String(50), nullable=False)
    starting_date = Column(DateTime, nullable=False)
    ending_date = Column(DateTime)
    status = Column(Integer, nullable=False)
    user_Id = Column(String(100), nullable=False)

        def __repr__(self):
            return f'<TblStaffStartingSalary (no primary key)>'
    
class TblStaffType(MISBaseModel):
        """Model for tbl_staff_type table"""
        __tablename__ = 'tbl_staff_type'
        
        staff_type_id = Column(String, nullable=False)
    staff_type_full_name = Column(String(50), nullable=False)
    staff_type_short_name = Column(String(50), nullable=False)

        def __repr__(self):
            return f'<TblStaffType (no primary key)>'
    
class TblStatus(MISBaseModel):
        """Model for tbl_status table"""
        __tablename__ = 'tbl_status'
        
        status_id = Column(String, nullable=False)
    status_full_name = Column(String(100), nullable=False)
    stud_status_short_name = Column(String(50), nullable=False)
    comments = Column(String(255), nullable=False)

        def __repr__(self):
            return f'<TblStatus (no primary key)>'
    
class TblStudentAccessControl(MISBaseModel):
        """Model for tbl_student_access_control table"""
        __tablename__ = 'tbl_student_access_control'
        
        access_control_Id = Column(String, nullable=False)
    reg_no = Column(String(100), nullable=False)
    access_date = Column(DateTime, nullable=False)
    acc_time = Column(String(50), nullable=False)
    status = Column(Integer, nullable=False, default='0')

        def __repr__(self):
            return f'<TblStudentAccessControl (no primary key)>'
    
class TblStudentAdmissionFee(MISBaseModel):
        """Model for tbl_student_admission_fee table"""
        __tablename__ = 'tbl_student_admission_fee'
        
        stud_admission_Id = Column(String, nullable=False)
    prog_amount_Id = Column(String, nullable=False)
    reg_no = Column(String(20), nullable=False)
    level_id = Column(String, nullable=False)
    amount = Column(String(20), nullable=False)
    comments = Column(Text, nullable=False)
    deadline_date = Column(DateTime, nullable=False)
    status = Column(String, nullable=False)

        def __repr__(self):
            return f'<TblStudentAdmissionFee (no primary key)>'
    
class TblStudentLogin(MISBaseModel):
        """Model for tbl_student_login table"""
        __tablename__ = 'tbl_student_login'
        
        id = Column(String, nullable=False)
    Identification = Column(String(200), nullable=False)
    family_name = Column(String(100), nullable=False)
    first_name = Column(String(100), nullable=False)
    email = Column(String(50), nullable=False)
    oldPasswrd = Column(String(225))
    password = Column(String(255), nullable=False)
    role_id = Column(String, nullable=False)
    telephone = Column(String(30), nullable=False)
    prg_type_id = Column(String, nullable=False)
    profile_id = Column(String, nullable=False)
    status = Column(String(1), nullable=False)
    reg_date = Column(DateTime)
    comments = Column(String(255))
    psswrdSetBy = Column(String(100))
    psswrdSetDate = Column(DateTime)
    recorded_by = Column(String(100))

        def __repr__(self):
            return f'<TblStudentLogin (no primary key)>'
    
class TblStudentRepeats(MISBaseModel):
        """Model for tbl_student_repeats table"""
        __tablename__ = 'tbl_student_repeats'
        
        Rpt_Id = Column(String, nullable=False)
    reg_no = Column(String(100), nullable=False)
    acad_cycle_id = Column(String, nullable=False)
    module_id = Column(String, nullable=False)
    CAT_marks = Column(Float, nullable=False)
    EXAM_marks = Column(Float, nullable=False)
    recorded_by = Column(String(100), nullable=False)
    recorded_date = Column(DateTime, nullable=False)
    removed_by = Column(String(100), nullable=False)
    removed_date = Column(DateTime, nullable=False)
    status_Id = Column(Integer, nullable=False)

        def __repr__(self):
            return f'<TblStudentRepeats (no primary key)>'
    
class TblStudentRequest(MISBaseModel):
        """Model for tbl_student_request table"""
        __tablename__ = 'tbl_student_request'
        
        request_Id = Column(String, nullable=False)
    request_number = Column(String(100), nullable=False)
    reg_no = Column(String(50), nullable=False)
    request_document = Column(String(25), nullable=False)
    intake_Id = Column(String, nullable=False)
    acc_year_Id = Column(String, nullable=False)
    request_date = Column(DateTime, nullable=False)
    approved_date = Column(DateTime)
    approved_by = Column(String(100))
    comment = Column(Text)
    status_Id = Column(String, nullable=False)

        def __repr__(self):
            return f'<TblStudentRequest (no primary key)>'
    
class TblStudentRequestDetails(MISBaseModel):
        """Model for tbl_student_request_details table"""
        __tablename__ = 'tbl_student_request_details'
        
        detail_Id = Column(String, nullable=False)
    ref_number = Column(String(200))
    request_number = Column(String(100), nullable=False)
    reg_no = Column(String(50), nullable=False)
    fee_category_Id = Column(String, nullable=False)
    status_Id = Column(String, nullable=False)
    printed_date = Column(DateTime)
    printed_by = Column(String(100))

        def __repr__(self):
            return f'<TblStudentRequestDetails (no primary key)>'
    
class TblSupplementaryExamsPeriod(MISBaseModel):
        """Model for tbl_supplementary_exams_period table"""
        __tablename__ = 'tbl_supplementary_exams_period'
        
        period_Id = Column(String, nullable=False)
    start_date = Column(DateTime)
    end_date = Column(DateTime)
    recorded_date = Column(DateTime, nullable=False)
    status_Id = Column(Integer, nullable=False)

        def __repr__(self):
            return f'<TblSupplementaryExamsPeriod (no primary key)>'
    
class TblSystemInfo(MISBaseModel):
        """Model for tbl_system_info table"""
        __tablename__ = 'tbl_system_info'
        
        Id = Column(String, nullable=False)
    systName = Column(Text, nullable=False)
    system_slogan = Column(Text)
    systWebsite = Column(String(500))
    tel1 = Column(String(25), nullable=False)
    tel2 = Column(String(25))
    tel3 = Column(String(25))
    acc_number_1 = Column(String(70))
    acc_number_2 = Column(String(70))
    acc_number_3 = Column(String(70))
    systemLogo = Column(String(100))
    emailAddress = Column(String(30))
    fullAddress = Column(String(500))
    regDate = Column(DateTime, nullable=False)
    statusId = Column(String, nullable=False)

        def __repr__(self):
            return f'<TblSystemInfo (no primary key)>'
    
class TblTranscripts(MISBaseModel):
        """Model for tbl_transcripts table"""
        __tablename__ = 'tbl_transcripts'
        
        trans_no = Column(String, nullable=False)
    reg_no = Column(String(100), nullable=False)
    acad_cycle_id = Column(String, nullable=False)
    level_id = Column(String(5), nullable=False)
    issue_date = Column(DateTime, nullable=False)
    re_issue_date = Column(DateTime)
    user_Id = Column(String(100))
    recorded_date = Column(DateTime)
    comments = Column(String)

        def __repr__(self):
            return f'<TblTranscripts (no primary key)>'
    
class TblUpdateHistory(MISBaseModel):
        """Model for tbl_update_history table"""
        __tablename__ = 'tbl_update_history'
        
        id = Column(String, nullable=False)
    reg_no = Column(String(20), nullable=False)
    intake_id = Column(String, nullable=False)
    prg_id = Column(String, nullable=False)
    dept_id = Column(String, nullable=False)
    splz_id = Column(String, nullable=False)
    prg_type = Column(String, nullable=False)
    level_id = Column(String, nullable=False)
    prg_mode_id = Column(String, nullable=False)
    year_id = Column(String, nullable=False)
    sem = Column(String, nullable=False)
    camp_id = Column(String, nullable=False)
    update_date = Column(DateTime, nullable=False)
    reg_active = Column(Integer, nullable=False)

        def __repr__(self):
            return f'<TblUpdateHistory (no primary key)>'
    
class TblUser(MISBaseModel):
        """Model for tbl_user table"""
        __tablename__ = 'tbl_user'
        
        id = Column(String, nullable=False)
    Identification = Column(String(10))
    family_name = Column(String(100), nullable=False)
    first_name = Column(String(100), nullable=False)
    email = Column(String(50), nullable=False)
    phone_number = Column(String(25))
    oldPasswrd = Column(String(225))
    password = Column(String(255))
    role_id = Column(String)
    profile_id = Column(String)
    fac_id = Column(String, nullable=False)
    dep_id = Column(String, nullable=False)
    campus_id = Column(String, nullable=False)
    empl_worload_Id = Column(String)
    status = Column(String(1))
    reg_date = Column(DateTime)
    recorded_by = Column(String(100))
    comments = Column(String(255))

        def __repr__(self):
            return f'<TblUser (no primary key)>'
    
class TblUserLoginAttempts(MISBaseModel):
        """Model for tbl_user_login_attempts table"""
        __tablename__ = 'tbl_user_login_attempts'
        
        id_login_attempts = Column(String, nullable=False)
    ip_addr = Column(String(20), nullable=False)
    user_id = Column(String, nullable=False)
    attempt_number = Column(String, nullable=False, default='1')
    date = Column(DateTime, nullable=False)

        def __repr__(self):
            return f'<TblUserLoginAttempts (no primary key)>'
    
class TblUserLogs(MISBaseModel):
        """Model for tbl_user_logs table"""
        __tablename__ = 'tbl_user_logs'
        
        loginId = Column(String, nullable=False)
    userName = Column(String(200), nullable=False)
    loginIp = Column(String(20), nullable=False)
    inTme = Column(DateTime, nullable=False)
    outTime = Column(DateTime, nullable=False)
    status = Column(String(7))

        def __repr__(self):
            return f'<TblUserLogs (no primary key)>'
    
class TblUserProfile(MISBaseModel):
        """Model for tbl_user_profile table"""
        __tablename__ = 'tbl_user_profile'
        
        profile_id = Column(String, nullable=False)
    role_id = Column(String, nullable=False)
    profile = Column(String(50), nullable=False)

        def __repr__(self):
            return f'<TblUserProfile (no primary key)>'
    
class TblUserRoles(MISBaseModel):
        """Model for tbl_user_roles table"""
        __tablename__ = 'tbl_user_roles'
        
        role_id = Column(String, nullable=False)
    role = Column(String(200), nullable=False)

        def __repr__(self):
            return f'<TblUserRoles (no primary key)>'
    
class TblUserSession(MISBaseModel):
        """Model for tbl_user_session table"""
        __tablename__ = 'tbl_user_session'
        
        id = Column(String, nullable=False)
    sess_id = Column(String(255), nullable=False, default='''')
    email = Column(String(255))
    ip = Column(String(20))
    time_login = Column(String(40))
    time_logout = Column(String(40))
    status = Column(String(3), nullable=False, default=''ON'')

        def __repr__(self):
            return f'<TblUserSession (no primary key)>'
    
class TblYear(MISBaseModel):
        """Model for tbl_year table"""
        __tablename__ = 'tbl_year'
        
        year_id = Column(String, nullable=False)
    year_full_name = Column(String(20), nullable=False)
    Date_ = Column(DateTime, nullable=False)
    Availability = Column(String, nullable=False)

        def __repr__(self):
            return f'<TblYear (no primary key)>'
    
class UmisComponents(MISBaseModel):
        """Model for umis_components table"""
        __tablename__ = 'umis_components'
        
        component_id = Column(String, nullable=False)
    component_name = Column(String(100), nullable=False)

        def __repr__(self):
            return f'<UmisComponents (no primary key)>'
    
class UmisComponentsPrivileges(MISBaseModel):
        """Model for umis_components_privileges table"""
        __tablename__ = 'umis_components_privileges'
        
        privilege_id = Column(String, nullable=False)
    component_id = Column(String, nullable=False)
    privilege_name = Column(String(100), nullable=False)

        def __repr__(self):
            return f'<UmisComponentsPrivileges (no primary key)>'
    
class UmisUserPrivileges(MISBaseModel):
        """Model for umis_user_privileges table"""
        __tablename__ = 'umis_user_privileges'
        
        profile_id = Column(String, nullable=False)
    component_id = Column(String, nullable=False)
    privilege_id = Column(String, nullable=False)

        def __repr__(self):
            return f'<UmisUserPrivileges (no primary key)>'
    
