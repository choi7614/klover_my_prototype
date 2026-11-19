# F1 공통 연결 패치 — 적용 전 (통합 채팅용)

> 2026-11-19 · F1 기능 브랜치 `feat/F1-mail-analysis` · 기준 develop `420078e`
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
네 패치를 모두 적용한 사본에서 서버 pytest **440 통과·24 skip**, ruff 통과,
`pnpm gen:api-types` 재생성 결과 동일, 데스크톱 lint·typecheck 통과·test 133 통과.
