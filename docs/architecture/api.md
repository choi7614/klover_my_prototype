# API 목록

> 최종 수정: 2026-11-18 | 상세 스펙은 서버 실행 후 `http://localhost:8000/docs` (FastAPI 자동 OpenAPI)

이 문서는 **요약 목록**이다. 엔드포인트를 추가·변경하면 여기에 한 줄 반영하고, `packages/api-types`의 타입을 다시 생성한다.

> 구현 상태 (2026-11-18): 공통 HTTP 서버와 `GET /health`만 실행 가능하다.
> 아래 업무 API·WebSocket은 아직 설계 목록이다. F4는 내부 메일 조회 서비스·저장소 계약·
> fixture CLI를 유지하며 보고서 HTTP API를 제공하지 않는다.
> [서버 실행 안내](../../apps/server/README.md)와 [F4 구현 계획](../dev/F4-weekly-report-plan.md)을 따른다.

## 공통

- 기본 주소: `http://localhost:8000` (데모)
- 업무 API 인증 계획: 앱 로그인 후 받은 토큰을 `Authorization: Bearer` 헤더로 전달 (미구현)
- `/health`와 개발용 `/docs`·`/openapi.json`은 인증 없이 확인한다. 사용자 데이터나 연결 정보를 반환하지 않는다.
- 날짜: ISO 8601, 시간대 Asia/Seoul
- 오류 응답: `{ "error": { "code": "...", "message": "..." } }`
- 현재 오류 코드: `not_found`(404), `method_not_allowed`(405), `validation_error`(422),
  `internal_error`(500), 기타 HTTP 오류의 `http_error`. 입력값·예외 상세는 응답에 포함하지 않는다.

## 실행 가능한 공통 API

| 기능 | 메서드 | 경로 | 설명 |
| --- | --- | --- | --- |
| 공통 | GET | `/health` | HTTP 프로세스 응답 확인. 200 `{"status":"ok"}`. DB·Gmail·AI 준비 상태는 확인하지 않음 |

실제 앱의 OpenAPI에서 `pnpm gen:api-types`로 `packages/api-types`를 생성한다.
서버 실행이나 외부 API 연결 없이 생성 가능하며 생성 파일을 직접 수정하지 않는다.

## 맥북 전용 Google 연결 경로 (2026-11-19)

`python -m app.cli.run_google_connection`으로 실행하는 별도 로컬 앱에서만 제공한다.
일반 `app.main:app`의 JSON API·OpenAPI·생성 TS 계약은 그대로다.

| 메서드 | 경로 | 설명 |
| --- | --- | --- |
| GET | `/auth/google` | 로컬 연결 안내·동의 시작 폼, HttpOnly 브라우저 쿠키 |
| POST | `/auth/google` | 같은 출처·폼 토큰 확인 후 Google으로 303 이동, state·PKCE |
| GET | `/auth/google/callback` | 일회용 요청 검증·코드 교환·Gmail 계정 확인·암호화 저장, HTML 결과 |

이는 로컬 운영자 한 명의 연결 도구다. 아래 설계의 앱용 POST 코드 교환 계약·Bearer 인증은
구현한 것이 아니다. 실제 Gmail 로그인은 사용자 맥북에서 미확인이며 메일 본문·목록은 읽지 않는다.
자세한 범위와 검사는 [Google 연결 안내](../dev/google-connection.md)를 따른다.

## 업무 엔드포인트 (설계·미구현)

| 기능 | 메서드 | 경로 | 설명 |
| --- | --- | --- | --- |
| F0 | POST | `/auth/google` | OAuth 코드 교환, 계정 연결 |
| F0 | GET | `/mails` | 목록 (`box`, `category`, `smart`, `cursor`, `sort`) |
| F0 | GET | `/mails/{mail_id}` | 상세 |
| F0 | POST | `/mails/send` | 보내기 |
| F0 | POST | `/mails/{mail_id}/archive` | 보관 |
| F0 | POST | `/mails/{mail_id}/spam` | 스팸 처리 |
| F0 | DELETE | `/mails/{mail_id}` | 삭제 |
| F0 | GET·PUT | `/settings/notifications` | 알림·시작 프로그램 설정 |
| F1 | PATCH | `/mails/{mail_id}/category` | 사용자 분류 수정 |
| F1 | GET | `/mails/counts` | 스마트 보기·카테고리별 건수 |
| F2 | GET·PUT | `/profile` | 프로필 조회·저장 |
| F2 | GET·DELETE | `/profile/style` | 문체 학습 결과 조회·삭제 |
| F2 | POST | `/profile/preview` | 설정값으로 예시 답장 |
| F2 | POST | `/drafts` | 답장 초안 생성 |
| F2 | POST | `/drafts/{draft_id}/revise` | 더 짧게·더 정중하게·다시 쓰기 |
| F3 | POST | `/search` | 자연어 검색 |
| F3 | GET | `/search/recent` | 최근 검색 |
| F4 | POST | `/reports/weekly` | 주간 보고 생성 |
| F4 | GET | `/reports/weekly/{report_id}/excluded` | 제외된 메일 |
| F4 | POST | `/reports/weekly/{report_id}/export` | Word 내보내기 |
| F5 | GET | `/suggestions` | 제안 목록 (`status=pending`: 놓친 제안 포함) |
| F5 | POST | `/suggestions/{id}/approve` | 승인 (수정값 포함 가능) |
| F5 | POST | `/suggestions/{id}/dismiss` | 무시 |
| F5 | GET·POST·PATCH | `/todos` | 할 일 |

## WebSocket `/ws` (설계·미구현)

| 이벤트 | 내용 | 앱 동작 |
| --- | --- | --- |
| `mail.received` | 새 메일 도착 (분석 전) | 목록에 추가 |
| `mail.analyzed` | 분석 완료 (요약·태그) | 목록 갱신 |
| `suggestion.created` | 새 AI 제안 | Windows 토스트 알림 |
