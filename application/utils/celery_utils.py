# application/utils/celery_utils.py
import logging
from celery import Celery

# This logger works immediately, even during imports
celery_setup_logger = logging.getLogger("celery_setup")

# Optional: make it pretty if no handlers exist yet
if not celery_setup_logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    celery_setup_logger.addHandler(handler)
    celery_setup_logger.setLevel(logging.INFO)

def make_celery(app):
    celery_setup_logger.info("Starting make_celery() — creating Celery instance")

    celery = Celery(
        app.import_name,
        broker=app.config['CELERY_BROKER_URL'],
        backend=app.config['CELERY_RESULT_BACKEND'],
        include=[
            'application.config_files.payment_sync',
            'application.config_files.tasks',
        ]
    )
    celery.conf.update(app.config)
    celery_setup_logger.info("Celery instance created and config updated")

    # App context for tasks
    class ContextTask(celery.Task):
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)
    celery.Task = ContextTask

    # THIS IS WHERE YOU ADD THE DEBUGGING
    try:
        with app.app_context():
            celery_setup_logger.info("Inside app context — initializing DatabaseManager...")
            from application.utils.database import init_database_manager
            init_database_manager(app)
            celery_setup_logger.info("DatabaseManager initialized successfully in Celery worker!")
    except Exception as e:
        celery_setup_logger.error(f"FAILED to initialize DatabaseManager in Celery: {e}", exc_info=True)
        raise  # Crash the worker early — better than silent failure!

    celery_setup_logger.info("make_celery() completed successfully")
    return celery