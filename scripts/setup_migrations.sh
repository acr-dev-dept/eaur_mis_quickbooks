#!/bin/bash

# EAUR MIS-QuickBooks Integration - Migration Setup Script
# This script initializes the Flask-Migrate environment and creates initial migration

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

# Check if we're in the project root
if [ ! -f "app.py" ]; then
    print_error "Please run this script from the project root directory"
    exit 1
fi

# Check if virtual environment is activated
if [ -z "$VIRTUAL_ENV" ]; then
    print_warning "No virtual environment detected. It's recommended to use a virtual environment."
    read -p "Continue anyway? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

print_status "Setting up Alembic for EAUR MIS-QuickBooks Integration..."

# Create logs directory if it doesn't exist
if [ ! -d "logs" ]; then
    print_status "Creating logs directory..."
    mkdir -p logs
    print_success "Logs directory created"
fi

# Check if Alembic is already initialized
if [ ! -d "alembic" ]; then
    print_status "Initializing Alembic..."

    # Initialize Alembic
    alembic init alembic

    if [ $? -eq 0 ]; then
        print_success "Alembic initialized successfully"
    else
        print_error "Failed to initialize Alembic"
        exit 1
    fi
else
    print_warning "Alembic directory already exists. Skipping initialization."
fi

# Check if .env file exists
if [ ! -f ".env" ]; then
    print_warning ".env file not found. Creating from .env.example..."
    if [ -f ".env.example" ]; then
        cp .env.example .env
        print_success ".env file created from .env.example"
        print_warning "Please update .env file with your actual configuration values"
    else
        print_error ".env.example file not found. Please create .env file manually"
        exit 1
    fi
fi

# Create initial migration for central models
print_status "Creating initial migration for central application models..."

# Generate initial migration with Alembic
alembic revision --autogenerate -m "Initial migration: central application models"

if [ $? -eq 0 ]; then
    print_success "Initial migration created successfully"
else
    print_error "Failed to create initial migration"
    exit 1
fi

print_success "Migration setup completed successfully!"
print_status "Next steps:"
echo "  1. Update your .env file with actual database credentials"
echo "  2. Run './scripts/run_migrations.sh' to apply migrations"
echo "  3. After importing MIS database, generate MIS models using database analysis tools"

# Make the run_migrations script executable
if [ -f "scripts/run_migrations.sh" ]; then
    chmod +x scripts/run_migrations.sh
    print_status "Made run_migrations.sh executable"
fi
