#!/usr/bin/env python3
"""
Check MySQL version for MIS database to determine JSON support
"""

import os
import sys
from dotenv import load_dotenv
import pymysql

# Load environment variables
load_dotenv()

def check_mysql_version():
    """Check MySQL version and JSON support"""
    
    # Get MIS database credentials from environment
    host = os.getenv('MIS_DB_HOST')
    port = int(os.getenv('MIS_DB_PORT', 3306))
    user = os.getenv('MIS_DB_USER')
    password = os.getenv('MIS_DB_PASSWORD')
    database = os.getenv('MIS_DB_NAME')
    
    if not all([host, user, password, database]):
        print("❌ MIS database credentials not configured in .env file")
        print("\nRequired environment variables:")
        print("- MIS_DB_HOST")
        print("- MIS_DB_USER") 
        print("- MIS_DB_PASSWORD")
        print("- MIS_DB_NAME")
        print("- MIS_DB_PORT (optional, defaults to 3306)")
        return False
    
    try:
        print(f"🔍 Connecting to MySQL database at {host}:{port}...")
        
        # Connect to MySQL
        connection = pymysql.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            database=database,
            charset='utf8mb4'
        )
        
        with connection.cursor() as cursor:
            # Get MySQL version
            cursor.execute("SELECT VERSION()")
            version = cursor.fetchone()[0]
            
            print(f"✅ Connected successfully!")
            print(f"📊 MySQL Version: {version}")
            
            # Parse version to check JSON support
            version_parts = version.split('.')
            major = int(version_parts[0])
            minor = int(version_parts[1])
            
            # Check JSON support
            if major > 5 or (major == 5 and minor >= 7):
                print("✅ JSON Support: YES (MySQL 5.7+)")
                print("💡 Recommendation: Keep JSON columns in models")
                
                # Test JSON functionality
                try:
                    cursor.execute("SELECT JSON_VALID('{\"test\": true}')")
                    result = cursor.fetchone()[0]
                    if result == 1:
                        print("✅ JSON Functions: Available")
                    else:
                        print("⚠️  JSON Functions: Limited")
                except Exception as e:
                    print(f"⚠️  JSON Functions: Error testing - {e}")
                    
            else:
                print("❌ JSON Support: NO (MySQL 5.6 or older)")
                print("💡 Recommendation: Replace JSON columns with TEXT columns")
                print("💡 Use Python json.dumps/loads for serialization")
            
            # Get additional database info
            cursor.execute("SELECT DATABASE()")
            current_db = cursor.fetchone()[0]
            print(f"📁 Current Database: {current_db}")
            
            cursor.execute("SHOW TABLES")
            tables = cursor.fetchall()
            print(f"📋 Tables Count: {len(tables)}")
            
            # Check character set
            cursor.execute("SELECT @@character_set_database, @@collation_database")
            charset_info = cursor.fetchone()
            print(f"🔤 Character Set: {charset_info[0]}")
            print(f"🔤 Collation: {charset_info[1]}")
            
        connection.close()
        return True
        
    except pymysql.Error as e:
        print(f"❌ MySQL Error: {e}")
        return False
    except Exception as e:
        print(f"❌ Connection Error: {e}")
        return False

def main():
    """Main function"""
    print("🔍 EAUR MIS Database - MySQL Version Check")
    print("=" * 50)
    
    success = check_mysql_version()
    
    print("\n" + "=" * 50)
    if success:
        print("✅ Database check completed successfully")
        print("\nNext steps:")
        print("1. Review the JSON support status above")
        print("2. If JSON is supported, keep current model structure")
        print("3. If JSON is NOT supported, update models to use TEXT columns")
    else:
        print("❌ Database check failed")
        print("\nTroubleshooting:")
        print("1. Verify MIS database credentials in .env file")
        print("2. Ensure database server is accessible")
        print("3. Check network connectivity and firewall settings")

if __name__ == '__main__':
    main()
