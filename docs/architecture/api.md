# API 목록

> 2026-11-25 Calendar 공통 통합: `0009_f5_calendar`(부모 `0008_history`)의 별도 암호화 자격 증명 표와
> 인증된 `GET /calendar/connection`, `POST /calendar/disconnect`, 제한된 앱 동의 IPC를 추가했다.
> 기존 Gmail 자격 증명은 보존한다. [통합 검증·제약](../dev/settings-calendar-integration.md)을 따른다.


## AI 정책·과거 수신 API (2026-11-24)

AI 설정에 mode(local_only/hybrid)를 추가한다. 새 설정은 local_only, 기존 모드 없는 저장본은 hybrid로 보존한다.
생성 결과에 ai_execution(calls/used, fallback, reason)을 붙인다. 검색 스트림은 answer/answer_error에 포함한다.
자동 preview는 로컬 고정. Claude 연결 검사는 전환하지 않는다.
`GET /mail-history`는 최근 20개 작업, `POST /mail-history {start,end}`는 명시적 시작,
`POST /mail-history/{job_id}/{action}`은 pause/resume이다. 기존 loopback/Bearer/Origin 경계를 재사용한다.
진행 응답에서 내부 Gmail 페이지 토큰·페이지 체크포인트·실행 번호는 제외한다.
[기간·상한·취소·업데이트 계약](../dev/local-ai-history-run.md)을 따른다.

## 공통

- 기본 주소: `http://localhost:8000` (데모)
- 현재 인증: 별도 로컬 API 토큰을 Electron main에서 `Authorization: Bearer` 헤더로 전달한다.
  일반 사용자 로그인·토큰 발급 서버·다중 사용자 인증은 후속 범위다.
- `/health`와 개발용 `/docs`·`/openapi.json`은 인증 없이 확인한다. 사용자 데이터나 연결 정보를 반환하지 않는다.
- 날짜: 시간대 오프셋을 포함한 ISO 8601. 저장된 UTC 값은 앱에서 한국 시간으로 표시한다.
- 오류 응답: `{ "error": { "code": "...", "message": "..." } }`
- 현재 오류 코드: `unauthenticated`(401), `forbidden`(403), `not_found`(404),
  `method_not_allowed`(405), `validation_error`(422), `internal_error`(500),
  `service_unavailable`(503), 기타 HTTP 오류의 `http_error`.
  입력값·예외 상세는 응답에 포함하지 않는다.

## 실행 가능한 공통 API

| 기능 | 메서드 | 경로 | 설명 |
| --- | --- | --- | --- |
| 공통 | GET | `/health` | HTTP 프로세스 응답 확인. 200 `{"status":"ok"}`. DB·Gmail·AI 준비 상태는 확인하지 않음 |

실제 앱의 OpenAPI에서 `pnpm gen:api-types`로 `packages/api-types`를 생성한다.
서버 실행이나 외부 API 연결 없이 생성 가능하며 생성 파일을 직접 수정하지 않는다.

## 실행 가능한 로컬 메일 조회 API

전용 명령 `python -m app.cli.run_mail_api`로 실행한다. 일반 `app.main:app`에는
경로·OpenAPI만 있고 계정 설정이 없어 데이터 조회를 허용하지 않는다.
준비·검사·맥북 앱 실행 순서는 [메일 API 안내](../dev/mail-read-api.md)를 따른다.

| 메서드 | 경로 | 응답 |
| --- | --- | --- |
| GET | `/auth/session` | `LocalSession`: 연결된 `user_id`, `account_id`, `email`, `sync_started_at` |
| GET | `/mails?box=inbox&limit=20&cursor=...` | `MailPage`: `items`와 `next_cursor`(마지막은 null). limit 1~100, 기본 20 |
| GET | `/mails/{mail_id}` | `MailDetail`: 해당 계정의 받은 메일 일반 텍스트 본문 |
| POST | `/mails/sync` | `MailSyncResult`: `saved`, `skipped`, `mode`(`initial`/`history`/`rescan`), `token_refreshed`. 앱 새로고침용 Gmail 새 받은 메일 가져오기 |

- `MailSummary`: `mail_id`, `subject`, `from_addr`, `from_name`, `preview`(본문 앞 160자),
  `received_at`, `is_read`, `analysis_status`(`pending`/`done`/`failed`).
- `MailDetail`: 위 필드와 `to`, `cc`(각 `{addr, name}` 배열), `body_text`.
  HTML 원문·첨부파일·Google 토큰·API 토큰은 반환하지 않는다.
- 수신 시각 내림차순, 같은 시각에는 ID 내림차순으로 페이지를 읽는다.
  cursor는 서버가 준 값 그대로 전달한다. 검색·분류·정렬 변경·다른 편지함은 미지원이며
  목록의 알 수 없거나 중복된 쿼리 인수는 422다.
- 소유자는 요청에서 받지 않는다. 기존 로컬 운영자·설정된 Gmail 계정·연결 기록으로 한정하고,
  사용 시작 이후 받은편지함과 명시적 가져오기 메일을 읽는다. 다른 계정 메일 ID도 없는 메일과 같이 404다.
- 로컬 접속과 허용 Host만 받으며 모든 Origin 헤더를 거부한다. Renderer 직접 fetch 대신
  Electron main의 Node fetch + 제한된 IPC를 사용한다. CORS를 추가해 우회하지 않는다.
- 인증 실패 401, 외부 출처 403, DB·계정 준비 부족 503. 개인 응답은 `Cache-Control: no-store`다.
- 조회(GET)는 저장된 DB를 읽으며 읽음 상태·메일·수신 커서를 바꾸거나 Gmail을 동기화하지 않는다.
- Gmail 수신은 `POST /mails/sync`만 한다(2026-11-19, F0). CLI `gmail_mail sync`와 같은 수신 기능을 써서
  사용 시작 시점 이후 받은편지함 메일만 저장하고 이미 저장한 메일은 건너뛴다. 실패한 배치와 커서는 되돌린다.
  인증·loopback·Host·Origin 규칙과 `Cache-Control: no-store`는 조회와 같다. 같은 서버에서 이미 가져오는 중이면
  409 `sync_in_progress`, Gmail·토큰 갱신 실패는 502 `gmail_unavailable`(외부 응답 상세 미포함), DB·계정 준비 부족은 503.
  응답에는 건수만 있고 메일 내용·토큰은 없다. 주기적 자동 수신(WebSocket·작업 큐)은 후속이다.

## F3 검색 API (선택 AI·로컬 의미 검색 연결)

`app.main`에 경로와 OpenAPI를 등록했고, `run_mail_api`는 기존 로컬 인증과 F3 저장소를
함께 조립한다. SelectedGeneration으로 로컬/Claude 해석·답변을 요청별 선택하고,
`build_semantic_search(engine)`로 F1의 로컬 임베딩·저장 벡터를 연결한다.
AI 설정 부족을 가짜 검색 성공으로 대체하지 않는다. 이번 연결의 반영 상태·검증은
[통합 기록](../dev/F3-memory-search-integration.md)을 따른다.

| 메서드 | 경로 | 계약 |
| --- | --- | --- |
| POST | `/search` | `{query, search_id?, overrides?}` → 해석, 전체/일부 일치, 근거가 붙은 답변 또는 답변 실패 |
| GET | `/search/recent` | 인증된 사용자·계정의 최근 질문 최대 3개 |

- 소유자·계정은 요청에서 받지 않는다. 기존 Bearer·loopback·Host·Origin 거부 규칙과
  `Cache-Control: no-store`를 유지한다. Renderer 직접 fetch 대신 main/IPC로 연결한다.
- 재검색의 `null` 조건은 삭제하고, 주제를 바꾸거나 지우면 이전 확장어도 제거한다.
- `Accept: application/x-ndjson`은 `parsed` → `results` → `answer`/`answer_error` 프레임을
  전달한다. 스트림 도중 실패는 `error` 프레임이며 HTTP 200이어도 확인해야 한다.
- `parser_unavailable`/`parse_unavailable`은 503, `parse_failed`/`unsupported_filter`는 422다.
  결과가 있으면 답변 실패는 결과와 함께 `answer_error`로 구분한다.
- Claude 선택·동의 시 질문·필요한 결과를 외부 전송할 수 있다. 조직·미회신·분류·첨부 조건은 미지원이다.
- `parsed.original_terms`는 질문에서 유지한 원래 표현이다. 결과에는 `search_warnings`와
  `semantic_coverage`(대상 메일·호환 메일·검사 청크 수·후보 상한 도달 여부)가 있다.
  JSON과 NDJSON `results` 프레임 모두 이 제한 정보를 전달한다.
- 의미 검색은 같은 사용자·계정·기간의 F1 분석 완료 벡터 중 제공자·모델·차원·모드가
  호환되는 것만 읽는다. 미설정·오류·호환 불일치는 제한 안내와 키워드 결과로 구분한다.
- 최근 검색을 쓰려면 `0003_search_runs` 마이그레이션이 필요하다. 이번 작업에서는
  합성 테스트 DB에서만 적용·검사했다. F0/F2 화면 연결은 완료, 실제 모델 정확도·5초 성능은 미검증이다.

최신 연결·검사는 [F3 통합 기록](../dev/F3-memory-search-integration.md),
기존 계약 이력은 [F3 전달 문서](../dev/F3-search-handoff.md)를 따른다.

## 맥북 전용 Google 연결 경로 (2026-11-19)

`python -m app.cli.run_google_connection`으로 실행하는 별도 로컬 앱에서만 제공한다.
일반 `app.main:app`의 JSON API·OpenAPI·생성 TS 계약은 그대로다.

| 메서드 | 경로 | 설명 |
| --- | --- | --- |
| GET | `/auth/google` | 로컬 연결 안내·동의 시작 폼, HttpOnly 브라우저 쿠키 |
| POST | `/auth/google` | 같은 출처·폼 토큰 확인 후 Google으로 303 이동, state·PKCE |
| GET | `/auth/google/callback` | 일회용 요청 검증·코드 교환·Gmail 계정 확인·암호화 저장, HTML 결과 |

이는 로컬 운영자 한 명의 연결 도구다. 아래 설계의 앱용 POST 코드 교환 계약·Bearer 인증은
구현한 것이 아니다. 사용자는 맥북에서 실제 Gmail 로그인 성공을 확인했다.
이 연결 도구 자체는 메일 본문·목록을 읽지 않는다.
자세한 범위와 검사는 [Google 연결 안내](../dev/google-connection.md)를 따른다.

## 업무 엔드포인트 (설계·미구현)

| 기능 | 메서드 | 경로 | 설명 |
| --- | --- | --- | --- |
| F0 | POST | `/auth/google` | OAuth 코드 교환, 계정 연결 |
| F0 | POST | `/mails/send` | 보내기 |
| F0 | POST | `/mails/{mail_id}/archive` | 보관 |
| F0 | POST | `/mails/{mail_id}/spam` | 스팸 처리 |
| F0 | DELETE | `/mails/{mail_id}` | 삭제 |
| F0 | GET·PUT | `/settings/notifications` | 알림·시작 프로그램 설정 |
| F1 | GET | `/mails/counts` | 스마트 보기·카테고리별 건수 |
| F4 | POST | `/reports/weekly/{report_id}/export` | Word 내보내기 |

## WebSocket `/ws` (설계·미구현)

| 이벤트 | 내용 | 앱 동작 |
| --- | --- | --- |
| `mail.received` | 새 메일 도착 (분석 전) | 목록에 추가 |
| `mail.analyzed` | 분석 완료 (요약·태그) | 목록 갱신 |
| `suggestion.created` | 새 AI 제안 | Windows 토스트 알림 |

## F2 프로필·답장 초안 API

F2 router는 `app.main`에 등록되어 있다. 0004_f2 마이그레이션을 적용한 DB와 F2Context(로컬 실행 명령에서 조립)가 필요하다.
GET/PUT /profile, GET/DELETE /profile/style, POST /profile/preview, POST /drafts,
GET/PATCH /drafts/{draft_id}, POST /drafts/{draft_id}/revise.
인증·Origin 제한은 기존 로컬 메일 조회 API를 그대로 따른다. 발송 API는 추가하지 않는다.
AI 미연결은 503 ai_unavailable이며 합성 결과로 대체하지 않는다.
입력·출력·버전·동의·오류 계약은 [F2 구현 안내](../dev/F2-profile-draft.md)를 따른다.


## F5 제안·할 일 API (서버 등록·Calendar 기본 차단)

F5 전용 라우터를 공통 앱에 등록하고 로컬 실행 명령에서 기존 인증 계정의 저장소에 연결한다.
새 DB 이력은 0005_f5이며 기존 계정·메일·Gmail 수신·F2·F3 경로는 유지한다.
F1 입력 전달·F0 IPC/화면은 #28·#32·#34에서 연결됐다. WebSocket·Calendar HTTP transport는 미연결이다.

| 메서드 | 경로 | 계약 |
| --- | --- | --- |
| GET | `/suggestions` | status, mail_id, notified, limit(1~100), cursor; items/next_cursor |
| GET | `/suggestions/{suggestion_id}` | 인증된 사용자·계정의 제안 1건 |
| POST | `/suggestions/{suggestion_id}/approve` | 필수 version, 선택 payload(유형별 전체 수정값) |
| POST | `/suggestions/{suggestion_id}/dismiss` | 필수 version; 무시 이력 저장 |
| POST | `/suggestions/{suggestion_id}/reregister` | 필수 version(본문 payload 불가); 등록한 일정을 사용자가 구글 캘린더에서 지웠을 때 새 일정 ID로 다시 등록. 아직 있으면 409 `calendar_event_exists`, 등록 완료 상태가 아니면 409 `reregister_not_available` |
| POST | `/suggestions/{suggestion_id}/conflicts` | 수정한 Calendar payload로 읽기 전용 겹침 확인 |
| GET | `/todos` | status(open/completed), limit, cursor; items/next_cursor |
| POST | `/todos` | request_id, title, due?, mail_id?; 재시도 중복 제거 |
| PATCH | `/todos/{todo_id}` | version과 title/due/status 중 하나 이상 |
| GET | `/suggestion-events` | limit(1~100); 미표시 pending 이벤트 조회 |
| POST | `/suggestion-events/{event_id}/ack` | 실제 표시 후 확인, 204 |

기존 loopback·Bearer·Origin 거부 정책을 재사용하고 소유자 ID를 클라이언트에서 받지 않는다.
다른 사용자/계정 ID는 404다. 개인 응답과 오류는 no-store이며 ErrorResponse를 사용한다.
상태 충돌은 409, 입력 오류 422, Calendar 권한/연결 부족 503, 외부 실행 실패 502다.
제안 생성은 F1 내부 연결 계약으로만 받으며 외부 POST 경로는 없다.

업무 상태 pending/approved/dismissed와 execution_status를 따로 확인한다.
Calendar 테스트는 pending+simulated+test다. 불명확한 실행은 uncertain으로 남기고
입력 변경·무시를 차단한다. 앱 할 일은 내부 저장 성공 후에만 approved가 된다.
알림 이벤트 조회만으로 표시 완료를 기록하지 않는다. 운영 DB 적용·Google/OS 실행은 별도다.
[F5 계약](../dev/F5-ai-scan-contract.md), [현황](../dev/F5-ai-scan-status.md)을 따른다.

## F4 주간 보고 (공통 패치 적용 후)

기존 로컬 Bearer·Origin·연결 계정 검사를 그대로 사용한다.
`GET /reports/weekly/options`, `POST /reports/weekly`, `GET /reports/weekly/{id}`,
`GET /reports/weekly/{id}/excluded`, `PATCH /reports/weekly/{id}`를 등록한다.
프로필은 F2, 메일 입력은 F1, AI는 공통 TextGeneration을 사용한다. 실제 제공자가 없으면
503으로 종료하며 대역으로 대체하지 않는다. 운영 서비스는 run_mail_api에서 조립한다.
사용자·계정은 요청 본문에서 받지 않고, 편집은 expected_revision과 근거를 검증한다.
일정 예약·내보내기·발송 경로는 추가하지 않는다.

## F1 분류 수정 (공통 패치 적용 후)

`PATCH /mails/{mail_id}/category`를 등록한다. 기존 로컬 Bearer·Origin·연결 계정 검사를 그대로
쓰고, 본문은 `{category: 영문 분류 키 7종}`만 받는다(user_id/account_id를 받지 않는다).
응답은 `{mail_id, user_label, effective_category}`, 다른 사용자·없는 메일은 같은 404,
저장소 미연결은 503이다. 수정은 `f1_mail_analysis.user_label`과 `f1_category_feedback`에
기록되고 청크의 필터 분류도 갱신한다. 엔진은 run_mail_api가 `app.state.mail_analysis_engine`에
넣는다. `/mails/counts`는 후속이다.

## F1 새 메일 자동 분석과 표시용 조회 (patches/F1/05)

- `POST /mails/sync`가 저장을 마치면 F1 자동 분석 작업자에 '분석 시작' 신호만 주고 바로 응답한다
  (`MailSyncContext.after_sync`). 응답 형식은 그대로다. 작업자는 서버 안에 하나이며 pending 메일을 분석한다.
  run_mail_api는 자동 분석에 로컬 Ollama를 강제 주입한다. 로컬 모델 미설정이면 pending이다. 수동 기능의 Claude 선택은 자동 분석에 영향을 주지 않는다.
- 분석이 DB에 확정되면 분석 완료 알림 지점(`analysis_runner.hooks`)이 F5 `AnalysisScanHook`을 불러 제안을 만든다
  (로컬 AI일 때만, F5 실패는 F1 분석에 영향 없음). 계약은 `docs/dev/F1-handoff.md`·`docs/dev/F5-handoff.md`.
- 기존 `GET /mails`·`GET /mails/{mail_id}` 응답은 바꾸지 않았다. AI 결과는 F1 전용 경로로 따로 읽는다.

| 메서드 | 경로 | 설명 |
| --- | --- | --- |
| GET | `/mails/analysis/batch?ids=…` (1~100개) | 목록 표시용 `{items: MailAnalysisView[], auto_analysis}`. 다른 소유자·없는 메일은 빠진다 |
| GET | `/mails/{mail_id}/analysis` | 한 건 `MailAnalysisView + auto_analysis`, 없으면 404 |
| POST | `/mails/{mail_id}/analysis/retry` | failed → pending 후 다시 분석(202). 분석 완료 409, AI 미연결 503 `analysis_unavailable` |

`MailAnalysisView`: `mail_id`, `analysis_status`(pending/done/failed), `category`(user_label 우선),
`ai_category`, `user_label`, `summary`, `needs_reply`, `action_items[{text,due}]`, `priority`,
`priority_reason`, `has_events`, `evidence_spans[{kind,start,end}]`, `failure_code`(failed일 때).
원문·벡터·모델 정보는 넣지 않는다. 운영에서 테스트 대역(mode=test) 결과는 pending으로 보인다.
`auto_analysis`: `ready` / `not_configured` / `external_blocked` / `not_connected`(작업자 미조립).

## 기능별 AI 설정·요청 (2026-11-20)

- `GET /settings/ai`: 기능별 기본값, 외부 전송 허용 여부, 키 등록 여부, 로컬 모델 설정 여부, Claude 모델 ID. 키 값은 반환하지 않음.
- `PUT /settings/ai`: `defaults`(draft/search/weekly_report 각각 ollama/claude), `external_consent`, 선택 `api_key`·`claude_model`·`clear_key`. 키 생략/빈 UI 입력은 유지. `clear_key`는 암호화 파일에 저장한 키만 삭제하며 환경 변수 키는 보존.
- `POST /settings/ai/check`: `{provider: ollama|claude}`. 메일 없는 고정 합성 요청으로 연결 검사(Claude 소량 과금). 실제 기능 품질 검사가 아님.
- 모두 기존 loopback·Bearer·Origin 차단 경계와 비공개 응답 정책을 사용한다. 기존 연결 계정의 로컬 운영자 설정이다.
- `POST /drafts`, `/drafts/{id}/revise`, `/profile/preview`, `/search`, `/reports/weekly`에 선택 `ai_provider: default|ollama|claude|null` 추가. 생략/null/default는 저장 기본값(새 설정은 로컬 전용·로컬 기본). `/profile/preview`는 선택과 무관하게 로컬 고정.
- F3는 해석과 답변이 같은 설정 스냅샷을 사용한다. 요청 간 변경은 다음 요청부터 적용한다.
- F4는 제공자별 생성 저장 키를 분리해 전환 시 기존 보고서·편집본을 덮어쓰지 않는다. 기존 ID 조회·편집은 유지한다.
- 첫 주 options는 remaining_days=0, 기본 기간=사용 시작일~오늘. 보고서에 partial_period·collection_started_at 추가(기존 저장본은 기본값으로 호환).
- 서버 타임아웃: 초안/보고서 120초, 미리보기 30초, 운영 검색 각 AI 단계 120초. 앱 초안/보고서/연결 검사는 150초까지 기다림. 실제 성능 보장과 구분한다.

## 이번 작업 브랜치의 통합 구현

기간 선택 과거 메일 가져오기, Claude→로컬 1회 대체 재시도, 강제 로컬 전용 모드는 통합 작업 브랜치에서 구현·자동 검사했으며 develop 반영 PR #39(사용자 병합 승인 완료)다.
`/profile/preview`는 서버에서 로컬을 강제한다. 수동 초안·수정의 Claude 선택은 별도이며
로컬 전용 모드·외부 전송 동의 검사를 통과해야 한다. [setup.md](../dev/setup.md)·[통합 전달 사항](../dev/integration-followups.md)을 따른다.
