#!/bin/sh

set -e

python manage.py collectstatic --no-input
python manage.py wait_for_db
python manage.py migrate

python manage.py init_superuser

## Run WSGI socket for NGINX
# uwsgi --socket :${PORT} --workers 6 --master --enable-threads --processes 6 --vacuum --py-call-uwsgi-fork-hooks --listen 300 --socket-timeout 300 --module app.wsgi
# uwsgi --http :${PORT} --workers 6 --master --enable-threads --processes 6 --vacuum --py-call-uwsgi-fork-hooks --listen 300 --socket-timeout 300 --module app.wsgi

# uwsgi --http :${PORT} --module app.wsgi --ini /app/uwsgi.ini
# daphne -b 0.0.0.0 -p ${PORT} app.asgi:application

gunicorn app.asgi:application -k uvicorn_worker.UvicornWorker 