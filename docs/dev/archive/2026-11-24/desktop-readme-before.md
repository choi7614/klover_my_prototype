> 과거 기록: f498d27의 apps/desktop/README.md. 현재 실행은 [setup.md](../../setup.md)를 따른다.

# Klover 데스크톱 — 첫 실행 화면·받은 메일 열람

기존 S01 첫 실행 화면을 보존하며, 로컬 메일 API의 계정 조회에 성공하면 받은편지함으로 들어간다.
받은 메일 목록·다음 페이지·DB 목록 새로고침·선택 메일의 텍스트 본문을 읽는다.
계정 연결은 기존 맥북 서버에서 완료된 것을 사용한다. 온보딩 완료 상태를 생성하지 않는다.
연결 전 창은 1040×680, 메일함은 화면 작업 영역에 맞춰 최대 1440×900으로 열린다.
이번 읽기 전용 단계에서는 창 닫기로 앱이 완전히 종료된다.

## 실행

저장소 루트에서 Node.js 22.22.2 이상인 22 LTS 또는 24.15 이상과 pnpm 10을 사용한다.

```bash
corepack pnpm install
corepack pnpm --filter desktop dev
```

실제 Gmail을 읽을 때는 먼저 서버를 실행하고 앱 터미널에 다음 환경 변수를 지정한다.
기존 키·계정·DB를 보존하는 맥북 전체 실행 순서는
[맥북 실행 안내](../../F0-mailbox-run.md)를 따른다.

```bash
export KLOVER_API_TOKEN_FILE="$PWD/.local-secrets/mail-api-token"
export KLOVER_API_BASE_URL="http://127.0.0.1:8000"
corepack pnpm --filter desktop dev
```

토큰 파일은 main만 읽고(일반 파일·절대 경로·최대 256바이트·POSIX 권한 600), 토큰 내용은
renderer·로그로 전달하지 않는다. 서버 API 토큰이며 Google JSON·암호화 키·OAuth 토큰이 아니다.
주소는 로컬 HTTP(`127.0.0.1`·`localhost`·`::1`)의 루트 주소만 허용하고 리디렉션을 따라가지 않는다.
main의 세 조회 IPC는 요청 창·상위 프레임·URL·인수를 검증한다. 임의 파일·URL·헤더 IPC는 없다.

Electron 창이 필요 없는 화면 확인은 다음 명령으로 같은 React 화면을 연다.
브라우저 미리보기에는 Electron의 preload API가 없다.

```bash
corepack pnpm --filter desktop dev:renderer
```

주소: `http://127.0.0.1:5173/#/onboarding/1`

## 검증

```bash
corepack pnpm --filter desktop lint
corepack pnpm --filter desktop typecheck
corepack pnpm --filter desktop test
corepack pnpm --filter desktop build
corepack pnpm --filter desktop exec playwright install chromium
corepack pnpm --filter desktop test:e2e
corepack pnpm --filter desktop test:electron
uv sync --locked --directory apps/server
corepack pnpm --filter desktop test:mail-read
```

`test:e2e`는 화면과 진행 차단을 Chromium에서 확인한다.
이미 설치된 Chromium을 쓰려면 `PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH`에 경로를 지정한다.
`test:electron`은 빌드 후 실행하며 실제 Electron 창 크기·보안 설정·preload·닫기 종료를 확인한다.
Linux에서는 실행 가능한 그래픽 환경이 필요하다. 최대화 제한 API는 Linux에서 지원되지 않는다.
최대화 제한·트레이·자동 실행 등 Windows 고유 동작은 Windows에서 따로 확인한다.
Playwright의 Electron 자동 검사는 기본적으로 Chromium OS sandbox를 끄고 실행한다.
따라서 격리 검사는 `contextIsolation`·Node 접근 차단·제한된 preload를 확인하며 OS sandbox 검증을 뜻하지 않는다.
화면 캡처는 저장소 루트의 `artifacts/`에 저장하고 Git에는 포함하지 않는다.

`test:mail-read`는 실제 FastAPI 읽기 라우터에 합성 저장소를 연결하고 실제 Electron의
계정·목록·페이지·본문·빈 목록·인증 실패를 검사한다. 실제 Google·사용자 DB는 호출하지 않는다.
단위 검사는 외부 URL·리디렉션·잘못된 IPC·오류 원문 노출·본문 HTML 삽입·오래된 응답 덮어쓰기를 확인한다.

## 아직 연결하지 않은 부분

- Google 연결 버튼과 다음 버튼은 기존처럼 비활성이다. 프로필·알림 설정과 AI를 완료로 표시하지 않는다.
- 계정 조회에 실패하면 기존 첫 화면에 일반 오류·재확인 버튼을 표시한다. 실제 오류 원문·비밀 경로는 표시하지 않는다.
- 계정 조회에 성공하면 메일함을 열 수 있지만 온보딩 2~5단계 완료를 뜻하지 않는다.
- 새로고침은 DB 재조회다. 기존 `gmail_mail sync` CLI가 새 메일을 수신한다.
- 발송·보관·삭제·읽음 변경·자동 수신·AI 분석·트레이·자동 실행은 이번 범위에 없다.
- 서버의 요청·응답 형식을 임의로 정하거나 `packages/api-types`를 수동 작성하지 않았다.
- `main/`은 창·OS 기능, `preload/`는 필요한 Electron 기능 공개, `renderer/`는 화면을 담당한다.
- 화면은 서버를 직접 fetch하지 않는다. main만 로컬 서버를 호출하고 앱에서 Gmail·DB·LLM을 직접 호출하지 않는다.

첫 수용 기준인 “5단계 완료 후 다시 나오지 않음” 전체는 아직 완료되지 않았다.
실제 맥북 앱에서 Gmail 표시 확인과 Windows 전용 동작 검증은 자동 검사와 구분한다.
