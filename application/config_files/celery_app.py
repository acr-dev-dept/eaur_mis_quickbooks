# application/celery_app.py
from application.utils.celery_utils import make_celery
from application import create_app

app = create_app()
celery = make_celery(app)

# This replaces the old include= and autodiscover
celery.autodiscover_tasks([
    'application.config_files',
    'application.tasks',
    # or just:
    'application',
])

celery.set_default()