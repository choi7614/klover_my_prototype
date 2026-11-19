# 맥북에서 Klover 받은 메일 열기

> 2026-11-19 · F0 읽기 전용 화면 연결 · 맥북 실제 Gmail 앱 표시는 사용자 확인 필요

이 문서의 앱 변경은 검토용 작업 폴더에서 구현·검사한다. **묶음 승인 후 GitHub의
`feat/F0-mailbox`에 반영되었다는 안내를 받은 다음** 아래 명령을 실행한다.
`develop`·`main` 병합은 각각 별도 승인이다. 아직 원격 F0 브랜치가 이전 버전이면 첫 화면만 나온다.
서버의 [API 실행 안내](mail-read-api.md)와 같은 환경 변수·포트를 사용한다.

## 1. 코드 받기와 서버 실행 — 첫 번째 터미널

Docker Desktop을 켠다. 기존 서버가 돌아가는 터미널은 **Control+C**로 멈춘 뒤 진행한다.

```bash
cd ~/Projects/klover-taeho-dev
git status --short --branch
```

변경 파일이 없을 때만 아래를 실행한다. 변경 파일이 있으면 초기화·삭제하지 말고 먼저 확인한다.
기존 F0 브랜치를 재사용하며 기존 커밋을 강제 초기화하지 않는다.

```bash
git fetch origin
git switch feat/F0-mailbox
git pull --ff-only origin feat/F0-mailbox
docker compose --env-file .env -f infra/docker-compose.yml up -d --wait
uv run --locked --directory apps/server python -m app.cli.run_mail_api
```

마지막 명령은 서버가 실행되는 동안 끝나지 않는다. **이 터미널을 켜둔다.**
기존 Google 연결·API 검사가 성공한 상태이므로 키 생성·재연결·DB 초기화·재수집은 필요하지 않다.
8000 포트를 다른 프로그램이 쓰면 임의로 종료하지 않는다. 전용 서버에 `--port 8010`을 붙였다면
다음 API 검사에도 `--port 8010`, 앱의 로컬 주소에도 `:8010`을 사용한다.

## 2. API 확인과 앱 실행 — 새 터미널

```bash
cd ~/Projects/klover-taeho-dev
uv run --locked --directory apps/server python -m app.cli.check_mail_api
corepack pnpm install --frozen-lockfile
export KLOVER_API_TOKEN_FILE="$PWD/.local-secrets/mail-api-token"
export KLOVER_API_BASE_URL="http://127.0.0.1:8000"
corepack pnpm --filter desktop dev
```

환경 변수는 **파일 경로와 로컬 주소**다. 토큰 값은 입력·복사·출력하지 않는다.
브라우저 미리보기(`dev:renderer`)에는 main/preload가 없으므로 실제 메일을 읽지 않는다.
`dev`가 여는 Electron 앱을 사용한다. Node.js는 22.22.2 이상인 22 LTS 또는 24.15 이상이 필요하다.

앱에서 확인한다.

1. 연결된 Gmail 주소가 표시된다.
2. 받은 메일을 누르면 제목·발신자·받는 사람·수신 시각·텍스트 본문이 보인다.
3. 다음 페이지가 있으면 버튼으로 불러온다. 마지막 페이지에는 버튼이 없다.
4. 새로고침은 저장된 메일 목록을 다시 읽는다. 메일을 열어도 읽음 상태는 바뀌지 않는다.
5. 앱을 껐다 다시 열어도 같은 계정·메일을 조회한다. 온보딩 전체·AI 기능은 완료로 표시되지 않는다.

서버가 꺼졌거나 인증·설정이 맞지 않으면 기존 첫 화면이나 메일 영역에 오류와 재시도 버튼이 보인다.
값을 채팅에 올리거나 키를 다시 만들지 말고, 서버 터미널·두 환경 변수·API 검사 결과부터 확인한다.
맥북의 API 성공 보고와 이 변경의 자동 검사 통과는 실제 앱 표시 성공 보고와 구분한다.

## 3. 새 Gmail을 더 가져올 때 — 별도 터미널

```bash
cd ~/Projects/klover-taeho-dev
uv run --locked --directory apps/server python -m app.cli.gmail_mail sync
```

그다음 앱의 **새로고침**을 누른다. 기존 수신 CLI를 그대로 사용한다.
앱은 키·계정·메일을 생성·수정·삭제하지 않는다. 발송·보관·삭제·읽음 변경·주기 수신은 이번 범위 밖이다.

## 개발자용 검증

루트에서 아래를 실행한다. 공유 API는 변경하지 않는다.

```bash
corepack pnpm --filter desktop lint
corepack pnpm --filter desktop typecheck
corepack pnpm --filter desktop test
corepack pnpm --filter @klover/api-types typecheck
corepack pnpm --filter desktop build
corepack pnpm --filter desktop test:e2e
corepack pnpm --filter desktop test:electron
corepack pnpm --filter desktop test:mail-read
```

Electron 검사는 그래픽 환경이 필요하며 Playwright의 OS sandbox 제한은 앱 README를 따른다.
메일 통합 검사는 실제 FastAPI 라우터 + 합성 저장소를 사용한다. 테스트 토큰·합성 메일만 쓰며
실제 Google·운영 DB·키를 읽지 않는다. PostgreSQL 전용 서버 검사는 별도 테스트 DB를 지정할 때만 실행한다.
