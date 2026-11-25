# 작업 방식 (1인 개발 + Codex·Claude)

> 최종 수정: 2026-11-19

규칙의 기준은 루트 [AGENTS.md](../../AGENTS.md) 하나다. 이 문서는 실제 작업 흐름을 쉽게 풀어 쓴 안내이며,
AGENTS.md와 다르면 AGENTS.md를 따른다.

## 1. 운영 방식

한 사람이 GPT Codex와 Claude Code를 번갈아 쓰며 개발한다. 채팅은 세 종류로 나눈다.

| 채팅 | 맡는 일 | 주로 바꾸는 곳 | 브랜치 |
| --- | --- | --- | --- |
| 기능별 채팅 (F0~F5) | 한 기능을 서버부터 화면까지 | 기능 전용 파일, `docs/dev/Fn-*` | `feat/Fn-이름` |
| 공통 채팅 | 규칙·개발 문서·CI | `AGENTS.md`, `CLAUDE.md`, `docs/dev/`, `.github/` | `chore/...`, `docs/...` |
| 통합 채팅 | 공통 영역 적용·기능 연결·develop 병합 전 검사 | DB 모델·마이그레이션, `main.py` 등록, api-types, 공통 앱 골격, 잠금 파일 | `integrate/...` |

한 채팅에서는 한 가지 일만 한다. 기능이 바뀌면 새 채팅을 연다.
현재 누가(어느 도구가) 어느 브랜치를 쓰는지는 [progress.md](progress.md) 현황판에서 확인한다.

## 2. 기능 하나를 만드는 순서

1. 기능 정의서(`docs/product/features/Fn-*.md`)를 읽고, 빠진 내용을 먼저 채운다. 말로 정한 것도 MD에 먼저 적는다.
2. 기능별 채팅에서 "정의서를 읽고 구현 계획을 세워줘"로 시작한다. 큰 작업은 계획을 먼저 받고 검토한 뒤 승인한다.
3. 작은 단위로 구현 → 정의서의 **수용 기준** 체크리스트를 하나씩 확인한다.
4. 공통 영역 변경이 필요하면 직접 고치지 않고 `patches/Fn/`(또는 `integration/Fn-*/`)에 적용 전 패치를 남기고
   status 문서의 '공통 영역 요청'에 적는다. 마이그레이션 번호는 progress.md에서 예약한다.
5. 바뀐 결정은 정의서와 `decisions.md`에 반영한다.
6. status 문서([양식](status-template.md))와 progress.md를 갱신하고, 변경·검사 결과를 한 번 보고해 묶음 승인을 받은 뒤 PR을 올린다.
7. 통합 채팅에서 공통 패치를 적용하고 develop 병합 승인을 따로 받는다.

## 3. Codex ↔ Claude 전환

- 넘기기 전: 커밋·Push, status 문서·progress.md 갱신. 미커밋 파일을 남기지 않는다.
- 한도로 끊길 것 같으면: 기능 브랜치에 `[WIP] 인수인계` 커밋·Push(사전 승인된 예외).
- 이어받을 때: fetch → progress.md → status 문서 → 미커밋/WIP 확인. 다른 도구가 작업 중인 브랜치는 손대지 않고 확인한다.
- 붙여 쓸 프롬프트: [handoff-prompts.md](handoff-prompts.md)

## 4. Git 규칙

- 통합 순서: 작업 브랜치 → `develop`(통합·검사) → `main`(검증된 안정 버전). `main`·`develop`에 직접 커밋·Push하지 않고 PR로 반영한다.
- 브랜치 이름: `feat/F3-search`, `fix/F1-category-retry`, `docs/F2-profile`, `chore/agent-guidelines`
- 커밋 메시지: `[F3] 검색 칩 삭제 시 재검색` 처럼 기능 번호로 시작 (공통 작업은 `[공통]`, 긴급 저장은 `[F3][WIP] 인수인계: ...`)
- PR은 작게 (하루 분량). PR 설명에 관련 기능 번호와 확인한 수용 기준을 적는다.
- 승인: 작업 단위마다 한 번 보고 → **로컬 통합·커밋·Push·PR 생성 묶음 승인**. **`develop` 병합과 `main` 병합은 각각 별도 승인.**
- 기존 작업과 브랜치를 보존한다. 강제 Push·기존 작업 삭제는 별도 명시적 승인 없이 실행하지 않는다.
- PR마다 GitHub Actions가 서버 ruff·pytest, 데스크톱 lint·typecheck·test를 실행한다(실제 DB가 필요한 검사는 skip).
  1인 개발이므로 사람 리뷰 대신 CI 통과와 사용자 승인으로 병합을 결정한다.

## 5. 공통 영역 (통합 채팅에서만 수정)

- `apps/server/app/db/models.py`, `apps/server/migrations/`, `docs/architecture/data-model.md`
- `apps/server/app/main.py` 라우터 등록, 실행 명령의 저장소 조립
- `packages/api-types/` (재생성만), `docs/architecture/api.md`의 공통 형식
- `apps/desktop/src/main`·`preload`, 공통 App·라우터, `renderer/components/`, `renderer/styles/`, `docs/design/design-system.md`
- `pnpm-lock.yaml`, `apps/server/uv.lock`
- 규칙 문서(`AGENTS.md`, `CLAUDE.md`, `docs/dev/` 공통 문서)는 공통 채팅에서 수정한다.

## 6. AI 도구 사용 요령

- 새 대화를 시작하면 Codex는 `AGENTS.md`를, Claude는 `CLAUDE.md`(→ `AGENTS.md` 불러옴)를 자동으로 읽는다.
  **같은 지적을 두 번 했다면 `AGENTS.md`에 규칙으로 추가**한다(공통 채팅).
- 화면 작업 때는 화면 정의서와 목업을 함께 알려 준다: "`docs/design/screens/S07-search.md`를 읽고 `mockups/png/S07-search.png`처럼 만들어줘. 색·크기는 `design-system.md`를 따라."
- 프롬프트(LLM에 보내는 지시문)는 코드가 아니라 `apps/server/app/ai/prompts/*.md`에 둔다.
- API 키·실제 메일 내용을 대화창에 붙여 넣지 않는다. 테스트는 fixture 메일로 한다.
