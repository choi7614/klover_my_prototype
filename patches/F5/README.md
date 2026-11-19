# F5 공통 연결 패치 — 적용 전

> 기준 develop: `420078e` · 원본 SHA-256은 [baseline.json](baseline.json) (값이 `null`이면 새로 만드는 파일)

F5 기능 브랜치에는 화면 쪽 F5 전용 파일만 들어 있다(`renderer/features/suggestions/`의
`ipc-client.ts`, `mail-suggestions.tsx`, `todo-list.tsx`와 테스트). main/preload·공통 App·F0 메일함 화면은
공통 영역이라 아래 패치로만 남긴다. **통합 채팅에서 적용하기 전에는 앱에서 F5 제안·할 일이 보이지 않는다.**

| 순서 | 패치 | 적용 대상·행동 |
| --- | --- | --- |
| 1 | [01-main-preload-ipc.patch](01-main-preload-ipc.patch) | 새 `shared/f5-bridge.ts`, `main/f5-client.ts`·`f5-ipc.ts`(+테스트), `main/index.ts` 등록, `preload` `klover.suggestions` 공개, `env.d.ts` 타입 |
| 2 | [02-app-routes.patch](02-app-routes.patch) | 공통 App의 `/todos` 경로, F0 메일함의 S04 제안 패널 진입과 사이드바 '할 일' 메뉴(+테스트). 01 뒤에 적용 |

공유 타입(`packages/api-types`)·서버·DB·잠금 파일 변경은 없다. F5 API와 타입은 이미 develop에 있다(#20).

## 연결 계약

- 통로 8개: 제안 `list`(`?mail_id`·`status`·`limit`·`cursor`만) `get` `approve` `dismiss` `conflicts`,
  할 일 `todos`(`status`·`limit`·`cursor`만) `createTodo` `updateTodo`. 채널 이름은 `klover:suggestions:*`.
- main은 기존 `readLocalAPI`(루프백 주소·토큰 파일)와 `trustedMailSender`(신뢰한 main frame)를 재사용한다.
  토큰은 main에서만 읽고, 화면에는 결과 봉투 `{ ok, data | error.code }`만 돌려준다. 서버 오류 원문은 넘기지 않는다.
- 인수 검사: ID는 `^[A-Za-z0-9_-]{1,128}$`, 승인·무시·할 일 수정은 `version ≥ 1` 필수, 허용 필드만 통과,
  승인 payload·겹침 확인 본문은 20,000자 이하, 할 일 제목 1~300자, 마감은 `YYYY-MM-DD` 또는 null.
  소유자(`user_id`·`account_id`)·`notified` 같은 필드는 받지 않는다.
- **AI는 제안만 한다.** 화면은 사용자가 버튼을 누를 때만 승인·무시·할 일 추가를 요청한다.
  캘린더 실제 등록은 서버의 기본 차단 실행기를 그대로 두고, 화면도 `calendarReady=false`·`replyReady=false`다.
- 이번 범위 아님: `/suggestion-events`(알림 outbox)·OS 알림·트레이·WebSocket·놓친 제안(S10),
  Calendar 실제 연결, 회신 제안→F2 초안 실행, 사이드바 '할 일' 건수 표시, F1 결과→F5 입력 변환.

## 적용·검사

저장소 루트에서 develop이 baseline과 같은지 확인한 뒤:

```bash
git apply --check patches/F5/01-main-preload-ipc.patch && git apply patches/F5/01-main-preload-ipc.patch
git apply --check patches/F5/02-app-routes.patch && git apply patches/F5/02-app-routes.patch
pnpm --filter desktop lint && pnpm --filter desktop typecheck && pnpm --filter desktop test && pnpm --filter desktop build
```

F5 브랜치 작성 시 두 패치를 적용한 상태에서 lint·typecheck 통과, Vitest 154개 통과, Electron 빌드 통과를 확인했다.
