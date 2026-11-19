import json
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

import httpx
from test_postgresql_storage import database as database
from test_search_repository import SCOPE
from test_search_repository import search_database as search_database

ROOT = Path(__file__).resolve().parents[3]


def test_real_local_http_process_and_node_fetch_with_synthetic_postgres(search_database):
    with socket.socket() as reservation:
        reservation.bind(("127.0.0.1", 0))
        port = reservation.getsockname()[1]
    environment = {
        **os.environ,
        "F3_SYNTHETIC_DATABASE_URL": search_database.url.render_as_string(hide_password=False),
        "F3_SYNTHETIC_SCOPE": SCOPE.model_dump_json(),
        "F3_SYNTHETIC_TOKEN": "f3-synthetic-live-token",
        "F3_SYNTHETIC_PORT": str(port),
    }
    process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "search_http_app:create_test_app",
            "--factory",
            "--app-dir",
            "tests",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
            "--no-access-log",
            "--no-proxy-headers",
            "--log-level",
            "warning",
        ],
        cwd=ROOT / "apps/server",
        env=environment,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        deadline = time.monotonic() + 10
        while True:
            try:
                response = httpx.get(
                    f"http://127.0.0.1:{port}/openapi.json",
                    trust_env=False,
                    timeout=0.2,
                )
                if response.status_code == 200:
                    break
            except httpx.HTTPError:
                pass
            assert process.poll() is None and time.monotonic() < deadline
            time.sleep(0.05)
        script = r"""
(async () => {
 const base = 'http://127.0.0.1:' + process.env.F3_SYNTHETIC_PORT;
 const headers = {Authorization:'Bearer ' + process.env.F3_SYNTHETIC_TOKEN,
  'Content-Type':'application/json', Accept:'application/x-ndjson'};
 const response = await fetch(base + '/search', {method:'POST', headers,
  body:JSON.stringify({query:'지난달 예산 메일', overrides:{directions:['received']}})});
 const frames = (await response.text()).trim().split('\n').map(JSON.parse);
 const parsed = frames.find(frame => frame.type === 'parsed').data;
 const data = frames.find(frame => frame.type === 'results').data;
 const answer = frames.find(frame => frame.type === 'answer').data;
 const recent = await fetch(base+'/search/recent', {headers});
 const removed = await fetch(base+'/search', {method:'POST', headers,
  body:JSON.stringify({query:'지난달 예산 메일', search_id:parsed.search_id,
   overrides:{period:null}})});
 const denied = await fetch(base+'/search/recent');
 const foreign = await fetch(base+'/search', {method:'POST', headers,
  body:JSON.stringify({query:'예산', user_id:'other-user'})});
 console.log(JSON.stringify({status:response.status, cache:response.headers.get('cache-control'),
  stages:frames.map(frame=>frame.type), ids:data.results.map(row=>row.mail_id).sort(),
  citationsValid:answer.citations.every(c=>data.results.some(r=>
   r.mail_id===c.mail_id && r.number===c.number)),
  semantic:data.semantic_enabled, recent:recent.status, recentCount:(await recent.json()).length,
  removed:removed.status, denied:denied.status, foreign:foreign.status}));
})().catch(() => process.exit(1));
"""
        result = subprocess.run(
            ["node", "-e", script],
            env=environment,
            capture_output=True,
            text=True,
            timeout=15,
            check=True,
        )
        assert json.loads(result.stdout) == {
            "status": 200,
            "cache": "no-store",
            "stages": ["parsed", "results", "answer"],
            "ids": ["m1", "m2", "m3"],
            "citationsValid": True,
            "semantic": False,
            "recent": 200,
            "recentCount": 1,
            "removed": 200,
            "denied": 401,
            "foreign": 422,
        }
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)
