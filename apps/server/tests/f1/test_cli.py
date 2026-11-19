import json
import os
import subprocess
import sys

import pytest

from app.cli.analyze_pending import main


def test_unconfigured_run_never_opens_database(monkeypatch, capsys):
    def reject_database():
        pytest.fail("제공자 미설정 시 DB를 열면 안 됩니다")

    monkeypatch.setattr("app.cli.analyze_pending.database_engine", reject_database)
    assert main(["run", "--user-id", "synthetic-user", "--account-id", "synthetic-account"]) == 1
    assert json.loads(capsys.readouterr().out) == {
        "status": "not_configured",
        "done": 0,
        "failed": 0,
    }


def test_reanalysis_must_name_a_mail(capsys):
    with pytest.raises(SystemExit):
        main(["run", "--user-id", "u", "--account-id", "a", "--reanalyze"])
    assert "--mail-id" in capsys.readouterr().err


def test_check_is_read_only_and_does_not_load_ai(f1_database, monkeypatch, capsys):
    monkeypatch.setattr("app.cli.analyze_pending.database_engine", lambda: f1_database)

    def reject_provider():
        pytest.fail("check에서 제공자를 불러오면 안 됩니다")

    monkeypatch.setattr("app.cli.analyze_pending.load_providers", reject_provider)
    assert main(["check", "--user-id", "synthetic-user", "--account-id", "synthetic-account"]) == 0
    assert json.loads(capsys.readouterr().out) == {
        "status": "checked",
        "storage_ready": True,
        "pending": 0,
        "providers_ready": False,
    }


def test_cli_process_unconfigured_does_not_fall_back_to_a_fixture():
    process = subprocess.run(
        [
            sys.executable,
            "-m",
            "app.cli.analyze_pending",
            "run",
            "--user-id",
            "synthetic-user",
            "--account-id",
            "synthetic-account",
        ],
        env={**os.environ, "DATABASE_URL": "invalid-on-purpose"},
        text=True,
        capture_output=True,
        timeout=10,
    )
    assert process.returncode == 1 and process.stderr == ""
    assert json.loads(process.stdout) == {"status": "not_configured", "done": 0, "failed": 0}


def test_missing_storage_check_has_nonzero_exit(f1_database, monkeypatch, capsys):
    monkeypatch.setattr("app.cli.analyze_pending.database_engine", lambda: f1_database)
    monkeypatch.setattr(
        "app.cli.analyze_pending.AnalysisRepository.readiness",
        lambda self, **kwargs: {"storage_ready": False, "pending": None},
    )
    assert main(["check", "--user-id", "u", "--account-id", "a"]) == 1
    assert json.loads(capsys.readouterr().out)["storage_ready"] is False
