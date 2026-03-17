import json
from unittest.mock import patch

from django.core.management import call_command


def test_health_endpoint_returns_ok(client):
    response = client.get("/health/")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@patch("config.urls.build_readiness_report")
def test_readiness_endpoint_returns_ok_when_all_checks_pass(mock_build_report, client):
    mock_build_report.return_value = {
        "status": "ok",
        "checks": {
            "database": {"status": "ok"},
            "cache": {"status": "ok"},
            "migrations": {"status": "ok"},
            "broker": {"status": "skipped"},
            "process": {"status": "skipped"},
        },
    }

    response = client.get("/ready/")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    mock_build_report.assert_called_once_with(check_migrations=True)


@patch("config.urls.build_readiness_report")
def test_readiness_endpoint_returns_503_when_any_check_fails(mock_build_report, client):
    mock_build_report.return_value = {
        "status": "error",
        "checks": {
            "database": {"status": "error", "detail": "Database down"},
            "cache": {"status": "ok"},
            "migrations": {"status": "skipped"},
            "broker": {"status": "skipped"},
            "process": {"status": "skipped"},
        },
    }

    response = client.get("/ready/")

    assert response.status_code == 503
    assert response.json()["status"] == "error"


@patch("config.management.commands.check_readiness.build_readiness_report")
def test_check_readiness_command_returns_success(mock_build_report, capsys):
    mock_build_report.return_value = {
        "status": "ok",
        "checks": {"database": {"status": "ok"}},
    }

    call_command("check_readiness")

    stdout = capsys.readouterr().out.strip()
    assert json.loads(stdout)["status"] == "ok"
    mock_build_report.assert_called_once_with(
        check_migrations=True,
        check_broker=False,
        expected_process=None,
    )


@patch("config.management.commands.check_readiness.build_readiness_report")
def test_check_readiness_command_exits_non_zero_on_failure(mock_build_report, capsys):
    mock_build_report.return_value = {
        "status": "error",
        "checks": {"database": {"status": "error", "detail": "Database down"}},
    }

    try:
        call_command(
            "check_readiness",
            "--skip-migrations",
            "--check-broker",
            "--expect-process",
            "worker",
        )
        raised = False
    except SystemExit as exc:
        raised = True
        assert exc.code == 1

    stderr = capsys.readouterr().err.strip()
    assert raised is True
    assert json.loads(stderr)["status"] == "error"
    mock_build_report.assert_called_once_with(
        check_migrations=False,
        check_broker=True,
        expected_process="worker",
    )