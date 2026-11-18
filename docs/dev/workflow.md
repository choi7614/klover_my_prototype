# 작업 방식 (4명 + Claude Code)

> 최종 수정: 2026-11-18

## 1. 역할 분담 (기능 단위)

한 사람이 맡은 기능을 **서버부터 화면까지** 끝까지 만든다.

| 담당 | 맡는 기능 | 주로 작업하는 폴더 |
| --- | --- | --- |
| A | 앱 뼈대 + F0 (첫 실행, 받은편지함·작성·보관·삭제), 트레이·알림, 디자인 시스템 | `apps/desktop/src/main`, `renderer/features/mailbox·onboarding`, `renderer/styles`, `renderer/components` |
| B | 서버 뼈대 + Gmail 커넥터, 수신 동기화, DB 스키마, 메일 API | `apps/server/app/connectors`, `pipeline/ingest`, `db/`, `api/mails`, `infra/` |
| C | F1 분류·메타데이터·임베딩 + F5 AI 스캔·일정 제안·Google Calendar | `pipeline/analyze·scan·embed`, `ai/`, `services/calendar`, `renderer/features/suggestions` |
| D | F2 프로필·문체·답장 초안 + F3 검색 + F4 주간 보고 | `services/`, `renderer/features/compose·search·weekly-report·settings` |

D의 분량이 가장 많으므로, F0가 끝나면 A가 F4 화면을 나눠 맡는다.

## 2. 시작 순서

1. **뼈대 (함께)** — 한 명이 폴더 구조·Docker Compose·앱/서버 빈 프로젝트를 만든다. 나머지는 기능 정의서를 검토하고, `data-model.md`를 4명이 함께 확정한다.
2. **연결 확인** — fixture 메일 1건이 서버에 들어와 분석되고, 앱 받은편지함에 카테고리 태그와 함께 보이면 통과.
3. **기능 병렬 개발** — 각자 기능 브랜치에서 진행.
4. **실제 Gmail 연결** — 테스트 Gmail 계정으로 전체 흐름 확인.
5. **데모 리허설** — 홍길동 과장 시나리오(설계안 예시 메일)를 따라가며 점검.

## 3. 기능 하나를 만드는 순서

1. 기능 정의서(`docs/product/features/Fn-*.md`)를 읽고, 빠진 내용을 먼저 채운다. 말로 정한 것도 MD에 먼저 적는다.
2. Claude Code에 요청: "`docs/product/features/F3-search.md`를 읽고 구현 계획을 세워줘" → 큰 작업은 **Plan mode**로 계획을 받고 검토한 뒤 승인한다.
3. 구현 → 정의서의 **수용 기준** 체크리스트를 하나씩 확인한다.
4. 구현하면서 바뀐 결정은 정의서와 `decisions.md`에 반영한다.
5. 변경 내용·검사 결과를 한 번 보고하고, 아래 Git 규칙에 따라 묶음 승인을 받은 뒤 PR을 올린다.

## 4. Git 규칙

- 통합 순서: 기능 작업 브랜치 → `develop`(통합·검사) → `main`(검증된 안정 버전). `main`·`develop`에 직접 커밋·Push하지 않고 PR로 반영한다.
- 브랜치 이름: `feat/F3-search`, `fix/F1-category-retry`, `docs/F2-profile`
- 커밋 메시지: `[F3] 검색 칩 삭제 시 재검색` 처럼 기능 번호로 시작
- PR은 작게 (하루 분량). PR 설명에 관련 기능 번호와 확인한 수용 기준을 적는다.
- 이 프로젝트의 모든 기능 채팅은 [공통 지침](../../AGENTS.md)의 승인 절차를 따른다. 작업 단위마다 변경 내용·파일·검사 결과·대상 브랜치를 한 번 보고한 뒤 **로컬 통합·커밋·Push·PR 생성을 묶어서 한 번 승인받는다**. 로컬 통합이 있으면 가져올 브랜치와 적용할 작업 브랜치도 보고한다. 승인된 범위 안에서는 단계별로 다시 묻지 않는다.
- **`develop` 병합과 `main` 병합은 각각 별도 승인받는다**. 위 묶음은 기능 작업 브랜치에서의 로컬 통합까지만 포함한다. 승인 절차 변경 자체는 개별 작업의 실행 승인이 아니며, 사용자가 제한한 승인 범위를 따른다.
- 기존 작업과 브랜치를 보존한다. 강제 Push·기존 작업 삭제는 별도 명시적 승인 없이 실행하지 않는다.
- 리뷰: 1명 이상 승인 후 병합

## 5. 공유 영역 (충돌 주의)

아래 파일을 바꾸는 PR은 **팀 채널에 먼저 알리고**, 담당 외 1명 이상 리뷰를 받는다.

- `apps/server/app/db/models.py`, 마이그레이션, `docs/architecture/data-model.md`
- `apps/server/app/api/` 의 요청·응답 형식, `docs/architecture/api.md`
- `docs/design/design-system.md`, `renderer/components/`, `renderer/styles/`
- `CLAUDE.md` (루트·앱별)

## 6. Claude Code 사용 요령

- 새 대화를 시작할 때 Claude는 `CLAUDE.md`를 자동으로 읽는다. **같은 지적을 두 번 했다면 `CLAUDE.md`에 규칙으로 추가**한다.
- 화면 작업 때는 화면 정의서와 목업을 함께 알려 준다: "`docs/design/screens/S07-search.md`를 읽고 `mockups/png/S07-search.png`처럼 만들어줘. 색·크기는 `design-system.md`를 따라." 받은편지함(S03)을 가장 먼저 만들고 나머지는 S03 스타일을 기준으로 한다.
- 한 대화에 한 가지 일. 기능이 바뀌면 새 대화를 연다.
- 프롬프트(LLM에 보내는 지시문)는 코드가 아니라 `apps/server/app/ai/prompts/*.md`에 둔다.
- API 키·실제 메일 내용을 대화창에 붙여 넣지 않는다. 테스트는 fixture 메일로 한다.
