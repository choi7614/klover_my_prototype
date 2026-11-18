# Klover 데스크톱 — F0 첫 단위

현재 범위는 Electron 실행 기반과 S01의 첫 화면이다.
첫 실행 설정은 1040×680 창으로 열리며 창 크기 변경과 최대화를 막는다.
설정 전에는 창 닫기로 앱이 완전히 종료된다.

## 실행

저장소 루트에서 Node.js 22.22.2 이상인 22 LTS 또는 24.15 이상과 pnpm 10을 사용한다.

```bash
corepack pnpm install
corepack pnpm --filter desktop dev
```

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
```

`test:e2e`는 화면과 진행 차단을 Chromium에서 확인한다.
이미 설치된 Chromium을 쓰려면 `PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH`에 경로를 지정한다.
`test:electron`은 빌드 후 실행하며 실제 Electron 창 크기·보안 설정·preload·닫기 종료를 확인한다.
Linux에서는 실행 가능한 그래픽 환경이 필요하다. 최대화 제한 API는 Linux에서 지원되지 않는다.
최대화 제한·트레이·자동 실행 등 Windows 고유 동작은 Windows에서 따로 확인한다.
Playwright의 Electron 자동 검사는 기본적으로 Chromium OS sandbox를 끄고 실행한다.
따라서 격리 검사는 `contextIsolation`·Node 접근 차단·제한된 preload를 확인하며 OS sandbox 검증을 뜻하지 않는다.
화면 캡처는 저장소 루트의 `artifacts/`에 저장하고 Git에는 포함하지 않는다.

## 아직 연결하지 않은 부분

- 실제 서버, Google OAuth 연결, 프로필·설정 저장, 메일 API는 현재 브랜치에 없다.
- Google 연결과 다음 버튼은 비활성이다. 연결된 계정이나 완료 상태를 만들지 않는다.
- 2~5단계와 메일함 주소를 직접 입력해도 첫 화면으로 돌아온다.
- 서버의 요청·응답 형식을 임의로 정하거나 `packages/api-types`를 수동 작성하지 않았다.
- `main/`은 창·OS 기능, `preload/`는 필요한 Electron 기능 공개, `renderer/`는 화면을 담당한다.
- 실제 서버 연결은 이후 별도 기능 연결부로 추가한다. 화면에서 Gmail·LLM을 직접 호출하지 않는다.

첫 수용 기준인 “5단계 완료 후 다시 나오지 않음” 전체는 아직 완료되지 않았다.
다음 단위는 실제 서버 기반과 OAuth 요청·응답·인증 복귀 방식을 준비한 뒤 1단계 연결을 구현하는 것이다.
