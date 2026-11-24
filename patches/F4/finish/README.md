# F4 앱 사용 마무리 — 적용 전 공통 변경안

기준: origin/develop `7668d94aa5f251541d95e17c9ed238fabc52b418` (PR #41).
01~05 패치는 이미 적용되었거나 후속 코드로 대체됨. 재적용 금지.

## 적용 순서 (통합 채팅)

1. 이번 F4 전용 client/page/test 변경을 먼저 가져온다.
2. `git apply --check patches/F4/finish/06-navigation-draft-scope.patch` 후 적용한다.
3. 앱 typecheck/lint/test/build 및 받은편지함→설정→주간 보고 왕복을 검사한다.
4. docs/dev/F4-app-finish-handoff.md의 맥북 절차를 실행한다.

패치 대상:
- app.tsx: 인증된 user_id/account_id 조합을 draftScope로 전달. 화면 복귀 편집본의 계정 격리에 필수.
- profile-draft/routes.tsx: 기존 onNavigate 포트를 주간 보고 경로에 연결. 기존 프로필의 미저장 확인을 그대로 사용.
- ai-settings-page.tsx: 주간 보고로 돌아가는 링크.

main/preload·서버 등록·DB·공유 타입·잠금 파일 변경 없음. 기존 통로 재사용.
실제 공통 파일에는 적용하지 않았다. 별도 /workspace/f4-patch-check에서만 적용 검증했다.
메모리 보존은 앱 실행 중 같은 연결 포트·같은 사용자/계정 복귀에 한정된다.
앱 종료/새로고침 전에는 서버 저장이 필요하며 기존 beforeunload 확인을 유지한다.
