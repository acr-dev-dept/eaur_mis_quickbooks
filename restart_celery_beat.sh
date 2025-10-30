#!/bin/bash
# restart_celery_beat.sh
# Script to restart the Celery Beat service for EAUR MIS-QuickBooks Integration

celery -A application.tasks.scheduled_tasks.celery beat --loglevel=info