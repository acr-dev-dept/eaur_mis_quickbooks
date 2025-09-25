from celery import Celery

def make_celery(app=None):
    celery = Celery(
        __name__,
        broker=app.config.get("CELERY_BROKER_URL"),
        backend=app.config.get("CELERY_RESULT_BACKEND")
    )
    if app:
        # Copy config from Flask app to Celery
        celery.conf.update(app.config)

        # Bind Flask context to Celery tasks
        class ContextTask(celery.Task):
            def __call__(self, *args, **kwargs):
                with app.app_context():
                    return self.run(*args, **kwargs)
        celery.Task = ContextTask

    return celery