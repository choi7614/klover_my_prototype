# 데이터 모델

> 2026-11-25 Calendar 공통 통합: `0009_f5_calendar`(부모 `0008_history`)의 별도 암호화 자격 증명 표와
> 인증된 `GET /calendar/connection`, `POST /calendar/disconnect`, 제한된 앱 동의 IPC를 추가했다.
> 기존 Gmail 자격 증명은 보존한다. [통합 검증·제약](../dev/settings-calendar-integration.md)을 따른다.


## 0008_history (2026-11-24)

`mails.history_imported` boolean NOT NULL default false: 명시적 수집만 true로 저장한다.
`history_import_jobs`: job_id, user_id/account_id 소유 FK, payload(JSONB: 기간·진행·페이지·실행 번호).
부모는 0007_f1. 기존 키·시작 시점·커서·메일을 보존한다. 현재 이력 적용은 명시적 명령으로만 한다.
[체크포인트·동시 실행·기간 정책](../dev/local-ai-history-run.md)을 따른다.

## 현재 구현된 저장 구조

0001 사용자/계정/메일 → 0002 Google 암호문 → 0003_search_runs → 0004_f2 프로필/학습 저장 경계/초안 →
0005_f5 제안/할 일/알림 outbox → 0006_f4 보고 스냅샷 → **0007_f1 분석/청크·벡터/분류 피드백**까지 develop에 반영됐다. 이번 작업 브랜치는 0008_history를 추가했다.
F4의 `F1ReportMailRepository`와 F2 프로필 어댑터는 실제 실행 서버에 연결되어 있다.
목표 표의 모든 열·작업자가 구현된 것은 아니며 아래 날짜별 초기 단위는 당시 기록으로 읽는다.
새 설치·업데이트·백업은 [setup.md](../dev/setup.md), 현재 범위는 [현황판](../dev/progress.md)을 따른다.

기간 선택 과거 메일 가져오기는 작업 브랜치에 구현됐다(develop 반영 PR #39(사용자 병합 승인 완료)). 기존 저장·조회·검색·보고의 시작 시점 경계와
중복 방지를 함께 정비했으며 기존 계정/키/메일을 초기화하거나 시작 시점을 수동 변경하지 않는다.
AI 설정·Claude 키는 DB 표가 아니라 서버 `.local-secrets/ai-settings.enc`와 별도 `ai-settings.key`에 저장한다.

## 날짜별 구현 기록과 목표 스키마

## 최소 저장 단위 (2026-11-18)

사용자의 DB 기반 준비 요청에 따라 아래 부분만 초기 마이그레이션으로 구현했다.
나머지 전체 설계는 계속 초안이며, 구현 시 후속 마이그레이션으로 추가한다.

- `users`: `user_id`(text PK), `created_at`(timestamptz).
- `mail_accounts`: `account_id`(text PK), `user_id`(FK), `source`(gmail/fixture),
  `email`, `sync_started_at`(timestamptz), `sync_cursor`(nullable text).
  이 최소 단위에는 토큰 열이 없다. 이후 Google 연결 단위의 별도 암호문 테이블은 아래에 설명한다.
- `mails`: 아래 목표 표 중 기본 ID·소유자·발신자·수신자·제목·본문·시간·읽음·메일함·분석 상태를 구현.
  AI 결과·첨부 메타데이터·보관 플래그 등 나머지 열은 후속 단위다.
- `mails.account_id`를 추가하고 `(account_id, user_id)` 복합 FK로 계정 소유자를 확인한다.
  소스는 해당 계정의 `source`를 참조하며 메일 행에 중복 저장하지 않는다.
- `(account_id, source_message_id)`는 유일하다. 중복 수신은 기존 메일 ID를 반환한다.
  서로 다른 계정은 같은 소스 메시지 ID를 사용할 수 있다.
- 저장소는 시간대가 있는 시각만 받고, 계정 사용 시작 시점보다 이른 메일은 저장하지 않는다.
  받은 메일 조회는 사용자 기준으로 분리하며 `(user_id, received_at, mail_id)` 인덱스를 둔다.
- 초기 마이그레이션은 사용자·계정·메일 테이블만 만든다. pgvector 이미지는 향후 벡터 확장을
  지원하지만 이번 단위는 확장·벡터 열·임베딩 모델을 선택하거나 생성하지 않는다.

초기 단위에서는 F4 어댑터가 없었다. 현재는 0007 분석 저장과 F4 실제 DB 어댑터까지 연결됐다.
실행·데이터 유지 방법은 [로컬 DB 안내](../dev/local-database.md)를 따른다.

## Google 연결 저장 단위 (2026-11-19)

위 최소 저장 단위 이후 `0002` 마이그레이션으로 `google_credentials`를 추가했다.
기존 사용자·계정·메일 테이블과 초기 마이그레이션은 보존한다.

- `account_id`: text PK/FK → mail_accounts.account_id.
- `token_ciphertext`: access/refresh 토큰·권한·만료 시각을 함께 암호화한 Fernet 문자열.
- `updated_at`: timestamptz. 키는 DB에 넣지 않고 맥북의 비공개 파일에 보관한다.
- 로컬 운영자 `local-development`의 테스트 Gmail 한 계정만 연결한다. 재연결은 기존
  계정 ID·sync_started_at·메일을 유지하며 토큰만 갱신한다. 기존 다른 계정을 덮어쓰지 않는다.

실제 계정 로그인은 사용자 맥북에서 성공을 확인했다. 새 수신·토큰 갱신의 실제 검증은 별도다.
[연결 안내](../dev/google-connection.md)를 따른다. 앱용 사용자 인증·메일 API·주기 수신은 후속 범위다.

## 새 받은 메일 저장 단위 (2026-11-19)

이전 연결 단위의 실제 로그인은 사용자 맥북에서 성공 확인했다. 이번 수신·갱신 확인은 별도다.
새 테이블·열·마이그레이션 없이 기존 구조를 사용한다. `sync_cursor`는 마지막으로 완료한
Gmail history ID다. 배치 시작에 확인한 ID를 저장해 실행 중 도착한 변경의 누락을 막고,
중복은 `(account_id, source_message_id)`로 제거한다. 시작 시점은 그대로 유지한다.
갱신 토큰 저장은 메일 배치와 별도 트랜잭션으로 먼저 확정하고, 메일·커서는 함께 저장한다.
계정/토큰 행 잠금으로 동시 수신·재연결과 토큰 갱신 충돌을 막는다.
처음 저장할 때 cc·is_read도 반영한다. 조회는 사용자와 계정을 함께 제한한다.
[수신 안내](../dev/gmail-mail-sync.md)를 따른다.

이 문서는 공유 영역이다. 변경·승인은 AGENTS.md의 공통/통합 채팅 규칙을 따른다.

## F3 최근 검색 저장 단위 (2026-11-19)

`0003_search_runs`는 기존 메일·계정·Google 암호문을 바꾸지 않고 최근 검색 테이블만 추가한다.
공통 `models.py`는 보존하고 F3 전용 메타데이터를 Alembic에 함께 등록한다.

- `search_id`: 32자리 임의 ID, text PK.
- `user_id`, `account_id`: text, `(account_id, user_id)` 복합 FK → `mail_accounts`.
- `query`: 원래 검색 질문. 메일 원문·토큰은 저장하지 않는다.
- `parsed`, `overrides`: jsonb, 검증된 기준 해석과 명시적 수정·삭제 값.
- `reference_date`: text, 최초 해석의 한국 기준 날짜 `YYYY-MM-DD`.
- `created_at`: timestamptz. 사용자·계정·시각의 인덱스로 최근 질문을 찾는다.

다른 사용자·계정의 검색 ID는 재사용할 수 없다. 실제 DB 적용은 별도 실행해야 하며,
이 작업에서는 격리된 합성 테스트 DB에서만 마이그레이션과 보존 여부를 검사했다.
[F3 전달 문서](../dev/F3-search-handoff.md)를 따른다.

## 원본 목표 테이블 개요 (실제 명칭·열은 마이그레이션 기준)

| 테이블 | 내용 | 주 사용 기능 |
| --- | --- | --- |
| `users` | 사용자, 계정 연결 정보 | 전체 |
| `mail_accounts` | 연결된 메일 계정, OAuth 토큰(암호화), 동기화 시작 시점·커서 | F0 |
| `mails` | 메일 1건 = 1행. 기본 정보 + AI 메타데이터 | F0, F1 |
| `mail_chunks` | 메일 본문 청크 + 임베딩 벡터 (메일 1건 = 여러 행) | F1, F2, F3 |
| `search_runs` | F3 최근 질문·검증된 해석·조건 수정 기록 | F3 |
| `category_feedback` | 사용자의 카테고리 수정 이력 | F1 |
| `profiles` | 기본 정보, 문체 설정, 주간 보고 양식 | F2, F4 |
| `style_learnings` | 보낸 메일에서 학습한 문체 결과 | F2 |
| `drafts` | 답장 초안과 근거 | F2 |
| `suggestions` | AI 스캔 제안 (일정·할 일·회신 등) | F5 |
| `todos` | 앱 안 할 일 | F5 |
| `weekly_reports` | 생성한 주간 보고 | F4 |
| `notification_settings` | 알림 유형별 켜기/끄기, 시작 프로그램 | F0, F5 |

## mails

| 컬럼 | 타입 | 설명 |
| --- | --- | --- |
| `mail_id` | text PK | Klover 내부 ID (소스 ID와 별도) |
| `source` | text | `gmail` / `fixture` / (`imap`, `exchange`) |
| `source_message_id` | text | 소스의 메시지 ID |
| `thread_id` | text | 스레드 ID |
| `user_id` | FK | 소유 사용자 |
| `direction` | text | `received` / `sent` |
| `mailbox` | text | `inbox` / `sent` / `draft` / `archive` / `spam` / `trash` |
| `from_addr`, `from_name`, `from_org` | text | 발신자 (조직은 서명·주소록에서 추정) |
| `to`, `cc` | jsonb | `[{addr, name, org}]` |
| `subject` | text | 제목 |
| `body_text` | text | 전처리된 본문 (인용·서명 제거) |
| `body_html` | text | 원문 HTML (화면 표시용) |
| `received_at` | timestamptz | 수신·발신 시각 |
| `attachments` | jsonb | `[{filename, mime, size}]` |
| `is_read` | bool | 읽음 여부 |
| `archived` | bool | 보관 여부 — 예이면 삭제 전까지 유지 |
| `analysis_status` | text | `pending` / `done` / `failed` |
| `category` | text | 고정 7종 중 하나 (아래) |
| `user_label` | text null | 사용자가 바꾼 카테고리 (있으면 이 값이 우선) |
| `summary` | text | 1~2줄 요약 |
| `action_items` | jsonb | `[{text, due: "YYYY-MM-DD" \| null}]` |
| `needs_reply` | bool | 회신 필요 여부 |
| `replied` | bool | 내가 회신했는지 (보낸 메일과 스레드로 판단) |
| `priority` | text | `high` / `normal` / `low` |
| `priority_reason` | text | 예: "팀장 참조, 마감 2일 이내" |
| `entities` | jsonb | `{projects: [], orgs: [], people: []}` |
| `events` | jsonb | `[{title, start, end, location}]` |

카테고리 값: `업무 요청` `회의·일정` `결재·승인` `보고·공유` `공지` `외부·고객` `뉴스레터·광고`
(코드에서는 `work_request` `meeting` `approval` `report_share` `notice` `external` `newsletter` 영문 키를 쓰고, 화면에서 한글로 표시)

## mail_chunks

| 컬럼 | 타입 | 설명 |
| --- | --- | --- |
| `chunk_id` | PK | |
| `mail_id` | FK → mails | 메타데이터와 연결 |
| `kind` | text | `body` / `summary` |
| `seq` | int | 본문 내 순서 |
| `text` | text | 청크 텍스트 |
| `embedding` | vector(N) | N은 임베딩 모델에 따라 결정 |
| `received_at`, `category`, `user_id` | | 필터용 복사본 (벡터 검색과 조건 필터를 함께 쓰기 위해) |

## suggestions

| 컬럼 | 타입 | 설명 |
| --- | --- | --- |
| `suggestion_id` | PK | |
| `mail_id` | FK | 근거 메일 |
| `type` | text | `calendar` / `todo` / `reply` / `approval` / `important` |
| `payload` | jsonb | 예: `{title, start, end, location, calendar_id, conflicts: []}` |
| `evidence_spans` | jsonb | 본문에서 강조할 근거 문장 위치 |
| `status` | text | `pending` / `approved` / `dismissed` |
| `notified_at` | timestamptz null | 알림을 보낸 시각 (null이면 다음 실행 때 모아서 표시) |
| `created_at`, `resolved_at` | timestamptz | |

## profiles

| 컬럼 | 타입 | 설명 |
| --- | --- | --- |
| `user_id` | PK/FK | |
| `name`, `title`, `org`, `duties` | text | 이름, 직급, 소속, 담당 업무 |
| `frequent_contacts` | jsonb | 자주 연락하는 부서·회사 |
| `formality` | int 0~100 | 격식 수준 |
| `reply_length` | text | `short` / `normal` / `long` |
| `greeting`, `closing`, `signature` | text | 첫 인사, 마무리, 서명 |
| `style_learning_enabled` | bool | 문체 학습 동의 |
| `report_sections` | jsonb | 주간 보고 섹션 순서 |
| `report_recipient` | text | 보고 대상 |
| `report_style` | text | `bullet` (개조식) / `prose` (서술형) |

## 나머지 테이블

아래는 원본 설계의 나머지 표 목록이다. drafts·todos·weekly_reports·style_learnings와 F1 피드백은 후속 마이그레이션에 구현되어 있으며 실제 이름/열은 해당 이력을 따른다. notification_settings 등 전체 목표를 구현 완료로 해석하지 않는다.

## F4 보고 입력 조회 계약 (2026-11-12)

첫 단위의 `ReportMail`은 위 `mails`에서 보고에 필요한 열만 읽는 내부 모델이다.
당시 첫 단위는 DB 이력을 정의하지 않았다. 이후 0006/0007과 실제 F1/F2/F4 어댑터가 구현됐다.

- 필수: `mail_id`, `user_id`, `direction`, 시간대가 있는 `received_at`,
  `analysis_status`, `subject`, `body_text`, `from_addr`, `to`.
- 선택/분석 열: `thread_id`, `from_name`, `category`, `user_label`, `summary`,
  `entities`(`projects`, `orgs`, `people`). 분류 키는 기존 영문 키를 그대로 쓴다.
- 조회 인자: `user_id`, `start_at`(포함), `end_before`(미포함). `direction`은
  `received`/`sent`이며 다른 사용자나 기간 밖의 메일을 반환하지 않는다.
- 결과: 업무 그룹별 원문·`mail_ids`, 제외 메일과 분류 사유, 포함 범위.
  메일 ID는 중복 없이 유지하고 범위 수치는 결과에서 계산한다.

날짜 경계, 사용자 분류 우선순위, 분석 미완료 처리와 그룹 연결 규칙은
[F4 구현 계획](../dev/F4-weekly-report-plan.md)의 내부 계약을 따른다.

## F2 저장 구조 (0004_f2)

0004_f2는 profiles/style_learnings/drafts만 추가한다. 기존 테이블·행·키는 바꾸지 않는다.
모델은 app.db.f2_models의 별도 F2Base.metadata이며 공통 Base.metadata와 함께 검사한다.
profiles는 위 설계의 필드와 excluded_phrases(jsonb), version(int>=1)을 저장한다.
style_learnings는 user_id(PK/FK), payload(jsonb: status/analyzed_count/phrases/traits)를 저장한다.
실제 학습 수집·쓰기 작업자는 아직 없다. drafts는 draft_id(PK), user_id(FK·인덱스),
payload(jsonb: DraftState 전체), version(int>=1)을 저장한다. 사용자·버전 조건으로 갱신한다.
학습 기록 삭제는 해당 사용자 기록을 지우고 학습 동의를 끄며 프로필 버전을 올린다.
세부 계약과 F4 읽기 포트는 [F2 구현 안내](../dev/F2-profile-draft.md)를 따른다.


## F5 저장 구조 (0005_f5)

0004_f2 뒤에 0005_f5를 추가한다. 기존 0001~0004, F2 프로필/초안과 F3 검색 기록은 보존한다.
메일 소유자 복합 유일 제약 `uq_mail_f5_owner(mail_id,user_id,account_id)`를 추가한다.
F5 메타데이터(공통 테이블 복사본 포함), search_metadata, F2Base.metadata를 함께 비교한다.
목표 표의 suggestions/todos는 실제로 충돌을 피한 f5_ 접두사의 다음 테이블에 저장한다.

- f5_suggestions: suggestion_id PK, 소유 사용자/계정/메일 복합 FK, type(calendar/todo/reply),
  action_key/evidence_key, body_sha256, payload/evidence_spans(JSON), status,
  execution_status/execution_mode/execution_payload/execution_token/started_at/result/last_error,
  version, notified_at/created_at/resolved_at. 같은 메일·유형·행동 키 또는 근거는 유일하다.
- f5_todos: todo_id PK, 소유 사용자/계정, mail_id/suggestion_id(선택), request_id/request_payload,
  title/due/status(open/completed)/version/created_at/updated_at. 제안당 하나이며
  직접 생성은 사용자·계정·request_id로 중복을 막는다. 소유권 복합 FK가 있다.
- f5_suggestion_outbox: event_id PK, suggestion_id 유일, 소유자 복합 FK, created_at/delivered_at.
  제안 생성과 함께 저장하고 전달 확인 전까지 재조회한다.
- f5_dismissals: suggestion_id PK와 소유자 복합 FK, dismissed_at. 감지 기준 자동 조정은 하지 않는다.

status는 pending/approved/dismissed, execution_status는
idle/executing/failed/uncertain/blocked/simulated/succeeded다.
테스트 영수증은 approved가 되지 않는다. 불명확한 실행은 후속 권한 오류가 나도 입력 잠금을 유지한다.
실행 중 프로세스 종료는 수동 조정 대상이다. 기존 사용자·계정·암호문·메일·수신 커서는 변경하지 않는다.
이 이력을 운영 DB에 실제 적용했는지는 별도 확인하며, 자동 마이그레이션은 하지 않는다.

## F4 보고서 저장소 (공통 패치 적용 후)

`weekly_reports`: report_id(PK), user_id(FK), selection_key, revision, payload(JSONB).
(user_id, selection_key)는 유일하다. payload에는 account_id·프로필·대상 메일 스냅샷·
검증된 문서를 보관하며 저장 버전을 비교해 갱신한다. 조회·편집 때 사용자와 계정을
다시 확인한다. 기존 사용자·메일·계정·키·수신 커서는 수정하지 않는다.
신규 이력은 0006_f4, 현재 down_revision은 0005_f5다. 통합 직전 head가 바뀌면
예약 번호와 down_revision을 다시 확인해야 한다. 기존 이력은 수정하지 않는다.

## F1 분석·청크·분류 수정 저장소 (0007_f1, 공통 패치 적용 후)

목표 표의 `mail_chunks`·`category_feedback`와 mails의 AI 열은 실제로 `f1_` 접두사의
부속 테이블에 저장한다. mails의 기존 열·원문·수신 커서는 바꾸지 않는다.

- `f1_mail_analysis`: mail_id PK, 소유 (mail_id,user_id,account_id) → mails 복합 FK
  (기존 `uq_mail_f5_owner` 재사용, ON DELETE CASCADE). category/user_label(영문 7종),
  summary, action_items·entities·events·evidence_spans(JSONB), needs_reply, priority(+이유),
  failure_code, attempts(0~2), LLM·임베딩의 provider/model/mode(live/test)/dimensions, updated_at.
  유효 분류는 `user_label ?? category`다.
- `f1_mail_chunks`: chunk_id PK, kind(body/summary)·seq (mail_id,kind,seq 유일),
  text, embedding(pgvector `vector`, 차원 미고정 + `vector_dims(embedding)=embedding_dimensions`
  검사), 임베딩 provider/model/mode, 필터용 received_at·category. 인덱스
  `ix_f1_chunks_scope(user_id,account_id,received_at,category)`. 검색은 사용자·계정과 임베딩
  provider/model/dimensions를 반드시 제한한다. 기본 임베딩은 로컬 Ollama bge-m3(1024차원).
- `f1_category_feedback`: feedback_id PK, 소유 복합 FK, from_addr·subject·user_label·created_at.
  인덱스 `ix_f1_feedback_sender(user_id,account_id,from_addr,feedback_id DESC)`.

신규 이력은 0007_f1, down_revision은 0006_f4다. `CREATE EXTENSION IF NOT EXISTS vector`를
포함하므로 pgvector가 있는 DB(infra의 pgvector/pgvector:pg16)에서 실행한다. downgrade는
F1 테이블만 지우고 확장·메일은 남긴다. ORM 비교용 정의는 `app/db/f1_models.py`이며,
env.py·비교 검사는 F5 metadata 대신 이를 쓴다(공통·F5 테이블 포함).
