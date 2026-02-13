from app.celery_app import celery_app


@celery_app.task(bind=True, name="tasks.sample.echo")
def echo(self, message: str) -> dict:
    """Simple smoke-test task — echoes the message back."""
    return {"echo": message, "task_id": self.request.id}
