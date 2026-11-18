# Klover — Claude Code 공통 규칙

Klover는 받은 메일을 AI가 분류·요약·제안해 주는 Windows 데스크톱 메일 앱(Gmail 대체)이다. 데스크톱 앱 + 서버로 구성되며, 현재 **데모 단계**다. 4명이 Claude Code로 개발한다.

## 먼저 읽을 것

- 기능을 구현·수정하기 전에 **해당 기능 정의서를 반드시 읽는다**: `docs/product/features/F0~F5-*.md`
- 기능 번호: F0 첫 실행·기본 메일함 / F1 분류·저장 / F2 프로필·답장 초안 / F3 자연어 검색 / F4 주간 보고 / F5 AI 스캔
- 화면 작업: `docs/design/screens/Sxx-*.md`(화면 정의서) + `docs/design/screens/mockups/png/Sxx-*.png`(목업) + `docs/design/design-system.md`
- 색·글꼴 토큰: `docs/design/tokens/klover-theme.css` (화면 코드에 임의 색상값 금지) · 로고·아이콘: `docs/design/brand/`
- 구조·데이터: `docs/architecture/system.md`, `data-model.md`, `api.md`
- 문서 전체 지도: `docs/README.md`

## 폴더 지도

```
docs/            기준 문서 (기능 정의서, 디자인, 구조, 개발 규칙)
apps/desktop/    Electron + React + TypeScript 앱 (자체 CLAUDE.md 있음)
apps/server/     Python FastAPI 서버 (자체 CLAUDE.md 있음)
packages/api-types/  서버 OpenAPI → TS 타입 (자동 생성, 직접 수정 금지)
fixtures/mails/  데모·개발용 가짜 메일
infra/           docker-compose (Postgres+pgvector, Redis)
scripts/         시드, 타입 생성 등
```

`apps/`, `packages/`, `fixtures/`, `infra/`는 아직 없으면 `docs/architecture/system.md`의 구조대로 만든다.

## 작업 규칙

브랜치·승인 절차는 루트 [AGENTS.md](AGENTS.md)의 공통 규칙을 따른다.
변경·검사 결과를 한 번 보고한 뒤 로컬 통합·커밋·Push·PR 생성은 묶어서 승인받고, `develop` 병합과 `main` 병합은 각각 별도 승인받는다.

1. **문서가 기준이다.** 정의서와 다르게 구현해야 하면 먼저 사용자에게 묻고, 정해지면 정의서와 `docs/product/decisions.md`를 고친다.
2. 기능을 끝내면 정의서의 **수용 기준** 체크리스트를 하나씩 확인하고 결과를 보고한다.
3. 정의서에 없는 기능을 임의로 추가하지 않는다. '이번 범위 아님'에 적힌 것은 만들지 않는다.
4. 결정이 필요한 애매한 부분은 `docs/product/open-questions.md`의 '데모 동안 임시 가정'을 따른다.
5. 공유 영역(DB 모델·마이그레이션, API 요청·응답 형식, 디자인 시스템·공통 컴포넌트, CLAUDE.md)을 바꾸는 경우 변경 내용을 요약해 사용자에게 알린다.

## 지켜야 할 구조 원칙

- 앱은 **서버 API만** 호출한다. 앱에서 Gmail·LLM에 직접 접근하지 않는다.
- 메일 소스별 코드는 `apps/server/app/connectors/`에만 둔다.
- LLM·임베딩은 `apps/server/app/ai/`의 인터페이스로만 호출한다. 프롬프트는 `ai/prompts/*.md` 파일로 둔다.
- DB 접근은 `apps/server/app/db/repositories/`로만 한다.
- **AI는 제안만 한다.** 메일 발송, 캘린더 등록은 항상 사용자 승인 후 실행한다.
- AI 결과(요약·답변·보고 항목)에는 근거 메일(`mail_id`)을 연결한다.

## 명령

```bash
docker compose -f infra/docker-compose.yml up -d     # DB, Redis
cd apps/server && uv run uvicorn app.main:app --reload  # 서버
cd apps/server && uv run pytest                      # 서버 테스트
pnpm --filter desktop dev                            # 앱
pnpm --filter desktop lint && pnpm --filter desktop typecheck
pnpm gen:api-types                                   # 서버 API 변경 후 TS 타입 재생성
```

## 금지

- `.env`, API 키, OAuth 토큰을 코드·문서·로그에 쓰지 않는다.
- 실제 메일 내용을 테스트 데이터·fixture에 넣지 않는다 (가짜 메일만).
- `main` 브랜치에 직접 커밋하지 않는다. 브랜치 이름: `feat/F3-search` 형식.
- 커밋 메시지는 `[F3] 무엇을 했는지` 형식, 한국어.

## 응답 언어

사용자와는 한국어로 대화한다. 코드의 변수·함수 이름은 영어, 주석과 화면 문구는 한국어.
