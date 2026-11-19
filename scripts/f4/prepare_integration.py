"""공통 원본은 수정하지 않고 F4 패치를 임시 복사본에서 준비한다."""
# ruff: noqa: E501

import argparse
import difflib
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "patches/F4"
CHANGES: dict[str, list[str]] = {}


def replace(tree, group, name, before, after):
    file = tree / name
    source = file.read_text()
    if source.count(before) != 1:
        raise RuntimeError(f"최신 공통 파일에서 패치 위치를 확인하세요: {name}")
    file.write_text(source.replace(before, after))
    CHANGES.setdefault(group, []).append(name)


def pending(tree, group, source, name):
    target = tree / name
    if target.exists():
        raise RuntimeError(f"기존 공통 파일을 새 파일로 덮지 않습니다: {name}")
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(OUTPUT / "files" / source, target)
    CHANGES.setdefault(group, []).append(name)


def prepare(tree):
    replace(
        tree,
        "01-server-registration",
        "apps/server/app/main.py",
        "from app.api.search import register_search_api\n",
        "from app.api.search import register_search_api\nfrom app.api.weekly_report import register_weekly_report_api\n",
    )
    replace(
        tree,
        "01-server-registration",
        "apps/server/app/main.py",
        "    register_search_api(application)\n",
        "    register_search_api(application)\n    register_weekly_report_api(application)\n",
    )
    replace(
        tree,
        "01-server-registration",
        "apps/server/app/cli/run_mail_api.py",
        "from app.services.search import SearchService\n",
        "from app.services.search import SearchService\nfrom app.services.weekly_report_runtime import WeeklyReportRuntime\n",
    )
    replace(
        tree,
        "01-server-registration",
        "apps/server/app/cli/run_mail_api.py",
        "        application.state.profile_draft = F2Context(F2Repository(engine))\n",
        "        application.state.profile_draft = F2Context(F2Repository(engine))\n        application.state.weekly_reports = WeeklyReportRuntime(engine)\n",
    )
    replace(
        tree,
        "01-server-registration",
        "apps/server/tests/test_weekly_report.py",
        'def test_production_main_routes_are_unchanged():\n    assert all(not path.startswith("/reports/") for path in create_app().openapi()["paths"])',
        'def test_production_main_routes_register_f4():\n    paths = create_app().openapi()["paths"]\n    assert "/reports/weekly" in paths and "/reports/weekly/options" in paths',
    )
    replace(
        tree,
        "01-server-registration",
        "apps/server/tests/test_http_server.py",
        '        "/profile/style",\n        "/search",',
        '        "/profile/style",\n        "/reports/weekly",\n        "/reports/weekly/options",\n        "/reports/weekly/{report_id}",\n        "/reports/weekly/{report_id}/excluded",\n        "/search",',
    )

    replace(
        tree,
        "02-report-storage",
        "apps/server/app/db/models.py",
        "    Index,\n",
        "    Index,\n    Integer,\n",
    )
    file = tree / "apps/server/app/db/models.py"
    file.write_text(
        file.read_text()
        + '''\n\nclass WeeklyReportRow(Base):
    """F4 보고서. 소유 계정은 검증된 payload와 선택 키에 함께 저장한다."""

    __tablename__ = "weekly_reports"
    __table_args__ = (
        UniqueConstraint("user_id", "selection_key", name="uq_weekly_report_owner_selection"),
    )

    report_id: Mapped[str] = mapped_column(Text, primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.user_id"), nullable=False)
    selection_key: Mapped[str] = mapped_column(Text, nullable=False)
    revision: Mapped[int] = mapped_column(Integer, nullable=False)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
'''
    )
    pending(
        tree,
        "02-report-storage",
        "0006_weekly_reports.py.pending",
        "apps/server/migrations/versions/0006_weekly_reports.py",
    )

    for template, target in (
        ("f4-bridge.ts.pending", "apps/desktop/src/shared/f4-bridge.ts"),
        ("f4-client.ts.pending", "apps/desktop/src/main/f4-client.ts"),
        ("f4-client.test.ts.pending", "apps/desktop/src/main/f4-client.test.ts"),
        ("f4-ipc.ts.pending", "apps/desktop/src/main/f4-ipc.ts"),
        ("f4-ipc.test.ts.pending", "apps/desktop/src/main/f4-ipc.test.ts"),
    ):
        pending(tree, "03-screen-ipc", template, target)
    replace(
        tree,
        "03-screen-ipc",
        "apps/desktop/src/main/index.ts",
        "import { F2APIClient } from './f2-client';\n",
        "import { F2APIClient } from './f2-client';\nimport { F4APIClient } from './f4-client';\nimport { registerF4IPC } from './f4-ipc';\n",
    )
    replace(
        tree,
        "03-screen-ipc",
        "apps/desktop/src/main/index.ts",
        "  window.once('closed', () => { unregister(); unregisterF2(); unregisterSearch(); });",
        "  const unregisterF4 = registerF4IPC(ipcMain, window.webContents, rendererURL, new F4APIClient(configuration));\n  window.once('closed', () => { unregister(); unregisterF2(); unregisterSearch(); unregisterF4(); });",
    )
    replace(
        tree,
        "03-screen-ipc",
        "apps/desktop/src/preload/index.ts",
        "import type { F2Bridge } from '../shared/f2-bridge';\n",
        "import type { F2Bridge } from '../shared/f2-bridge';\nimport type { F4Bridge } from '../shared/f4-bridge';\n",
    )
    replace(
        tree,
        "03-screen-ipc",
        "apps/desktop/src/preload/index.ts",
        "contextBridge.exposeInMainWorld('klover', Object.freeze({ platform: process.platform, mail, f2, search }));",
        """const weeklyReport = Object.freeze<F4Bridge>({
  options: () => ipcRenderer.invoke('klover:weekly-report:options'),
  generate: request => ipcRenderer.invoke('klover:weekly-report:generate', request),
  get: id => ipcRenderer.invoke('klover:weekly-report:get', id),
  excluded: id => ipcRenderer.invoke('klover:weekly-report:excluded', id),
  save: (id, revision, sections) => ipcRenderer.invoke('klover:weekly-report:save', id, revision, sections),
});
contextBridge.exposeInMainWorld('klover', Object.freeze({ platform: process.platform, mail, f2, search, weeklyReport }));""",
    )
    replace(
        tree,
        "03-screen-ipc",
        "apps/desktop/src/renderer/env.d.ts",
        "    f2?: import('../shared/f2-bridge').F2Bridge;\n",
        "    f2?: import('../shared/f2-bridge').F2Bridge;\n    weeklyReport?: import('../shared/f4-bridge').F4Bridge;\n",
    )
    replace(
        tree,
        "03-screen-ipc",
        "apps/desktop/src/renderer/app.tsx",
        "import { createSearchIPCClient } from './bridges/search-ipc-client';\n",
        "import { createSearchIPCClient } from './bridges/search-ipc-client';\nimport { WeeklyReportPage } from './features/weekly-report/weekly-report-page';\nimport { createWeeklyReportIPCClient, unavailableWeeklyReportClient } from './features/weekly-report/ipc-client';\n",
    )
    replace(
        tree,
        "03-screen-ipc",
        "apps/desktop/src/renderer/app.tsx",
        "  const searchBridge = window.klover?.search;\n",
        "  const searchBridge = window.klover?.search;\n  const weeklyReportBridge = window.klover?.weeklyReport;\n  const weeklyReport = useMemo(() => weeklyReportBridge ? createWeeklyReportIPCClient(weeklyReportBridge) : unavailableWeeklyReportClient, [weeklyReportBridge]);\n",
    )
    replace(
        tree,
        "03-screen-ipc",
        "apps/desktop/src/renderer/app.tsx",
        '        {session && <Route path="/search" element={<SearchRoute client={search} session={session} />} />}\n',
        '        {session && <Route path="/search" element={<SearchRoute client={search} session={session} />} />}\n        {session && <Route path="/report/weekly" element={<WeeklyReportPage key={session.account_id} client={weeklyReport} />} />}\n',
    )
    replace(
        tree,
        "03-screen-ipc",
        "apps/desktop/src/renderer/features/mailbox/mailbox-page.tsx",
        '          <a href="#/settings/profile" className="mt-auto',
        '          <a href="#/report/weekly" className="mt-auto rounded-md px-3 py-2 text-body text-foreground hover:bg-accent focus-visible:outline-ring">주간 보고</a>\n          <a href="#/settings/profile" className="mt-2',
    )

    for name in ("docs/architecture/api.md", "docs/architecture/data-model.md"):
        file = tree / name
        if name.endswith("api.md"):
            addition = """\n## F4 주간 보고 (공통 패치 적용 후)\n\n기존 로컬 Bearer·Origin·연결 계정 검사를 그대로 사용한다.\n`GET /reports/weekly/options`, `POST /reports/weekly`, `GET /reports/weekly/{id}`,\n`GET /reports/weekly/{id}/excluded`, `PATCH /reports/weekly/{id}`를 등록한다.\n프로필은 F2, 메일 입력은 F1, AI는 공통 TextGeneration을 사용한다. 실제 제공자가 없으면\n503으로 종료하며 대역으로 대체하지 않는다. 운영 서비스는 run_mail_api에서 조립한다.\n사용자·계정은 요청 본문에서 받지 않고, 편집은 expected_revision과 근거를 검증한다.\n일정 예약·내보내기·발송 경로는 추가하지 않는다.\n"""
        else:
            addition = """\n## F4 보고서 저장소 (공통 패치 적용 후)\n\n`weekly_reports`: report_id(PK), user_id(FK), selection_key, revision, payload(JSONB).\n(user_id, selection_key)는 유일하다. payload에는 account_id·프로필·대상 메일 스냅샷·\n검증된 문서를 보관하며 저장 버전을 비교해 갱신한다. 조회·편집 때 사용자와 계정을\n다시 확인한다. 기존 사용자·메일·계정·키·수신 커서는 수정하지 않는다.\n신규 이력은 0006_f4, 현재 down_revision은 0005_f5다. 통합 직전 head가 바뀌면\n예약 번호와 down_revision을 다시 확인해야 한다. 기존 이력은 수정하지 않는다.\n"""
        file.write_text(file.read_text() + addition)
        CHANGES.setdefault("05-shared-documents", []).append(name)


def main():
    parser = argparse.ArgumentParser(description="F4 공통 원본 보존형 패치 생성")
    parser.add_argument("--validation-dir", type=Path, help="없던 경로에 제안 합본을 남겨 검사")
    args = parser.parse_args()
    names = set(subprocess.check_output(["git", "ls-files"], cwd=ROOT, text=True).splitlines())
    names.update(
        subprocess.check_output(
            ["git", "ls-files", "--others", "--exclude-standard"], cwd=ROOT, text=True
        ).splitlines()
    )
    with tempfile.TemporaryDirectory(prefix="klover-f4-proposals-") as temporary:
        tree = Path(temporary)
        for name in names:
            if name.startswith("patches/F4/") and not name.startswith("patches/F4/files/"):
                continue
            source = ROOT / name
            if source.is_file() and not source.is_symlink():
                target = tree / name
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source, target)
        prepare(tree)
        python_changes = sorted(
            {
                name
                for paths in CHANGES.values()
                for name in paths
                if name.startswith("apps/server/") and name.endswith(".py")
            }
        )
        subprocess.run(
            [sys.executable, "-m", "ruff", "format", *python_changes],
            cwd=tree,
            check=True,
        )
        openapi = tree / "packages/api-types/openapi.json"
        subprocess.run(
            [sys.executable, "-m", "app.cli.export_openapi", "--output", str(openapi)],
            cwd=tree / "apps/server",
            check=True,
        )
        executable = ROOT / "packages/api-types/node_modules/.bin/openapi-typescript"
        schema = tree / "packages/api-types/src/schema.d.ts"
        subprocess.run([str(executable), str(openapi), "-o", str(schema)], check=True)
        CHANGES["04-generated-api-types"] = [
            "packages/api-types/openapi.json",
            "packages/api-types/src/schema.d.ts",
        ]
        baseline = {}
        for group, paths in CHANGES.items():
            parts = []
            for name in dict.fromkeys(paths):
                before = (ROOT / name).read_text() if (ROOT / name).exists() else ""
                after = (tree / name).read_text()
                baseline[name] = hashlib.sha256(before.encode()).hexdigest() if before else None
                parts.extend(
                    difflib.unified_diff(
                        before.splitlines(keepends=True),
                        after.splitlines(keepends=True),
                        fromfile="a/" + name if before else "/dev/null",
                        tofile="b/" + name,
                    )
                )
            patch = OUTPUT / (group + ".patch")
            patch.write_text("".join(parts))
            subprocess.run(["git", "apply", "--check", str(patch)], cwd=ROOT, check=True)
        (OUTPUT / "baseline.json").write_text(
            json.dumps(
                {
                    "develop": subprocess.check_output(
                        ["git", "rev-parse", "origin/develop"], cwd=ROOT, text=True
                    ).strip(),
                    "sha256": baseline,
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n"
        )
        if args.validation_dir:
            if args.validation_dir.exists():
                raise SystemExit("검사 경로가 이미 있습니다. 기존 파일은 덮지 않습니다.")
            shutil.copytree(tree, args.validation_dir)
    print("F4 패치 5개 생성·적용 가능성 확인 완료. 공통 원본은 변경하지 않았습니다.")


if __name__ == "__main__":
    main()
