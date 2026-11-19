"""새 임시 복사본·명시한 로컬 테스트 DB에서만 F5 적용 전 패치를 검사한다."""

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from sqlalchemy.engine import make_url

ROOT = Path(__file__).resolve().parents[2]


def main():
    parser = argparse.ArgumentParser(description="F5 적용 전 패치 분리 검사")
    parser.add_argument("--database-url", required=True)
    args = parser.parse_args()
    url = make_url(args.database_url)
    if url.host not in {"127.0.0.1", "localhost"} or url.database != "klover_f5_test":
        parser.error("로컬 전용 klover_f5_test DB만 허용합니다")
    scratch = Path(tempfile.mkdtemp(prefix="klover-f5-verify-"))
    ignored = shutil.ignore_patterns(
        ".venv", "node_modules", "__pycache__", ".pytest_cache", ".ruff_cache", "*.pyc"
    )
    for relative in [
        "apps/server",
        "fixtures",
        "packages/api-types",
        "docs/architecture",
        "patches",
        "integration",
    ]:
        shutil.copytree(ROOT / relative, scratch / relative, ignore=ignored)
    for patch in ["0001-server-and-schema.patch", "0002-generated-api-types.patch"]:
        source = ROOT / "docs/dev/f5-patches" / patch
        applied = (
            subprocess.run(
                ["git", "apply", "--reverse", "--check", str(source)],
                cwd=scratch,
                capture_output=True,
                check=False,
            ).returncode
            == 0
        )
        if not applied:
            subprocess.run(["git", "apply", "--check", str(source)], cwd=scratch, check=True)
            subprocess.run(["git", "apply", str(source)], cwd=scratch, check=True)
    env = {
        **os.environ,
        "KLOVER_F5_TEST_DATABASE_URL": args.database_url,
        "KLOVER_TEST_DATABASE_URL": args.database_url,
        "KLOVER_F1_TEST_DATABASE_URL": args.database_url,
    }
    env.pop("DATABASE_URL", None)
    server = scratch / "apps/server"
    subprocess.run([sys.executable, "-m", "pytest", "-q"], cwd=server, env=env, check=True)
    subprocess.run([sys.executable, "-c", MIGRATION_CHECK], cwd=server, env=env, check=True)
    exported = scratch / "exported-openapi.json"
    subprocess.run(
        [sys.executable, "-m", "app.cli.export_openapi", "--output", str(exported)],
        cwd=server,
        env=env,
        check=True,
    )
    assert json.loads(exported.read_text()) == json.loads(
        (scratch / "packages/api-types/openapi.json").read_text()
    ), "공유 OpenAPI 패치와 앱의 계약이 다릅니다"
    print(
        json.dumps(
            {
                "patches": "ok",
                "migration_preservation": "ok",
                "openapi": "ok",
                "scratch": str(scratch),
            },
            ensure_ascii=False,
        )
    )


MIGRATION_CHECK = """
import os,sys
from pathlib import Path
from uuid import uuid4
from sqlalchemy import create_engine, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session
from alembic import command
from alembic.config import Config
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from app.db.models import GoogleCredential, Mail, MailAccount
from app.db.f2_models import F2Base, ProfileRecord
from app.db.repositories.mail import MailRepository
from app.db.repositories.f5 import F5Repository
from app.db.repositories.f5_schema import F5Base
from app.db.repositories.search_recent import search_metadata, search_runs
from app.services.f5 import F5Service
sys.path.insert(0, str(Path.cwd() / 'tests'))
from f5.helpers import OWNER, START, BODY, analysis

raw = make_url(os.environ['KLOVER_F5_TEST_DATABASE_URL'])
schema = 'f5_verify_' + uuid4().hex
admin = create_engine(raw, hide_parameters=True)
with admin.begin() as c:
    c.execute(text(f'CREATE SCHEMA "{schema}"'))
url = raw.update_query_dict({'options': '-csearch_path=' + schema})
os.environ['DATABASE_URL'] = url.render_as_string(hide_password=False)
engine = create_engine(url, hide_parameters=True)
config = Config('alembic.ini')
try:
    command.upgrade(config, '0004_f2')
    with Session(engine) as session, session.begin():
        repo = MailRepository(session)
        repo.add_user(user_id=OWNER.user_id)
        repo.add_account(user_id=OWNER.user_id, account_id=OWNER.account_id,
                         source='fixture', email='fixture@example.invalid', sync_started_at=START)
        repo.store_received(user_id=OWNER.user_id, account_id=OWNER.account_id,
                            mail_id='f5-mail', source_message_id='synthetic-source',
                            received_at=START, from_addr='sender@example.invalid',
                            subject='보존할 합성 메일', body_text=BODY)
        account = session.get(MailAccount, OWNER.account_id)
        account.sync_cursor = 'synthetic-original-cursor'
        session.add(GoogleCredential(account_id=OWNER.account_id,
                    token_ciphertext='synthetic-original-ciphertext', updated_at=START))
        session.add(ProfileRecord(
            user_id=OWNER.user_id, name='보존할 합성 프로필', title='', org='', duties='',
            frequent_contacts=[], formality=50, reply_length='normal', greeting='', closing='',
            signature='', style_learning_enabled=False, excluded_phrases=[], report_sections=[],
            report_recipient='', report_style='bullet', version=1,
        ))
        session.execute(search_runs.insert().values(
            search_id='synthetic-search', user_id=OWNER.user_id, account_id=OWNER.account_id,
            query='보존할 합성 검색', parsed={}, overrides={}, reference_date='2026-11-19',
            created_at=START,
        ))
    def unchanged():
        with Session(engine) as session:
            assert session.get(Mail, 'f5-mail').body_text == BODY
            account = session.get(MailAccount, OWNER.account_id)
            credential = session.get(GoogleCredential, OWNER.account_id)
            assert account.sync_cursor == 'synthetic-original-cursor'
            assert credential.token_ciphertext == 'synthetic-original-ciphertext'
            assert session.get(ProfileRecord, OWNER.user_id).name == '보존할 합성 프로필'
            query = select(search_runs.c.query).where(search_runs.c.search_id == 'synthetic-search')
            assert session.scalar(query) == '보존할 합성 검색'
    command.upgrade(config, 'head')
    command.upgrade(config, 'head')
    unchanged()
    with engine.connect() as c:
        target = [F5Base.metadata, search_metadata, F2Base.metadata]
        assert compare_metadata(MigrationContext.configure(c), target) == []
    service = F5Service(F5Repository(engine))
    assert len(service.scan(OWNER, analysis()).created_ids) == 3
    command.downgrade(config, '0004_f2')
    unchanged()
    command.upgrade(config, 'head')
    unchanged()
    with engine.connect() as c:
        target = [F5Base.metadata, search_metadata, F2Base.metadata]
        assert compare_metadata(MigrationContext.configure(c), target) == []
    assert F5Repository(engine).list(OWNER).items == []
finally:
    engine.dispose()
    with admin.begin() as c:
        c.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
    admin.dispose()
"""


if __name__ == "__main__":
    main()
