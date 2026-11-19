# F0 첫 실행·기본 메일함 — 상태

## 양식 요약

> 양식: [status-template.md](status-template.md) · 현황판: [progress.md](progress.md)

| 항목 | 내용 |
| --- | --- |
| 브랜치 | `feat/F0-mailbox` |
| 작업 도구 | 없음 |
| 상태 | develop 병합 ([#10](https://github.com/choi7614/klover_my_prototype/pull/10), `7a9d4dd`) |
| 마지막 커밋 | `abda40d` 2026-11-19 — [F0] 최신 develop 반영 후 재검사 결과와 현황판 갱신 |
| 기준 develop | `19e0161` (통합 채팅에서 로컬 통합, 충돌 없음) |
| 미커밋 변경 | 없음 (원격 기준) |
| 갱신일 | 2026-11-19 |

## 현재 상태

- 완료(develop): 데스크톱 실행 기반과 첫 실행 시작 화면(#3).
- develop 병합(#10): 로컬 인증으로 받은 메일 목록·텍스트 본문 표시, main 프로세스 메일 클라이언트·IPC,
  메일함 화면과 검사, 실행 안내 `docs/dev/F0-mailbox-run.md`.
- 통합(#16): F2 화면 경로(`/settings/profile`, `/reply/:mailId`)를 App에 등록. 돌아가기는 `/mail/inbox`. 단 메일함에서 그 화면으로 가는 버튼과 F2용 IPC는 아직 없다.
- 미구현: 작성·발송, 보관·삭제·스팸, 트레이·알림, F1 AI 표시, F3·F2 화면 진입 버튼, F2용 IPC 연결.

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
  통합 채팅에서 확인함: develop과 충돌 없음, #10으로 병합. F2 `03-screen-routes`는 `app.tsx`에 수동으로 합쳤다(#16).
- 남은 요청: F2용 main/preload IPC 클라이언트(F0의 메일 IPC와 같은 방식)를 만들어 `App`의 `f2Client`로 넘긴다.

## 다음 할 일

1. 메일함에서 F2 화면(프로필·답장 초안)과 F3 검색 화면으로 가는 진입 연결, F2용 IPC 연결
2. 맥북에서 실제 Gmail 목록·본문 표시 확인 (`docs/dev/F0-mailbox-run.md`)
3. 작성·보관·삭제 단위 진행

## 인수인계 메모

- 멈춘 지점: PR #10 develop 병합 완료
- 주의할 점: 이어받으면 develop과의 차이를 먼저 확인한다.
