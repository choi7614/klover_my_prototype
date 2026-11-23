# Klover — 공통 작업 규칙 (Codex·Claude 공용)

이 파일이 저장소의 **유일한 규칙집**이다. GPT Codex와 Claude Code 모두 이 파일을 따른다.
`CLAUDE.md`는 이 파일을 불러오고 Claude 전용 메모만 둔다. 규칙을 바꿀 때는 이 파일만 고친다.
상세 기능 명세는 기존 문서를 참조하며 여기에 중복 작성하지 않는다.

## 프로젝트와 운영 방식

- Klover는 받은 메일을 AI가 분류·요약·제안해 주는 Windows 데스크톱 메일 앱(Gmail 대체)이다.
  데스크톱 앱 + 서버로 구성되며, 현재 **데모 단계**다.
- **1인 개발**이다. 한 사람이 GPT Codex와 Claude Code를 번갈아 쓰며, 채팅을 세 종류로 나눠 운영한다.

| 채팅 | 하는 일 | 작업 브랜치 |
| --- | --- | --- |
| 기능별 채팅 (F0~F5) | 해당 기능의 전용 파일 구현·검사, 공통 영역 변경은 패치·요청으로 남김 | `feat/Fn-이름` |
| 공통 채팅 | 규칙·문서·개발 절차·CI 같은 저장소 공통 설정 | `chore/...`, `docs/...` |
| 통합 채팅 | 공통 영역 변경 적용, 기능 간 연결, `develop` 병합 전 통합 검사 | `integrate/...` 또는 승인된 작업 브랜치 |

- 기능 번호: F0 첫 실행·기본 메일함 / F1 분류·저장 / F2 프로필·답장 초안 / F3 자연어 검색 / F4 주간 보고 / F5 AI 스캔
- 진행 현황은 [docs/dev/progress.md](docs/dev/progress.md)(현황판), 기능별 상세는 `docs/dev/Fn-*-status.md`에 둔다.

## 소통과 작업 범위

- 사용자는 비개발자다. 진행 상황과 결과를 쉬운 한국어로 설명하고, 필요한 기술 용어는 풀어서 쓴다.
  코드의 변수·함수 이름은 영어, 주석과 화면 문구는 한국어로 쓴다.
- 요청한 기능을 작은 단위로 나누어 개발한다. 관련 없는 코드·명세를 바꾸거나 명세에 없는 기능을 임의로 추가하지 않는다.
  정의서의 '이번 범위 아님'에 적힌 것은 만들지 않는다.
- 기능별 채팅은 독립적으로 운영한다. 다른 채팅의 작업 완료를 가정하지 말고 현재 브랜치의 파일·커밋·API로 확인한다.
  없는 의존 기능은 미구현으로 알리고, 임시 구현·가짜 데이터 사용 여부를 명시한다.

## 새 작업마다 먼저 확인

- 변경 전에 저장소·원격 저장소·현재 브랜치와 기존 변경사항(커밋하지 않은 파일 포함)을 확인한다.
  브랜치 전환이나 파일 수정이 기존 작업에 영향을 주면 멈추고 사용자에게 알린다.
- 새 채팅과 기존 채팅의 새 작업마다 현재 브랜치의 `AGENTS.md`, [progress.md](docs/dev/progress.md),
  해당 기능 명세와 status 문서를 다시 읽는다. 이전 채팅의 기억으로 대신하지 않는다. 필요한 문서가 없으면 알리고 확인한 뒤 진행한다.
- [프로젝트 소개](README.md)와 [문서 지도](docs/README.md)에서 관련 문서를 찾는다.
- 기능: `docs/product/features/`의 해당 `Fn-*.md`에서 범위·수용 기준을 확인한다. 결정 사항과 임시 가정은
  [decisions.md](docs/product/decisions.md), [open-questions.md](docs/product/open-questions.md)의 '데모 동안 임시 가정'을 따른다.
- UI: [화면 목록](docs/design/screens/README.md)에서 해당 `Sxx-*.md`와 `docs/design/screens/mockups/`의 HTML·PNG 목업을 함께 확인한다.
  [디자인 시스템](docs/design/design-system.md)과 [색·글꼴 토큰](docs/design/tokens/klover-theme.css)을 따른다(화면 코드에 임의 색상값 금지). 로고·아이콘은 `docs/design/brand/`.
- 기술 구조: [system.md](docs/architecture/system.md), [data-model.md](docs/architecture/data-model.md), [api.md](docs/architecture/api.md)의 기술 스택·폴더 구조·계층 경계를 존중한다.
- 실행·테스트·작업 흐름은 [setup.md](docs/dev/setup.md), [workflow.md](docs/dev/workflow.md)를 참조한다.
- 명세·목업이 없거나 서로 충돌하면 관련 부분을 알리고 확인한다. 명세와 다른 구현이 필요하면 사용자와 합의한 뒤
  정의서와 `docs/product/decisions.md`를 갱신한다.

## 폴더 지도

```
docs/                기준 문서 (기능 정의서, 디자인, 구조, 개발 규칙·현황판)
apps/desktop/        Electron + React + TypeScript 앱
apps/server/         Python FastAPI 서버
packages/api-types/  서버 OpenAPI → TS 타입 (자동 생성, 직접 수정 금지)
fixtures/mails/      데모·개발용 가짜 메일
infra/               docker-compose (Postgres+pgvector)
integration/, patches/  기능 채팅이 남긴 공통 영역 적용 전 패치·요청
scripts/             시드, 타입 생성 등
```

## 지켜야 할 구조 원칙

- 앱은 **서버 API만** 호출한다. 앱에서 Gmail·LLM에 직접 접근하지 않는다.
- 메일 소스별 코드는 `apps/server/app/connectors/`에만 둔다.
- LLM·임베딩은 `apps/server/app/ai/`의 인터페이스로만 호출한다. 프롬프트는 `ai/prompts/*.md` 파일로 둔다.
- DB 접근은 `apps/server/app/db/repositories/`로만 한다.
- **AI는 제안만 한다.** 메일 발송, 캘린더 등록은 항상 사용자 승인 후 실행한다.
- AI 결과(요약·답변·보고 항목)에는 근거 메일(`mail_id`)을 연결한다.

## 공통 영역은 통합 채팅에서만 바꾼다

아래 파일은 **통합 채팅에서만** 수정한다. 기능별 채팅은 직접 수정하지 않고, 필요한 변경을
`patches/Fn/` 또는 `integration/Fn-*/`의 적용 전 패치와 status 문서의 '공통 영역 요청'으로 남긴다.

- DB 모델과 마이그레이션: `apps/server/app/db/models.py`, `apps/server/migrations/` (`env.py`·`versions/` 포함), `docs/architecture/data-model.md`
- 서버 등록: `apps/server/app/main.py`의 라우터 등록, 실행 명령의 저장소 조립(`app/cli/run_mail_api.py` 등)
- 공유 타입: `packages/api-types/` (`pnpm gen:api-types`로만 재생성), `docs/architecture/api.md`의 공통 형식
- 공통 앱 골격: `apps/desktop/src/main`·`preload`, 공통 App·라우터, `renderer/components/`, `renderer/styles/`, 디자인 시스템 문서
- 의존성 잠금 파일: `pnpm-lock.yaml`, `apps/server/uv.lock`

마이그레이션 번호는 [progress.md](docs/dev/progress.md)의 '마이그레이션 번호 예약' 표에서 먼저 예약한 뒤 사용한다.
공통 영역을 바꾼 경우 변경 내용을 요약해 사용자에게 알린다. 규칙 문서(`AGENTS.md`, `CLAUDE.md`, `docs/dev/`) 변경은 공통 채팅에서 한다.

## 브랜치와 승인

- 기능 개발은 기능별 `feat/Fn-이름` 브랜치에서 진행한다. 흐름은 `feat/...` → `develop`(기능 통합·통합 테스트) → `main`(검증된 안정 버전)이다.
  `main`과 `develop`에 직접 커밋·Push하지 않고 PR로 반영한다. 커밋 메시지는 `[F3] 무엇을 했는지` 형식의 한국어로 쓴다(공통 작업은 `[공통]`).
- 새 기능 브랜치를 만들기 전에 `git fetch origin`으로 원격 정보를 갱신하고, 로컬·원격에 같은 기능 브랜치가 있는지 확인한다.
  없을 때만 최신 `origin/develop`에서 만든다. 원격 갱신에 실패하면 최신 상태라고 가정하지 않는다.
- 이미 있는 기능 브랜치는 재사용한다. 원격에만 있으면 이를 이어받는 로컬 브랜치를 사용한다. 기존 브랜치를 재생성하거나 강제 초기화하지 않는다.
  원격과 로컬의 차이를 확인하고 기존 커밋을 보존한다.
- 요청받지 않은 기능의 브랜치를 미리 만들지 않는다.
- 작은 작업 단위마다 변경 내용·변경 파일·검증 결과·대상 브랜치를 한 번 보고한 뒤, **로컬 통합·커밋·Push·PR 생성을 묶어서 한 번 승인받는다**.
  로컬 통합이 필요하면 가져올 브랜치와 적용할 작업 브랜치도 보고한다. 승인된 범위 안에서는 각 단계마다 다시 승인받지 않는다.
- **`develop` 병합과 `main` 병합은 각각 별도 승인받는다**. 로컬·원격 병합과 자동 병합 설정 모두 해당한다.
  위 묶음 승인은 기능 작업 브랜치에서의 로컬 통합만 포함한다.
- 파일 작성 요청이나 승인 절차 변경만으로 개별 작업의 묶음 실행까지 승인받았다고 간주하지 않는다. 사용자가 범위를 제한하면 그 범위를 따른다.
  승인 후 변경 범위나 대상이 달라지면 바뀐 내용·재검증 결과를 보고하고 다시 승인받는다.
- Force Push(강제 Push), Sync fork(포크 동기화), 기존 작업 삭제는 사용자의 명시적 승인 없이 실행하지 않는다. 기존 변경사항을 덮어쓰거나 되돌리거나 삭제하지 않는다.
- 기존 기능 브랜치에는 새 규칙이 자동 반영되지 않는다. 최신 `develop`을 기능 브랜치로 가져오는 로컬 통합은 위 묶음 승인에 포함할 수 있다.

## 도구 전환과 인수인계 (Codex ↔ Claude)

같은 브랜치를 두 도구가 동시에 만지지 않는 것이 핵심이다. 프롬프트 예시는 [handoff-prompts.md](docs/dev/handoff-prompts.md)에 있다.

### 넘길 때 (정상 인수인계)

1. 작업 단위를 마무리하거나, 끝내지 못했으면 멈춘 지점을 정리한다.
2. 해당 기능 status 문서(`docs/dev/Fn-*-status.md`)를 [양식](docs/dev/status-template.md)대로 갱신한다: 한 일·검사 결과·미커밋 없음·다음 할 일.
3. [progress.md](docs/dev/progress.md)의 해당 행을 갱신한다: 작업 도구를 `없음`(또는 넘겨받을 도구), 상태, 마지막 커밋, 다음 할 일, 갱신일.
4. **반드시 커밋·Push**한다. 커밋·Push는 위 묶음 승인 절차를 따른다. 미커밋 파일을 남긴 채 도구를 바꾸지 않는다.

### 사용 한도로 끊길 위험이 있을 때 (긴급 저장)

- 사용 한도·세션 종료로 작업이 끊길 위험이 있으면, **기능 브랜치(`feat/...`, `chore/...`, `docs/...` 등 작업 브랜치)에 한해**
  `[WIP] 인수인계` 커밋과 Push는 **사전 승인된 것으로 간주**한다. 별도 승인을 기다리지 않는다.
- 커밋 메시지: `[Fn][WIP] 인수인계: 멈춘 지점 한 줄`. 검사를 통과하지 않아도 되지만, status 문서의 '인수인계 메모'에
  멈춘 지점·실패 중인 검사·다음 할 일을 적고 progress.md 상태를 `WIP 저장`으로 바꾼다.
- 이 예외는 `develop`·`main`에는 적용되지 않는다. 병합·PR 병합·Force Push는 기존대로 별도 승인이다.
- `.env`·키·토큰·실제 메일 내용이 스테이징되지 않았는지 확인한 뒤 커밋한다.

### 이어받을 때

순서대로 확인한다.

1. `git fetch origin` 후 대상 브랜치의 로컬·원격 차이를 확인한다.
2. `docs/dev/progress.md`를 읽는다. **다른 도구가 작업 중으로 표시된 브랜치는 건드리지 않고 사용자에게 확인한다.**
3. 해당 기능 status 문서의 '현재 상태'와 '인수인계 메모'를 읽는다.
4. 미커밋 변경과 `[WIP]` 커밋이 있는지 확인한다(`git status`, `git log origin/develop..`). WIP이면 멈춘 지점부터 이어서 한다.
5. progress.md의 작업 도구를 자신(Codex/Claude)으로 바꾸고, 규칙(`AGENTS.md`)이 바뀌었는지와 최신 `develop` 반영 여부를 보고한 뒤 작업한다.

## 구현과 검증

- 작은 단위마다 해당 수용 기준과 관련 테스트를 실행한다. 기능을 끝내면 정의서의 **수용 기준** 체크리스트를 하나씩 확인하고 결과를 보고한다.
- 테스트하지 않은 기능은 정상 작동한다고 보고하지 않는다. 통과·실패·미실행을 구분하고, 미실행 이유와 남은 확인 항목을 적는다.
- 문서만 바꾼 경우에는 참조 경로·내용 일관성·변경 범위를 확인하고, 앱 기능 테스트를 실행한 것처럼 보고하지 않는다.
- PR마다 GitHub Actions(`.github/workflows/ci.yml`)가 서버 ruff·pytest와 데스크톱 lint·typecheck·test를 실행한다.
  실제 DB가 필요한 검사는 CI에서 skip될 수 있으며, 그 경우 로컬 DB 검사 결과를 status 문서에 따로 적는다.

## 명령

```bash
docker compose --env-file .env -f infra/docker-compose.yml up -d --wait  # 개발용 DB
uv run --locked --directory apps/server python -m app.cli.run_mail_api  # 앱용 서버(사전 준비: docs/dev/setup.md)
uv run --locked --directory apps/server pytest             # 서버 테스트
uv run --locked --directory apps/server ruff check .
uv run --locked --directory apps/server ruff format --check .
pnpm --filter desktop dev                                 # 앱
pnpm --filter desktop lint && pnpm --filter desktop typecheck && pnpm --filter desktop test
pnpm gen:api-types                                        # 서버 API 변경 후 TS 타입 재생성 (통합 채팅)
```

## 금지

- `.env`, API 키, OAuth 토큰을 코드·문서·로그에 쓰지 않는다.
- 실제 메일 내용을 테스트 데이터·fixture에 넣지 않는다 (가짜 메일만).
- `main`·`develop` 브랜치에 직접 커밋하지 않는다.

## 작업 후 보고

아래 내용을 쉬운 한국어로 보고한다.

1. 구현·수정 내용, 변경 파일과 각 파일의 변경 목적
2. 수정 방법과 사용자가 확인할 방법
3. 실행한 테스트·확인 명령과 결과, 미실행 항목과 이유
4. 남은 문제·의존 작업과 다음 단계 (status 문서·progress.md 갱신 여부 포함)
5. 작업 브랜치와 PR 링크(있는 경우), 사용자 승인 또는 확인이 필요한 사항
