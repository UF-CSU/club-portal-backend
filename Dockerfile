# check=skip=UndefinedVar
FROM python:3.13.7-alpine3.22

LABEL maintainer="ikehunter.com"

# see logs immediately
ENV PYTHONUNBUFFERED=1

WORKDIR /app
USER root

# default to production
ARG DEV=false

# Install uv
COPY --from=ghcr.io/astral-sh/uv:0.9.6 /uv /uvx /bin/

# Install other packages
RUN python -m venv /py && \
    /py/bin/pip install --upgrade pip && \
    # Psycopg & handling images
    apk add --update --no-cache postgresql-client jpeg-dev && \
    # Oauth, health checks
    apk add --update --no-cache xmlsec-dev curl && \
    # Base requirements
    apk add --update --no-cache --virtual .tmp-build-deps \
    build-base gcc musl-dev zlib zlib-dev linux-headers \
    # Oauth, celery, etc
    libressl libffi-dev libxslt-dev libxml2-dev \
    # Psycopg
    postgresql-dev

COPY ./pyproject.toml /app/pyproject.toml
COPY ./uv.lock /app/uv.lock
COPY ./scripts /scripts

ENV UV_LINK_MODE=copy
    
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    if [ $DEV = "true" ]; then \
        uv sync --locked --no-editable --all-groups --no-install-project; \
    else \
        uv sync --locked --no-editable --all-groups  --no-install-project --no-group dev; \
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
    mkdir -p /docs/_build && \
    chown -R django-user:django-user /vol && \
    chown -R django-user:django-user /tmp && \
    chown -R django-user:django-user /docs && \
    chown -R django-user:django-user /app/.venv && \
    chown django-user:django-user /app && \
    chmod -R 755 /vol && \
    chmod -R +x /scripts

ENV DEV=${DEV}

# Copy project into image
COPY ./app /app/app

RUN --mount=type=cache,target=/root/.cache/uv \
    if [ $DEV = "true" ]; then \
        uv sync --all-groups --locked ; \
    else \
        uv sync --all-groups --locked --no-group dev; \
    fi
    

WORKDIR /app/app

ENV PATH="/scripts:/app/.venv/bin:/root/.local/bin:/py/bin:/usr/bin:$PATH"
ENV PYTHONPATH="/app/.venv/bin:$PYTHONPATH"
USER django-user

CMD ["entrypoint.sh"]
