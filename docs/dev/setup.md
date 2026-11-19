# 개발 환경 준비

> 최종 수정: 2026-11-18 | F0 첫 화면·공통 HTTP 서버·F4 보고 입력 준비

## 현재 실행 가능한 범위

- `apps/desktop/`: 첫 실행 시작 화면과 인증된 계정의 받은 목록·텍스트 본문 열람.
- `apps/server/`: 공통 상태 확인·로컬 인증·메일 조회 API와 기존 F4 보고 입력 준비 서비스·CLI.
- `packages/api-types/`: 실제 서버 OpenAPI에서 자동 생성하는 TypeScript 타입.
- `infra/docker-compose.yml`: 개발용 PostgreSQL 16+pgvector 이미지, 로컬 전용 접속·영구 볼륨.

공통 기본 서버의 `/health`와 별도로, 전용 메일 서버는 인증·계정·받은 메일 조회 API를 제공한다.
맥북 실제 앱 실행은 [F0 메일함 실행 안내](F0-mailbox-run.md)를 따른다. DB 연결·최소 저장 구조는
[맥북 DB 실행 안내](local-database.md)에서 별도 실행·검사한다.
명령 기반 새 메일 수신·조회·토큰 갱신은 [수신 안내](gmail-mail-sync.md)를 따른다.

맥북 전용 Google 로그인·계정 확인 코드는 [Google 연결 안내](google-connection.md)의
별도 로컬 서버로 실행한다. 토큰을 암호화해 저장하며, 사용자가 맥북 로그인·새 메일 수신·API 본문 조회 성공을 보고했다.
실제 앱의 Gmail 표시는 사용자 후속 확인으로 구분한다.
앱은 main 전용 로컬 인증으로 계정·목록·본문을 조회한다. 기존 Gmail 연결과 수신 CLI를 사용한다.
Google 연결·다음 버튼과 프로필·알림 설정·AI 기능은 미완료 상태를 유지한다.
F4 보고 입력 CLI는 별도이며 자동으로 보고서를 만들지 않는다.

## 데스크톱 실행·검증 (F0 첫 단위)

저장소 루트에서 실행한다. pnpm 버전은 루트 `package.json`에 고정한다.

```bash
corepack pnpm install
corepack pnpm --filter desktop dev
```

화면만 브라우저로 확인하려면 `corepack pnpm --filter desktop dev:renderer`를 실행한 뒤
`http://127.0.0.1:5173/#/onboarding/1`을 연다.

```bash
corepack pnpm --filter desktop lint
corepack pnpm --filter desktop typecheck
corepack pnpm --filter desktop test
corepack pnpm --filter desktop build
```

브라우저·Electron 실행 검증 방법과 미구현 범위는
[`apps/desktop/README.md`](../../apps/desktop/README.md)에 있다.

## 공통 HTTP 서버 실행·상태 확인

저장소 루트에서 새 터미널을 열어 실행한다. DB·Redis·계정 연결이나 API 키는 필요하지 않다.

```bash
cd apps/server
uv sync --locked
uv run uvicorn app.main:app --host 127.0.0.1 --port 8000
```

서버를 켠 상태로 새 터미널에서 `curl http://127.0.0.1:8000/health`를 실행하거나
브라우저로 같은 주소를 열면 `{"status":"ok"}`가 나온다. 이는 HTTP 프로세스가
응답한다는 뜻이며 DB·Gmail 연결 완료를 뜻하지 않는다. `/docs`에서 현재 API를 확인한다.
포트가 사용 중이면 실행 옵션과 확인 주소에 같은 다른 포트 번호를 사용한다.

서버 검사와 공유 타입 생성 방법은 [서버 실행 안내](../../apps/server/README.md)를 따른다.
API 변경 후 저장소 루트에서 `corepack pnpm gen:api-types`로 타입을 다시 생성한다.

## 보고 입력 준비·검증 (F4 첫 단위)

Python 3.12 이상과 uv로 실행한다. DB·Gmail·AI 키 없이 **지정한 가짜 메일만**
읽어서 보고 입력을 준비한다. HTTP API나 완성된 보고서를 제공하는 명령은 아니다.

저장소 루트에서 새 터미널을 열어 실행한다.

```bash
cd apps/server
uv sync --locked
uv run python -m app.cli.weekly_report_input \
  --fixture ../../fixtures/mails/F4-weekly-report.json \
  --user-id demo-hong --start 2026-10-05 --end 2026-10-09
uv run pytest
uv run ruff check .
uv run ruff format --check .
```

출력은 업무 그룹별 `mail_ids`·메일 정보, 제외 목록, `scope`다. 예제의 범위는
전체 12건 = 묶인 9건 + 제외 3건, 업무 6개다. 기간 밖 2건과 다른 사용자 1건은
조회되지 않는다. 작업 분할과 수용 기준은 [F4 구현 계획](F4-weekly-report-plan.md)에 있다.

## 필요한 도구

| 도구 | 버전 | 용도 |
| --- | --- | --- |
| Git | 최신 | 저장소 |
| Node.js | 22 LTS (22.22.2 이상) 또는 24.15 이상 | 데스크톱 앱·테스트 |
| pnpm | 10.34.9 (루트 package.json에 고정) | JS 패키지 관리 (모노레포 workspace) |
| Python | 3.12 | 서버 |
| uv | 최신 | Python 패키지·가상환경 관리 |
| Docker Desktop | 최신 | 개발용 PostgreSQL 실행. Redis는 후속 구현 |
| Claude Code | 최신 | 바이브 코딩 |

개발은 macOS·Windows 어디서나 가능하다. 단 **트레이·토스트 알림·시작 프로그램은 Windows PC에서 최종 확인**한다.

## 전체 앱 실행 계획 (후속 기반 구현 후 사용)

아래 명령과 환경 변수는 서버·DB·수신 파이프라인이 준비된 뒤 사용하는 계획이다.
현재 `infra/docker-compose.yml`·`.env.example`·DB 마이그레이션은 최소 DB 단위로 준비했다.
아래 전체 앱 실행 예시의 Redis·작업자는 아직 없으므로 현재 실행에는 로컬 DB 안내를 따른다.
가짜 메일 자동 도착 모드와 실제 Gmail 연결도 아직 구현되지 않았다.
현재 실행할 명령은 위의 F0·공통 서버·F4 첫 단위 절차를 따른다.

### 처음 한 번

```bash
git clone <저장소 주소> klover && cd klover
cp .env.example .env              # API 키 등 채우기 (.env는 커밋 금지)
docker compose -f infra/docker-compose.yml up -d
pnpm install                      # 앱 의존성
cd apps/server && uv sync         # 서버 의존성
uv run alembic upgrade head       # DB 테이블 생성
```

### 매일 실행

```bash
# 터미널 1 — 서버
cd apps/server && uv run uvicorn app.main:app --reload

# 터미널 2 — 작업자 (수신·분석 파이프라인)
cd apps/server && uv run arq workers.main.WorkerSettings

# 터미널 3 — 데스크톱 앱
pnpm --filter desktop dev
```

### 메일 소스 선택

`.env`의 `MAIL_SOURCE`로 바꾼다.

- `fixture` (기본): `fixtures/mails/`의 가짜 메일을 시간차로 '도착'시킨다. Gmail 계정 없이 전체 흐름 개발 가능.
- `gmail`: 테스트 Gmail 계정 연결. Google Cloud 프로젝트의 OAuth 클라이언트가 필요하고, 계정을 **테스트 사용자**로 등록해야 한다(검수 전 앱 제한).

### 환경 변수 (.env.example)

| 이름 | 설명 |
| --- | --- |
| `DATABASE_URL` | Postgres 접속 주소 |
| `REDIS_URL` | Redis 접속 주소 |
| `MAIL_SOURCE` | `fixture` / `gmail` |
| `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` | Gmail·Calendar OAuth |
| `LLM_PROVIDER`, `LLM_API_KEY`, `LLM_MODEL` | LLM 설정 |
| `EMBEDDING_PROVIDER`, `EMBEDDING_MODEL` | 임베딩 설정 |
| `TOKEN_ENCRYPTION_KEY` | OAuth 토큰 암호화 키 |

API 키는 팀 비밀 저장소에서 공유한다. 채팅·문서·코드에 붙여 넣지 않는다.
