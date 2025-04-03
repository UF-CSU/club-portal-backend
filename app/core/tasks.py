from celery import shared_task


@shared_task
def heartbeat_task():
    return True
