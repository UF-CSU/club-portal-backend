# Club Portal Backend

[![Django Tests](https://github.com/ufosc/Club-Manager/actions/workflows/django-test.yml/badge.svg)](https://github.com/ufosc/Club-Manager/actions/workflows/django-test.yml)
[![Code Linting](https://github.com/UF-CSU/club-portal-backend/actions/workflows/code-lint.yml/badge.svg)](https://github.com/UF-CSU/club-portal-backend/actions/workflows/code-lint.yml)

## Table of Contents

- [Getting Started](#getting-started)
  - [Prerequisites](#prerequisites)
  - [Setup](#setup)
  - [Running the Dev Server](#running-the-dev-server)
    - [With TaskFile](#with-taskfile)
    - [Without Taskfile](#without-taskfile)
- [Taskfile Commands](#taskfile-commands)
- [Local Dev Links](#local-dev-links)
- [Admin Dashboard](#admin-dashboard)
- [Server "Modes"](#server-modes)
- [Contributing](#contributing)

## Getting Started

### Prerequisites

- Docker, Docker Compose: <https://docs.docker.com/desktop/>
- Python: <https://www.python.org/downloads/>
- VSCode: <https://code.visualstudio.com/download>

Optional:

- Taskfile for managing commands and local tasks: <https://taskfile.dev/installation/>
- Anaconda for managing Python virtual environments: <https://www.anaconda.com/download>

### Setup

To setup your vscode environment, you will need to create a python virtual environment and install the packages found in `requirements.txt` and `requirements.dev.txt`.

This command will create a new python environment with venv and install the necessary packages:

```sh
task setup
```

_This command is still being ironed out, and may not work for certain environments_

### Running the Dev Server

#### With TaskFile

If you have Taskfile installed, you can just run:

```sh
task dev
```

This will build the docker containers and spin up the dev servers.

#### Without Taskfile

You can manually start up the docker containers with the following commands:

```sh
# Setup env variables and build docker images
cp sample.env .env
docker-compose build
```

After building the docker image, you can run this to start the servers:

```sh
docker-compose up
```

To run unit tests:

```sh
docker-compose run --rm app sh -c "python manage.py test"
```

## Taskfile Commands

If you have Taskfile installed, you can use the following:

| Command                       | Purpose                                                       |
| ----------------------------- | ------------------------------------------------------------- |
| `task setup`                  | Setup local python environment                                |
| `task dev`                    | Start the server in "dev" mode                                |
| `task dev:slim`               | Start only essential dev services                             |
| `task network`                | Starts the server in "network" mode                           |
| `task test`                   | Run unit tests                                                |
| `task test -- app_name`       | Run unit tests for a specific app (replace app_name)          |
| `task makemigrations`         | Create database migration files                               |
| `task makemigrations:dry-run` | Run makemigrations but don't create files                     |
| `task migrate`                | Apply migration files to the database                         |
| `task lint`                   | Check code lint rules with Flake8                             |
| `task format`                 | Check but don't apply formatting rules                        |
| `task format:fix`             | Format codebase using Black                                   |
| `task shell`                  | Start a new Django interactive shell                          |
| `task down`                   | Stop all docker containers created by `task dev`              |
| `task clean`                  | Stop containers and remove volumes created by `task dev`      |
| `task down:slim`              | Stop all docker containers created by `task dev:slim`         |
| `task clean:slim`             | Stop containers and remove volumes created by `task dev:slim` |

## Local Dev Links

Running the server in dev mode will start up the following services:

| Service         | Description                                              | Link                                           |
| --------------- | -------------------------------------------------------- | ---------------------------------------------- |
| Django Server   | Main development server                                  | <http://localhost:8000/>                       |
| API Docs        | REST API documentation created by Swagger/OpenAPI        | <http://localhost:8000/api/docs/>              |
| OAuth API Docs  | OAuth REST API documentation created by django-allauth   | <http://localhost:8000/api/oauth/openapi.html> |
| Admin Dashboard | Django's model admin dashboard                           | <http://localhost:8000/admin/>                 |
| Test Coverage   | A detailed view of test coverage                         | <http://localhost:8001/>                       |
| PGAdmin         | Directly view and manage postgres database for debugging | <http://localhost:8888/>                       |
| MailHog         | Local test email server to view emails sent by django    | <http://localhost:8025/>                       |

## Admin Dashboard

You can log into the admin dashboard by going to the route `/admin` and using the following credentials:

- Username: `admin@example.com`
- Password: `changeme`

These defaults are set via environment variables:

```txt
DJANGO_SUPERUSER_EMAIL="admin@example.com"
DJANGO_SUPERUSER_PASS="changeme"
```

If you want to change these values, copy the sample.env file to a new `.env` file and change the values. If you already created an admin with the other credentials, then another one won't be created automatically. To get another one to be created automatically, remove the database and restart the app with this command:

```sh
docker-compose down --remove-orphans -v
docker-compose up
```

If you want to create a new admin without removing the old database, run this command:

```sh
docker-compose run --rm app sh -c "python manage.py createsuperuser --no-input"
```

## Server "Modes"

You can run the project in multiple different environments, which are referred to as "modes".

| Mode       | Purpose                                                                          |
| ---------- | -------------------------------------------------------------------------------- |
| Dev        | Main development mode, uses mock data in leu of making requests to microservices |
| Network    | Does not use mock data, connects to any needed microservices                     |
| Test       | Slimmer version of dev mode for unit testing                                     |
| Production | When the project is run in a cloud environment and receiving traffic             |

## Contributing

To contribute to the project, you can work on any issues not claimed by anyone. Any unassigned issue is fair-game, so make sure to comment on an issue you want to work on so it can be assigned to you.

It is recommended to open smaller pull requests (PRs) that have completed features, compared to larger PRs with a set of different/similar features. This is to reduce merge conflicts and make sure everyone has the updated code.

For more information about contributing, view [CONTRIBUTING.md](./CONTRIBUTING.md).
