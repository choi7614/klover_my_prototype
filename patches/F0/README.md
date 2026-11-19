# F0 공통 패치 — 적용 전 (통합 채팅용)

> 2026-11-19 `feat/F0-mailbox` 기준(`origin/develop` `c8951a1` 위). 기능 채팅에서는 공통 파일을 직접 고치지 않고 이 패치만 남긴다.
> 적용은 통합 채팅에서 한다. 적용 전 `git apply --check patches/F0/0*.patch`로 확인한다.

| 패치 | 영향 | 확인한 범위 |
| --- | --- | --- |
| 01-server-registration | `app/main.py`에 `POST /mails/sync` 라우터 등록, `app/cli/run_mail_api.py`에 Gmail 수신 저장소·클라이언트 조립, `tests/test_http_server.py` OpenAPI 경로 목록 | 임시 사본에서 적용 후 서버 ruff·pytest 통과(221 통과, 90 skip=실제 PostgreSQL 필요) |
| 02-main-preload-sync | `src/main/mail-client.ts` `sync()`(POST, 120초 대기, 409·502 구분, 응답 재구성), `mail-ipc.ts` `klover:mail:sync` 통로(인수 없음·신뢰한 화면만), `preload` 공개, main 검사 2개 파일 | 임시 사본에서 tsc·eslint·vitest(80개) 통과 |
| 03-app-routes | 공통 App: `/mail/inbox/:mailId?`(F0 `MailboxRoute`), `/search`(F0 `SearchRoute` + F3 `SearchPage`), `searchClient` 주입 자리(기본 '준비 부족') | 위와 같음 |
| 04-generated-api-types | 01 적용 후 OpenAPI·TS 재생성 결과(`MailSyncResult`, `/mails/sync`) | `export_openapi` + `openapi-typescript`로 생성. 적용 대신 `pnpm gen:api-types` 재실행도 같다 |
| 05-shared-documents | `docs/architecture/api.md`에 `POST /mails/sync` 계약, `docs/dev/mail-read-api.md`의 'DB 재조회만' 문구 | 문서만 |

- 01·02를 적용해야 앱 새로고침이 실제로 Gmail을 가져온다. 적용 전 F0 화면은 저장된 목록만 다시 읽고 그렇게 안내한다.
- 04 적용 뒤 `shared/mail-read.ts`의 수동 `MailSyncResult` 형식은 생성 타입으로 바꿔도 된다(형식 동일).
- F2·F3 서버 통로(main/preload IPC 클라이언트)는 이 패치에 없다. 다음 단위에서 `App`의 `f2Client`·`searchClient`로 넘긴다.
- 새 의존성·잠금 파일·DB 마이그레이션 변경은 없다.
