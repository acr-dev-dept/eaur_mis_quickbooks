# application/utils/celery_utils.py
from celery import Celery
def make_celery(app):
    celery = Celery(
        app.import_name,
        broker=app.config.get('CELERY_BROKER_URL'),
        backend=app.config.get('CELERY_RESULT_BACKEND'),
        include=['application.config_files.payment_sync']
    )
    celery.conf.update(app.config)

    class ContextTask(celery.Task):
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)

    celery.Task = ContextTask

    # This is the key: initialize DatabaseManager in worker
    from application.utils.database import init_database_manager
    with app.app_context():
        init_database_manager(app)  # This ensures it's ready for tasks

    return celery