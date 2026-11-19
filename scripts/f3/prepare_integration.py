"""공통 파일을 고치지 않고 검토용 F3 패치를 생성한다. 적용/커밋은 수행하지 않는다."""

import difflib
import hashlib
import json
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DESTINATION = ROOT / "integration/F3-search"


def change(path, before, after):
    if path.endswith(".py"):
        ruff = ROOT / "apps/server/.venv/bin/ruff"
        after = subprocess.run(
            [
                str(ruff),
                "check",
                "--select",
                "I",
                "--fix",
                "--stdin-filename",
                str(ROOT / path),
                "-",
            ],
            input=after,
            text=True,
            capture_output=True,
            check=True,
            cwd=ROOT / "apps/server",
        ).stdout
        after = subprocess.run(
            [str(ruff), "format", "--stdin-filename", str(ROOT / path), "-"],
            input=after,
            text=True,
            capture_output=True,
            check=True,
            cwd=ROOT / "apps/server",
        ).stdout
    return "".join(
        difflib.unified_diff(
            before.splitlines(keepends=True),
            after.splitlines(keepends=True),
            fromfile=f"a/{path}" if before else "/dev/null",
            tofile=f"b/{path}",
        )
    )


def main():
    if (ROOT / "apps/server/migrations/versions/0003_search_runs.py").exists() or (
        "register_search_api(application)" in (ROOT / "apps/server/app/main.py").read_text()
    ):
        raise SystemExit(
            "F3 패치가 이미 적용되어 있습니다. 보관된 승인 전 패치를 덮어쓰지 않습니다."
        )
    DESTINATION.mkdir(parents=True, exist_ok=True)
    env_path = "apps/server/migrations/env.py"
    before = (ROOT / env_path).read_text()
    after = before.replace(
        "from app.db.models import Base\n",
        "from app.db.models import Base\n"
        "from app.db.repositories.search_recent import search_metadata\n",
    ).replace(
        "target_metadata=Base.metadata",
        "target_metadata=[Base.metadata, search_metadata]",
    )
    storage = change(env_path, before, after)
    migration = '''"""F3 최근 검색. 기존 사용자·계정·메일은 변경하지 않는다."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0003_search_runs"
down_revision = "0002_google_credentials"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "search_runs",
        sa.Column("search_id", sa.Text(), primary_key=True),
        sa.Column("user_id", sa.Text(), nullable=False),
        sa.Column("account_id", sa.Text(), nullable=False),
        sa.Column("query", sa.Text(), nullable=False),
        sa.Column("parsed", postgresql.JSONB(), nullable=False),
        sa.Column("overrides", postgresql.JSONB(), nullable=False),
        sa.Column("reference_date", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["account_id", "user_id"], ["mail_accounts.account_id", "mail_accounts.user_id"],
            name="fk_search_run_account_owner",
        ),
    )
    op.create_index(
        "ix_search_run_owner_created", "search_runs", ["user_id", "account_id", "created_at"]
    )


def downgrade():
    op.drop_index("ix_search_run_owner_created", table_name="search_runs")
    op.drop_table("search_runs")
'''
    # 실제 revision 이름은 현재 이력을 읽어 맞춘다.
    history = (ROOT / "apps/server/migrations/versions/0002_google_credentials.py").read_text()
    revision_line = next(line for line in history.splitlines() if line.startswith("revision ="))
    revision = revision_line.split("=", 1)[1].strip().strip("\"'")
    migration = migration.replace(
        'down_revision = "0002_google_credentials"', f'down_revision = "{revision}"'
    )
    storage += change("apps/server/migrations/versions/0003_search_runs.py", "", migration)
    test_path = "apps/server/tests/test_postgresql_storage.py"
    test_before = (ROOT / test_path).read_text()
    test_after = test_before.replace(
        "from app.db.models import Base, Mail\n",
        "from app.db.models import Base, Mail\n"
        "from app.db.repositories.search_recent import search_metadata\n",
    ).replace(
        "compare_metadata(MigrationContext.configure(connection), Base.metadata)",
        "compare_metadata(MigrationContext.configure(connection), "
        "[Base.metadata, search_metadata])",
    )
    storage += change(test_path, test_before, test_after)
    (DESTINATION / "01-storage.patch").write_text(storage)

    main_path = "apps/server/app/main.py"
    before = (ROOT / main_path).read_text()
    after = before.replace(
        "from app.api.mail_read import register_mail_api\n",
        "from app.api.mail_read import register_mail_api\n"
        "from app.api.search import register_search_api\n",
    ).replace(
        "    register_mail_api(application)\n",
        "    register_mail_api(application)\n    register_search_api(application)\n",
    )
    server = change(main_path, before, after)
    cli_path = "apps/server/app/cli/run_mail_api.py"
    before = (ROOT / cli_path).read_text()
    after = before.replace(
        "from app.db.repositories.mail_query import MailQueryRepository\n",
        "from app.db.repositories.mail_query import MailQueryRepository\n"
        "from app.db.repositories.search import SQLSearchRepository\n"
        "from app.db.repositories.search_recent import SQLRecentSearchRepository\n"
        "from app.services.search import SearchService\n",
    ).replace(
        '        print(f"메일 조회 API 실행:',
        "        application.state.search_service = SearchService(\n"
        "            SQLSearchRepository(engine), SQLRecentSearchRepository(engine),\n"
        "        )\n"
        '        print(f"메일 조회 API 실행:',
    )
    server += change(cli_path, before, after)
    http_test = "apps/server/tests/test_http_server.py"
    before = (ROOT / http_test).read_text()
    after = before.replace(
        '{"/health", "/auth/session", "/mails", "/mails/{mail_id}"}',
        '{"/health", "/auth/session", "/mails", "/mails/{mail_id}", "/search", "/search/recent"}',
    )
    server += change(http_test, before, after)
    (DESTINATION / "02-server-registration.patch").write_text(server)

    # 테스트용 앱에서 스키마만 생성한다. 운영 앱 파일·생성 타입은 변경하지 않는다.
    with tempfile.TemporaryDirectory(prefix="klover-f3-types-") as directory:
        directory = Path(directory)
        source, target = directory / "openapi.json", directory / "schema.d.ts"
        code = (
            "import json,sys; from app.main import create_app; "
            "from app.api.search import register_search_api; "
            "application=create_app(); register_search_api(application); "
            "open(sys.argv[1], 'w').write(json.dumps(application.openapi(), "
            "ensure_ascii=False, indent=2, sort_keys=True)+'\\n')"
        )
        subprocess.run(
            [str(ROOT / "apps/server/.venv/bin/python"), "-c", code, str(source)],
            cwd=ROOT / "apps/server",
            check=True,
            capture_output=True,
        )
        subprocess.run(
            [
                str(ROOT / "packages/api-types/node_modules/.bin/openapi-typescript"),
                str(source),
                "-o",
                str(target),
            ],
            check=True,
            capture_output=True,
        )
        types_patch = ""
        for path, generated in [
            ("packages/api-types/openapi.json", source),
            ("packages/api-types/src/schema.d.ts", target),
        ]:
            types_patch += change(path, (ROOT / path).read_text(), generated.read_text())
        (DESTINATION / "03-shared-api-types.patch").write_text(types_patch)

    paths = [
        "apps/server/app/main.py",
        "apps/server/app/cli/run_mail_api.py",
        "apps/server/app/db/models.py",
        "apps/server/migrations/env.py",
        "apps/server/tests/test_postgresql_storage.py",
        "apps/server/tests/test_http_server.py",
        "apps/server/uv.lock",
        "pnpm-lock.yaml",
        "packages/api-types/openapi.json",
        "packages/api-types/src/schema.d.ts",
        "apps/desktop/src/renderer/app.tsx",
        "apps/desktop/src/renderer/main.tsx",
        "apps/desktop/src/main/index.ts",
        "apps/desktop/src/preload/index.ts",
    ]
    manifest = {
        "base_commit": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip(),
        "protected_files": {
            path: hashlib.sha256((ROOT / path).read_bytes()).hexdigest() for path in paths
        },
    }
    (DESTINATION / "baseline.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print("적용 전 패치 3개와 공통 파일 기준 해시를 준비했습니다. 실제 파일은 바꾸지 않았습니다.")


if __name__ == "__main__":
    main()
