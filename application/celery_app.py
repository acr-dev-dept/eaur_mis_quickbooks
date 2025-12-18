# application/celery_app.py   ← new file (put it in application/ root)
from application.utils.celery_utils import make_celery
from application import create_app

# This creates the real celery instance with the real app
app = create_app()
celery = make_celery(app)
celery.set_default()   # important!