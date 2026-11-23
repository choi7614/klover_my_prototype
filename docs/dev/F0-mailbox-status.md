# F0 첫 실행·메일함 — 현재 상태

## 현재 상태 — 2026-11-24 통합 작업

- 작업: `integrate/local-ai-mail-history` · Codex · 기준 `origin/develop 5e2b7a7`(PR #38).
- 메일함에서 기간 선택 가져오기 화면으로 이동한다. 고정 IPC·서버 인증·중복/중단/재개를 연결했다. Electron 검사 기대값은 현재 IPC와 새로고침으로 수정했으나 네이티브 실행은 미검증이다.
- 서버 590개(분리 PostgreSQL, skip 0), 앱 185개, 합성 Chromium 4개 통과. Ruff·lint·typecheck·빌드 결과는 [통합 검증 기록](verification-local-ai-history.md)을 따른다.
- 실제 사용자 DB·Gmail·Ollama·유료 Claude·네이티브 Electron은 미실행이다.
- 기존 기능 브랜치·키·메일·설정은 보존했다. 이번 변경은 **미커밋·미Push·PR 없음**, 묶음 승인 대기다. develop/main 병합은 각각 별도 승인이다.
- 다음 할 일: 승인 후 PR 제출, develop 병합 별도 검토, [맥북 업데이트/실기 확인](local-ai-history-run.md). 이미 반영된 과거 공통 패치는 재적용하지 않는다.

<details>
<summary>PR #38 당시 요약 — 이번 작업 전 기준</summary>

> 2026-11-24 · 실제 기준 `origin/develop f498d27` · PR #37 병합 확인 · 이번 작업은 문서만 수정

## 현재 구현과 남은 일

- 구현·자동 검사 완료: 앱 목록·본문·Gmail 새로고침·F1 분석 표시·F2/F3/F4/F5 진입과 IPC는 연결됨(#18·#19·#23·#28·#34·#37).
- 남은 일·실환경 제한: 앱 Google 연결·다음 버튼, 5단계 완료, 작성·발송·보관·삭제·주기 수신·Windows 동작은 미구현. 실제 신규 사용자 전체 흐름은 미검증.
- 새 설치·평소 실행·업데이트는 [setup.md](setup.md), 공통 확인 수준은 [현황판](progress.md)·[이번 검증](verification-2026-11-24.md)을 따른다.
- 과거의 '미연결/미커밋/승인 대기'는 아래 당시 기록이다. PR #37과 기존 공통 패치는 이미 병합되어 재적용하지 않는다.
- 확정된 개발 예정: 기간 선택 과거 메일 가져오기, Claude→로컬 1회 자동 재시도, 로컬 전용 모드. 모두 현재 미구현이며 이번에 코드를 변경하지 않는다.

</details>

<details>
<summary>이전 기능 브랜치·검사·인수인계 기록 (현재 실행 지시 아님)</summary>

# F0 첫 실행·기본 메일함 — 상태

## 최신 통합 작업 (2026-11-20, Codex)

- 기준 develop `e5f7efd`(PR #36 포함), 작업 `integrate/ai-provider-selection`.
- 이 아래의 이전 기능 브랜치·검사·미연결 설명은 당시 기록이다. 이번 구현과 검증은
  [AI 선택 안내](ai-provider-selection.md)를 우선한다.
- AI 설정/서버 실행/공유 타입/main·preload와 세 기능의 제공자 선택을 함께 연결한다.
  자동 분석·임베딩·제안은 로컬, 수동 초안·검색·보고서는 저장 기본값/요청 선택을 사용한다.
- 첫 주 보고 생성, 본문 인용 기반 답장 근거 검증도 포함한다. DB 마이그레이션은 없다.
- 검사: 분리 DB 포함 서버 575 통과/skip 0, 앱 182·Chromium 합성 화면 3 통과, lint·typecheck·Ruff·빌드 통과. 실제 Claude/맥북 검사는 미실행.
- 현재 미커밋 작업이 이 통합 브랜치에 있다. 커밋·Push·PR 생성은 묶음 승인 대기이며,
  기존 기능 브랜치는 변경하지 않는다. 맥북·실제 Claude 검사는 별도로 남는다.


## 양식 요약

> 양식: [status-template.md](status-template.md) · 현황판: [progress.md](progress.md)

| 항목 | 내용 |
| --- | --- |
| 브랜치 | `feat/F0-mailbox` |
| 작업 도구 | 없음 |
| 상태 | develop 병합 (#17), 공통 패치 `patches/F0` 01~05 적용 ([#18](https://github.com/choi7614/klover_my_prototype/pull/18), `integrate/F0-patches`) |
| 마지막 커밋 | `438b29d` 2026-11-19 — [F0] 새로고침을 Gmail 새 메일 가져오기로 바꾸고 F2·F3 화면 진입 연결 |
| 기준 develop | `4b24378` (#17 병합, 공통 패치는 이 위에 적용) |
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
- 공통 패치 적용(통합 채팅, `integrate/F0-patches`): 서버 `POST /mails/sync` 등록·로컬 실행 명령 조립(01),
  main/preload `mail.sync` IPC(02), App 경로 `/mail/inbox/:mailId?`·`/search`(03), 공유 타입 재생성(04), api 문서(05).
  이제 앱 새로고침이 서버를 거쳐 실제로 Gmail 새 메일을 가져온다(실제 Gmail 확인은 미실행).
  `/search`는 F3 IPC가 없어 '준비 부족' 클라이언트로 열린다.
- F1 분류·요약 표시(2026-11-19, Claude, `feat/F1-mail-analysis`에서 F0 파일 변경): `mailbox-page.tsx`에 선택 prop
  `analysis`(F1 통로)를 추가해 목록 한 줄에 ◆ 요약·분류·회신 필요·마감 태그, 읽기 영역에 AI 요약 박스와 대기·실패 상태를 보여 준다.
  `routes.tsx`의 `MailboxRoute`가 그대로 전달한다. 통로가 없으면 기존 모양 그대로. 서버 `app/api/mail_sync.py`에
  `MailSyncContext.after_sync`(저장 성공 뒤 F1 자동 분석 신호, 응답 형식 변경 없음)를 추가했다. 공통 연결은 `patches/F1/05·07`.
  자세한 내용은 [F1-analysis-status.md](F1-analysis-status.md).
- S04 제안 패널(F5)은 F5 미착수라 만들지 않았다. S04의 회신 초안 진입은 S03 도구 줄 버튼과 같은 경로다.
- 미구현: 작성·발송, 보관·삭제·스팸, 트레이·알림, 주기 자동 수신. (F1 AI 표시는 F1 브랜치에서 구현, 공통 패치 F1/07 적용 전)

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

공통 패치 01~05 적용 후 (2026-11-19, 통합 채팅, `integrate/F0-patches`, 기준 `4b24378`):

| 검사 | 결과 |
| --- | --- |
| 패치 `git apply --check` | 01~05 모두 통과, 충돌 없음 |
| 04 공유 타입 | `pnpm gen:api-types` 재생성 결과가 패치 04와 동일 |
| 서버 `ruff check`·`ruff format --check` | 통과 |
| 서버 `pytest` | 221 통과, 90 skip (실제 PostgreSQL 필요 — 이 환경에 DB 없음, 미실행) |
| 데스크톱 `lint`·`typecheck` | 통과 |
| 데스크톱 `test` | 7개 파일 80개 통과 |
| `packages/api-types` typecheck | 통과 |
| `alembic heads` | `0004_f2` 하나 (DB 변경 없음) |

미실행: 실제 Gmail 새로고침 수신, Electron 실제 창, 실제 DB.

## 공통 영역 요청

`patches/F0/` 01~05 적용 완료(통합 채팅, `integrate/F0-patches`). 기록: `patches/F0/README.md`

1. 01 서버 등록: `main.py`에 `register_mail_sync`, `run_mail_api.py`에 `MailSyncContext(GmailSyncRepository, GmailMailClient)` 조립.
2. 02 main/preload: `MailAPIClient.sync()`, `klover:mail:sync` IPC, preload `mail.sync`.
3. 03 App 경로: `/mail/inbox/:mailId?`, `/search`, `searchClient` 주입 자리.
4. 04 공유 타입 재생성(`pnpm gen:api-types`), 05 api.md·mail-read-api.md 문구.
5. F2·F3용 main/preload IPC 연결: 완료(통합 채팅, `integrate/F2-F3-ipc`). `App`이 `window.klover.f2`·`search`가 있으면 실제 연결, 없으면 '준비 부족'.

## 다음 할 일

1. 맥북에서 새로고침으로 실제 Gmail 새 메일 수신 확인 (`docs/dev/F0-mailbox-run.md`)
2. 맥북에서 실제 앱으로 프로필 저장·답장 초안·검색 흐름 확인 (F2·F3 통로 연결됨). 선택: `shared/mail-read.ts`의 수동 `MailSyncResult`를 생성 타입으로 교체
3. 작성·보관·삭제 단위 진행

## 인수인계 메모

- 멈춘 지점: 공통 패치 01~05 적용·검사 완료.
- 주의할 점: F2·F3 통로(`main/f2-*.ts`, `main/search-ipc.ts`)는 `mail-ipc.ts`의 `trustedMailSender`와 `mail-client.ts`의 `readLocalAPI`(토큰 읽기)를 함께 쓴다. 바꿀 때 세 통로를 같이 검사한다.

</details>
