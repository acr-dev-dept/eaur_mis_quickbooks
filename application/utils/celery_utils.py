from celery import Celery

def make_celery(app=None):
    """Create a new Celery object and tie together the Celery config to the app's config."""
    celery = Celery(
        __name__,
        broker=app.config.get("broker_url"),
        backend=app.config.get("result_backend")
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