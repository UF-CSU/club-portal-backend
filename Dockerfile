FROM python:3.13-alpine3.20

LABEL maintainer="ikehunter.com"

# see logs immediately
ENV PYTHONUNBUFFERED=1

WORKDIR /app
USER root

# default to production
ARG DEV=false

RUN python -m venv /py && \
    /py/bin/pip install --upgrade pip && \
    apk add --update --no-cache postgresql-client jpeg-dev && \
    apk add --update --no-cache xmlsec-dev && \
    apk add --update --no-cache --virtual .tmp-build-deps \
    build-base gcc musl-dev zlib zlib-dev linux-headers \
    libressl libffi-dev libxslt-dev libxml2-dev \
    postgresql-dev && \
    /py/bin/pip install uwsgi==2.0.28 --retries 10

COPY ./requirements.txt /tmp/requirements.txt
COPY ./requirements.dev.txt /tmp/requirements.dev.txt
COPY ./scripts /scripts
    
RUN /py/bin/pip install -r /tmp/requirements.txt && \
    if [ $DEV = "true" ]; \
        then /py/bin/pip install -r /tmp/requirements.dev.txt ; \
    fi && \
    rm -rf /tmp && \
    apk del .tmp-build-deps && \
    # Create new user
    adduser \
    --disabled-password \
    --no-create-home \
    django-user && \
    mkdir -p /vol/web/media && \
    mkdir -p /vol/web/static && \
    mkdir /tmp && \
    chown -R django-user:django-user /vol && \
    chown -R django-user:django-user /tmp && \
    chmod -R 755 /vol && \
    chmod -R +x /scripts

ENV DEV=${DEV}

COPY ./app /app
ENV PATH="/scripts:/py/bin:/usr/bin:$PATH"
USER django-user

CMD ["entrypoint.sh"]
