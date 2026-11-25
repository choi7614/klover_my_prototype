# Gmail 수신 계약

> 2026-11-24 · 기준 `develop f498d27`

현재 실행은 [설치·실행 안내](setup.md)를 따른다. 앱 새로고침은 사용 시작 이후 INBOX를 수신한 뒤 로컬 자동 분석을 시작한다. CLI 수신은 저장만 한다.

## 현재 수신의 경계

- 계정 최초 연결의 `sync_started_at` 이후 INBOX만 저장한다. history 만료 시에도 같은 시작 시점을 보존한다.
- `(account_id, source_message_id)`로 중복을 막고, 실패 시 메일 배치·커서는 함께 되돌린다. 토큰 갱신은 별도 확정한다.
- 텍스트 본문 위주이며 첨부 API를 호출하지 않는다. 기존 메일의 읽음·보관·삭제 상태를 동기화하거나 Gmail 원본을 변경하지 않는다.
- 실행당 후보·본문 크기 등의 상한과 대량 배치 재개 제한이 있다. 기간 선택·진행·중단·재시도를 갖춘
  [과거 메일 가져오기](../product/features/planned-mail-history-import.md)는 확정된 개발 예정이며 현재 미구현이다.
- 자동 분석은 앱 서버의 sync 후속 훅에서 시작한다. CLI `gmail_mail sync`만 실행하면 분석 훅은 실행되지 않는다.

구현 근거: `app/connectors/gmail_mail.py`, `app/db/repositories/gmail_sync.py`, `app/cli/gmail_mail.py`,
`app/cli/run_mail_api.py`(모두 apps/server 아래). 정확한 제한은 이 코드와 자동 검사를 기준으로 한다.

원본 설계 출처: [Gmail 동기화](https://developers.google.com/workspace/gmail/api/guides/sync),
[검색 시간대](https://developers.google.com/workspace/gmail/api/guides/filtering),
[오프라인 갱신](https://developers.google.com/identity/protocols/oauth2/web-server#offline).

## 과거 기록

[정리 전 원문](archive/2026-11-24/gmail-mail-sync-before.md)은 당시 단위의 구현·검사 기록이다. 개인 경로·병합 전 가정·과거 명령을 현재 실행 지시로 사용하지 않는다.
