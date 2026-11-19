"""승인 전 패치 검사 전용. 기본 pytest 수집에는 포함하지 않고 명시적으로 실행한다."""

import hashlib
import json
import runpy
import shutil
import subprocess
from pathlib import Path

from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from test_postgresql_storage import database as database
from test_postgresql_storage import seed_account, store

from app.db.models import Base, GoogleCredential, Mail, MailAccount
from app.db.repositories.search_recent import search_metadata

ROOT = Path(__file__).resolve().parents[3]
PATCHES = ROOT / "integration/F3-search"


def test_protected_files_are_unchanged_and_proposed_patches_apply_cleanly():
    manifest = json.loads((PATCHES / "baseline.json").read_text())
    assert (
        manifest["base_commit"]
        == subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=ROOT,
            text=True,
        ).strip()
    )
    for name, expected in manifest["protected_files"].items():
        actual = hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
        assert actual == expected, f"보호 대상 파일 변경: {name}"
        original = subprocess.check_output(["git", "show", f"HEAD:{name}"], cwd=ROOT)
        assert actual == hashlib.sha256(original).hexdigest(), name
    subprocess.run(
        ["git", "apply", "--check", *map(str, sorted(PATCHES.glob("*.patch")))],
        cwd=ROOT,
        check=True,
        capture_output=True,
    )


def test_proposed_migration_matches_model_and_preserves_existing_mail(database, tmp_path):
    engine, _ = database
    # 패치는 독립 테스트 복사본에만 적용한다. 실제 Alembic 이력은 바꾸지 않는다.
    target = tmp_path / "candidate"
    migration_dir = target / "apps/server/migrations"
    shutil.copytree(ROOT / "apps/server/migrations", migration_dir)
    copied_test = target / "apps/server/tests/test_postgresql_storage.py"
    copied_test.parent.mkdir(parents=True)
    shutil.copyfile(ROOT / "apps/server/tests/test_postgresql_storage.py", copied_test)
    subprocess.run(
        ["git", "apply", str(PATCHES / "01-storage.patch")],
        cwd=target,
        check=True,
        capture_output=True,
    )
    config = Config(str(ROOT / "apps/server/alembic.ini"))
    config.set_main_option("script_location", str(migration_dir))
    with Session(engine) as session, session.begin():
        store(seed_account(session))
        session.add(
            GoogleCredential(
                account_id="account-a",
                token_ciphertext="synthetic-existing-ciphertext",
                updated_at=session.get(MailAccount, "account-a").sync_started_at,
            )
        )
    command.upgrade(config, "head")
    command.upgrade(config, "head")
    with engine.connect() as connection:
        assert (
            compare_metadata(
                MigrationContext.configure(connection),
                [Base.metadata, search_metadata],
            )
            == []
        )
    command.downgrade(config, "0002")
    with Session(engine) as session:
        assert session.get(Mail, "mail-a").body_text == "실제 메일이 아닌 자동 검사 데이터"
        assert session.get(MailAccount, "account-a").sync_cursor is None
        assert (
            session.get(GoogleCredential, "account-a").token_ciphertext
            == "synthetic-existing-ciphertext"
        )
    command.upgrade(config, "head")


def test_proposed_shared_types_are_generated_and_typecheck(tmp_path):
    target = tmp_path / "candidate"
    for name in [
        "packages/api-types/openapi.json",
        "packages/api-types/src/schema.d.ts",
        "apps/server/app/main.py",
        "apps/server/app/cli/run_mail_api.py",
        "apps/server/tests/test_http_server.py",
    ]:
        path = target / name
        path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / name, path)
    subprocess.run(
        [
            "git",
            "apply",
            str(PATCHES / "02-server-registration.patch"),
            str(PATCHES / "03-shared-api-types.patch"),
        ],
        cwd=target,
        check=True,
        capture_output=True,
    )
    schema = json.loads((target / "packages/api-types/openapi.json").read_text())
    from app.api.search import register_search_api
    from app.main import create_app

    application = create_app()
    register_search_api(application)
    assert schema == application.openapi()
    candidate = runpy.run_path(str(target / "apps/server/app/main.py"))
    assert candidate["create_app"]().openapi() == schema
    with TestClient(
        candidate["create_app"](), base_url="http://127.0.0.1:8000", client=("127.0.0.1", 10000)
    ) as client:
        response = client.post(
            "/search", json={"query": "예산"}, headers={"Authorization": "Bearer synthetic-token"}
        )
        assert response.status_code == 503 and "results" not in response.json()
    # 공유 등록 검사도 제안된 경로 목록과 맞는지 독립 복사본에서 실행한다.
    namespace = {}
    test_file = target / "apps/server/tests/test_http_server.py"
    exec(compile(test_file.read_text(), str(test_file), "exec"), namespace)
    namespace["create_app"] = candidate["create_app"]
    namespace["test_openapi_describes_only_implemented_api_and_its_response"]()
    compile((target / "apps/server/app/cli/run_mail_api.py").read_text(), "candidate-cli", "exec")
    tsc = ROOT / "packages/api-types/node_modules/.bin/tsc"
    subprocess.run(
        [str(tsc), "--noEmit", "--strict", str(target / "packages/api-types/src/schema.d.ts")],
        check=True,
        capture_output=True,
    )
