from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from django.core.management import CommandError, call_command

from config.backups import BACKUP_SUBDIR, build_backup_filename, build_backup_object_key


def test_build_backup_filename_includes_db_name_and_timestamp():
    filename = build_backup_filename(
        "app_db",
        timestamp=datetime(2026, 3, 17, 12, 30, 45, tzinfo=timezone.utc),
    )

    assert filename == "app_db_20260317T123045Z.dump"


def test_build_backup_object_key_uses_project_prefix_directory():
    key = build_backup_object_key("djtmplt", "backup.dump")

    assert key == f"djtmplt/{BACKUP_SUBDIR}/backup.dump"


@patch("config.management.commands.backup_db.upload_backup")
@patch("config.management.commands.backup_db.dump_database")
@patch("config.management.commands.backup_db.get_s3_backup_config")
@patch("config.management.commands.backup_db.get_database_cli_config")
def test_backup_db_command_uploads_dump(
    mock_get_db,
    mock_get_s3,
    mock_dump,
    mock_upload,
    settings,
):
    mock_get_db.return_value = Mock(name="app_db")
    mock_get_db.return_value.name = "app_db"
    mock_get_s3.return_value = Mock(bucket="backups", prefix="djtmplt")

    call_command("backup_db", "--filename", "manual.dump")

    dump_path = Path(mock_dump.call_args.args[0])
    assert dump_path.name == "manual.dump"
    mock_upload.assert_called_once()
    assert mock_upload.call_args.args[1] == f"djtmplt/{BACKUP_SUBDIR}/manual.dump"


@patch("config.management.commands.restore_db.restore_database")
@patch("config.management.commands.restore_db.download_backup")
@patch("config.management.commands.restore_db.find_latest_backup_key")
@patch("config.management.commands.restore_db.get_s3_backup_config")
def test_restore_db_command_uses_latest_key_when_requested(
    mock_get_s3,
    mock_find_latest,
    mock_download,
    mock_restore,
):
    mock_get_s3.return_value = Mock(bucket="backups", prefix="djtmplt")
    mock_find_latest.return_value = f"djtmplt/{BACKUP_SUBDIR}/latest.dump"

    call_command("restore_db", "--latest", "--yes")

    mock_download.assert_called_once()
    downloaded_path = Path(mock_download.call_args.args[1])
    assert downloaded_path.name == "latest.dump"
    mock_restore.assert_called_once_with(downloaded_path)


def test_restore_db_requires_confirmation_flag():
    with pytest.raises(CommandError, match="Pass --yes"):
        call_command("restore_db", "--latest")


def test_restore_db_requires_exactly_one_source_option():
    with pytest.raises(CommandError, match="Specify exactly one"):
        call_command("restore_db", "--yes")