# F0 첫 실행·기본 메일함 — 상태

## 양식 요약

> 양식: [status-template.md](status-template.md) · 현황판: [progress.md](progress.md)

| 항목 | 내용 |
| --- | --- |
| 브랜치 | `feat/F0-mailbox` |
| 작업 도구 | 없음 (Claude 작업 후 인수인계) |
| 상태 | PR 대기 → develop 병합 승인됨 (새로고침 Gmail 가져오기·F2/F3 진입 단위) |
| 마지막 커밋 | 이번 커밋 — [F0] 새로고침을 Gmail 새 메일 가져오기로 바꾸고 F2·F3 화면 진입 연결 |
| 기준 develop | `c8951a1` (F2 공통 패치 #16 포함, 빨리감기 통합·충돌 없음) |
| 미커밋 변경 | 없음 |
| 갱신일 | 2026-11-19 |

## 현재 상태

- 완료(develop): 데스크톱 실행 기반·첫 실행 시작 화면(#3), 받은 메일 목록·텍스트 본문 표시(#10).
- 이번 단위(2026-11-19, Claude):
  - 서버 `POST /mails/sync`(`app/api/mail_sync.py`): CLI `gmail_mail sync`와 같은 `synchronize()`를 재사용해
    사용 시작 이후 받은편지함 메일만 저장하고 중복은 건너뛴다. 기존 Bearer·loopback·Origin 규칙 재사용,
    같은 서버 동시 실행 409, Gmail 실패 502(상세 미포함), DB·계정 503. 응답은 건수만.
  - 앱 새로고침: "Gmail에서 새 메일 확인 중…"(버튼 잠금) → 성공 시 "새 메일 N건"·목록 재조회,
    실패 시 기존 목록 유지 + 오류 + [새 메일 다시 가져오기]. 인증 실패는 연결 해제로.
    main/preload 연결(패치 02) 전에는 저장된 목록만 다시 읽고 "Gmail 가져오기 연결 준비 중"으로 안내.
  - F2·F3 진입(S03): 사이드바 [설정] → `/settings/profile`, 메일 읽기 도구 줄 [◆ 답장 초안 만들기] → `/reply/:mailId`,
    상단 자연어 검색창(`Ctrl K` 포커스) Enter → `/search?q=`. F0 쪽 경로 부품 `features/mailbox/routes.tsx`
    (`MailboxRoute` = `/mail/inbox/:mailId?`, `SearchRoute`, `unavailableSearchClient`).
- 공통 영역은 `patches/F0/01~05`로만 남김(미적용). `/search` 경로는 패치 03 적용 전에는 받은편지함으로 돌아간다.
- S04 제안 패널(F5)은 F5 미착수라 만들지 않았다. S04의 회신 초안 진입은 S03 도구 줄 버튼과 같은 경로다.
- 미구현: 작성·발송, 보관·삭제·스팸, 트레이·알림, F1 AI 표시, F2·F3 서버 통로(IPC), 주기 자동 수신.

## 검사 결과

2026-11-19, 이 환경(Claude):

| 검사 | 결과 |
| --- | --- |
| 서버 `ruff check`·`ruff format --check` | 통과 |
| 서버 `pytest` | 221 통과, 90 skip (실제 PostgreSQL 필요 — 이 환경에 DB 없음, 미실행) |
| 신규 `tests/test_mail_sync_api.py` | 12개 통과 (합성 저장소·클라이언트: 성공·중복·인증·Origin·409·502·503·500·동시 요청) |
| 데스크톱 `lint`·`typecheck` | 통과 |
| 데스크톱 `test` | 7개 파일 77개 통과 (새로고침 8개·진입 4개 추가) |
| 패치 01~05 `git apply --check` | 통과 |
| 패치 적용 사본 | 서버 ruff·pytest 221 통과/90 skip, 데스크톱 tsc·eslint 통과·vitest 80개 통과 |

미실행: 실제 Gmail로 새로고침 수신, Electron 실제 창 확인, 화면 목업 대조(스크린샷), 실제 DB 검사.

## 공통 영역 요청

`patches/F0/README.md` 참고. 통합 채팅에서 적용한다.

1. 01 서버 등록: `main.py`에 `register_mail_sync`, `run_mail_api.py`에 `MailSyncContext(GmailSyncRepository, GmailMailClient)` 조립.
2. 02 main/preload: `MailAPIClient.sync()`, `klover:mail:sync` IPC, preload `mail.sync`.
3. 03 App 경로: `/mail/inbox/:mailId?`, `/search`, `searchClient` 주입 자리.
4. 04 공유 타입 재생성(`pnpm gen:api-types`), 05 api.md·mail-read-api.md 문구.
5. 남은 요청(다음 단위): F2·F3용 main/preload IPC 클라이언트를 `App`의 `f2Client`·`searchClient`로 연결.

## 다음 할 일

1. 통합 채팅에서 `patches/F0` 적용 후 맥북에서 새로고침으로 실제 Gmail 새 메일 수신 확인 (`docs/dev/F0-mailbox-run.md`)
2. F2·F3 서버 통로(IPC) 연결
3. 작성·보관·삭제 단위 진행

## 인수인계 메모

- 멈춘 지점: 이번 단위 구현·검사·커밋 완료. PR → develop 병합(사용자 승인).
- 주의할 점: 패치는 `c8951a1` 기준이다. develop이 바뀌면 `git apply --check`부터 다시 한다.
