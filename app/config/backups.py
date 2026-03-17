"""Utilities for PostgreSQL backup and restore via S3-compatible storage."""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import boto3
from botocore.config import Config
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured


BACKUP_SUBDIR = "database-backups"


@dataclass(frozen=True)
class DatabaseCliConfig:
    name: str
    user: str
    password: str
    host: str
    port: str


@dataclass(frozen=True)
class S3BackupConfig:
    bucket: str
    prefix: str
    endpoint_url: str | None
    region_name: str | None
    access_key_id: str | None
    secret_access_key: str | None
    session_token: str | None
    addressing_style: str
    verify: bool


def _env(*names: str, default: str | None = None) -> str | None:
    for name in names:
        value = os.environ.get(name)
        if value is not None and value != "":
            return value
    return default


def _env_bool(name: str, default: bool = True) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() not in {"0", "false", "no", "off"}


def get_database_cli_config() -> DatabaseCliConfig:
    """Extract PostgreSQL connection details suitable for pg_dump/pg_restore."""
    database = settings.DATABASES["default"]
    engine = database.get("ENGINE", "")

    if "postgresql" not in engine:
        raise ImproperlyConfigured(
            "Database backup commands currently support PostgreSQL only."
        )

    return DatabaseCliConfig(
        name=str(database.get("NAME") or ""),
        user=str(database.get("USER") or ""),
        password=str(database.get("PASSWORD") or ""),
        host=str(database.get("HOST") or "localhost"),
        port=str(database.get("PORT") or "5432"),
    )


def get_s3_backup_config(prefix_override: str | None = None) -> S3BackupConfig:
    """Build S3 configuration from common environment variable names."""
    bucket = _env(
        "AWS_STORAGE_BUCKET_NAME",
        "AWS_S3_BUCKET_NAME",
        "S3_BUCKET_NAME",
    )
    if not bucket:
        raise ImproperlyConfigured(
            "Set AWS_STORAGE_BUCKET_NAME (or S3_BUCKET_NAME) for backups."
        )

    prefix = prefix_override or _env(
        "DB_BACKUP_S3_PREFIX",
        "S3_BACKUP_PREFIX",
        "PROJECT_NAME",
        "COMPOSE_PROJECT_NAME",
    )
    if not prefix:
        raise ImproperlyConfigured(
            "Set DB_BACKUP_S3_PREFIX to the project directory in S3."
        )

    return S3BackupConfig(
        bucket=bucket,
        prefix=prefix.strip("/"),
        endpoint_url=_env(
            "AWS_S3_ENDPOINT_URL",
            "AWS_ENDPOINT_URL_S3",
            "S3_ENDPOINT_URL",
        ),
        region_name=_env(
            "AWS_S3_REGION_NAME",
            "AWS_REGION",
            "AWS_DEFAULT_REGION",
        ),
        access_key_id=_env("AWS_ACCESS_KEY_ID"),
        secret_access_key=_env("AWS_SECRET_ACCESS_KEY"),
        session_token=_env("AWS_SESSION_TOKEN"),
        addressing_style=_env("AWS_S3_ADDRESSING_STYLE", default="auto") or "auto",
        verify=_env_bool("AWS_S3_VERIFY", default=True),
    )


def build_backup_filename(database_name: str, *, timestamp: datetime | None = None) -> str:
    """Generate a timestamped PostgreSQL dump filename."""
    safe_db_name = database_name.replace("/", "-")
    stamp = (timestamp or datetime.now(timezone.utc)).strftime("%Y%m%dT%H%M%SZ")
    return f"{safe_db_name}_{stamp}.dump"


def build_backup_object_key(prefix: str, filename: str) -> str:
    """Store backups under the project directory, never at bucket root."""
    normalized_prefix = prefix.strip("/")
    return f"{normalized_prefix}/{BACKUP_SUBDIR}/{filename}"


def get_s3_client(config: S3BackupConfig):
    session = boto3.session.Session()
    return session.client(
        "s3",
        endpoint_url=config.endpoint_url,
        region_name=config.region_name,
        aws_access_key_id=config.access_key_id,
        aws_secret_access_key=config.secret_access_key,
        aws_session_token=config.session_token,
        verify=config.verify,
        config=Config(
            signature_version="s3v4",
            s3={"addressing_style": config.addressing_style},
        ),
    )


def get_pg_env(password: str) -> dict[str, str]:
    env = os.environ.copy()
    if password:
        env["PGPASSWORD"] = password
    return env


def run_pg_command(command: list[str], *, password: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        command,
        check=True,
        env=get_pg_env(password),
        capture_output=True,
        text=True,
    )


def dump_database(output_path: Path) -> None:
    """Create a PostgreSQL custom-format dump file."""
    db = get_database_cli_config()
    run_pg_command(
        [
            "pg_dump",
            "--format=custom",
            "--compress=9",
            f"--file={output_path}",
            f"--host={db.host}",
            f"--port={db.port}",
            f"--username={db.user}",
            db.name,
        ],
        password=db.password,
    )


def restore_database(input_path: Path) -> None:
    """Restore a PostgreSQL custom-format dump into the configured database."""
    db = get_database_cli_config()
    run_pg_command(
        [
            "pg_restore",
            "--clean",
            "--if-exists",
            "--no-owner",
            "--no-privileges",
            f"--host={db.host}",
            f"--port={db.port}",
            f"--username={db.user}",
            f"--dbname={db.name}",
            str(input_path),
        ],
        password=db.password,
    )


def upload_backup(local_path: Path, key: str, config: S3BackupConfig) -> None:
    client = get_s3_client(config)
    client.upload_file(str(local_path), config.bucket, key)


def download_backup(key: str, local_path: Path, config: S3BackupConfig) -> None:
    client = get_s3_client(config)
    client.download_file(config.bucket, key, str(local_path))


def find_latest_backup_key(config: S3BackupConfig) -> str:
    """Return the latest backup object key for the configured project prefix."""
    prefix = f"{config.prefix}/{BACKUP_SUBDIR}/"
    client = get_s3_client(config)
    paginator = client.get_paginator("list_objects_v2")

    latest_object = None
    for page in paginator.paginate(Bucket=config.bucket, Prefix=prefix):
        for obj in page.get("Contents", []):
            if latest_object is None or obj["LastModified"] > latest_object["LastModified"]:
                latest_object = obj

    if latest_object is None:
        raise FileNotFoundError(f"No backup objects found under '{prefix}'.")

    return latest_object["Key"]


def create_temp_backup_dir() -> Path:
    return Path(tempfile.mkdtemp(prefix="db-backup-"))


def cleanup_temp_dir(temp_dir: Path) -> None:
    shutil.rmtree(temp_dir, ignore_errors=True)