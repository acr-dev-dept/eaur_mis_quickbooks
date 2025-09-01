#!/usr/bin/env python3
"""
Performance testing tool for customer synchronization optimization
"""

import sys
import os
import requests
import json
import time

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_applicant_performance():
    """Test applicant preview API performance"""
    print("🚀 Testing Applicant Preview API Performance...")
    
    test_cases = [
        {'limit': 5, 'name': 'Small batch'},
        {'limit': 10, 'name': 'Medium batch'},
        {'limit': 25, 'name': 'Large batch'},
        {'limit': 50, 'name': 'Extra large batch'}
    ]
    
    results = []
    
    for test_case in test_cases:
        limit = test_case['limit']
        name = test_case['name']
        
        print(f"\n📊 Testing {name} (limit={limit})...")
        
        try:
            # Measure response time
            start_time = time.time()
            
            url = f"https://api.eaur.ac.rw/api/v1/sync/customers/preview/applicants?limit={limit}"
            response = requests.get(url, timeout=60)  # 60 second timeout
            
            end_time = time.time()
            response_time = end_time - start_time
            
            if response.status_code == 200:
                data = response.json()
                
                # Extract performance metrics
                applicants = data.get('data', {}).get('applicants', [])
                actual_count = len(applicants)
                conversion_errors = data.get('data', {}).get('conversion_errors', [])
                performance_info = data.get('data', {}).get('performance', {})
                
                # Check for enriched data quality
                enriched_count = 0
                for app in applicants:
                    if (app.get('country_of_birth') and not str(app.get('country_of_birth')).isdigit() and
                        app.get('program_mode') and not str(app.get('program_mode')).isdigit()):
                        enriched_count += 1
                
                result = {
                    'test_case': name,
                    'limit': limit,
                    'response_time': round(response_time, 2),
                    'actual_count': actual_count,
                    'enriched_count': enriched_count,
                    'enrichment_rate': round((enriched_count / actual_count * 100) if actual_count > 0 else 0, 1),
                    'conversion_errors': len(conversion_errors),
                    'optimized': performance_info.get('optimized_batch_loading', False),
                    'status': 'SUCCESS'
                }
                
                print(f"   ✅ Response Time: {response_time:.2f}s")
                print(f"   ✅ Records Retrieved: {actual_count}")
                print(f"   ✅ Enrichment Rate: {result['enrichment_rate']}%")
                print(f"   ✅ Conversion Errors: {len(conversion_errors)}")
                print(f"   ✅ Batch Optimized: {result['optimized']}")
                
                if response_time > 10:
                    print(f"   ⚠️  Slow response time: {response_time:.2f}s")
                
                if len(conversion_errors) > 0:
                    print(f"   ⚠️  {len(conversion_errors)} conversion errors detected")
                
            else:
                result = {
                    'test_case': name,
                    'limit': limit,
                    'response_time': response_time,
                    'status': 'ERROR',
                    'error': f"HTTP {response.status_code}: {response.text[:200]}"
                }
                print(f"   ❌ HTTP Error: {response.status_code}")
                print(f"   ❌ Response Time: {response_time:.2f}s")
            
            results.append(result)
            
        except requests.exceptions.Timeout:
            result = {
                'test_case': name,
                'limit': limit,
                'status': 'TIMEOUT',
                'error': 'Request timed out after 60 seconds'
            }
            print(f"   ❌ TIMEOUT: Request took longer than 60 seconds")
            results.append(result)
            
        except Exception as e:
            result = {
                'test_case': name,
                'limit': limit,
                'status': 'EXCEPTION',
                'error': str(e)
            }
            print(f"   ❌ Exception: {e}")
            results.append(result)
    
    return results

def test_limit_functionality():
    """Test if limit parameter works correctly"""
    print("\n🔢 Testing Limit Parameter Functionality...")
    
    test_limits = [1, 3, 5, 10, 15]
    
    for limit in test_limits:
        try:
            url = f"https://api.eaur.ac.rw/api/v1/sync/customers/preview/applicants?limit={limit}"
            response = requests.get(url, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                actual_count = len(data.get('data', {}).get('applicants', []))
                
                if actual_count == limit:
                    print(f"   ✅ Limit {limit}: Got {actual_count} records")
                else:
                    print(f"   ⚠️  Limit {limit}: Expected {limit}, got {actual_count} records")
            else:
                print(f"   ❌ Limit {limit}: HTTP {response.status_code}")
                
        except Exception as e:
            print(f"   ❌ Limit {limit}: Exception - {e}")

def print_performance_summary(results):
    """Print performance test summary"""
    print("\n" + "=" * 70)
    print("PERFORMANCE TEST SUMMARY")
    print("=" * 70)
    
    successful_tests = [r for r in results if r.get('status') == 'SUCCESS']
    
    if successful_tests:
        avg_response_time = sum(r['response_time'] for r in successful_tests) / len(successful_tests)
        max_response_time = max(r['response_time'] for r in successful_tests)
        min_response_time = min(r['response_time'] for r in successful_tests)
        
        print(f"📊 Successful Tests: {len(successful_tests)}/{len(results)}")
        print(f"⏱️  Average Response Time: {avg_response_time:.2f}s")
        print(f"⏱️  Fastest Response: {min_response_time:.2f}s")
        print(f"⏱️  Slowest Response: {max_response_time:.2f}s")
        
        # Performance assessment
        if max_response_time < 5:
            print("🎉 EXCELLENT: All responses under 5 seconds")
        elif max_response_time < 10:
            print("✅ GOOD: All responses under 10 seconds")
        elif max_response_time < 30:
            print("⚠️  ACCEPTABLE: Some responses over 10 seconds")
        else:
            print("❌ POOR: Responses over 30 seconds detected")
        
        # Check optimization
        optimized_tests = [r for r in successful_tests if r.get('optimized')]
        if optimized_tests:
            print(f"🚀 Batch Optimization: Active ({len(optimized_tests)}/{len(successful_tests)} tests)")
        else:
            print("⚠️  Batch Optimization: Not detected")
    
    # Show failed tests
    failed_tests = [r for r in results if r.get('status') != 'SUCCESS']
    if failed_tests:
        print(f"\n❌ Failed Tests: {len(failed_tests)}")
        for test in failed_tests:
            print(f"   - {test['test_case']}: {test.get('error', 'Unknown error')}")

def main():
    """Main performance test function"""
    print("=" * 70)
    print("EAUR Customer Sync Performance Test Suite")
    print("=" * 70)
    
    # Test 1: Performance across different batch sizes
    performance_results = test_applicant_performance()
    
    # Test 2: Limit parameter functionality
    test_limit_functionality()
    
    # Test 3: Summary and recommendations
    print_performance_summary(performance_results)
    
    print("\n" + "=" * 70)
    print("Performance Test Complete")
    print("=" * 70)

if __name__ == '__main__':
    main()
