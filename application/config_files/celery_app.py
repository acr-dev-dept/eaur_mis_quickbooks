# application/config_filescelery_app.py
from application.utils.celery_utils import make_celery
from application import create_app

app = create_app()
celery = make_celery(app)

# This replaces the old include= and autodiscover
celery.autodiscover_tasks([
    'application.config_files',
    'application.config_files.payment_sync',
    'application.config_files.wallet_sync',
    'application.config_files.tasks',
    'application.config_files.sync_students_task',
    'application.config_files.sync_invoices_task'
])

#celery.set_default()