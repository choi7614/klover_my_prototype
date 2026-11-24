> 과거 기록: f498d27의 apps/server/README.md. 현재 실행은 [setup.md](../../setup.md)를 따른다.

# Klover 공통 서버

FastAPI HTTP 서버를 실행하고 `GET /health`로 프로세스 응답을 확인한다.
기존 F4 보고 입력 준비 서비스·CLI는 같은 프로젝트에서 그대로 사용한다.

## 실행과 확인

Python 3.12 이상과 uv를 사용한다. 저장소 루트에서:

```bash
cd apps/server
uv sync --locked
uv run uvicorn app.main:app --host 127.0.0.1 --port 8000
```

서버를 켠 상태로 새 터미널에서 확인한다.

```bash
curl http://127.0.0.1:8000/health
```

정상 응답은 HTTP 200과 `{"status":"ok"}`다. 브라우저에서도 같은 주소를 열 수 있다.
`/docs`는 API 문서, `/openapi.json`은 현재 앱에서 생성한 API 명세다.
포트가 사용 중이면 `--port 8010`처럼 바꾸고 확인 주소에도 같은 포트를 쓴다.
개발 중 자동 재시작이 필요하면 `uv run uvicorn app.main:app --reload`를 사용할 수 있다.

`/health`는 인증·DB·Redis·Google·AI 키 없이 실행한다. HTTP 프로세스의 응답만 확인하며,
DB 연결이나 Gmail 동기화·기능 준비 완료를 뜻하지 않는다. 메일 조회는 아래 전용 명령을 사용한다.
WebSocket은 아직 없다.
앱의 Google 연결·설정 진행 버튼은 여전히 비활성이다.

## 앱 연결용 메일 조회

기존 Google 연결·DB·메일을 보존하며 별도 로컬 API 토큰으로 계정·목록·본문을 읽는다.
루트에서 `uv run --locked --directory apps/server python -m app.cli.prepare_mail_api`로
한 번 준비하고 `uv run --locked --directory apps/server python -m app.cli.run_mail_api`로 실행한다.
새 터미널의 `python -m app.cli.check_mail_api`로 내용·키를 출력하지 않고 검사할 수 있다.
실제 전체 명령과 F0 연결 후 앱 실행은 [메일 API 안내](../../mail-read-api.md),
F0 전달 문장은 [연결 요청](../../F0-mail-api-handoff.md)을 따른다.

## 오류와 검증

오류는 `{"error":{"code":"...","message":"..."}}` 형식으로 반환한다.
없는 경로는 404, 허용되지 않은 요청 방식은 405, 입력 형식 오류는 422,
내부 오류는 500이다. 응답에 입력값·예외 상세를 포함하지 않는다.

`apps/server`에서 실행한다.

```bash
uv run pytest
uv run ruff check .
uv run ruff format --check .
```

검사는 기존 F4 시나리오와 HTTP 응답·오류·OpenAPI 내보내기, 실제 Uvicorn 프로세스
시작과 로컬 HTTP 요청을 포함한다. 프로세스 검사는 빈 포트를 골라 실행한 뒤 종료한다.

## 공유 타입 생성

서버 API를 추가·변경한 뒤 저장소 루트에서 실행한다.

```bash
corepack pnpm install --frozen-lockfile
corepack pnpm gen:api-types
corepack pnpm --filter @klover/api-types typecheck
```

서버를 켜거나 외부 서비스에 연결할 필요 없이 실제 앱의 OpenAPI에서 생성한다.
`packages/api-types/openapi.json`과 `src/schema.d.ts`는 자동 생성 결과로 직접 수정하지 않는다.

## 후속 단위

맥북의 Google 로그인·동의·계정 확인과 토큰 암호화 저장은
[Google 연결 안내](../../google-connection.md)의 별도 로컬 실행 명령을 따른다.
일반 서버의 앱용 인증·메일 API는 아직 없다. 실제 Gmail 로그인은 사용자 맥북에서 별도 확인한다.

DB 연결·최소 저장 구조는 [로컬 DB 안내](../../local-database.md)를 따른다.
DB는 명시적 명령으로 실행·마이그레이션·검사한다. `/health`와 F4 CLI는 DB 없이 계속 실행된다.
F4의 기존 보고 조회 계약·fixture는 그대로이며 실제 DB 어댑터는 아직 연결하지 않았다.

새 받은 메일의 명령 기반 수신·저장·조회와 토큰 갱신은
[메일 수신 안내](../../gmail-mail-sync.md)를 따른다. 실제 계정의 수신 확인은 아직 대기다.
다음은 인증된 메일 API → F0 화면 연결이다.
사용자는 맥북과 개인 Google 프로젝트를 준비했으며, 실제 계정 연결 확인을 우선한다.
자동 검사에는 합성 메일을 사용한다. AI 분류·검색·Calendar 쓰기·전체 Gmail 과거 메일 수집은
이번 단위에 포함하지 않는다.
