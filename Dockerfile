# ──────────────────────────────────────────────
#  Multi-stage Dockerfile for Django + Celery
# ──────────────────────────────────────────────

# ── Stage 1: Build dependencies ──────────────
FROM python:3.12-slim AS builder

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build

COPY requirements/ requirements/
RUN pip install --no-cache-dir --prefix=/install -r requirements/prod.txt


# ── Stage 2: Runtime ─────────────────────────
FROM python:3.12-slim AS runtime

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd -r app && useradd -r -g app -d /app -s /sbin/nologin app

COPY --from=builder /install /usr/local

WORKDIR /app

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

COPY app/ /app/

ENV DJANGO_SETTINGS_MODULE=config.settings.prod
RUN SECRET_KEY=build-dummy-key ALLOWED_HOSTS=build python manage.py collectstatic --noinput

RUN chown -R app:app /app
USER app

EXPOSE 8000

ENTRYPOINT ["/entrypoint.sh"]
CMD ["sh", "-c", "gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers ${GUNICORN_WORKERS:-3} --timeout 120 --max-requests 1000 --max-requests-jitter 50"]
