# F0 채팅에 보낼 연결 요청

> 과거 전달·검사 기록을 포함한다. 2026-11-24 현재 API/IPC·F1 입력·F4 AI 통합은 PR #37까지 반영됐다. 미연결·패치 적용 요청은 당시 기록이며 현재 작업 상태는 [progress.md](progress.md)와 각 status, 실행은 [setup.md](setup.md)를 따른다. 기존 패치를 재적용하지 않는다.

서버 단위의 develop 병합과 맥북 `check_mail_api` 확인이 끝난 뒤 아래 문장을 그대로 보낸다.
실제 원격 커밋·코드를 확인하고 연결해야 하며, 이 문서 자체는 화면 연결 완료 보고가 아니다.

---

최종 목표는 맥북에서 Klover 앱을 개발 실행해 실제 Gmail 메일 목록과 본문을 보는 것이야.
Windows 앱 목표는 유지하고, 이번에는 맥북 실행과 읽기 전용 화면 연결만 진행해줘.

저장소는 choi7614/klover_my_prototype야. 최신 원격 develop과 기존 F0 브랜치·PR·코드를
직접 확인하고 AGENTS.md·CLAUDE.md·F0 명세·S02/S03 화면 정의와 목업·디자인 토큰을 읽어줘.
기존 F0 브랜치를 보존해 재사용하고, develop이 자동 반영됐다고 가정하지 마.
통합이 필요하면 범위와 적용 결과를 검토할 수 있게 준비하고 묶음 승인을 받아줘.

서버 연결 계약은 docs/dev/mail-read-api.md, docs/architecture/api.md,
packages/api-types의 실제 OpenAPI·생성 TS를 기준으로 해줘.

- 서버에는 로컬 Bearer 인증의 GET /auth/session, GET /mails?box=inbox&limit=20&cursor=…,
  GET /mails/{mail_id}가 있어. 계정 이메일·받은 목록·선택 메일의 일반 텍스트 본문을 표시해줘.
  limit는 1~100, 응답은 items와 next_cursor이며 마지막 페이지는 null이야.
- Electron main만 KLOVER_API_TOKEN_FILE의 파일을 읽어 Authorization 헤더에 토큰을 붙여줘.
  경로는 맥북 저장소의 .local-secrets/mail-api-token이고 토큰 값은 출력·노출하지 마.
  KLOVER_API_BASE_URL 기본값은 http://127.0.0.1:8000이며 로컬 HTTP 주소만 허용해줘.
  토큰을 Google JSON·암호화 키·OAuth 토큰과 혼동하지 마.
- API가 Origin 헤더를 거부하므로 renderer 직접 fetch나 CORS 우회를 하지 마.
  main의 Node fetch와 제한된 typed IPC/preload bridge로 계정·목록·본문 조회만 연결해줘.
  IPC 인수와 요청 창을 검증하고 임의 URL·경로·헤더·파일 읽기 기능을 열지 마.
  토큰은 renderer·preload 응답·로그에 포함하지 마.
- 공유 TS 타입을 재사용하고 로딩·빈 목록·오류·연결 부족·다음 페이지·DB 목록 새로고침을 표시해줘.
  서버가 준 body_text는 글자로 렌더링하고 HTML 삽입·원격 이미지 로딩은 하지 마.
- 이미 Gmail 연결은 완료했으므로 재연결·키 재생성·DB 초기화 없이 열람해야 해.
  기존 첫 실행 화면을 보존하면서 연결된 계정의 메일 화면으로 진입하게 해줘.
  미구현 프로필·알림 설정·AI를 완료한 것처럼 표시하거나 5단계 전체를 가짜 완료 처리하지 마.
- 수신은 기존 서버 CLI gmail_mail sync로 실행해. 앱 새로고침은 DB 재조회이며
  자동 수신·발송·보관·삭제·읽음 변경은 이번에 추가하지 마.
- 앱에서 Gmail·DB에 직접 접근하지 말고 서버 API·DB·계정·키·기존 메일·수신 기능을 보존해줘.
  계약을 바꿔야 하면 먼저 공통 서버 채팅에 전달할 구체적인 변경 요청을 작성해줘.

합성 데이터로 API·IPC·화면을 검사하고 실제 맥북 확인과 자동 검사를 구분해 보고해줘.
변경·검사 보고 후 로컬 통합·커밋·Push·PR 생성은 묶어서 승인받아줘.
develop과 main 병합은 각각 따로 승인받고 기존 브랜치를 보존해줘.
완료하면 docs/dev/mail-read-api.md의 서버·앱 터미널 실행 순서와 실제 환경 변수 계약이
맞는지 확인하고, 비개발자인 내가 복사해서 실행할 최종 명령을 단계별로 알려줘.
