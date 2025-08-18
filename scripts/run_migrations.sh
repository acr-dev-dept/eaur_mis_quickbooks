#!/bin/bash

# EAUR MIS-QuickBooks Integration - Migration Runner Script
# This script applies database migrations and handles database operations

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to show usage
show_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  -h, --help              Show this help message"
    echo "  -u, --upgrade           Apply all pending migrations (default)"
    echo "  -d, --downgrade [REV]   Downgrade to specific revision (or previous)"
    echo "  -c, --current           Show current migration revision"
    echo "  -s, --status            Show migration status"
    echo "  -r, --reset             Reset database (WARNING: destroys all data)"
    echo "  --dry-run               Show what would be done without executing"
    echo ""
    echo "Examples:"
    echo "  $0                      # Apply all pending migrations"
    echo "  $0 --status             # Show current migration status"
    echo "  $0 --downgrade          # Downgrade one revision"
    echo "  $0 --downgrade abc123   # Downgrade to specific revision"
    echo "  $0 --reset              # Reset database (with confirmation)"
}

# Default action
ACTION="upgrade"
DRY_RUN=false
REVISION=""

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_usage
            exit 0
            ;;
        -u|--upgrade)
            ACTION="upgrade"
            shift
            ;;
        -d|--downgrade)
            ACTION="downgrade"
            if [[ $# -gt 1 && ! $2 =~ ^- ]]; then
                REVISION="$2"
                shift
            fi
            shift
            ;;
        -c|--current)
            ACTION="current"
            shift
            ;;
        -s|--status)
            ACTION="status"
            shift
            ;;
        -r|--reset)
            ACTION="reset"
            shift
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        *)
            print_error "Unknown option: $1"
            show_usage
            exit 1
            ;;
    esac
done

# Check if we're in the project root
if [ ! -f "app.py" ]; then
    print_error "Please run this script from the project root directory"
    exit 1
fi

# Check if migrations directory exists
if [ ! -d "migrations" ]; then
    print_error "Migrations directory not found. Run './scripts/setup_migrations.sh' first"
    exit 1
fi

# Check if .env file exists
if [ ! -f ".env" ]; then
    print_error ".env file not found. Please create it from .env.example"
    exit 1
fi

# Set environment variables
export FLASK_APP=app.py
export FLASK_ENV=development

# Load environment variables from .env file
if command -v python3 &> /dev/null; then
    PYTHON_CMD=python3
elif command -v python &> /dev/null; then
    PYTHON_CMD=python
else
    print_error "Python not found. Please install Python 3.7+"
    exit 1
fi

# Function to check database connectivity
check_database() {
    print_status "Checking database connectivity..."
    
    $PYTHON_CMD -c "
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine

load_dotenv()

# Check central database
db_url = os.getenv('DEV_DATABASE_URL') or os.getenv('SQLALCHEMY_DATABASE_URI')
if db_url:
    try:
        engine = create_engine(db_url)
        with engine.connect() as conn:
            conn.execute('SELECT 1')
        print('✓ Central database connection successful')
    except Exception as e:
        print(f'✗ Central database connection failed: {e}')
        exit(1)
else:
    print('✗ No central database URL configured')
    exit(1)
"
    
    if [ $? -eq 0 ]; then
        print_success "Database connectivity check passed"
    else
        print_error "Database connectivity check failed"
        exit 1
    fi
}

# Function to execute Flask-Migrate commands
execute_migration() {
    local cmd="$1"
    local description="$2"
    
    if [ "$DRY_RUN" = true ]; then
        print_status "[DRY RUN] Would execute: flask db $cmd"
        return 0
    fi
    
    print_status "$description"
    flask db $cmd
    
    if [ $? -eq 0 ]; then
        print_success "$description completed"
    else
        print_error "$description failed"
        exit 1
    fi
}

# Main execution based on action
case $ACTION in
    "upgrade")
        check_database
        execute_migration "upgrade" "Applying database migrations"
        ;;
    "downgrade")
        check_database
        if [ -n "$REVISION" ]; then
            execute_migration "downgrade $REVISION" "Downgrading to revision $REVISION"
        else
            execute_migration "downgrade" "Downgrading one revision"
        fi
        ;;
    "current")
        execute_migration "current" "Showing current migration revision"
        ;;
    "status")
        execute_migration "history" "Showing migration history"
        echo ""
        execute_migration "current" "Current revision"
        ;;
    "reset")
        if [ "$DRY_RUN" = true ]; then
            print_status "[DRY RUN] Would reset database (destroy all data)"
            exit 0
        fi
        
        print_warning "This will destroy ALL data in the database!"
        read -p "Are you sure you want to reset the database? Type 'yes' to confirm: " -r
        echo
        if [[ $REPLY == "yes" ]]; then
            check_database
            execute_migration "downgrade base" "Downgrading to base (empty database)"
            execute_migration "upgrade" "Applying all migrations"
            print_success "Database reset completed"
        else
            print_status "Database reset cancelled"
        fi
        ;;
esac

print_success "Migration operation completed successfully!"
