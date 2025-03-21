# Club Portal Backend

[![Django Tests](https://github.com/ufosc/Club-Manager/actions/workflows/django-test.yml/badge.svg)](https://github.com/ufosc/Club-Manager/actions/workflows/django-test.yml)
[![Code Linting](https://github.com/UF-CSU/club-portal-backend/actions/workflows/code-lint.yml/badge.svg)](https://github.com/UF-CSU/club-portal-backend/actions/workflows/code-lint.yml)

## Getting Started

### Prerequisites

- Docker, Docker Compose: <https://docs.docker.com/desktop/>
- Python: <https://www.python.org/downloads/>
- VSCode: <https://code.visualstudio.com/download>

Optional:

- Taskfile for managing commands and local tasks: <https://taskfile.dev/installation/>
- Anaconda for managing Python virtual environments: <https://www.anaconda.com/download>

### Running Dev Server

```sh
cp sample.env .env
docker-compose up --build
```

After first build, you can just run:

```sh
docker-compose up
```

To run unit tests:

```sh
docker-compose run --rm app sh -c "python manage.py test"
```

### Taskfile Commands

If you have Taskfile installed, you can use the following:

| Command                       | Purpose                                   |
| ----------------------------- | ----------------------------------------- |
| `task dev`                    | Start dev server                          |
| `task network`                | Starts the server in "network" mode       |
| `task test`                   | Run unit tests                            |
| `task makemigrations`         | Create database migration files           |
| `task makemigrations:dry-run` | Run makemigrations but don't create files |
| `task migrate`                | Apply migration files to the database     |
| `task lint`                   | Check code lint rules with Flake8         |
| `task format`                 | Check but don't apply formatting rules    |
| `task format:fix`             | Format codebase using Black               |

### Admin Dashboard

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
