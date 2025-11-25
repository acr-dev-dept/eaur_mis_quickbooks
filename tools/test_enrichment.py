#!/usr/bin/env python3
"""
Test script for customer enrichment fixes
"""

import sys
import os
import requests
import json

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_applicant_preview_api():
    """Test the applicant preview API endpoint"""
    print("++ Testing Applicant Preview API...")

    try:
        # Test the preview endpoint
        url = "https://api.eaur.ac.rw/api/v1/sync/customers/preview/applicants?limit=5"
        response = requests.get(url)

        if response.status_code == 200:
            data = response.json()

            print(f"==YES==API Response Status: {response.status_code}")
            print(f"==YES==Success: {data.get('success')}")
            print(f"==YES==Message: {data.get('message')}")

            applicants = data.get('data', {}).get('applicants', [])
            print(f"==YES==Retrieved {len(applicants)} applicants")

            if applicants:
                print("\n📊 Sample Applicant Data:")
                sample_applicant = applicants[0]

                # Check for enriched fields
                enriched_fields = [
                    'campus_name', 'program_name', 'program_mode',
                    'country_of_birth', 'national_id'
                ]

                print(f"   Applicant: {sample_applicant.get('display_name')}")
                print(f"   Tracking ID: {sample_applicant.get('tracking_id')}")

                for field in enriched_fields:
                    value = sample_applicant.get(field, 'MISSING')
                    status = "✅" if value and value != 'MISSING' else "❌"

                    # Special check for country_of_birth - should not be numeric
                    if field == 'country_of_birth' and value and str(value).isdigit():
                        status = "⚠️ "
                        print(f"   {status} {field}: '{value}' (still showing ID instead of country name)")
                    # Special check for program_mode - should not be numeric
                    elif field == 'program_mode' and value and str(value).isdigit():
                        status = "⚠️ "
                        print(f"   {status} {field}: '{value}' (still showing ID instead of mode name)")
                    else:
                        print(f"   {status} {field}: '{value}'")

                # Check for error indicators
                if sample_applicant.get('error_occurred'):
                    print(f"   ⚠️  Error occurred: {sample_applicant.get('error_message')}")

                # Check for conversion errors in response
                conversion_errors = data.get('data', {}).get('conversion_errors', [])
                if conversion_errors:
                    print(f"\n⚠️  Conversion Errors: {len(conversion_errors)}")
                    for error in conversion_errors[:3]:  # Show first 3 errors
                        print(f"     - {error.get('appl_Id')}: {error.get('error')}")

            return True

        else:
            print(f"❌ API Error: {response.status_code}")
            print(f"❌ Response: {response.text}")
            return False

    except Exception as e:
        print(f"❌ Exception: {e}")
        return False

def test_student_preview_api():
    """Test the student preview API endpoint"""
    print("++ Testing Student Preview API...")
    
    try:
        # Test the preview endpoint
        url = "https://api.eaur.ac.rw/api/v1/sync/customers/preview/students?limit=5"
        response = requests.get(url)
        
        if response.status_code == 200:
            data = response.json()
            
            print(f"==YES==API Response Status: {response.status_code}")
            print(f"==YES==Success: {data.get('success')}")
            print(f"==YES==Message: {data.get('message')}")
            
            students = data.get('data', {}).get('students', [])
            print(f"==YES==Retrieved {len(students)} students")
            
            if students:
                print("\n📊 Sample Student Data:")
                sample_student = students[0]
                
                # Check for enriched fields
                enriched_fields = [
                    'campus_name', 'program_name', 'level_name',
                    'intake_details', 'program_type', 'national_id', 'nationality'
                ]
                
                print(f"   Student: {sample_student.get('display_name')}")
                print(f"   Reg No: {sample_student.get('reg_no')}")
                
                for field in enriched_fields:
                    value = sample_student.get(field, 'MISSING')
                    status = "✅" if value and value != 'MISSING' else "❌"

                    # Special check for nationality - should not be numeric
                    if field == 'nationality' and value and value.isdigit():
                        status = "⚠️ "
                        print(f"   {status} {field}: '{value}' (still showing ID instead of country name)")
                    else:
                        print(f"   {status} {field}: '{value}'")
                
                # Check for error indicators
                if sample_student.get('error_occurred'):
                    print(f"   ⚠️  Error occurred: {sample_student.get('error_message')}")
                
                # Check for conversion errors in response
                conversion_errors = data.get('data', {}).get('conversion_errors', [])
                if conversion_errors:
                    print(f"\n⚠️  Conversion Errors: {len(conversion_errors)}")
                    for error in conversion_errors[:3]:  # Show first 3 errors
                        print(f"     - {error.get('reg_no')}: {error.get('error')}")
            
            return True
            
        else:
            print(f"❌ API Error: {response.status_code}")
            print(f"❌ Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Exception: {e}")
        return False

def test_debug_endpoint(reg_no):
    """Test the debug endpoint for a specific student"""
    print(f"\n🔍 Testing Debug Endpoint for Student: {reg_no}")
    
    try:
        url = f"https://api.eaur.ac.rw/api/v1/sync/customers/debug/student/{reg_no}"
        response = requests.get(url)
        
        if response.status_code == 200:
            data = response.json()
            
            print(f"==YES==Debug Response Status: {response.status_code}")
            debug_results = data.get('data', {})
            
            print(f"==YES==Student: {debug_results.get('reg_no')}")
            
            # Show enrichment results
            enrichment_results = debug_results.get('enrichment_results', {})
            print("\n📊 Enrichment Results:")
            for method, result in enrichment_results.items():
                status = "✅" if result and not result.startswith('ERROR:') else "❌"
                print(f"   {status} {method}: '{result}'")
            
            # Show errors
            errors = debug_results.get('errors', [])
            if errors:
                print(f"\n❌ Errors ({len(errors)}):")
                for error in errors:
                    print(f"   - {error}")
            
            # Show full QuickBooks dict status
            if 'full_quickbooks_dict' in debug_results:
                print("\n==YES==Full QuickBooks dict generated successfully")
                qb_dict = debug_results['full_quickbooks_dict']
                print(f"   - Display Name: {qb_dict.get('display_name')}")
                print(f"   - Campus: {qb_dict.get('campus_name')}")
                print(f"   - Program: {qb_dict.get('program_name')}")
                print(f"   - Level: {qb_dict.get('level_name')}")
                nationality = qb_dict.get('nationality', '')
                if nationality and nationality.isdigit():
                    print(f"   ⚠️  Nationality: '{nationality}' (still showing ID)")
                else:
                    print(f"   ==YES==Nationality: '{nationality}'")
            elif 'full_quickbooks_dict_error' in debug_results:
                print(f"\n❌ Full QuickBooks dict error: {debug_results['full_quickbooks_dict_error']}")
            
            return True
            
        else:
            print(f"❌ Debug API Error: {response.status_code}")
            print(f"❌ Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Exception: {e}")
        return False

def test_country_debug_endpoint(reg_no):
    """Test the country debug endpoint for a specific student"""
    print(f"\n🌍 Testing Country Debug Endpoint for Student: {reg_no}")

    try:
        url = f"https://api.eaur.ac.rw/api/v1/sync/customers/debug/country/{reg_no}"
        response = requests.get(url)

        if response.status_code == 200:
            data = response.json()

            print(f"==YES==Country Debug Response Status: {response.status_code}")
            debug_results = data.get('data', {})

            print(f"==YES==Student: {debug_results.get('reg_no')}")

            # Show raw data
            raw_data = debug_results.get('raw_data', {})
            print("\n📊 Raw Country Data:")
            print(f"   cntr_id: {raw_data.get('cntr_id')}")
            print(f"   nationality: {raw_data.get('nationality')}")
            print(f"   has_country_relationship: {raw_data.get('has_country_relationship')}")

            # Show lookup results
            lookup_results = debug_results.get('country_lookup_results', {})
            print("\n🔍 Country Lookup Results:")

            if 'by_cntr_id' in lookup_results:
                cntr_result = lookup_results['by_cntr_id']
                if cntr_result.get('found'):
                    print(f"   ==YES==By cntr_id: {cntr_result.get('cntr_name')} ({cntr_result.get('cntr_nationality')})")
                else:
                    print(f"   ❌ By cntr_id: Not found")

            if 'by_nationality_field' in lookup_results:
                nat_result = lookup_results['by_nationality_field']
                if nat_result.get('found'):
                    print(f"   ==YES==By nationality field: {nat_result.get('cntr_name')} ({nat_result.get('cntr_nationality')})")
                else:
                    print(f"   ❌ By nationality field: Not found")

            # Show enrichment result
            if 'enrichment_result' in debug_results:
                enrichment_result = debug_results['enrichment_result']
                if enrichment_result and not enrichment_result.isdigit():
                    print(f"\n==YES==Enrichment Result: '{enrichment_result}'")
                else:
                    print(f"\n⚠️  Enrichment Result: '{enrichment_result}' (still showing ID)")
            elif 'enrichment_error' in debug_results:
                print(f"\n❌ Enrichment Error: {debug_results['enrichment_error']}")

            return True

        else:
            print(f"❌ Country Debug API Error: {response.status_code}")
            print(f"❌ Response: {response.text}")
            return False

    except Exception as e:
        print(f"❌ Exception: {e}")
        return False

def test_applicant_debug_endpoint(appl_id):
    """Test the applicant debug endpoint for a specific applicant"""
    print(f"\n🎓 Testing Applicant Debug Endpoint for ID: {appl_id}")

    try:
        url = f"https://api.eaur.ac.rw/api/v1/sync/customers/debug/applicant/{appl_id}"
        response = requests.get(url)

        if response.status_code == 200:
            data = response.json()

            print(f"==YES==Applicant Debug Response Status: {response.status_code}")
            debug_results = data.get('data', {})

            print(f"==YES==Applicant ID: {debug_results.get('appl_Id')}")
            print(f"==YES==Tracking ID: {debug_results.get('tracking_id')}")

            # Show raw data
            raw_data = debug_results.get('raw_data', {})
            print("\n📊 Raw Applicant Data:")
            print(f"   country_of_birth: {raw_data.get('country_of_birth')}")
            print(f"   present_nationality: {raw_data.get('present_nationality')}")
            print(f"   program_mode_id: {raw_data.get('program_mode_id')}")

            # Show enrichment results
            enrichment_results = debug_results.get('enrichment_results', {})
            print("\n📊 Enrichment Results:")
            for method, result in enrichment_results.items():
                status = "✅" if result and not str(result).isdigit() else "⚠️ "
                if str(result).isdigit():
                    print(f"   {status} {method}: '{result}' (still showing ID)")
                else:
                    print(f"   {status} {method}: '{result}'")

            # Show errors
            errors = debug_results.get('errors', [])
            if errors:
                print(f"\n❌ Errors ({len(errors)}):")
                for error in errors:
                    print(f"   - {error}")

            # Show full QuickBooks dict status
            if 'full_quickbooks_dict' in debug_results:
                print("\n==YES==Full QuickBooks dict generated successfully")
                qb_dict = debug_results['full_quickbooks_dict']
                print(f"   - Display Name: {qb_dict.get('display_name')}")
                print(f"   - Country of Birth: {qb_dict.get('country_of_birth')}")
                print(f"   - Program Mode: {qb_dict.get('program_mode')}")
            elif 'full_quickbooks_dict_error' in debug_results:
                print(f"\n❌ Full QuickBooks dict error: {debug_results['full_quickbooks_dict_error']}")

            return True

        else:
            print(f"❌ Applicant Debug API Error: {response.status_code}")
            print(f"❌ Response: {response.text}")
            return False

    except Exception as e:
        print(f"❌ Exception: {e}")
        return False

def main():
    """Main test function"""
    print("=" * 70)
    print("EAUR Customer Enrichment Test Suite")
    print("=" * 70)

    # Test 1: Preview APIs
    applicant_success = test_applicant_preview_api()
    student_success = test_student_preview_api()
    
    # Test 2: Debug specific records (use ones from the preview)
    if applicant_success:
        # Get an applicant ID from the preview to test debug
        try:
            url = "https://api.eaur.ac.rw/api/v1/sync/customers/preview/applicants?limit=1"
            response = requests.get(url)
            if response.status_code == 200:
                data = response.json()
                applicants = data.get('data', {}).get('applicants', [])
                if applicants:
                    appl_id = applicants[0].get('appl_Id')
                    if appl_id:
                        test_applicant_debug_endpoint(appl_id)
        except:
            print("\n⚠️  Could not get applicant for debug test")

    if student_success:
        # Get a student reg_no from the preview to test debug
        try:
            url = "https://api.eaur.ac.rw/api/v1/sync/customers/preview/students?limit=1"
            response = requests.get(url)
            if response.status_code == 200:
                data = response.json()
                students = data.get('data', {}).get('students', [])
                if students:
                    reg_no = students[0].get('reg_no')
                    if reg_no:
                        test_debug_endpoint(reg_no)
                        test_country_debug_endpoint(reg_no)
        except:
            print("\n⚠️  Could not get student for debug test")
    
    print("\n" + "=" * 70)
    print("Test Suite Complete")
    print("=" * 70)

if __name__ == '__main__':
    main()
