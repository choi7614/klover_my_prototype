import pytest

from app.cli import init_local_db
from app.db.config import DatabaseConfigurationError, database_url


@pytest.mark.parametrize("value", ["not a url", "sqlite:///local.db", ""])
def test_invalid_database_url_does_not_echo_secret(monkeypatch, value):
    monkeypatch.setattr("app.db.config.dotenv_values", lambda _: {})
    monkeypatch.setenv("DATABASE_URL", value)
    monkeypatch.delenv("POSTGRES_PASSWORD", raising=False)
    with pytest.raises(DatabaseConfigurationError) as error:
        database_url()
    assert "not a url" not in str(error.value)


def test_database_url_handles_special_password_characters(monkeypatch):
    monkeypatch.setattr("app.db.config.dotenv_values", lambda _: {})
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("POSTGRES_PASSWORD", "synthetic:/@?#password")
    monkeypatch.setenv("POSTGRES_PORT", "15432")
    url = database_url()
    assert url.password == "synthetic:/@?#password"
    assert url.port == 15432
    assert url.drivername == "postgresql+psycopg"
    assert "synthetic" not in str(url)


def test_local_settings_initialization_preserves_existing_file(tmp_path, monkeypatch, capsys):
    fake_module = tmp_path / "apps/server/app/cli/init_local_db.py"
    monkeypatch.setattr(init_local_db, "__file__", str(fake_module))
    init_local_db.main()
    target = tmp_path / ".env"
    original = target.read_bytes()
    assert b"POSTGRES_PASSWORD=" in original
    assert target.stat().st_mode & 0o777 == 0o600
    init_local_db.main()
    assert target.read_bytes() == original
    assert original.decode().splitlines()[0] not in capsys.readouterr().out


def test_invalid_port_has_clear_error(monkeypatch):
    monkeypatch.setattr("app.db.config.dotenv_values", lambda _: {})
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("POSTGRES_PASSWORD", "synthetic-value")
    monkeypatch.setenv("POSTGRES_PORT", "99999")
    with pytest.raises(DatabaseConfigurationError, match="POSTGRES_PORT"):
        database_url()
