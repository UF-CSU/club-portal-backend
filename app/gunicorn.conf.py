# Production Gunicorn Server Config
# Docs: https://docs.gunicorn.org/en/latest/settings.html#

import os

PORT = os.environ.get("PORT", "9000")

bind = f"0.0.0.0:{PORT}"

lifespan = "off"
timeout = 300
workers = os.environ.get(
    "WORKER_COUNT", 5
)  # The number of worker processes for handling requests.
threads = os.environ.get(
    "THREAD_COUNT", 1
)  # Run each worker with the specified number of threads.
preload = True  # Load application code before the worker processes are forked.
