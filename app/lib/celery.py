def delay_task(cb: callable, *args, **kwargs):
    """If celery is enabled schedule the task, or run immediately."""
    delay = kwargs.pop("DELAY_TASK", False)
    
    if delay == True:
        cb.delay(*args, **kwargs)
    else:
        cb(*args, **kwargs)