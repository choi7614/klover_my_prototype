# 데이터 모델

> 상태: 초안 — **4명이 함께 확정** 후 `apps/server/app/db/models.py`로 옮긴다 | 최종 수정: 2026-10-16

이 문서는 공유 영역이다. 바꿀 때는 팀 채널에 알리고 PR 리뷰를 받는다.

## 테이블 개요

| 테이블 | 내용 | 주 사용 기능 |
| --- | --- | --- |
| `users` | 사용자, 계정 연결 정보 | 전체 |
| `mail_accounts` | 연결된 메일 계정, OAuth 토큰(암호화), 동기화 시작 시점·커서 | F0 |
| `mails` | 메일 1건 = 1행. 기본 정보 + AI 메타데이터 | F0, F1 |
| `mail_chunks` | 메일 본문 청크 + 임베딩 벡터 (메일 1건 = 여러 행) | F1, F2, F3 |
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

`drafts`, `todos`, `weekly_reports`, `category_feedback`, `style_learnings`, `notification_settings`는 담당자가 해당 기능 구현 시 이 문서에 먼저 추가한 뒤 구현한다.

## F4 보고 입력 조회 계약 (2026-11-12)

첫 단위의 `ReportMail`은 위 `mails`에서 보고에 필요한 열만 읽는 내부 모델이다.
새 DB 테이블이나 마이그레이션을 정의하지 않는다. 실제 DB 어댑터는 아직 없다.

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
