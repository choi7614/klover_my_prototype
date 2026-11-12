# API 목록

> 최종 수정: 2026-10-16 | 상세 스펙은 서버 실행 후 `http://localhost:8000/docs` (FastAPI 자동 OpenAPI)

이 문서는 **요약 목록**이다. 엔드포인트를 추가·변경하면 여기에 한 줄 반영하고, `packages/api-types`의 타입을 다시 생성한다.

> 구현 상태 (2026-11-12): 아래는 설계 목록이다. 현재 실행 가능한 HTTP 서버와
> 보고서 API는 없다. F4 첫 단위는 내부 메일 조회 서비스·저장소 계약·fixture CLI만
> 제공하며 엔드포인트를 추가하지 않는다. 진행 상태는
> [F4 구현 계획](../dev/F4-weekly-report-plan.md)을 따른다.

## 공통

- 기본 주소: `http://localhost:8000` (데모)
- 인증: 앱 로그인 후 받은 토큰을 `Authorization: Bearer` 헤더로 전달
- 날짜: ISO 8601, 시간대 Asia/Seoul
- 오류 응답: `{ "error": { "code": "...", "message": "..." } }`

## 엔드포인트

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

## WebSocket `/ws`

| 이벤트 | 내용 | 앱 동작 |
| --- | --- | --- |
| `mail.received` | 새 메일 도착 (분석 전) | 목록에 추가 |
| `mail.analyzed` | 분석 완료 (요약·태그) | 목록 갱신 |
| `suggestion.created` | 새 AI 제안 | Windows 토스트 알림 |
