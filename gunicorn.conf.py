# gunicorn.conf.py
import os

PORT = os.environ.get("PORT")
if not PORT:
    PORT = "8000"  # local

bind = f"0.0.0.0:{PORT}"

workers = int(os.environ.get("WEB_CONCURRENCY", "1"))
threads = int(os.environ.get("GUNICORN_THREADS", "1"))

timeout = int(os.environ.get("GUNICORN_TIMEOUT", "120"))
graceful_timeout = 30
keepalive = 2

accesslog = "-"
errorlog = "-"
loglevel = os.environ.get("GUNICORN_LOG_LEVEL", "info")

preload_app = False