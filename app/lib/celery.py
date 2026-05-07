import functools
import logging
from collections.abc import Callable
from typing import Optional

from app.settings import DJANGO_ENABLE_CELERY, TESTING
from celery import shared_task
from django.core.cache import cache


def _get_task_identifier(
    func: Callable, args: Optional[list] = None, kwargs: Optional[dict] = None
):
    """Get unique identifier for called tasks, using args and kwargs."""

    args_str = str((args or []).sort())
    kwargs_str = str(kwargs or {})
    return f"{func.__name__}:{args_str}:{kwargs_str}"


def delay_task(cb: callable, *args, **kwargs):
    """
    Schedule a celery task for execution.

    This extends the default `func.delay(...)` functionality
    for shared tasks to improve testing and debouncing.

    Example usage:

    ```
    delay_task(example_task, model_id=foo.id)
    ```

    Given a task that looks like:

    ```
    @shared_task
    def example_task(model_id: int):
        pass
    ```
    """

    from core.abstracts.tests import TESTING_TASK_QUEUE, TestingDebouncedTask

    delay_sec = getattr(cb, "delay_sec", None)

    # If delay_sec was set, configure debouncing for function
    if DJANGO_ENABLE_CELERY and delay_sec:
        cb_key = _get_task_identifier(cb, args=args, kwargs=kwargs)
        if cache.has_key(cb_key):
            cache.incr(cb_key)
        else:
            cache.set(cb_key, 0)

    # Schedule task depending on implementation/environment
    if DJANGO_ENABLE_CELERY and delay_sec and not TESTING:
        cb.apply_async(args=args, kwargs=kwargs, countdown=delay_sec)
    elif DJANGO_ENABLE_CELERY and delay_sec:
        TESTING_TASK_QUEUE.get().append(
            TestingDebouncedTask(cb=cb, args=args, kwargs=kwargs)
        )
    elif DJANGO_ENABLE_CELERY and not TESTING:
        cb.delay(*args, **kwargs)
    else:
        cb(*args, **kwargs)


def debounced_task(delay_sec: int, *args, **kwargs) -> Callable:
    """
    Extend `@shared_task` to enable debouncing logic.

    The `args` and `kwargs` passed in after `delay_sec` go directly to `@shared_task`.

    Example usage:
    ```
    @debounced_task(delay_sec=1)
    def example_task(model_id: int):
        pass
    """

    def decorator(func: Callable):
        @shared_task(*args, **kwargs)
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            key = _get_task_identifier(func, args=args, kwargs=kwargs)
            queue_pos = cache.get(key, default=0)
            if cache.has_key(key):
                cache.decr(key)

            if queue_pos != 0:
                logging.debug(
                    f"Skipping task {key}, debounced queue position: {queue_pos}"
                )
                return
            logging.debug(
                f"Proceeding with {key}, debounced queue position: {queue_pos}"
            )

            return func(*args, **kwargs)

        wrapper.delay_sec = delay_sec
        return wrapper

    return decorator
