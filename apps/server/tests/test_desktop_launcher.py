"""합성 도구·프로세스만 사용한다. Docker/실제 앱/Google/AI는 시작하지 않는다."""

import importlib.util
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

ROOT = Path(__file__).resolve().parents[3]
SPEC = importlib.util.spec_from_file_location("klover_launcher", ROOT / "scripts/launcher/run.py")
launcher = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(launcher)
REAL_OLLAMA_READY = launcher.ollama_ready


@pytest.fixture
def configured(monkeypatch, tmp_path):
    ai = SimpleNamespace(
        ollama=SimpleNamespace(
            base_url="http://localhost:11434", models={"analysis": "synthetic:1"}
        ),
        embedding=SimpleNamespace(model="embed"),
    )
    monkeypatch.setattr(launcher, "ROOT", tmp_path / "folder with spaces & 문자")
    launcher.ROOT.mkdir()
    monkeypatch.setattr(launcher, "SERVER", launcher.ROOT / "apps/server")
    monkeypatch.setattr(launcher, "DESKTOP", launcher.ROOT / "apps/desktop")
    monkeypatch.setattr(
        launcher, "prerequisites", lambda: ("node", "docker", Path("cli.js"), "synthetic-token", ai)
    )
    monkeypatch.setattr(launcher, "run_command", Mock(return_value=True))
    monkeypatch.setattr(launcher, "ollama_ready", Mock(return_value=True))
    monkeypatch.setattr(launcher, "port_available", Mock(return_value=True))
    return ai


def test_os_lock_rejects_duplicate_and_releases_after_exit(tmp_path):
    path = tmp_path / "launcher.lock"
    with launcher.LaunchLock(path):
        with pytest.raises(launcher.LaunchError):
            with launcher.LaunchLock(path):
                pass
    with launcher.LaunchLock(path):
        pass


def test_windows_lock_uses_one_byte_and_closes_on_failure(monkeypatch, tmp_path):
    import sys

    locking = Mock(side_effect=OSError)
    monkeypatch.setitem(sys.modules, "msvcrt", SimpleNamespace(locking=locking, LK_NBLCK=1))
    monkeypatch.setattr(launcher, "WINDOWS", True)
    lock = launcher.LaunchLock(tmp_path / "lock")
    with pytest.raises(launcher.LaunchError):
        lock.__enter__()
    assert lock.stream.closed
    assert locking.call_args.args[1:] == (1, 1)


def test_check_only_never_starts_services_or_migrates(configured, monkeypatch, capsys):
    children = Mock()
    monkeypatch.setattr(launcher, "Children", lambda: children)
    launcher.launch(check_only=True)
    children.start.assert_not_called()
    commands = launcher.run_command.call_args_list
    assert len(commands) == 2
    assert "info" in commands[0].args[0]
    assert commands[1].args[0][-1] == "app.cli.check_database"
    assert "synthetic-token" not in capsys.readouterr().out


@pytest.mark.parametrize("kind", ["docker", "port", "db", "ollama", "server"])
def test_readiness_failure_never_starts_desktop_and_cleans_owned_children(
    configured, monkeypatch, kind, capsys
):
    children = Mock()
    monkeypatch.setattr(launcher, "Children", lambda: children)
    if kind == "docker":
        launcher.run_command.return_value = False
    elif kind == "port":
        launcher.port_available.return_value = False
    elif kind == "db":
        launcher.run_command.side_effect = [True, True, False]
    elif kind == "ollama":
        launcher.ollama_ready.return_value = False
        monkeypatch.setattr(launcher, "local_json", lambda *_: {"models": []})
    else:
        monkeypatch.setattr(launcher, "wait_ready", lambda *_args, **_kwargs: False)
    with pytest.raises(launcher.LaunchError):
        launcher.launch()
    for call in children.start.call_args_list:
        assert "dev" not in call.args[0]
    if kind != "docker":
        children.close.assert_called_once()
    assert "synthetic-token" not in capsys.readouterr().out


def test_complete_launch_uses_absolute_token_and_owns_only_new_processes(configured, monkeypatch):
    children = Mock()
    server = Mock()
    server.poll.return_value = None
    desktop = Mock(returncode=0)
    desktop.poll.return_value = 0
    children.start.side_effect = [server, desktop]
    monkeypatch.setattr(launcher, "Children", lambda: children)
    monkeypatch.setattr(launcher, "wait_ready", lambda check, **_: check())
    monkeypatch.setattr(
        launcher,
        "local_json",
        lambda *_: {
            "user_id": "synthetic",
            "account_id": "synthetic",
            "email": "test@example.invalid",
            "sync_started_at": "2026-11-25",
        },
    )
    launcher.launch()
    assert children.start.call_count == 2
    desktop_call = children.start.call_args_list[1]
    assert desktop_call.args[0] == ["node", "cli.js", "dev"]
    assert desktop_call.kwargs["env"]["KLOVER_API_TOKEN_FILE"] == str(
        launcher.ROOT / ".local-secrets/mail-api-token"
    )
    assert desktop_call.kwargs["env"]["KLOVER_API_BASE_URL"] == "http://127.0.0.1:8000"
    commands = [call.args[0] for call in launcher.run_command.call_args_list]
    assert "--pull" in commands[1] and "never" in commands[1]
    assert not any("upgrade" in x or "down" in x for x in commands)
    children.close.assert_called_once()


def test_model_tag_validation_and_missing_model(monkeypatch, configured):
    monkeypatch.setattr(
        launcher,
        "local_json",
        lambda *_: {"models": [{"name": "synthetic:1"}, {"name": "embed:latest"}]},
    )
    assert REAL_OLLAMA_READY(configured)
    monkeypatch.setattr(launcher, "local_json", lambda *_: {"models": [{"name": "synthetic:1"}]})
    assert not REAL_OLLAMA_READY(configured)


def test_cleanup_windows_never_targets_external_processes(monkeypatch):
    calls = Mock(return_value=True)
    monkeypatch.setattr(launcher, "WINDOWS", True)
    monkeypatch.setattr(launcher, "run_command", calls)
    children = launcher.Children()
    children.items = [Mock(pid=123, poll=Mock(return_value=None))]
    children.close()
    assert calls.call_args.args[0] == ["taskkill", "/PID", "123", "/T", "/F"]


def test_cleanup_posix_uses_only_owned_groups(monkeypatch):
    kill = Mock()
    monkeypatch.setattr(launcher.os, "killpg", kill, raising=False)
    monkeypatch.setattr(launcher, "WINDOWS", False)
    children = launcher.Children()
    children.items = [Mock(pid=123)]
    children.close()
    kill.assert_called_once_with(123, launcher.signal.SIGTERM)


def test_wait_timeout_and_child_exit(monkeypatch):
    monkeypatch.setattr(launcher.time, "monotonic", Mock(side_effect=[0, 1, 99]))
    monkeypatch.setattr(launcher.time, "sleep", lambda _: None)
    assert not launcher.wait_ready(lambda: False, seconds=2)
    monkeypatch.setattr(launcher.time, "monotonic", lambda: 0)
    assert not launcher.wait_ready(lambda: True, process=Mock(poll=Mock(return_value=1)))


def test_main_sanitizes_unexpected_errors_and_releases_lock(configured, monkeypatch, capsys):
    monkeypatch.setattr(launcher.sys, "argv", ["run.py"])
    monkeypatch.setattr(launcher, "launch", Mock(side_effect=RuntimeError("private-key-mail")))
    assert launcher.main() == 1
    assert "private-key-mail" not in capsys.readouterr().out
    with launcher.LaunchLock(launcher.ROOT / ".local-run/launcher.lock"):
        pass


def test_launcher_does_not_create_google_secret_directory(configured, monkeypatch):
    monkeypatch.setattr(launcher.sys, "argv", ["run.py", "--check"])
    monkeypatch.setattr(launcher, "launch", Mock())
    assert launcher.main() == 0
    assert not (launcher.ROOT / ".local-secrets").exists()


def test_port_check_reports_busy_without_stopping_listener():
    import socket

    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        listener.listen()
        port = listener.getsockname()[1]
        assert not launcher.port_available(port)
        assert listener.getsockname()[1] == port


def test_http_probe_blocks_redirect_and_does_not_forward_token(monkeypatch):
    import json
    import threading
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

    seen = []

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_args):
            pass

        def do_GET(self):
            seen.append((self.path, self.headers.get("Authorization")))
            if self.path == "/redirect":
                self.send_response(302)
                self.send_header("Location", "/destination")
                self.end_headers()
            else:
                self.send_response(200)
                self.end_headers()
                self.wfile.write(json.dumps({"status": "synthetic"}).encode())

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        base = f"http://127.0.0.1:{server.server_port}"
        monkeypatch.setenv("HTTP_PROXY", "http://127.0.0.1:1")
        assert launcher.local_json(base + "/ok") == {"status": "synthetic"}
        assert launcher.local_json(base + "/redirect", "synthetic-token") is None
        assert seen == [("/ok", None), ("/redirect", "Bearer synthetic-token")]
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


def test_macos_wrapper_works_with_spaces_without_installing_tools(tmp_path):
    import os
    import subprocess

    if os.name == "nt":
        pytest.skip("bash wrapper 검사는 POSIX 환경에서 실행")
    folder = tmp_path / "Klover & spaces"
    python = folder / "apps/server/.venv/bin/python"
    python.parent.mkdir(parents=True)
    python.write_text(
        '#!/bin/sh\n[ "$1" = "'
        + str(folder / "scripts/launcher/run.py")
        + '" ] || exit 2\nexit 0\n'
    )
    python.chmod(0o700)
    wrapper = folder / "Klover-Start.command"
    wrapper.write_bytes((ROOT / "Klover-Start.command").read_bytes())
    result = subprocess.run(
        ["bash", str(wrapper)], input="\n", text=True, capture_output=True, cwd=tmp_path, timeout=5
    )
    assert result.returncode == 0


def test_missing_macos_setup_keeps_actionable_message(tmp_path):
    import os
    import subprocess

    if os.name == "nt":
        pytest.skip("bash wrapper 검사는 POSIX 환경에서 실행")
    wrapper = tmp_path / "Klover-Start.command"
    wrapper.write_bytes((ROOT / "Klover-Start.command").read_bytes())
    result = subprocess.run(
        ["bash", str(wrapper)], input="\n", text=True, capture_output=True, timeout=5
    )
    assert result.returncode == 1
    assert "최초 설치" in result.stdout


def test_real_child_cleanup_preserves_unrelated_process():
    import subprocess
    import sys

    unrelated = subprocess.Popen(
        [sys.executable, "-c", "import time; time.sleep(60)"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    children = launcher.Children()
    try:
        owned = children.start([sys.executable, "-c", "import time; time.sleep(60)"])
        children.close()
        assert owned.poll() is not None
        assert unrelated.poll() is None
    finally:
        if unrelated.poll() is None:
            unrelated.terminate()
        unrelated.wait(timeout=5)


def test_windows_wrapper_missing_setup_is_actionable(tmp_path):
    import os
    import subprocess

    if os.name != "nt":
        pytest.skip("실제 cmd 시작 파일 검사는 Windows CI에서 실행")
    wrapper = tmp_path / "Klover-Start.cmd"
    wrapper.write_bytes((ROOT / "Klover-Start.cmd").read_bytes())
    result = subprocess.run(
        ["cmd.exe", "/d", "/c", str(wrapper)],
        input="\n",
        text=True,
        encoding="utf-8",
        capture_output=True,
        timeout=10,
    )
    assert result.returncode == 1
    assert "최초 설치" in result.stdout
