# Club Portal Backend

[![Django Tests](https://github.com/ufosc/Club-Manager/actions/workflows/django-test.yml/badge.svg)](https://github.com/ufosc/Club-Manager/actions/workflows/django-test.yml)
[![Code Checks](https://github.com/UF-CSU/club-portal-backend/actions/workflows/code-check.yml/badge.svg)](https://github.com/UF-CSU/club-portal-backend/actions/workflows/code-check.yml)

## Table of Contents

- [Getting Started](#getting-started)
  - [Prerequisites](#prerequisites)
  - [Quick Start](#quick-start)
  - [Dev Setup](#dev-setup)
  - [Running the Server](#running-the-server)
- [Admin Dashboard](#admin-dashboard)
- [Usage](#usage)
  - [REST API](#rest-api)
- [Server "Modes"](#server-modes)
- [Taskfile Commands](#taskfile-commands)
- [Local Dev Links](#local-dev-links)
- [Contributing](#contributing)
  - [Pull Requests](#pull-requests)

## Getting Started

### Prerequisites

- Docker, Docker Compose: <https://docs.docker.com/desktop/>
- Python: <https://www.python.org/downloads/>
- VSCode: <https://code.visualstudio.com/download>

Optional:

- Taskfile for managing commands and local tasks: <https://taskfile.dev/installation/>
- Anaconda for managing Python virtual environments: <https://www.anaconda.com/download>

### Quick Start

If you have docker installed, run these commands:

```sh
# Pull the repo from github
git clone https://github.com/UF-CSU/club-portal-backend.git
cd ./club-portal-backend

# Setup and start the server
cp sample.env .env
docker-compose --profile dev up --build
```

### Dev Setup

To setup your vscode environment, you will need to create a python virtual environment and install the packages found in `requirements.txt` and `requirements.dev.txt`.

This command will create a new python environment with venv and install the necessary packages:

```sh
task setup
```

_This command is still being ironed out, and may not work for certain environments_

### Running the Server

#### With TaskFile

If you have Taskfile installed, you can just run:

```sh
task dev
```

This will build the docker containers and spin up the dev servers.

You can add mock data (located in `app/fixtures/`) with this command:

```sh
task loaddata
```

And you can run unit tests with:

```sh
task test
```

If you make changes to the database, make sure to create a migration file and apply that migration file to the database:

```sh
task makemigrations
task migrate
```

Finally, to stop all docker container and clear the database:

```sh
task clean
```

#### Without Taskfile

You can manually start up the docker containers with the following commands:

```sh
# Setup env variables and build docker images
cp sample.env .env
docker-compose --profile dev build
```

After building the docker image, you can run this to start the servers:

```sh
docker-compose --profile dev up
```

To load mock data:

```sh
docker-compose run --rm app sh -c "python manage.py loaddata fixtures/*"
```

To make migration files and apply them to the database:

```sh
docker-compose run --rm app sh -c "python manage.py makemigrations"
docker-compose run --rm app sh -c "python manage.py migrate"
```

To run unit tests:

```sh
docker-compose run --rm app sh -c "python manage.py test"
```

And finally, to clean up all the docker containers and clear the database:

```sh
docker-compose --profile dev down --remove-orphans -v
```

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

## Usage

For more detailed info, look at the docs in [`docs/pages/`](./docs/pages), or visit <http://localhost:8001/> if you have the server running.

### REST API

1. Go to <http://localhost:8000/api/v1/docs/#/user/user_token_create>
2. Use `admin@example.com` as the username and `changeme` as the password (unless you have overridden it) and submit a POST request to the user token route.
3. Use this token to access the rest of the api.

## Server "Modes"

You can run the project in multiple different environments, which are referred to as "modes".

| Mode       | Purpose                                                                          |
| ---------- | -------------------------------------------------------------------------------- |
| Dev        | Main development mode, uses mock data in leu of making requests to microservices |
| Network    | Does not use mock data, connects to any needed microservices                     |
| Test       | Slimmer version of dev mode for unit testing                                     |
| Production | When the project is run in a cloud environment and receiving traffic             |

## Taskfile Commands

If you have Taskfile installed, you can use the following:

| Command                       | Purpose                                                          |
| ----------------------------- | ---------------------------------------------------------------- |
| `task setup`                  | Setup local python environment                                   |
| `task dev`                    | Start the server in "dev" mode                                   |
| `task dev:slim`               | Start only essential dev services                                |
| `task network`                | Starts the server in "network" mode                              |
| `task test`                   | Run unit tests                                                   |
| `task test -- app_name`       | Run unit tests for a specific app (replace app_name)             |
| `task makemigrations`         | Create database migration files                                  |
| `task makemigrations:dry-run` | Test makemigrations output and don't create files                |
| `task migrate`                | Apply migration files to the database                            |
| `task lint`                   | Check code lint rules with Flake8                                |
| `task format`                 | Check but don't apply formatting rules                           |
| `task format:fix`             | Format codebase using Black                                      |
| `task shell`                  | Start a new Django interactive shell                             |
| `task show_urls`              | Show all available urls for the server, and their reverse labels |
| `task loaddata`               | Load all available fixtures/mock data into database              |
| `task generate_types`         | Create TypeScript interfaces for serializers                    |
| `task down`                   | Stop all docker containers created by `task dev`                 |
| `task clean`                  | Stop containers and remove volumes created by `task dev`         |
| `task down:slim`              | Stop all docker containers created by `task dev:slim`            |
| `task clean:slim`             | Stop containers and remove volumes created by `task dev:slim`    |

## Local Dev Links

Running the server in `dev` mode will start up the following services:

| Service            | Description                                              | Link                                           |
| ------------------ | -------------------------------------------------------- | ---------------------------------------------- |
| Django Server      | Main development server                                  | <http://localhost:8000/>                       |
| API Docs           | REST API documentation created by Swagger/OpenAPI        | <http://localhost:8000/api/docs/>              |
| OAuth API Docs     | OAuth REST API documentation created by django-allauth   | <http://localhost:8000/api/oauth/openapi.html> |
| Admin Dashboard    | Django's model admin dashboard                           | <http://localhost:8000/admin/>                 |
| Documentation Site | Browseable documentation site for the project            | <http://localhost:8001/>                       |
| Test Coverage      | A detailed view of test coverage                         | <http://localhost:8002/>                       |
| PGAdmin            | Directly view and manage postgres database for debugging | <http://localhost:8888/>                       |
| MailHog            | Local test email server to view emails sent by django    | <http://localhost:8025/>                       |

All of these servers are started up with the "dev" profile in docker compose, if you want to run only essential services you can run:

```sh
task dev:slim
```

Or, without taskfile:

```sh
docker-compose --profile slim build
docker-compose --profile slim up
```

## Contributing

To contribute to the project, you can work on any issues not claimed by anyone. Any unassigned issue is fair-game, so make sure to comment on an issue you want to work on so it can be assigned to you.

It is recommended to open smaller pull requests (PRs) that have completed features, compared to larger PRs with a set of different/similar features. This is to reduce merge conflicts and make sure everyone has the updated code.

For more information about contributing, view [CONTRIBUTING.md](./CONTRIBUTING.md).

### Pull Requests

When submitting a pull request (PR), it will be rejected if the unit tests fail. It is recommended to format your code before making a PR, but it's not required (code can still be merged into main if it fails the linting tests).

To run unit tests:

```sh
task test
```

Check linting:

```sh
task lint
```

Format code:

```sh
task format:fix
```
