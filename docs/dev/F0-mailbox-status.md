# F0 첫 실행·기본 메일함 — 상태

## 양식 요약

> 양식: [status-template.md](status-template.md) · 현황판: [progress.md](progress.md)

| 항목 | 내용 |
| --- | --- |
| 브랜치 | `feat/F0-mailbox` |
| 작업 도구 | 없음 |
| 상태 | PR 대기 ([#10](https://github.com/choi7614/klover_my_prototype/pull/10), develop 미병합) |
| 마지막 커밋 | `02eab96` 2026-11-18 — [F0] 로컬 인증으로 Gmail 목록과 텍스트 본문 연결 |
| 기준 develop | `0f68ad1` (이후 F1·F3·F2가 develop에 병합되어 뒤처짐) |
| 미커밋 변경 | 없음 (원격 기준) |
| 갱신일 | 2026-11-19 |

## 현재 상태

- 완료(develop): 데스크톱 실행 기반과 첫 실행 시작 화면(#3).
- PR #10(미병합): 로컬 인증으로 받은 메일 목록·텍스트 본문 표시, main 프로세스 메일 클라이언트·IPC,
  메일함 화면과 검사, 실행 안내 `docs/dev/F0-mailbox-run.md`.
- 미구현: 작성·발송, 보관·삭제·스팸, 트레이·알림, F1 AI 표시, F3·F2 화면 진입 연결.

## 검사 결과

PR #10 브랜치 기준 검사는 해당 브랜치 문서(`docs/dev/F0-mailbox-run.md`)를 따른다.
최신 develop 반영 후 재검사는 아직 하지 않았다(미실행).

## 공통 영역 요청

- PR #10은 `src/main`·`src/preload`·`renderer/app.tsx`·`pnpm-lock.yaml`을 바꾼다. 공통 앱 골격·잠금 파일이므로
  develop 병합 전 통합 채팅에서 F2(`patches/F2/03-screen-routes.patch`)·F3 화면 연결과 충돌 여부를 확인한다.

## 다음 할 일

1. `feat/F0-mailbox`에 최신 `origin/develop` 로컬 통합 → lint·typecheck·test 재검사 (묶음 승인 필요)
2. PR #10 develop 병합 (별도 승인)
3. 작성·보관·삭제 단위 진행

## 인수인계 메모

- 멈춘 지점: PR #10 생성 후 병합 대기
- 주의할 점: develop보다 뒤처져 있으므로 이어받으면 먼저 차이를 확인한다.
