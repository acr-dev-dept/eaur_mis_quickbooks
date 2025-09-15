#!/bin/bash

# Navigate to project directory
cd /home/eaur/eaur_mis_quickbooks || exit 1

# Activate the virtual environment
source venv/bin/activate

# Run the Python sync script
python3 sync_students.py
# Capture the exit status of the Python script and send it to the log
EXIT_STATUS=$?
# Log the completion of the script
echo "Student sync script executed on $(date) with exit status $EXIT_STATUS" >> customer_sync_cron.log