"""공통 파일을 쓰지 않고 검토용 패치만 만든다. 적용·커밋·외부 전송은 하지 않는다."""

import argparse
import ast
import difflib
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "patches/F2"


def diff(path: str, after: str, *, new=False) -> str:
    before = "" if new else (ROOT / path).read_text(encoding="utf-8")
    return "".join(
        difflib.unified_diff(
            before.splitlines(keepends=True),
            after.splitlines(keepends=True),
            fromfile="/dev/null" if new else f"a/{path}",
            tofile=f"b/{path}",
        )
    )


def python_source(text: str, path: str) -> str:
    ast.parse(text, filename=path)
    ruff = ROOT / "apps/server/.venv/bin/ruff"
    for arguments in [
        ["check", "--select", "I", "--fix", "--stdin-filename", path, "-"],
        ["format", "--stdin-filename", path, "-"],
    ]:
        result = subprocess.run(
            [str(ruff), *arguments], input=text, capture_output=True, text=True, check=True
        )
        text = result.stdout
    return text


def main():
    parser = argparse.ArgumentParser(description="F2 적용 전 패치 생성")
    parser.add_argument("--openapi", type=Path, required=True)
    parser.add_argument("--types", type=Path, required=True)
    args = parser.parse_args()
    OUTPUT.mkdir(parents=True, exist_ok=True)

    env_path = "apps/server/migrations/env.py"
    env = (ROOT / env_path).read_text(encoding="utf-8")
    env = env.replace(
        "from app.db.models import Base",
        "from app.db.f2_models import F2Base\nfrom app.db.models import Base",
    )
    env = env.replace(
        "target_metadata=[Base.metadata, search_metadata]",
        "target_metadata=[Base.metadata, search_metadata, F2Base.metadata]",
    )
    migration = (OUTPUT / "files/0004_profile_draft.py.pending").read_text(encoding="utf-8")
    (OUTPUT / "01-database.patch").write_text(
        diff(env_path, python_source(env, env_path))
        + diff("apps/server/migrations/versions/0004_profile_draft.py", migration, new=True),
        encoding="utf-8",
    )

    main_path = "apps/server/app/main.py"
    main = (ROOT / main_path).read_text(encoding="utf-8")
    main = main.replace(
        "from app.schemas.common import ErrorResponse",
        "from app.api.profile_draft import register_profile_draft\nfrom app.schemas.common import ErrorResponse",
    )
    main = main.replace(
        "    register_mail_api(application)",
        "    register_mail_api(application)\n    register_profile_draft(application)",
    )
    runner_path = "apps/server/app/cli/run_mail_api.py"
    runner = (ROOT / runner_path).read_text(encoding="utf-8")
    runner = runner.replace(
        "from app.db.config import",
        "from app.api.profile_draft import F2Context\nfrom app.db.repositories.profile_draft import F2Repository\nfrom app.db.config import",
    )
    runner = runner.replace(
        '        print(f"메일 조회 API 실행:',
        '        application.state.profile_draft = F2Context(F2Repository(engine))\n        print(f"메일 조회 API 실행:',
    )
    common_test_path = "apps/server/tests/test_http_server.py"
    common_test = (ROOT / common_test_path).read_text(encoding="utf-8")
    # 이미 통합된 F3 등 기존 경로를 보존하고 F2 경로만 기대 목록에 더한다.
    for node in ast.walk(ast.parse(common_test)):
        if (
            isinstance(node, ast.Assert)
            and isinstance(node.test, ast.Compare)
            and ast.unparse(node.test.left) == "set(schema['paths'])"
            and isinstance(node.test.comparators[0], ast.Set)
        ):
            paths = ast.literal_eval(node.test.comparators[0]) | {
                "/profile",
                "/profile/style",
                "/profile/preview",
                "/drafts",
                "/drafts/{draft_id}",
                "/drafts/{draft_id}/revise",
            }
            lines = common_test.splitlines(keepends=True)
            lines[node.lineno - 1 : node.end_lineno] = [
                '    assert set(schema["paths"]) == {'
                + ", ".join(repr(path) for path in sorted(paths))
                + "}\n"
            ]
            common_test = "".join(lines)
            break
    else:
        raise SystemExit("공통 OpenAPI 검사 형식이 바뀌었습니다. 먼저 검토하세요.")
    (OUTPUT / "02-server-registration.patch").write_text(
        diff(main_path, python_source(main, main_path))
        + diff(runner_path, python_source(runner, runner_path))
        + diff(common_test_path, python_source(common_test, common_test_path)),
        encoding="utf-8",
    )

    app_path = "apps/desktop/src/renderer/app.tsx"
    app = (ROOT / app_path).read_text(encoding="utf-8")
    app = app.replace(
        "export function App()",
        "export function App({ f2Client = unavailableF2Client, mailboxPath = '/onboarding/1' }: { f2Client?: F2Client; mailboxPath?: string } = {})",
    )
    app = app.replace(
        "\nexport function App",
        "\nimport { F2ProfileRoute, F2ReplyRoute, unavailableF2Client, type F2Client } from './features/profile-draft';\n\nexport function App",
    )
    app = app.replace(
        "      <Routes>",
        '      <Routes>\n        <Route path="/settings/profile" element={<F2ProfileRoute client={f2Client} mailboxPath={mailboxPath} />} />\n        <Route path="/reply/:mailId" element={<F2ReplyRoute client={f2Client} mailboxPath={mailboxPath} />} />',
    )
    (OUTPUT / "03-screen-routes.patch").write_text(diff(app_path, app), encoding="utf-8")

    (OUTPUT / "04-generated-api-types.patch").write_text(
        diff("packages/api-types/openapi.json", args.openapi.read_text(encoding="utf-8"))
        + diff("packages/api-types/src/schema.d.ts", args.types.read_text(encoding="utf-8")),
        encoding="utf-8",
    )

    api_note = """\n## F2 등록 후의 API (승인 전 패치)\n\nF2 router와 F2Context를 등록하고 0004_f2 마이그레이션을 적용한 경우에만 사용한다.\nGET/PUT /profile, GET/DELETE /profile/style, POST /profile/preview, POST /drafts,\nGET/PATCH /drafts/{draft_id}, POST /drafts/{draft_id}/revise.\n인증·Origin 제한은 기존 로컬 메일 조회 API를 그대로 따른다. 발송 API는 추가하지 않는다.\nAI 미연결은 503 ai_unavailable이며 합성 결과로 대체하지 않는다.\n입력·출력·버전·동의·오류 계약은 [F2 구현 안내](../dev/F2-profile-draft.md)를 따른다.\n"""
    data_note = """\n## F2 저장 구조 (승인 전 패치)\n\n0004_f2는 profiles/style_learnings/drafts만 추가한다. 기존 테이블·행·키는 바꾸지 않는다.\n모델은 app.db.f2_models의 별도 F2Base.metadata이며 공통 Base.metadata와 함께 검사한다.\nprofiles는 위 설계의 필드와 excluded_phrases(jsonb), version(int>=1)을 저장한다.\nstyle_learnings는 user_id(PK/FK), payload(jsonb: status/analyzed_count/phrases/traits)를 저장한다.\n실제 학습 수집·쓰기 작업자는 아직 없다. drafts는 draft_id(PK), user_id(FK·인덱스),\npayload(jsonb: DraftState 전체), version(int>=1)을 저장한다. 사용자·버전 조건으로 갱신한다.\n학습 기록 삭제는 해당 사용자 기록을 지우고 학습 동의를 끄며 프로필 버전을 올린다.\n세부 계약과 F4 읽기 포트는 [F2 구현 안내](../dev/F2-profile-draft.md)를 따른다.\n"""
    docs = ""
    for path, note in [
        ("docs/architecture/api.md", api_note),
        ("docs/architecture/data-model.md", data_note),
    ]:
        docs += diff(path, (ROOT / path).read_text(encoding="utf-8") + note)
    (OUTPUT / "05-shared-documents.patch").write_text(docs, encoding="utf-8")
    print("F2 검토용 패치 5개 생성. 공통 파일에는 적용하지 않았습니다.")


if __name__ == "__main__":
    main()
