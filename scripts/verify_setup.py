#!/usr/bin/env python3
"""
Setup Verification Script for EAUR MIS-QuickBooks Integration

This script verifies that the initial setup is working correctly.
"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def test_imports():
    """Test that all critical imports work"""
    print("Testing imports...")
    
    try:
        from application import create_app
        print("✓ Application factory import successful")
    except ImportError as e:
        print(f"✗ Application factory import failed: {e}")
        return False
    
    try:
        from config import get_config
        print("✓ Configuration import successful")
    except ImportError as e:
        print(f"✗ Configuration import failed: {e}")
        return False
    
    try:
        from application.utils.database import DatabaseManager
        print("✓ Database manager import successful")
    except ImportError as e:
        print(f"✗ Database manager import failed: {e}")
        return False
    
    try:
        from application.services.quickbooks import QuickBooks
        print("✓ QuickBooks service import successful")
    except ImportError as e:
        print(f"✗ QuickBooks service import failed: {e}")
        return False
    
    try:
        from application.helpers.quickbooks_helpers import QuickBooksHelper
        print("✓ QuickBooks helper import successful")
    except ImportError as e:
        print(f"✗ QuickBooks helper import failed: {e}")
        return False
    
    return True

def test_app_creation():
    """Test Flask app creation"""
    print("\nTesting Flask app creation...")
    
    try:
        from application import create_app
        app = create_app('testing')
        print("✓ Flask app created successfully")
        
        with app.app_context():
            print("✓ App context works")
            
        return True
    except Exception as e:
        print(f"✗ Flask app creation failed: {e}")
        return False

def test_configuration():
    """Test configuration loading"""
    print("\nTesting configuration...")
    
    try:
        from config import get_config
        
        # Test different environments
        dev_config = get_config('development')
        test_config = get_config('testing')
        prod_config = get_config('production')
        
        print("✓ All configuration environments loaded")
        
        # Test required attributes
        required_attrs = ['SECRET_KEY', 'SQLALCHEMY_TRACK_MODIFICATIONS', 'JWT_SECRET_KEY']
        for attr in required_attrs:
            if hasattr(dev_config, attr):
                print(f"✓ {attr} configured")
            else:
                print(f"✗ {attr} missing")
                return False
        
        return True
    except Exception as e:
        print(f"✗ Configuration test failed: {e}")
        return False

def test_database_models():
    """Test database models"""
    print("\nTesting database models...")
    
    try:
        from application.models.central_models import Company, QuickbooksAuditLog
        print("✓ Central models imported successfully")
        
        # Test model attributes
        if hasattr(Company, '__tablename__'):
            print("✓ Company model has table name")
        
        if hasattr(QuickbooksAuditLog, '__tablename__'):
            print("✓ QuickbooksAuditLog model has table name")
        
        return True
    except Exception as e:
        print(f"✗ Database models test failed: {e}")
        return False

def test_api_blueprints():
    """Test API blueprint registration"""
    print("\nTesting API blueprints...")
    
    try:
        from application import create_app
        app = create_app('testing')
        
        # Check registered blueprints
        blueprint_names = [bp.name for bp in app.blueprints.values()]
        
        expected_blueprints = ['api_v1', 'health']
        for bp_name in expected_blueprints:
            if bp_name in blueprint_names:
                print(f"✓ {bp_name} blueprint registered")
            else:
                print(f"✗ {bp_name} blueprint missing")
                return False
        
        return True
    except Exception as e:
        print(f"✗ API blueprints test failed: {e}")
        return False

def test_health_endpoints():
    """Test health check endpoints"""
    print("\nTesting health endpoints...")
    
    try:
        from application import create_app
        app = create_app('testing')
        
        with app.test_client() as client:
            # Test basic health check
            response = client.get('/health/')
            if response.status_code == 200:
                print("✓ Basic health check endpoint works")
            else:
                print(f"✗ Basic health check failed: {response.status_code}")
                return False
            
            # Test detailed health check
            response = client.get('/health/detailed')
            if response.status_code in [200, 503]:  # 503 is OK if DB not configured
                print("✓ Detailed health check endpoint works")
            else:
                print(f"✗ Detailed health check failed: {response.status_code}")
                return False
        
        return True
    except Exception as e:
        print(f"✗ Health endpoints test failed: {e}")
        return False

def test_file_structure():
    """Test that all required files exist"""
    print("\nTesting file structure...")
    
    required_files = [
        'app.py',
        'config.py',
        'requirements.txt',
        '.env.example',
        'README.MD',
        'application/__init__.py',
        'application/api/__init__.py',
        'application/api/v1/__init__.py',
        'application/api/v1/quickbooks.py',
        'application/api/v1/mis_data.py',
        'application/api/health.py',
        'application/models/__init__.py',
        'application/models/central_models.py',
        'application/services/quickbooks.py',
        'application/helpers/quickbooks_helpers.py',
        'application/utils/__init__.py',
        'application/utils/database.py',
        'scripts/setup_migrations.sh',
        'scripts/run_migrations.sh',
        'tools/analyze_database.py'
    ]
    
    missing_files = []
    for file_path in required_files:
        if os.path.exists(file_path):
            print(f"✓ {file_path}")
        else:
            print(f"✗ {file_path} missing")
            missing_files.append(file_path)
    
    return len(missing_files) == 0

def main():
    """Run all verification tests"""
    print("="*60)
    print("EAUR MIS-QuickBooks Integration - Setup Verification")
    print("="*60)
    
    tests = [
        ("File Structure", test_file_structure),
        ("Imports", test_imports),
        ("Configuration", test_configuration),
        ("Database Models", test_database_models),
        ("Flask App Creation", test_app_creation),
        ("API Blueprints", test_api_blueprints),
        ("Health Endpoints", test_health_endpoints),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n{'-'*40}")
        print(f"Running: {test_name}")
        print(f"{'-'*40}")
        
        try:
            if test_func():
                print(f"✓ {test_name} PASSED")
                passed += 1
            else:
                print(f"✗ {test_name} FAILED")
        except Exception as e:
            print(f"✗ {test_name} ERROR: {e}")
    
    print(f"\n{'='*60}")
    print(f"VERIFICATION RESULTS: {passed}/{total} tests passed")
    print(f"{'='*60}")
    
    if passed == total:
        print("🎉 All tests passed! Setup is working correctly.")
        print("\nNext steps:")
        print("1. Update .env file with your actual configuration")
        print("2. Run './scripts/setup_migrations.sh' to initialize database")
        print("3. Obtain MIS database dump and run analysis tool")
        print("4. Configure QuickBooks OAuth credentials")
        return 0
    else:
        print("❌ Some tests failed. Please review the errors above.")
        return 1

if __name__ == '__main__':
    sys.exit(main())
