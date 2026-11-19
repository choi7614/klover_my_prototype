# F1 공통 연결 패치

## 05~07 — 새 메일 자동 분석·받은편지함 분류·요약 표시 (미적용, 2026-11-19)

> F1 기능 브랜치 `feat/F1-mail-analysis` · 기준 develop `d9257c0`(#32 포함) · **아직 적용하지 않았다.** 통합 채팅에서 순서대로 적용한다.
> 기능 브랜치에는 자동 분석 작업자(`app/pipeline/auto_analysis.py`), 분석 완료 알림 지점(`app/pipeline/analysis_hooks.py`),
> F1 표시용 조회·재시도 경로(이미 등록된 F1 라우터에 추가), `MailSyncContext.after_sync` 자리, 앱 화면 부품
> (`renderer/features/mail-analysis/`, F0 받은편지함 연결)이 들어 있다. 아래 패치 없이도 기존 동작은 그대로다
> (자동 분석은 `not_connected`, 앱은 AI 표시 없이 미리보기만).

| 순서 | 패치 | 적용 대상·행동 |
| --- | --- | --- |
| 5 | [05-server-auto-analysis.patch](05-server-auto-analysis.patch) | `app/cli/run_mail_api.py`: `build_auto_analysis(engine, mail_query.session)`로 작업자를 만들어 `app.state.mail_analysis_runner`에 두고, 작업자가 ready(로컬 AI)이면 분석 완료 알림 지점에 F5 `AnalysisScanHook`을 등록, `MailSyncContext(after_sync=analysis_runner.kick)`. `docs/architecture/api.md`에 F1 자동 분석·조회 경로 설명 |
| 6 | [06-generated-api-types.patch](06-generated-api-types.patch) | `pnpm gen:api-types` 결과. 경로 3개(`/mails/analysis/batch`, `/mails/{mail_id}/analysis`, `/mails/{mail_id}/analysis/retry`)와 스키마 6개 **추가만**(기존 스키마 변경 없음) |
| 7 | [07-desktop-analysis-bridge.patch](07-desktop-analysis-bridge.patch) | main `f1-client.ts`·`f1-ipc.ts`(+검사 2개) 새 파일, `main/index.ts` 등록, preload `klover.analysis`(batch·retry만), `renderer/env.d.ts`, 공통 `App`이 `MailboxRoute`에 `analysis` 전달 |

### 적용·검사 (저장소 루트)

```bash
git apply --check patches/F1/05-server-auto-analysis.patch
git apply --check patches/F1/06-generated-api-types.patch
git apply --check patches/F1/07-desktop-analysis-bridge.patch
git apply patches/F1/0{5,6,7}-*.patch
cd apps/server && uv run --locked ruff check . && uv run --locked ruff format --check . && uv run --locked pytest -q
cd ../.. && pnpm gen:api-types && git diff --exit-code packages/api-types   # 06과 같아야 한다
pnpm --filter desktop lint && pnpm --filter desktop typecheck && pnpm --filter desktop test
```

F1 채팅 확인(2026-11-19, develop `d9257c0`을 합친 기능 브랜치에 05~07 적용한 사본, 일회용 PostgreSQL 16 + pgvector):
서버 ruff 통과·pytest 513 통과/28 skip, `gen:api-types` 결과 = 06, 데스크톱 lint·typecheck 통과·test 25개 파일 169개 통과.
05~07은 develop `d9257c0` 자체에도 `git apply --check`가 통과하지만, 05는 이 브랜치의 F1 코드(`build_auto_analysis`)가 필요하므로 **이 브랜치 PR을 develop에 병합한 뒤** 적용한다.

- 05 적용 후에도 `.env`에 `AI_PROVIDER`가 없으면 분석하지 않는다(메일은 pending, 화면은 "AI 연결 전이라 분석을 기다리고 있어요").
  `AI_PROVIDER=claude`이면 실제 Gmail 본문을 보내지 않는다(외부 전송 차단, 화면은 "외부 AI 설정이라…").
- F5 연결은 05에 들어 있다. 다른 기능도 `analysis_runner.hooks.register(콜백)` 한 줄로 붙인다. 계약은
  [F1-handoff.md](../../docs/dev/F1-handoff.md)의 '분석 완료 알림 지점'.

---

## 01~04 — 적용 완료 (기록용)

> 2026-11-19 통합 채팅에서 develop `4725284` 기준으로 01~04를 적용했다(`integrate/F1-F3-patches`, F3 01과 함께). 모두 충돌 없이 적용됐고
> 04는 `pnpm gen:api-types` 재생성 결과와 같았다. 이미 반영된 소스에 다시 적용하지 않는다. 아래는 적용 전 기록이다.

> 2026-11-19 · F1 기능 브랜치 `feat/F1-mail-analysis` · 기준 develop `5971346`
> 이 디렉터리의 패치는 **아직 적용하지 않았다.** 공통 영역은 통합 채팅에서만 적용한다.

F1 브랜치에는 AI 제공자 선택(`app/ai/runtime.py` 등), 분류 수정 등록 함수
(`register_mail_analysis`), 비교용 ORM(`app/db/f1_models.py`), 0007 제안 이력
(`files/0007_f1_analysis.py.pending`)이 들어 있다. 운영 연결은 아래 패치로만 한다.

| 순서 | 패치 | 적용 대상·행동 |
| --- | --- | --- |
| 1 | [01-database.patch](01-database.patch) | `migrations/versions/0007_f1_analysis.py` 추가(revision `0007_f1`, 부모 `0006_f4`), `env.py`·공통 비교 검사 2개가 F5 metadata 대신 F1 metadata(공통·F5 포함)를 보게 함, `data-model.md` 설명 |
| 2 | [02-server-registration.patch](02-server-registration.patch) | `app/main.py`에 `register_mail_analysis` 등록, `run_mail_api.py`에서 엔진 주입, 운영 경로 검사 2개 갱신, `api.md` 설명 |
| 3 | [03-dependencies.patch](03-dependencies.patch) | `pyproject.toml`에 `anthropic>=1,<2` 추가, `uv.lock` 재생성(추가 4개: anthropic 1.17.0·docstring-parser·jiter·sniffio, 기존 버전 변경 없음), `.env.example` AI 항목(값 없음) |
| 4 | [04-generated-api-types.patch](04-generated-api-types.patch) | `pnpm gen:api-types`로 생성한 타입(PATCH `/mails/{mail_id}/category`와 CategoryUpdate/CategoryUpdated 추가만) |

## 적용 전 확인

- progress.md의 마이그레이션 예약 `0007`(부모 `0006_f4`)과 실제 Alembic head가 `0006_f4`인지 확인한다.
  head가 바뀌었으면 `files/0007_f1_analysis.py.pending`의 `down_revision`을 맞추고 01을 다시 만든다.
- 0007은 `integration/F1-mail-analysis/001_storage.sql`과 같은 구조다. 차이: mails의 소유 유일 제약은
  0005의 `uq_mail_f5_owner`를 재사용(중복 제약을 만들지 않음), 모든 제약·인덱스에 이름을 붙임,
  vector 형식·함수는 `public.`으로 지정(검색 경로에 public이 없어도 동작).
- 0007은 `CREATE EXTENSION IF NOT EXISTS vector`를 실행한다. pgvector가 있는 DB(infra의
  `pgvector/pgvector:pg16`)에서 실행한다. downgrade는 F1 테이블만 지운다.
- 02 적용 후 `PATCH /mails/{mail_id}/category`가 운영 앱에 생긴다. 엔진이 없으면 503이다.
- 02와 `patches/F3/01-search-ai-wiring.patch`는 같은 `run_mail_api.py`를 고친다. 서로 다른 줄을
  고치도록 맞춰 두어 어느 순서로 적용해도 된다(2026-11-19 확인).
- 03 적용 전에는 Claude 경로가 "anthropic 패키지 미설치"로 미연결이며, 관련 검사 일부는 skip이다.
- 패치 적용만으로 실제 AI가 켜지지 않는다. `.env`에 `AI_PROVIDER` 등을 설정해야 한다.

## 적용·검사 (저장소 루트)

```bash
git apply --check patches/F1/01-database.patch
git apply --check patches/F1/02-server-registration.patch
git apply --check patches/F1/03-dependencies.patch
git apply --check patches/F1/04-generated-api-types.patch
git apply patches/F1/0{1,2,3,4}-*.patch
cd apps/server && uv sync --locked && uv run --locked ruff check . && uv run --locked ruff format --check .
KLOVER_F1_TEST_DATABASE_URL=<분리된 _test DB> KLOVER_TEST_DATABASE_URL=<분리된 _test DB> uv run --locked pytest -q
cd ../.. && pnpm install --frozen-lockfile && pnpm gen:api-types && git diff --exit-code packages/api-types
pnpm --filter desktop lint && pnpm --filter desktop typecheck && pnpm --filter desktop test
```

F1 채팅의 확인 결과(분리 PostgreSQL 16 + pgvector 일회용 DB, 실제 메일·키 없음):
develop `5971346`에 F1을 합친 상태에서 F1 01~04와 F3 01을 모두 적용한 사본의 서버 pytest
**460 통과·24 skip**, ruff 통과. (이전 기준 `420078e`에서는 서버 440 통과·24 skip,
`pnpm gen:api-types` 재생성 결과 동일, 데스크톱 lint·typecheck 통과·test 133 통과.)
