# Klover 데스크톱

> 현재 구현 기준 `develop f498d27`(PR #37), 2026-11-24 확인. Electron+React+TypeScript 개발 실행.

**신규 설치·토큰·실제 앱 실행·평소 실행·종료·업데이트는 [setup.md](../../docs/dev/setup.md)를 따른다.**
기존 Google 설정이 있다고 가정하지 않는다. Node/pnpm 설치만으로 Gmail이 연결되지는 않는다.
`dev`가 Electron을 열고 `dev:renderer`는 Electron 통로 없는 브라우저 미리보기다.

## 현재 연결

받은 목록·텍스트 본문·Gmail 새로고침·분류/요약·제안 패널·할 일·프로필·초안/수정·검색/답변·주간 보고·AI 설정이
실제 main/preload API 통로로 연결되어 있다. 서버·DB·계정·모델 설정이 필요하며 '코드 연결됨'은 실환경 검증과 다르다.
최초 Google 연결은 CLI다. 온보딩 Google·다음 버튼은 여전히 비활성이며 5단계 완료를 저장하지 않는다.

## 보안 경계와 제한

- 화면은 Gmail·DB·LLM·서버를 직접 fetch하지 않는다. renderer → 제한된 preload IPC → main → 로컬 서버다.
- main만 절대 경로의 토큰 파일(일반 파일·최대 256바이트·POSIX 600)을 읽는다. 토큰 내용은 renderer/로그에 넘기지 않는다.
- 서버 주소는 loopback HTTP의 루트 주소만 허용하고 리디렉션을 따르지 않는다. IPC는 창·상위 프레임·URL·인수를 검증한다.
- 현재 창 닫기는 앱 종료다. 트레이·OS 알림·자동 실행·메일 발송·보관/삭제·주기 수신은 미구현이다.
- 프로필 자동 미리보기는 Claude 기본값·동의가 있으면 외부 전송/과금될 수 있다. 생성 버튼만 주의하면 충분한 상태가 아니다.
- Windows는 제품 목표이나 이번 신규 OS별 설치 전체 검증은 미실행. 설치용 DMG/EXE·자동 업데이트는 제공하지 않는다.

## 검사 안내

명령은 setup.md의 개발자용 검사로 통일한다. Vitest는 합성 데이터, Chromium은 합성 IPC 화면,
`test:mail-read`는 FastAPI+합성 저장소+Electron 검사다. 실제 Google·사용자 DB 성공과 구분한다.
`test:electron`/`test:mail-read`는 그래픽 환경이 필요하다. Playwright Electron 검사는 OS sandbox를 끄므로
OS sandbox 검증이 아니다. 두 smoke 스크립트의 옛 IPC/버튼 기대값은 [통합 수정](../../docs/dev/integration-followups.md)이 필요하며 이번에는 실제 Electron 창 검증을 완료하지 못했다. Windows 고유 동작·실제 모델 품질·속도는 별도 검사한다.

[현황판](../../docs/dev/progress.md) · [이번 검증](../../docs/dev/verification-2026-11-24.md) ·
[과거 앱 README](../../docs/dev/archive/2026-11-24/desktop-readme-before.md) · [브랜드 리소스](resources/README.md)
