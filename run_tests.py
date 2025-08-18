#!/usr/bin/env python3
"""
Test runner for EAUR MIS-QuickBooks Integration
"""

import unittest
import sys
import os
from io import StringIO

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def run_tests(test_pattern='test_*.py', verbosity=2, coverage=False):
    """
    Run tests with optional coverage reporting
    
    Args:
        test_pattern (str): Pattern to match test files
        verbosity (int): Test output verbosity (0-2)
        coverage (bool): Whether to run with coverage reporting
    """
    
    if coverage:
        try:
            import coverage as cov
            # Start coverage
            cov_instance = cov.Coverage()
            cov_instance.start()
            print("Running tests with coverage...")
        except ImportError:
            print("Coverage package not installed. Install with: pip install coverage")
            coverage = False
    
    # Discover and run tests
    loader = unittest.TestLoader()
    start_dir = 'tests'
    suite = loader.discover(start_dir, pattern=test_pattern)
    
    # Create test runner
    stream = StringIO()
    runner = unittest.TextTestRunner(
        stream=stream,
        verbosity=verbosity,
        buffer=True
    )
    
    # Run tests
    result = runner.run(suite)
    
    # Print results
    print(stream.getvalue())
    
    if coverage:
        try:
            # Stop coverage and generate report
            cov_instance.stop()
            cov_instance.save()
            
            print("\n" + "="*50)
            print("COVERAGE REPORT")
            print("="*50)
            
            # Print coverage report
            cov_instance.report(show_missing=True)
            
            # Generate HTML report
            cov_instance.html_report(directory='htmlcov')
            print(f"\nHTML coverage report generated in 'htmlcov' directory")
            
        except Exception as e:
            print(f"Error generating coverage report: {e}")
    
    # Print summary
    print("\n" + "="*50)
    print("TEST SUMMARY")
    print("="*50)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Skipped: {len(result.skipped) if hasattr(result, 'skipped') else 0}")
    
    if result.failures:
        print("\nFAILURES:")
        for test, traceback in result.failures:
            print(f"- {test}: {traceback.split('AssertionError:')[-1].strip()}")
    
    if result.errors:
        print("\nERRORS:")
        for test, traceback in result.errors:
            print(f"- {test}: {traceback.split('Exception:')[-1].strip()}")
    
    # Return exit code
    return 0 if result.wasSuccessful() else 1


def main():
    """Main function to handle command line arguments"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Run tests for EAUR MIS-QuickBooks Integration')
    parser.add_argument('--pattern', '-p', default='test_*.py',
                       help='Pattern to match test files (default: test_*.py)')
    parser.add_argument('--verbosity', '-v', type=int, default=2, choices=[0, 1, 2],
                       help='Test output verbosity (0=quiet, 1=normal, 2=verbose)')
    parser.add_argument('--coverage', '-c', action='store_true',
                       help='Run tests with coverage reporting')
    parser.add_argument('--specific', '-s', 
                       help='Run specific test file (e.g., test_health.py)')
    
    args = parser.parse_args()
    
    # If specific test file is requested
    if args.specific:
        if not args.specific.startswith('test_'):
            args.specific = f'test_{args.specific}'
        if not args.specific.endswith('.py'):
            args.specific = f'{args.specific}.py'
        args.pattern = args.specific
    
    # Run tests
    exit_code = run_tests(
        test_pattern=args.pattern,
        verbosity=args.verbosity,
        coverage=args.coverage
    )
    
    sys.exit(exit_code)


if __name__ == '__main__':
    main()
