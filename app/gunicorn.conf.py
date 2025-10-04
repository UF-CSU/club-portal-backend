# Production Gunicorn Server Config

import os

PORT = os.environ.get("PORT", "9000")

bind = f"0.0.0.0:{PORT}"
workers = os.environ.get("WORKER_COUNT", 5)
timeout = 300
threads = os.environ.get("THREAD_COUNT", 1)
preload = True  # Load application code before the worker processes are forked.
