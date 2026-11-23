# F2 전달 문장과 남은 연결

> 과거 전달·검사 기록을 포함한다. 2026-11-24 현재 API/IPC·F1 입력·F4 AI 통합은 PR #37까지 반영됐다. 미연결·패치 적용 요청은 당시 기록이며 현재 작업 상태는 [progress.md](progress.md)와 각 status, 실행은 [setup.md](setup.md)를 따른다. 기존 패치를 재적용하지 않는다.

작업 브랜치: `feat/F2-profile-draft`, 시작 기준 `origin/develop` 0f68ad1.
승인 후 F1/F3가 포함된 `origin/develop` 9244454를 같은 작업 브랜치로 가져왔다.
이 문서의 내용은 전달용으로 정리한 것이며 다른 채팅에 메시지를 발송하지 않았다.
공통 파일·운영 DB·실제 Gmail·AI는 연결하거나 변경하지 않았다.

## F0에 전달할 문장

> F2의 `ProfilePage`와 `ReplyDraftPage`, 라우트용 `F2ProfileRoute`·`F2ReplyRoute`를
> `apps/desktop/src/renderer/features/profile-draft/index.ts`에서 export했습니다.
> 공통 App/router, main/preload, 메일함, 토큰은 수정하지 않았습니다.
> `patches/F2/03-screen-routes.patch`는 현재 기준의 미적용 연결안입니다.
> F0의 실제 메일함 경로와 인증 IPC를 `F2Client`로 주입해 주세요. 미주입 시 준비 부족을 표시합니다.
> 서버 경로·DB는 01/02 패치와 사용자 묶음 승인 후 연결해야 합니다.
> 토큰은 main에만 두고 기존 로컬 Bearer·Host·Origin 제한을 유지해 주세요.
> Renderer 직접 fetch나 임의 URL/IPC 공개, CORS 우회는 사용하지 않습니다.
> 보내기는 비활성이며 발송 API나 발송 IPC를 F2에서 만들지 않았습니다.

연결할 경로는 `/settings/profile`, `/reply/:mailId`다.
임시 저장을 다시 열 때 `/reply/:mailId?draft=:draftId` 또는 `ReplyDraftPage`의 `draftId`를 사용한다.
이 경우 새 생성 대신 GET `/drafts/{id}`로 사용자 편집을 복원한다.
초안 ID와 원본 ID가 맞지 않으면 본문을 표시하지 않는다.

| F2Client 메서드 | main에서 호출할 서버 경로 |
| --- | --- |
| profile, saveProfile | GET/PUT `/profile` |
| style, deleteStyle | GET/DELETE `/profile/style` |
| preview | POST `/profile/preview` |
| mail | 기존 GET `/mails/{mail_id}` |
| createDraft, draft | POST `/drafts`, GET `/drafts/{draft_id}` |
| saveDraft, reviseDraft | PATCH `/drafts/{draft_id}`, POST `/drafts/{draft_id}/revise` |

각 IPC는 위 동작과 검증된 ID·본문만 받아야 한다. 인증 헤더·소유자·임의 경로를
Renderer가 선택하면 안 된다. 오류 `{error:{code,message}}`는 `F2Problem`으로 전달한다.
Electron 창의 최소 크기 1280×720, 기본 1440×900과 상단/본문 높이도 F0에서 맞춰야 한다.
현재 공통 창은 첫 실행 전용이며, 창 크기·main/preload 변경 패치는 F0의 진행 코드에 맞춰 작성해야 한다.
기존 App 연결안은 F0 메일함 경로가 아직 없으므로 `/onboarding/1`을 기본 돌아가기 경로로 사용한다.

ProfilePage 내부의 나가기·설정 메뉴는 미저장 변경을 확인하고,
ReplyDraftPage 내부의 나가기는 편집을 임시 저장한 뒤 실행한다.
F0가 추가하는 공통 메뉴·SPA 이동도 같은 확인/저장 흐름을 통과해야 하며 아직 검증하지 않았다.
생성이 실패한 뒤 직접 입력한 본문은 화면 메모리에 보존한다. 임시 저장된 초안 ID가 없으면
자동 저장할 수 없음을 나갈 때 알린다. S05로 넘길 때 `onManualReply(mailId, body)`를 사용한다.
프로필·초안 페이지는 합성 검사 앱에서 확인했으며 실제 F0 앱 통합은 미완료다.

## F4에 전달할 문장

> F4는 `F2Repository.report_profile(user_id=서버에서_확인한_소유자)`로
> `ProfileState {profile, exists, version}`을 읽으면 됩니다.
> `profile.report_sections` 순서, `report_recipient`, `report_style`, `formality`를 사용해 주세요.
> 섹션 ID는 highlights=금주 주요 업무, ongoing=진행 중인 업무,
> issues=이슈·요청사항, next_week=차주 계획입니다.
> `exists=false`이면 프로필 설정을 요청하고 다른 사용자나 가짜 프로필로 대신하지 않습니다.
> F2 DB 연결은 승인 전 패치 상태입니다. 기존 F4 코드·ReportMail 계약은 수정하지 않았습니다.

학습 결과가 필요한 경우 `F2Repository.style(user_id=확인한_소유자)`를 사용한다.
동의가 꺼지면 표현·특징은 빈 값이며, 제외 표현도 생성 입력에서 제거한다.
실제 학습 수집·분석 기반은 아직 없으므로 학습 완료로 취급하면 안 된다.
보고서에 사용한 프로필 버전을 기록하면 이후 설정 변경과 구분할 수 있다.

## F1에 전달할 계약과 후속 요청

> F2는 외부 AI SDK·제공자를 중복 구현하지 않았습니다.
> F1의 `TextGeneration.generate(GenerationRequest)`를 `SharedDraftAI` 어댑터로 재사용합니다.
> F2 업무 경계는 `app.ai.f2_port.DraftAI.generate(GenerationInput) -> GeneratedDraft`입니다.
> 운영 기본 구현은 503 ai_unavailable이며, 테스트 대역은 tests 안에만 있습니다.
> 실제 제공자가 준비되면 `SharedDraftAI(generator)`를 F2Context에 명시적으로 주입해 주세요.
> 원본·관련 메일은 데이터로만 취급하고 실제 Gmail 내용을 외부 AI로 보내는 실험은 하지 않았습니다.

- 제공자는 본문 가운데 부분·방향 2~3개·선택 방향·근거를 반환한다.
  서버가 저장된 인사·마무리·서명을 그대로 붙이므로 중복해서 생성하지 않는다.
- 근거 위치는 Unicode 코드포인트 `[start,end)`다. JS 문자열 길이(UTF-16)와 다르다.
  근거 source는 입력된 `mail:{id}` 또는 실제 사용한 `profile.phrase`다.
- 수정 입력에는 현재 사용자 편집 본문·action·direction이 들어간다.
  사용자 편집을 무시하고 원래 생성문만 다시 쓰면 안 된다.
- `RelatedMailSearch.find_ids(user_id, account_id, mail_id)`는 동일 스레드/상대의 메일과
  의미 유사 상위 3건을 합쳐 중복 없는 ID 최대 50개를 반환하는 F2용 연결 포트다.
  F2는 모든 ID를 인증된 메일 읽기로 재검증한다. 현재 검색 구현은 없다.
- 현재 기존 메일 조회는 사용 시작 이후 **받은편지함의 받은 메일만** 허용한다.
  보낸 메일·보관 메일 등의 관련 문맥을 쓰려면 사용자·계정 경계를 지키는 별도 승인된 읽기 계약이 필요하다.
  F2가 기존 메일 API의 조회 범위를 임의로 넓히지 않았다.
- F1 분석 모듈은 추가됐지만 기존 MailDetail에는 F1 action_items가 없다.
  원본 패널은 준비 부족을 표시하며 요청사항을 만들지 않는다.
  F1 분석 결과를 F2에서 읽는 연결과 검사가 필요하다.
- 문체 학습은 동의·끄기·삭제·표현 제외만 구현했다. 실제 발송 기록·수집·10건 단위 갱신·삭제 이후
  늦은 학습 작업 차단은 보낸 메일 기반과 작업자가 준비된 뒤 연결해야 한다.

실제 AI 품질, 생성 지연, 스트리밍, 실제 관련 메일 검색은 아직 검증하지 않았다.
