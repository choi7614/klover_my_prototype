import json
import socket
import subprocess
import sys
import time
from http.client import HTTPConnection


def test_uvicorn_process_starts_and_serves_health(tmp_path):
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]

    log = tmp_path / "server.log"
    with log.open("w+") as output:
        process = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "app.main:app",
                "--host",
                "127.0.0.1",
                "--port",
                str(port),
            ],
            stdout=output,
            stderr=subprocess.STDOUT,
        )
        try:
            deadline = time.monotonic() + 15
            while time.monotonic() < deadline:
                assert process.poll() is None, log.read_text()
                connection = HTTPConnection("127.0.0.1", port, timeout=1)
                try:
                    connection.request("GET", "/health")
                    response = connection.getresponse()
                    assert response.status == 200
                    assert json.loads(response.read()) == {"status": "ok"}
                    break
                except OSError:
                    time.sleep(0.05)
                finally:
                    connection.close()
            else:
                raise AssertionError(
                    "서버가 제한 시간 안에 응답하지 않았습니다.\n" + log.read_text()
                )
        finally:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
