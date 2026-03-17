"""Health and readiness checks for runtime dependencies."""

from __future__ import annotations

import uuid
from pathlib import Path

from django.core.cache import caches
from django.db import DEFAULT_DB_ALIAS, connections
from django.db.migrations.executor import MigrationExecutor


def probe_database() -> dict[str, str]:
    """Verify the default database is reachable."""
    connection = connections[DEFAULT_DB_ALIAS]
    connection.ensure_connection()
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1")

    return {"status": "ok"}


def probe_cache() -> dict[str, str]:
    """Verify the default cache backend is reachable and writable."""
    cache = caches["default"]
    cache_key = f"healthcheck:{uuid.uuid4()}"

    cache.set(cache_key, "ok", timeout=5)
    cached_value = cache.get(cache_key)
    cache.delete(cache_key)

    if cached_value != "ok":
        raise RuntimeError("Cache round-trip check failed.")

    return {"status": "ok"}


def probe_pending_migrations() -> dict[str, str]:
    """Fail readiness if unapplied migrations are detected."""
    connection = connections[DEFAULT_DB_ALIAS]
    executor = MigrationExecutor(connection)
    pending_migrations = executor.migration_plan(executor.loader.graph.leaf_nodes())

    if pending_migrations:
        raise RuntimeError(
            f"Found {len(pending_migrations)} unapplied migration(s)."
        )

    return {"status": "ok"}


def probe_celery_broker() -> dict[str, str]:
    """Verify the configured Celery broker is reachable."""
    from .celery import app as celery_app

    with celery_app.connection_for_read() as broker_connection:
        broker_connection.ensure_connection(max_retries=1)

    return {"status": "ok"}


def probe_process(expected_substring: str) -> dict[str, str]:
    """Verify container PID 1 matches the expected process role."""
    cmdline = Path("/proc/1/cmdline").read_text().replace("\x00", " ").strip()
    if expected_substring not in cmdline:
        raise RuntimeError(
            f"Expected process containing '{expected_substring}', got '{cmdline}'."
        )

    return {"status": "ok", "detail": cmdline}


def _run_check(enabled: bool, probe) -> dict[str, str]:
    if not enabled:
        return {"status": "skipped"}

    try:
        result = probe() or {}
    except Exception as exc:  # pragma: no cover - defensive wrapper
        return {"status": "error", "detail": str(exc)}

    return {"status": "ok", **result}


def build_readiness_report(
    *,
    check_migrations: bool = True,
    check_broker: bool = False,
    expected_process: str | None = None,
) -> dict[str, object]:
    """Build a readiness report for HTTP endpoints and CLI healthchecks."""
    checks = {
        "database": _run_check(True, probe_database),
        "cache": _run_check(True, probe_cache),
        "migrations": _run_check(check_migrations, probe_pending_migrations),
        "broker": _run_check(check_broker, probe_celery_broker),
        "process": _run_check(
            expected_process is not None,
            lambda: probe_process(expected_process or ""),
        ),
    }

    overall_status = "ok"
    if any(check["status"] == "error" for check in checks.values()):
        overall_status = "error"

    return {
        "status": overall_status,
        "checks": checks,
    }