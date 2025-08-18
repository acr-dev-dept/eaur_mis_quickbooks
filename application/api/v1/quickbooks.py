from flask import Blueprint, request, jsonify, render_template, redirect, url_for
from app.models.quickbooks import QuickBooks
from app.decorators.role_decorator import role_required
from app.routes.quickbooks.forms import ChartOffAccountForm, JournalEntryForm
from flask import app as app, flash, session, current_app
from app.helpers.auxillary import Auxillary
import os
import logging
from dotenv import load_dotenv
from app.models.central import Company
from app.utils.db_connection import DatabaseConnection
from app.models.company_quickbooks import QuickbooksAuditLogs
from app.helpers.quickbooks_helpers import QuickBooksHelper
from app.helpers.auxillary import Auxillary
import traceback
from decimal import Decimal

load_dotenv()

quickbooks_bp = Blueprint('quickbooks', __name__)

@quickbooks_bp.route('/create_account', methods=['POST'])
@role_required(['hr', 'company_hr', 'accountant', 'manager'])
def create_account():
    """Create an account."""
    # Initialize the database connection
    db_connection = current_app.config['db_connection']

    form = ChartOffAccountForm()
    # Get the QuickBooks client
    qb = QuickBooks(company_id=session.get('company_id'))
    try:
        app.logger.info('Getting account types')
        account_types = qb.get_account_types(qb.realm_id)
        #Initialize an empty list to hold unique account types and unique account subtypes
        unique_account_subtypes = []
        unique_account_types = []
        # get the account types before making them in the form
        for account_type in account_types:
            if account_type['AccountType'].strip() not in unique_account_types:
                unique_account_types.append(account_type['AccountType'])
            if account_type['AccountSubType'].strip() not in unique_account_subtypes:
                unique_account_subtypes.append(account_type['AccountSubType'])

        app.logger.info(f"Unique account types: {unique_account_types}")
        app.logger.info(f"Unique account subtypes: {unique_account_subtypes}")
        # Set the choices for the account type field
        form.account_type.choices = [(account_type, account_type) for account_type in unique_account_types]
        form.account_subtype.choices = [(account_subtype, account_subtype) for account_subtype in unique_account_subtypes]
    except Exception as e:
        app.logger.error(f"Error getting account types: {e}")
        form.account_type.choices = []
    if request.method == 'POST':
        if not form.validate_on_submit():
           app.logger.error('Form validation failed')
           # Try logging the form errors
           app.logger.error(form.errors)
           flash('Form validation failed', 'danger')
           return jsonify({'error': 'Form validation failed'}), 400

        # Retrieve the form data
        name = form.name.data
        description = form.description.data
        account_type = form.account_type.data
        account_subtype = form.account_subtype.data

        try:
            # Create the account
            account_data = {
                "Name": name,
                "Description": description,
                "AccountType": account_type,
                "AccountSubType": account_subtype
            }
            account = qb.create_account(qb.realm_id, account_data)
            app.logger.info(f"Account created: {account}")
            flash('Account created successfully', 'success')
            return jsonify({'message': 'Account created successfully'}), 200
        except Exception as e:
            app.logger.error(f"Error creating account: {e}")
            return jsonify({'error': 'Error creating account'}), 500

    try:
        app.logger.info('Rendering create_chart_of_account.html')
        return render_template('quickbooks/create_chart_of_account.html', form=form)
    except Exception as e:
        app.logger.error(f"Error rendering create_chart_of_account.html: {e}")
        return jsonify({'error': 'Error rendering create_chart_of_account.html'}), 500

@quickbooks_bp.route('/post_journal_entry', methods=['GET', 'POST'])
@role_required(['hr', 'company_hr', 'accountant', 'manager'])
def post_journal_entry():
    """Post a journal entry by mapping totals to QuickBooks accounts."""
    # Initialize the database connection
    db_connection = current_app.config['db_connection']
    try:
        company_id = session.get('company_id')
        database_name = session.get('database_name')
        current_app.logger.info(f"Company ID: {company_id}, Database Name: {database_name}")
    except Exception as e:
        company_id = None
        database_name = None
    try:
        employees_with_deductions = session.get('employees_with_deductions')
        current_app.logger.info(f"Employees with deductions: {employees_with_deductions}")
    except Exception as e:
        current_app.logger.error(f"Error getting employees with deductions from session: {e}")
        employees_with_deductions = []
    if not employees_with_deductions:
        flash("No journal data found.", "warning")
        return jsonify({'error': 'No journal data found'}), 400

    # Get the QuickBooks client
    try:
        qb = QuickBooks(company_id=session.get('company_id'))
        current_app.logger.info(f"QuickBooks client: {qb} access_token: {qb.access_token}, refresh_token: {qb.refresh_token}")
    except Exception as e:
        error_details = traceback.format_exc()
        message = f"Error getting QuickBooks client:\n{error_details}"
        current_app.logger.error(message)
    # First check if the company has QuickBooks tokens
    if qb.access_token is None or qb.refresh_token is None:
        current_app.logger.error("QuickBooks integration not set up.")
        flash("QuickBooks integration not set up. Please authorize the app.", "warning")
        # Redirect to the authorization URL
        return redirect(url_for('quickbooks.get_auth_url'))
    # Get the vendors
    try:
        vendors = qb.get_vendors(qb.realm_id)
        my_vendors = vendors.get('QueryResponse', {}).get('Vendor', [])
    except Exception as e:
        current_app.logger.error(f"Error getting vendors: {e}")
        my_vendors = []  # Make sure it's always defined

    # Get QuickBooks locations (departments in QB) and departments (classes in QB)
    locations = []
    departments = []
    try:
        # Get locations from QuickBooks (these are called "Departments" in QuickBooks)
        locations_response = qb.get_locations(qb.realm_id)
        if 'QueryResponse' in locations_response and 'Department' in locations_response['QueryResponse']:
            locations = locations_response['QueryResponse']['Department']
            current_app.logger.info(f"Retrieved {len(locations)} locations from QuickBooks")
        else:
            current_app.logger.warning("No locations found in QuickBooks or unexpected response format")

        # Get departments from QuickBooks (these are called "Classes" in QuickBooks)
        departments_response = qb.get_departments(qb.realm_id)
        if 'QueryResponse' in departments_response and 'Class' in departments_response['QueryResponse']:
            departments = departments_response['QueryResponse']['Class']
            current_app.logger.info(f"Retrieved {len(departments)} departments from QuickBooks")
        else:
            current_app.logger.warning("No departments found in QuickBooks or unexpected response format")
    except Exception as e:
        current_app.logger.error(f"Error getting locations and departments from QuickBooks: {e}")
        locations = []
        departments = []

    account_totals = {}

    def add_to_account(name, dr=0, cr=0):
        dr = Auxillary.round_to_decimal(dr)
        cr = Auxillary.round_to_decimal(cr)

        # Skip the account if both dr and cr are 0
        if dr == 0 and cr == 0:
            return
        # If the account doesn't exist, create it
        if name not in account_totals:
            account_totals[name] = {'DR': 0, 'CR': 0}
        account_totals[name]['DR'] += dr
        account_totals[name]['CR'] += cr

    for e in employees_with_deductions:
        add_to_account('Gross salary', dr=e['gross_needed'])
        add_to_account('Pension ER-Contr-8%', dr=e['pension_er_value'])
        add_to_account('Maternity ER-Contr-0.3%', dr=e['maternity_er_value'])
        add_to_account('Medical ER-Contr-7.5%', dr=e['rama_ee'])
        add_to_account('Other staff expenses', dr=e['total_reimbursements'])
        add_to_account('PAYE Payable', cr=e['paye'])

        # Combine employer and employee pension into a single "Pension Payable"
        pension_payable = Decimal(str(e['pension_ee_value'])) + Decimal(str(e['pension_er_value']))
        pension_payable = Auxillary.round_to_decimal(pension_payable)
        add_to_account('Pension Payable', cr=pension_payable)

        # Combine employer and employee maternity into a single "Maternity Payable"
        maternity_payable = Decimal(str(e['maternity_er_value'])) + Decimal(str(e['maternity_ee_value']))
        maternity_payable = Auxillary.round_to_decimal(maternity_payable)
        add_to_account('Maternity Payable', cr=maternity_payable)

        # Calculate net salary payable with consistent rounding (same as download_journal_entry)
        net_salary_value = Decimal(str(e['net_salary_value']))
        total_deductions = Decimal(str(e['total_deductions']))
        total_reimbursements = Decimal(str(e['total_reimbursements']))
        brd_deduction = Decimal(str(e['brd_deduction']))
        salary_advance = Decimal(str(e['salary_advance']))

        # Log the values before calculation for debugging
        current_app.logger.info(f"Employee {e['employee'].get('first_name', '')} {e['employee'].get('last_name', '')}: net_salary_value={net_salary_value}, total_deductions={total_deductions}, total_reimbursements={total_reimbursements}, brd_deduction={brd_deduction}, salary_advance={salary_advance}")

        # Calculate with proper Decimal arithmetic - using the same order as in payroll_summary.py
        net_salary_payable = net_salary_value - total_deductions + total_reimbursements - brd_deduction - salary_advance
        current_app.logger.info(f"Before rounding: net_salary_payable={net_salary_payable}")

        # Round to whole number for consistency
        net_salary_payable = Auxillary.round_to_decimal(net_salary_payable)
        current_app.logger.info(f"After rounding: net_salary_payable={net_salary_payable}")
        add_to_account('Net Salary Payable', cr=net_salary_payable)

        add_to_account('CBHI Payable', cr=e['cbhi_value'])
        add_to_account('RAMA (Medical) Payable', cr=e['total_rama'])
        add_to_account('BRD Payable', cr=e['brd_deduction'])
        add_to_account('Salary Advance', cr=e['salary_advance'])
        add_to_account('Other Deductions', cr=e['total_deductions'])

    # Check if debits and credits balance
    total_dr = sum(values['DR'] for values in account_totals.values())
    total_cr = sum(values['CR'] for values in account_totals.values())

    # Round totals for comparison
    total_dr = Auxillary.round_to_decimal(total_dr)
    total_cr = Auxillary.round_to_decimal(total_cr)

    if total_dr != total_cr:
        current_app.logger.warning(f"Journal entries do not balance: DR={total_dr}, CR={total_cr}, Difference={total_dr-total_cr}")
        # Adjust the Net Salary Payable to balance the journal entry
        if 'Net Salary Payable' in account_totals:
            difference = total_dr - total_cr
            account_totals['Net Salary Payable']['CR'] += difference
            # Recalculate totals
            total_dr = Auxillary.round_to_decimal(sum(values['DR'] for values in account_totals.values()))
            total_cr = Auxillary.round_to_decimal(sum(values['CR'] for values in account_totals.values()))
            current_app.logger.info(f"Journal entries balanced by adjusting Net Salary Payable: New DR={total_dr}, CR={total_cr}")

    try:
        accounts = qb.get_accounts(qb.realm_id)
        my_accounts = accounts['QueryResponse']['Account']
        current_app.logger.info(f"Accounts that have been fetched: {accounts}")
        current_app.logger.info("")
        current_app.logger.info(f"Accounts that have been retrieved: {my_accounts}")

        account_choices = []
        for acc in my_accounts:
            current_app.logger.info("")
            current_app.logger.info(f"Account inside the for loop: {acc}")
            account_info = {
                "Id": acc['Id'],
                "Name": acc['FullyQualifiedName'],
                "AccountType": acc.get('AccountSubType'),
                "Currency": acc['CurrencyRef']['name']
            }
            account_choices.append(account_info)
        current_app.logger.info(f"Account choices: {account_choices}")

    except Exception as e:
        current_app.logger.error(f"Error fetching accounts: {e}")
        account_choices = []

    if request.method == 'POST':
        mappings = request.form.to_dict()
        current_app.logger.info(f"Mappings: {mappings}")
        lines = []

        # Get the journal memo from the form
        journal_memo = mappings.get('journal_memo', "Payroll Journal Entry")
        current_app.logger.info(f"Journal memo: {journal_memo}")

        for name, amounts in account_totals.items():
            account_id = mappings.get(name)
            current_app.logger.info(f"Account ID for {name}: {account_id}")
            if not account_id:
                flash(f"Missing account for {name}", "danger")
                return redirect(request.url)
            # Check if the account is of type "Accounts Payable" and add vendor reference
            vendor_reference = None
            account_info = next((acc for acc in account_choices if acc['Id'] == account_id), None)

            # Get vendor key from the mappings dict
            vendor_key = f'vendor_{name}'  # name corresponds to account name like 'PAYE Payable'
            vendor_id = mappings.get(vendor_key)
            if vendor_id:
                vendor_info = next((v for v in my_vendors if v['Id'] == vendor_id), None)
                vendor_name = vendor_info['DisplayName'] if vendor_info else "Unknown Vendor"
                current_app.logger.info(f"Vendor ID: {vendor_id}, Vendor Name: {vendor_name}")

                vendor_reference = {
                    "Entity": {
                        "Type": "Vendor",
                        "EntityRef": {
                            "value": vendor_id
                        }
                    }
                }


            # Get the custom description from the form
            description_key = f'desc_{name}'
            custom_description = mappings.get(description_key, name)
            current_app.logger.info(f"Description for {name}: {custom_description}")

            # Get line-specific location and department
            line_location_id = mappings.get(f'location_{name}')
            line_department_id = mappings.get(f'department_{name}')

            # Get location and department names for description
            line_location_name = None
            line_department_name = None

            if line_location_id:
                location_obj = next((loc for loc in locations if loc.get('Id') == line_location_id), None)
                if location_obj:
                    line_location_name = location_obj.get('Name')

            if line_department_id:
                department_obj = next((dept for dept in departments if dept.get('Id') == line_department_id), None)
                if department_obj:
                    line_department_name = department_obj.get('Name')

            # Add location/department to description if available
            line_description = custom_description
            if line_location_name:
                line_description += f" - {line_location_name}"
            if line_department_name:
                line_description += f" - {line_department_name}"

            if amounts['DR']:
                # Round the amount using Auxillary.round_to_decimal for consistency
                dr_amount = Auxillary.round_to_decimal(amounts['DR'])

                # Create the line detail with department reference if available
                line_detail = {
                    "PostingType": "Debit",
                    "AccountRef": {"value": account_id}
                }

                # Add class (department) reference if available
                if line_department_id:
                    line_detail["ClassRef"] = {
                        "value": line_department_id
                    }

                # Add department (location) reference if available
                if line_location_id:
                    line_detail["DepartmentRef"] = {
                        "value": line_location_id
                    }

                lines.append({
                    "DetailType": "JournalEntryLineDetail",
                    "Amount": float(dr_amount),
                    "Description": line_description,
                    "JournalEntryLineDetail": line_detail
                })

            if amounts['CR']:
                # Round the amount using Auxillary.round_to_decimal for consistency
                cr_amount = Auxillary.round_to_decimal(amounts['CR'])

                # Create the line detail with department reference if available
                line_detail = {
                    "PostingType": "Credit",
                    "AccountRef": {"value": account_id},
                    **(vendor_reference if vendor_reference else {})
                }

                # Add class (department) reference if available
                if line_department_id:
                    line_detail["ClassRef"] = {
                        "value": line_department_id
                    }

                # Add department (location) reference if available
                if line_location_id:
                    line_detail["DepartmentRef"] = {
                        "value": line_location_id
                    }

                lines.append({
                    "DetailType": "JournalEntryLineDetail",
                    "Amount": float(cr_amount),
                    "Description": line_description,
                    "JournalEntryLineDetail": line_detail
                })

        try:
            # Calculate total debits and credits to ensure they balance
            total_debits = sum(float(line["Amount"]) for line in lines if line["JournalEntryLineDetail"]["PostingType"] == "Debit")
            total_credits = sum(float(line["Amount"]) for line in lines if line["JournalEntryLineDetail"]["PostingType"] == "Credit")

            # Use Auxillary.round_to_decimal for consistent rounding
            total_debits = Auxillary.round_to_decimal(total_debits)
            total_credits = Auxillary.round_to_decimal(total_credits)

            current_app.logger.info(f"Total debits: {total_debits}, Total credits: {total_credits}")

            # Check if debits and credits are balanced
            if total_debits != total_credits:
                current_app.logger.error(f"Debits and credits are not balanced: Debits={total_debits}, Credits={total_credits}")
                flash(f"Journal entry is not balanced. Debits ({total_debits}) must equal Credits ({total_credits}).", "danger")
                return redirect(request.url)

            # Create journal entry with memo
            journal_entry_data = {
                "PrivateNote": journal_memo,
                "Line": lines
            }

            current_app.logger.info(f"Journal entry data: {journal_entry_data}")
            response = qb.create_journal_entry(qb.realm_id, journal_entry_data)
            current_app.logger.info(f"Journal entry posted: {response}")
            # Process the response from QuickBooks
            message, status = QuickBooksHelper.handle_quickbooks_response(response)
            current_app.logger.info(f"QuickBooks response processed: message='{message}', status='{status}'")

            if status == "Success":
                current_app.logger.info(f"Journal entry posted successfully: {message}")
                flash("Journal entry posted successfully", "success")
            else:
                current_app.logger.error(f"Error posting journal entry: {message}")
                flash(message, "danger")
            # Save the audit trail logs in the database so that we can later track
            database_name = qb.database_name
            # connect to the database
            # get the user id from the session
            user_id = session.get('user_id')
            with db_connection.get_session(database_name) as db_session:
                # Add the audit log
                log_entry = {
                    "action_type": "Post Journal Entry",
                    "operation_status": status,
                    "error_message": message if status == "Failure" else None,
                    "request_payload": journal_entry_data,
                    "response_payload": response,
                    "user_id": user_id
                }
                try:
                    result = QuickbooksAuditLogs.add_quickbooks_audit_log(db_session, **log_entry)
                    current_app.logger.info(f"Audit log entry created: {result}")
                except Exception as e:
                    current_app.logger.error(f"Error creating audit log entry: {e}")
                    flash("Failed to create audit log entry, but journal entry was posted successfully.", "warning")

            # No need for duplicate success message since we already flashed one above
            return redirect(url_for('quickbooks.post_journal_entry'))
        except Exception as e:
            current_app.logger.error(f"Failed to create journal entry: {e}")
            flash("Failed to post journal entry.", "danger")
            return redirect(request.url)

    try:
        return render_template('quickbooks/post_journal_entry.html',
                           account_totals=account_totals,
                           account_choices=account_choices,
                           vendors=my_vendors,
                           locations=locations,
                           departments=departments)
    except Exception as e:
        message = f"Failed to render post journal entry page: {e}"
        current_app.logger.error(message)
        flash(message, "danger")
        return redirect(url_for('admin.dashboard'))


@quickbooks_bp.route('/get_company_info', methods=['GET'])
@role_required(['hr', 'company_hr', 'accountant', 'manager'])
def get_company_info():
    """Get company info."""
    qb = QuickBooks(company_id=session.get('company_id'))
    try:
        app.logger.info('Getting company info')
        company_info = qb.get_company_info(qb.realm_id)
        app.logger.info(f"Company info: {company_info}")
        return jsonify(company_info), 200
    except Exception as e:
        app.logger.error(f"Error getting company info: {e}")
        return jsonify({'error': 'Error getting company info'}), 500

@quickbooks_bp.route('/get_accounts', methods=['GET'])
@role_required(['hr', 'company_hr', 'accountant', 'manager'])
def get_accounts():
    """Get accounts."""
    qb = QuickBooks(company_id=session.get('company_id'))
    try:
        current_app.logger.info('Getting accounts')
        accounts = qb.get_accounts(qb.realm_id)
        current_app.logger.info(f"Accounts length: {len(accounts)}")
        return jsonify(accounts), 200
    except Exception as e:
        current_app.logger.error(f"Error getting accounts: {e}")
        return jsonify({'error': 'Error getting accounts'}), 500

@quickbooks_bp.route('/get_vendors', methods=['GET'])
@role_required(['hr', 'company_hr', 'accountant', 'manager'])
def get_vendors():
    """Get vendors."""
    qb = QuickBooks(company_id=session.get('company_id'))
    try:
        current_app.logger.info('Getting vendors')
        vendors = qb.get_vendors(qb.realm_id)
        current_app.logger.info(f"Vendors length: {len(vendors)}")
        return jsonify(vendors), 200
    except Exception as e:
        current_app.logger.error(f"Error getting vendors: {e}")
        return jsonify({'error': 'Error getting vendors'}), 500

@quickbooks_bp.route('/get_auth_url', methods=['GET'])
@role_required(['hr', 'company_hr', 'accountant', 'manager'])
def get_auth_url():
    """Get the QuickBooks OAuth2 authorization URL."""
    company_id = session.get('company_id')
    if not company_id:
        current_app.logger.error("No company ID found in session")
        return jsonify({'error': 'No company ID found in session'}), 400
    # get the quickbooks object
    try:
        qb = QuickBooks(company_id=company_id)
        current_app.logger.info(f"QuickBooks client: {qb}")
    except Exception as e:
        current_app.logger.error(f"Error getting QuickBooks client: {e}")
        return jsonify({'error': 'Error getting QuickBooks client'}), 400
    try:
        auth_url = qb.get_authorization_url()
        current_app.logger.info(f"Authorization URL: {auth_url}")
        # save the audit logs
        database_name = qb.database_name
        # connect to the database
        # get the user id from the session
        user_id = session.get('user_id')
        """with db_connection.get_session(database_name) as db_session:
            # Add the audit log
            log_entry = {
                "action_type": "Get Authorization URL",
                "operation_status": "Success",
                "request_payload": None,
                "response_payload": auth_url,
                "user_id": user_id
            }
            try:
                result = QuickbooksAuditLogs.add_quickbooks_audit_log(db_session, **log_entry)
                current_app.logger.info(f"Audit log entry created: {result}")
            except Exception as e:
                current_app.logger.error(f"Error creating audit log entry: {e}")
                flash("Failed to create audit log entry.", "danger")
            """
        return redirect(auth_url)
    except Exception as e:
        current_app.logger.error(f"Error getting authorization URL: {e}")
        return jsonify({'error': 'Error getting authorization URL'}), 400

@quickbooks_bp.route('/disconnect', methods=['GET'])
@role_required(['hr', 'company_hr', 'accountant', 'manager'])
def disconnect():
    """Disconnect from QuickBooks."""
    # Initialize the database connection
    db_connection = current_app.config['db_connection']
    company_id = session.get('company_id')
    if not company_id:
        current_app.logger.error("No company ID found in session")
        return jsonify({'error': 'No company ID found in session'}), 400
    # get the quickbooks object
    try:
        qb = QuickBooks(company_id=company_id)
        current_app.logger.info(f"QuickBooks client: {qb}")
    except Exception as e:
        current_app.logger.error(f"Error getting QuickBooks client: {e}")
        return jsonify({'error': 'Error getting QuickBooks client'}), 400
    try:
        qb.disconnect_app()
        flash("QuickBooks integration disconnected successfully!", "success")
        message = "Netpick integration disconnected successfully!"
        return jsonify({'success': True, 'message': message}), 200
    except Exception as e:
        current_app.logger.error(f"Error disconnecting from QuickBooks: {e}")
        message = "Error disconnecting from QuickBooks"
        return jsonify({'success': False, 'message': message}), 404

@quickbooks_bp.route('/webhook', methods=['GET'])
@role_required(['hr', 'company_hr', 'accountant', 'manager'])
def webhook():
    """Callback route for QuickBooks OAuth2."""
    code = request.args.get('code')
    state = request.args.get('state')
    error = request.args.get('error')
    realm_id = request.args.get('realmId')
    current_app.logger.info(f"Callback realm ID: {realm_id}")

    current_app.logger.info(f"Callback state: {state}")
    current_app.logger.info(f"Callback code: {code}")
    current_app.logger.info(f"Callback error: {error}")
    if error:
        current_app.logger.error(f"Error in callback: {error}")
        return jsonify({'error': 'Error in callback'}), 400

    if not code:
        current_app.logger.error("No code provided in callback")
        return jsonify({'error': 'No code provided'}), 400
    if not realm_id:
        current_app.logger.error("No realm ID provided in callback")
        return jsonify({'error': 'No realm ID provided'}), 400
    # get the quickbooks object
    company_id = session.get('company_id')
    if not company_id:
        current_app.logger.error("No company ID found in session")
        return jsonify({'error': 'No company ID found in session'}), 400

    try:
        current_app.logger.info(f"Getting QuickBooks client for company ID: {company_id}")
        qb = QuickBooks(company_id=company_id)
        current_app.logger.info(f"QuickBooks client: {qb}")
    except Exception as e:
        current_app.logger.error(f"Error getting QuickBooks client: {e}")
        return jsonify({'error': 'Error getting QuickBooks client'}), 400

    try:
        tokens = qb.get_quickbooks_access_token(code)
        current_app.logger.info(f"Access token: {tokens['access_token']}")
        current_app.logger.info(f"Refresh token: {tokens['refresh_token']}")
        flash("QuickBooks integration successful!", "success")
        # Update the data in the company table
        company_id = session.get('company_id')
        company = session.get('company')
        current_app.logger.info(f"Company ID: {company_id}")
        current_app.logger.info(f"Company: {company}")
        if company_id:
            result = Company.update_company_data(company_id,
                                        quickbooks_access_token=QuickBooksHelper.encrypt(tokens['access_token']),
                                        quickbooks_refresh_token=QuickBooksHelper.encrypt(tokens['refresh_token']),
                                        quickbooks_authorization_code=QuickBooksHelper.encrypt(code),
                                        quickbooks_realm_id=realm_id)
            if result:
                current_app.logger.info(f"Updated QuickBooks tokens for company ID {company_id} with a result of {result}")
                flash("QuickBooks tokens updated successfully!", "success")
            else:
                current_app.logger.error(f"Failed to update QuickBooks tokens for company ID {company_id}")
                flash("Failed to update QuickBooks tokens.", "danger")
                return jsonify({'error': 'Failed to update QuickBooks tokens'}), 400
        else:
            current_app.logger.error("No company ID found in session")
            flash("No company ID found in session", "danger")
        return redirect(url_for('admin_data.dashboard'))
    except Exception as e:
        current_app.logger.error(f"Error getting access token: {e}")
        message = "Error getting access token"
        flash(message, "danger")
        return jsonify({'success': False, 'message': message}), 404