# application/utils/celery_utils.py
from celery import Celery

def make_celery(app):
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

    # This gives every task automatic app context
    class ContextTask(celery.Task):
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)
    celery.Task = ContextTask

    # THIS IS THE MISSING LINE YOU NEED:
    with app.app_context():
        from application.utils.database import init_database_manager
        try:
            init_database_manager(app)
            app.logger.info("DatabaseManager initialized for Celery")
        except Exception as e:
            app.logger.error(f"Failed to init DatabaseManager in Celery: {e}")
            raise

    return celery