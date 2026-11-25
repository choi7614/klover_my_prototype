"""설치 완료된 로컬 Klover 실행. 비밀 설정·메일·외부 응답을 출력하지 않는다."""

import argparse
import contextlib
import json
import os
import shutil
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path
from urllib.request import ProxyHandler, Request, build_opener

ROOT = Path(__file__).resolve().parents[2]
SERVER = ROOT / "apps/server"
DESKTOP = ROOT / "apps/desktop"
WINDOWS = os.name == "nt"


class LaunchError(Exception):
    pass


def message(text):
    print(text, flush=True)


def run_command(command, *, cwd=ROOT, env=None, timeout=30):
    try:
        return (
            subprocess.run(
                command,
                cwd=cwd,
                env=env,
                timeout=timeout,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            ).returncode
            == 0
        )
    except (OSError, subprocess.TimeoutExpired):
        return False


def git(args, *, timeout=30):
    """고정 인자의 git만 실행한다. 인증 입력창이 뜨지 않게 하고 (종료 코드, 출력)을 돌려준다."""
    try:
        done = subprocess.run(
            ["git", *args],
            cwd=ROOT,
            env={**os.environ, "GIT_TERMINAL_PROMPT": "0"},
            timeout=timeout,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            check=False,
        )
        return done.returncode, done.stdout.strip()
    except (OSError, subprocess.TimeoutExpired):
        return 1, ""


# 이 경로가 바뀐 업데이트일 때 필요한 후속 처리
SERVER_DEPENDENCY_FILES = {"apps/server/uv.lock", "apps/server/pyproject.toml"}
LAUNCHER_PREFIXES = ("scripts/launcher/", "Klover-Start.")


def update_dependencies(changed):
    """잠금 파일이 바뀐 때만 설치한다. 실패하면 실행하지 않고 안내한다."""
    if changed & SERVER_DEPENDENCY_FILES:
        uv = shutil.which("uv")
        message("서버 패키지를 갱신하고 있어요…")
        if not uv or not run_command(
            [uv, "sync", "--locked", "--directory", str(SERVER)], timeout=600
        ):
            raise LaunchError(
                "새 버전은 받았지만 서버 패키지를 갱신하지 못했어요. "
                "docs/dev/setup.md 9절의 uv sync를 직접 실행하세요."
            )
    if any(name == "pnpm-lock.yaml" or name.endswith("package.json") for name in changed):
        corepack, pnpm = shutil.which("corepack"), shutil.which("pnpm")
        command = [corepack, "pnpm"] if corepack else [pnpm] if pnpm else None
        message("앱 패키지를 갱신하고 있어요. 몇 분 걸릴 수 있어요…")
        if not command or not run_command([*command, "install", "--frozen-lockfile"], timeout=900):
            raise LaunchError(
                "새 버전은 받았지만 앱 패키지를 갱신하지 못했어요. "
                "docs/dev/setup.md 9절의 pnpm install을 직접 실행하세요."
            )


def auto_update():
    """main 브랜치를 안전하게 최신으로 맞춘다. 실행 도구 자신이 바뀌면 True(다시 시작 필요).

    다음 조건을 모두 만족할 때만 받는다: git 저장소, main 브랜치, 고친 파일 없음, 빨리감기 가능.
    그 밖에는 아무것도 바꾸지 않고 현재 버전으로 계속한다. reset·강제 전환·덮어쓰기를 하지 않는다.
    """
    if os.environ.get("KLOVER_NO_UPDATE") == "1":
        message("자동 업데이트를 건너뜁니다(KLOVER_NO_UPDATE=1).")
        return False
    if not (ROOT / ".git").exists() or not shutil.which("git"):
        message("Git 저장소가 아니라서 자동 업데이트를 건너뜁니다.")
        return False
    code, branch = git(["rev-parse", "--abbrev-ref", "HEAD"])
    if code or branch != "main":
        message(
            "main 브랜치가 아니라서 자동 업데이트를 건너뜁니다(작업 중인 브랜치는 건드리지 않아요)."
        )
        return False
    code, dirty = git(["status", "--porcelain", "--untracked-files=no"])
    if code or dirty:
        message("직접 고친 파일이 있어서 자동 업데이트를 건너뜁니다. 현재 버전으로 실행해요.")
        return False
    message("최신 버전을 확인하고 있어요…")
    if git(["fetch", "origin", "main"], timeout=30)[0]:
        message("최신 버전을 확인하지 못했어요(인터넷·저장소 확인). 현재 버전으로 실행해요.")
        return False
    _, before = git(["rev-parse", "HEAD"])
    code, after = git(["rev-parse", "origin/main"])
    if code or not before or before == after:
        message("이미 최신 버전이에요.")
        return False
    if git(["merge-base", "--is-ancestor", "HEAD", "origin/main"])[0]:
        message(
            "이 컴퓨터의 main이 원격과 달라서 자동 업데이트를 건너뜁니다. 현재 버전으로 실행해요."
        )
        return False
    if git(["merge", "--ff-only", "origin/main"], timeout=60)[0]:
        message("새 버전을 적용하지 못해 현재 버전으로 실행해요. 변경은 없습니다.")
        return False
    _, names = git(["diff", "--name-only", before, "HEAD"])
    changed = {line.strip() for line in names.splitlines() if line.strip()}
    message(f"새 버전으로 업데이트했어요({len(changed)}개 파일 변경).")
    update_dependencies(changed)
    if any(name.startswith("apps/server/migrations/") for name in changed):
        message(
            "이번 업데이트에는 DB 구조 변경이 포함돼 있어요. 백업한 뒤 docs/dev/setup.md 9절의 "
            "마이그레이션을 실행해야 실행됩니다."
        )
    return any(name.startswith(LAUNCHER_PREFIXES) for name in changed)


def local_json(url, token=None):
    # 프록시와 리디렉션을 사용하지 않는다. 인증은 고정 loopback 주소에만 보낸다.
    from urllib.request import HTTPRedirectHandler

    class NoRedirect(HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            return None

    headers = {"Accept": "application/json"}
    if token:
        headers["Authorization"] = "Bearer " + token
    try:
        with build_opener(ProxyHandler({}), NoRedirect()).open(
            Request(url, headers=headers), timeout=2
        ) as response:
            data = response.read(1_048_577)
            if len(data) > 1_048_576:
                return None
            return json.loads(data)
    except Exception:
        return None


class LaunchLock:
    """OS 잠금은 프로세스 종료 시 해제된다. PID 파일로 다른 프로세스를 종료하지 않는다."""

    def __init__(self, path):
        self.path, self.stream = path, None

    def __enter__(self):
        self.path.parent.mkdir(mode=0o700, exist_ok=True)
        self.stream = self.path.open("a+b")
        self.stream.seek(0)
        if self.path.stat().st_size == 0:
            self.stream.write(b"0")
            self.stream.flush()
        self.stream.seek(0)
        try:
            if WINDOWS:
                import msvcrt

                msvcrt.locking(self.stream.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl

                fcntl.flock(self.stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            self.stream.close()
            raise LaunchError(
                "Klover 실행 도구가 이미 열려 있어요. 기존 실행 창을 확인하세요."
            ) from None
        return self

    def __exit__(self, *_):
        self.stream.close()


class Children:
    def __init__(self):
        self.items = []

    def start(self, args, *, cwd=ROOT, env=None):
        try:
            process = subprocess.Popen(
                args,
                cwd=cwd,
                env=env,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                **(
                    {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP}
                    if WINDOWS
                    else {"start_new_session": True}
                ),
            )
        except OSError:
            raise LaunchError("실행 파일을 열지 못했어요. 설치 상태를 확인하세요.") from None
        self.items.append(process)
        return process

    def close(self):
        for process in reversed(self.items):
            if WINDOWS:
                # 이 도구가 직접 만든 프로세스 트리만 대상으로 한다.
                if process.poll() is None:
                    run_command(["taskkill", "/PID", str(process.pid), "/T", "/F"], timeout=10)
            else:
                with contextlib.suppress(ProcessLookupError):
                    os.killpg(process.pid, signal.SIGTERM)
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    with contextlib.suppress(ProcessLookupError):
                        os.killpg(process.pid, signal.SIGKILL)
            with contextlib.suppress(subprocess.TimeoutExpired):
                process.wait(timeout=5)


def wait_ready(check, *, seconds=45, process=None):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        if process is not None and process.poll() is not None:
            return False
        if check():
            return True
        time.sleep(0.5)
    return False


def port_available(port):
    with socket.socket() as sock:
        try:
            sock.bind(("127.0.0.1", port))
            return True
        except OSError:
            return False


def prerequisites():
    sys.path.insert(0, str(SERVER))
    from app.ai.config import environment_values, read_ai_settings
    from app.google_config import load_settings
    from app.mail_api_config import read_api_token

    if not (ROOT / ".env").is_file():
        raise LaunchError("먼저 설치 안내에 따라 DB·Google·AI 최초 설정을 완료하세요.")
    try:
        load_settings()
        token = read_api_token()
        ai = read_ai_settings({**environment_values(), "AI_PROVIDER": "ollama"})
    except Exception:
        raise LaunchError(
            "Google·메일 API·로컬 AI 설정을 확인하세요. 기존 키를 다시 만들지 마세요."
        ) from None
    node, docker = shutil.which("node"), shutil.which("docker")
    cli = DESKTOP / "node_modules/electron-vite/bin/electron-vite.js"
    electron = DESKTOP / "node_modules/electron/path.txt"
    if not node or not docker or not cli.is_file() or not electron.is_file():
        raise LaunchError(
            "Node.js·Docker·앱 의존성 또는 Electron 실행 파일이 없어요. 설치 안내를 확인하세요."
        )
    # path.txt가 있어도 실행 파일 다운로드가 끝났는지 확인한다.
    relative = electron.read_text().strip()
    if not relative or not (electron.parent / "dist" / relative).is_file():
        raise LaunchError(
            "Electron 다운로드가 완료되지 않았어요. 설치 안내의 Electron 오류 해결을 확인하세요."
        )
    return node, docker, cli, token, ai


def ollama_ready(ai):
    data = local_json(ai.ollama.base_url + "/api/tags")
    if not isinstance(data, dict) or not isinstance(data.get("models"), list):
        return False
    present = {row.get("name") for row in data["models"] if isinstance(row, dict)}
    required = set(ai.ollama.models.values()) | {ai.embedding.model}
    return all(
        model in present or (":" not in model and model + ":latest" in present)
        for model in required
    )


def launch(check_only=False):
    node, docker, cli, token, ai = prerequisites()
    compose = [
        docker,
        "compose",
        "--env-file",
        str(ROOT / ".env"),
        "-f",
        str(ROOT / "infra/docker-compose.yml"),
    ]
    if not run_command([docker, "info"], timeout=15):
        raise LaunchError("Docker Desktop을 켜고 준비가 끝나면 다시 실행하세요.")
    children = Children()
    try:
        if not check_only:
            if not port_available(8000):
                raise LaunchError(
                    "8000번 포트를 사용 중이에요. 기존 Klover 서버를 종료한 뒤 다시 실행하세요."
                )
            message("1/4 DB를 준비하고 있어요…")
            if not run_command(
                compose
                + [
                    "up",
                    "-d",
                    "--wait",
                    "--wait-timeout",
                    "90",
                    "--pull",
                    "never",
                    "db",
                ],
                timeout=110,
            ):
                raise LaunchError("DB를 준비하지 못했어요. Docker 상태·기존 DB 설정을 확인하세요.")
        if not run_command([sys.executable, "-m", "app.cli.check_database"], cwd=SERVER):
            raise LaunchError(
                "DB 연결 또는 버전 확인이 필요해요. 설치 안내의 업데이트를 먼저 완료하세요."
            )
        message("2/4 로컬 AI와 모델을 확인하고 있어요…")
        if not ollama_ready(ai) and not check_only:
            # 이미 켜진 Ollama가 있으면 건드리지 않는다. 모델 누락일 때 서버를 중복 실행하지 않는다.
            if local_json(ai.ollama.base_url + "/api/tags") is None:
                executable = shutil.which("ollama")
                if executable:
                    env = {**os.environ, "OLLAMA_HOST": ai.ollama.base_url}
                    process = children.start([executable, "serve"], env=env)
                    wait_ready(
                        lambda: local_json(ai.ollama.base_url + "/api/tags") is not None,
                        seconds=20,
                        process=process,
                    )
        if not ollama_ready(ai):
            raise LaunchError(
                "Ollama 또는 필요한 모델을 확인하지 못했어요. 설치 안내에 따라 실행·다운로드하세요."
            )
        if check_only:
            message("기본 준비 확인 완료. 실제 Google·AI 생성·앱 창 동작은 별도 확인이 필요해요.")
            return
        message("3/4 Klover 서버를 시작하고 있어요…")
        server = children.start([sys.executable, "-m", "app.cli.run_mail_api"], cwd=SERVER)

        def authenticated():
            data = local_json("http://127.0.0.1:8000/auth/session", token)
            return isinstance(data, dict) and all(
                isinstance(data.get(x), str) and data[x]
                for x in ("user_id", "account_id", "email", "sync_started_at")
            )

        if not wait_ready(authenticated, seconds=45, process=server):
            raise LaunchError(
                "서버·저장된 계정 연결을 확인하지 못했어요. 기존 Google 설정과 DB를 확인하세요."
            )
        message("4/4 Klover를 열고 있어요. 앱을 종료하면 이번에 시작한 서버도 정리합니다.")
        env = {
            **os.environ,
            "KLOVER_API_BASE_URL": "http://127.0.0.1:8000",
            "KLOVER_API_TOKEN_FILE": str(ROOT / ".local-secrets/mail-api-token"),
        }
        desktop = children.start([node, str(cli), "dev"], cwd=DESKTOP, env=env)
        while desktop.poll() is None:
            if server.poll() is not None:
                raise LaunchError(
                    "서버가 종료됐어요. 앱을 닫고 기존 설정을 확인한 뒤 다시 실행하세요."
                )
            time.sleep(0.5)
        if desktop.returncode:
            raise LaunchError("앱을 열지 못했어요. Node.js·Electron 설치와 앱 의존성을 확인하세요.")
    finally:
        children.close()
        message("이번 실행 도구가 시작한 앱·서버를 정리했습니다. DB·기존 Ollama는 유지합니다.")


def main():
    parser = argparse.ArgumentParser(description="설정 완료된 Klover 실행")
    parser.add_argument("--check", action="store_true", help="서비스 시작 없이 준비 상태 확인")
    parser.add_argument(
        "--no-update", action="store_true", help="시작 전 자동 업데이트를 하지 않음"
    )
    args = parser.parse_args()
    restart = False
    try:
        with LaunchLock(ROOT / ".local-run/launcher.lock"):
            # 준비 상태 확인(--check)은 아무것도 바꾸지 않는다.
            if not args.check and not args.no_update:
                restart = auto_update()
            if not restart:
                launch(args.check)
        if restart:
            # 실행 도구 자신이 바뀌었으면 새 코드로 다시 시작한다(잠금은 이미 풀었다).
            message("실행 도구가 새로워져서 다시 시작합니다.")
            return subprocess.call([sys.executable, str(Path(__file__).resolve()), "--no-update"])
    except KeyboardInterrupt:
        message("Klover 실행을 종료했습니다.")
    except LaunchError as error:
        message(str(error))
        message(
            "docs/dev/desktop-launcher.md 안내를 확인하세요. 키·메일·전체 로그는 공유하지 마세요."
        )
        return 1
    except Exception:
        message(
            "실행 준비 중 오류가 발생했어요. 설치 안내를 확인하세요. 비밀 설정을 공유하지 마세요."
        )
        return 1
    return 0


if __name__ == "__main__":
    for name in ("SIGTERM", "SIGHUP"):
        if hasattr(signal, name):
            signal.signal(getattr(signal, name), lambda *_: sys.exit(130))
    raise SystemExit(main())
