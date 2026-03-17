# Django Infrastructure Template

Production-focused Django + Celery + Redis + Postgres baseline.  
Local dev via `docker-compose.override.yml`, production via `docker-compose.yml` in Dokploy.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Docker Network                         │
│                                                             │
│  ┌──────────┐  ┌──────────────┐  ┌────────────────────────┐│
│  │  Postgres │  │    Redis     │  │      Web (Django)      ││
│  │  :5432    │  │    :6379     │  │      :8000 (expose)    ││
│  └──────────┘  └──────────────┘  └────────────────────────┘│
│                       │                                     │
│               ┌───────┴───────┐                             │
│               │               │                             │
│        ┌──────────┐    ┌──────────┐                         │
│        │  Celery   │    │  Celery  │                        │
│        │  Worker   │    │  Beat    │                        │
│        └──────────┘    └──────────┘                         │
└─────────────────────────────────────────────────────────────┘
         ▲ Dokploy/Traefik routes traffic to :8000
```

## Quick Start (Local Development)

```bash
# 1. Copy env file
cp .env.example .env

# 2. Start everything (override is auto-merged)
docker compose up --build

# 3. Create superuser
docker compose exec web python manage.py createsuperuser

# 4. Open
#    App:    http://localhost:8000
#    Admin:  http://localhost:8000/admin/
#    Flower: http://localhost:5555
```

## Project Structure

```
├── docker-compose.yml            # Production (Dokploy)
├── docker-compose.override.yml   # Local dev overrides
├── Dockerfile                    # Multi-stage build
├── entrypoint.sh                 # Migrations + wait for DB
├── .env.example                  # Template for local .env
├── requirements/
│   ├── base.txt                  # Shared dependencies
│   ├── dev.txt                   # Dev tools (debug, testing)
│   └── prod.txt                  # Gunicorn, Sentry
└── app/
    ├── manage.py
    └── config/
        ├── __init__.py
        ├── celery.py             # Celery app
        ├── urls.py               # Root URLs + health check
        ├── wsgi.py
        ├── asgi.py
        └── settings/
            ├── __init__.py
            ├── base.py           # All env-driven settings
            ├── dev.py            # DEBUG=True, CORS_ALLOW_ALL
            └── prod.py           # SSL, HSTS, secure cookies
```

## Local vs Production — What's Different

| Concern                | Local (`override.yml`)        | Production (`docker-compose.yml`)      |
|------------------------|-------------------------------|----------------------------------------|
| Web port               | `ports: 8000:8000`            | `expose: 8000` (Traefik routes)        |
| DB port                | `ports: 5432:5432`            | `expose: 5432` (internal only)         |
| Redis port             | `ports: 6379:6379`            | `expose: 6379` (internal only)         |
| Code mounting          | `volumes: ./app:/app`         | Baked into image                       |
| Django server          | `runserver` (auto-reload)     | `gunicorn` (3 workers)                 |
| Settings module        | `config.settings.dev`         | `config.settings.prod`                 |
| DEBUG                  | `1`                           | `0`                                    |
| CORS                   | Allow all                     | Explicit origins only                  |
| SSL                    | Off                           | Forced + HSTS                          |
| Env vars source        | `.env` file                   | Dokploy Environment Settings           |
| Flower                 | ✅ on `:5555`                  | Not deployed                           |

## Production Deployment (Dokploy)

### 1. Create Compose Project in Dokploy

- Source: Git repository
- Provider: GitHub / GitLab / etc.

### 2. Set Environment Variables

In Dokploy → Project → Environment:

```env
SECRET_KEY=<generate-a-strong-50-char-key>
DEBUG=0
ALLOWED_HOSTS=yourdomain.com
CSRF_TRUSTED_ORIGINS=https://yourdomain.com
CORS_ALLOWED_ORIGINS=https://yourdomain.com,https://app.yourdomain.com
POSTGRES_USER=app_user
POSTGRES_PASSWORD=<strong-password>
POSTGRES_DB=app_db
DATABASE_URL=postgres://app_user:<strong-password>@db:5432/app_db
REDIS_URL=redis://redis:6379/0
CELERY_BROKER_URL=redis://redis:6379/1
```

### 3. Domain / SSL

Configure domain in Dokploy → Project → Domains.  
Dokploy auto-provisions Let's Encrypt certificates via Traefik.

### 4. Deploy

Push to your repo branch — Dokploy auto-deploys.

## Key Design Decisions

### Everything from `os.environ`

`ALLOWED_HOSTS`, `CORS_ALLOWED_ORIGINS`, `CSRF_TRUSTED_ORIGINS`, `SECRET_KEY`, `DATABASE_URL` — all read from environment. Zero hardcoded values.

### `expose` vs `ports`

- `docker-compose.yml` uses **`expose`** — services are only reachable within the Docker network. Traefik/Dokploy handles external routing.
- `docker-compose.override.yml` adds **`ports`** — maps to host for local access with tools like pgAdmin, RedisInsight, browser.

### Split settings

- `base.py` — all env-driven, shared logic
- `dev.py` — DEBUG, CORS allow-all, console email
- `prod.py` — SSL redirect, HSTS, secure cookies

### Health and readiness endpoints

- `/health/` is a lightweight liveness probe for the Django process.
- `/ready/` verifies database connectivity, Redis cache access, and unapplied migrations before reporting ready.

Production `web` healthchecks now target `/ready/` so the container only becomes healthy after runtime dependencies are available.

### Entrypoint

Waits for Postgres, runs migrations, then starts the main process. Same entrypoint for web, worker, and beat — they just override the `CMD`.

## Current Production Baseline

This template is suitable as a production baseline, but it is not a complete platform out of the box.

Included today:

- split `dev` / `prod` settings
- Gunicorn + non-root container runtime
- Postgres, Redis, Celery worker, Celery beat
- WhiteNoise static file serving
- liveness and readiness probes
- optional Sentry integration

Still expected from the deploying team:

- backup/restore scheduling and retention policy for Postgres and Redis
- secrets rotation policy
- monitoring/alerting beyond basic logs and optional Sentry
- final decision for user-uploaded media storage
- CI pipeline with linting, tests, and `manage.py check --deploy`

## Database Backup / Restore

The template now includes management commands for PostgreSQL backups to S3-compatible storage.

Required environment variables:

- `AWS_STORAGE_BUCKET_NAME` or `S3_BUCKET_NAME`
- `DB_BACKUP_S3_PREFIX` — project directory inside the bucket
- standard S3 credentials such as `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY`
- optional custom endpoint: `AWS_S3_ENDPOINT_URL`

Backups are uploaded under:

- `s3://<bucket>/<DB_BACKUP_S3_PREFIX>/database-backups/<filename>.dump`

Examples:

```bash
# Create backup and upload to S3
docker compose exec web python manage.py backup_db

# Create backup with explicit name
docker compose exec web python manage.py backup_db --filename pre_release.dump

# Restore the latest backup for the current project prefix
docker compose exec web python manage.py restore_db --latest --yes

# Restore a specific object key
docker compose exec web python manage.py restore_db \
    --key djtmplt/database-backups/pre_release.dump \
    --yes
```

Notes:

- Commands use `pg_dump` and `pg_restore` inside the container.
- Restore is destructive and requires `--yes`.
- The command never writes objects to the S3 bucket root; it always uses the configured project prefix.

## Common Operations

```bash
# Run migrations manually
docker compose exec web python manage.py migrate

# Open Django shell
docker compose exec web python manage.py shell

# Run tests
docker compose exec web pytest

# Run Django deployment checks
docker compose exec web python manage.py check --deploy

# View Celery worker logs
docker compose logs -f celery-worker

# Scale workers
docker compose up -d --scale celery-worker=3
```

## Adding a New App

```bash
# Create app inside the container
docker compose exec web python manage.py startapp core

# Then add to INSTALLED_APPS in config/settings/base.py
```
