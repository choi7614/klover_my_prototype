# F0 첫 실행·기본 메일함 — 상태

## 양식 요약

> 양식: [status-template.md](status-template.md) · 현황판: [progress.md](progress.md)

| 항목 | 내용 |
| --- | --- |
| 브랜치 | `feat/F0-mailbox` |
| 작업 도구 | 없음 |
| 상태 | PR 대기 ([#10](https://github.com/choi7614/klover_my_prototype/pull/10), 최신 develop 반영·재검사 통과) |
| 마지막 커밋 | `353b594` 2026-11-19 — [F0] 최신 develop(F1·F2·F3·공통 규칙) 반영 |
| 기준 develop | `19e0161` (통합 채팅에서 로컬 통합, 충돌 없음) |
| 미커밋 변경 | 없음 (원격 기준) |
| 갱신일 | 2026-11-19 |

## 현재 상태

- 완료(develop): 데스크톱 실행 기반과 첫 실행 시작 화면(#3).
- PR #10(미병합): 로컬 인증으로 받은 메일 목록·텍스트 본문 표시, main 프로세스 메일 클라이언트·IPC,
  메일함 화면과 검사, 실행 안내 `docs/dev/F0-mailbox-run.md`.
- 미구현: 작성·발송, 보관·삭제·스팸, 트레이·알림, F1 AI 표시, F3·F2 화면 진입 연결.

## 검사 결과

최신 develop(`19e0161`) 반영 후 재검사 (2026-11-19, 통합 채팅):

| 검사 | 결과 |
| --- | --- |
| 서버 `ruff check`·`ruff format --check` | 통과 |
| 서버 `pytest` | 209 통과, 90 skip (실제 PostgreSQL 필요 검사 — 이 환경에 DB 없음, 미실행) |
| 데스크톱 `lint`·`typecheck` | 통과 |
| 데스크톱 `test` | 7개 파일 65개 통과 |

실제 Gmail·Electron 실행 확인(`docs/dev/F0-mailbox-run.md`)은 이번 통합에서 실행하지 않았다.

## 공통 영역 요청

- PR #10은 `src/main`·`src/preload`·`renderer/app.tsx`·`pnpm-lock.yaml`(`@klover/api-types` 연결 3줄)을 바꾼다.
  통합 채팅에서 확인함: develop과 충돌 없음. 단 F2 `patches/F2/03-screen-routes.patch`는 F0 반영 후 `app.tsx`에
  그대로 적용되지 않으므로 통합 채팅(`integrate/F2-patches`)에서 수동으로 합친다.

## 다음 할 일

1. PR #10 develop 병합 (사용자 승인됨: 검사 통과 시 진행)
2. F2 화면 진입(프로필·답장 초안)과 F3 검색 화면 진입 연결
3. 작성·보관·삭제 단위 진행

## 인수인계 메모

- 멈춘 지점: 최신 develop 반영·재검사 완료, PR #10 병합 대기
- 주의할 점: 이어받으면 develop과의 차이를 먼저 확인한다.
