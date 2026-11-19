# F2 프로필·답장 초안 — 분리 구현과 연결 계약

최초 기준: `origin/develop` 0f68ad1. 승인 후 `9244454`의 F1/F3를 가져와 호환성을 검사한다.
F2는 공통 파일·기존 계정·메일·키를 직접 변경하지 않는다.
이 문서는 F2 전용 구현 보충 명세이며 기존 수용 기준을 완료 처리하지 않는다.

## 구현 단위

1. 프로필 전체 조회·저장·검증·사용자 격리·저장 충돌 검사. 취소는 저장 요청을 보내지 않는다.
2. 미리보기·초안 생성 입력/출력 포트, 프로필의 인사·마무리·서명 그대로 적용,
   방향 2~3개, 근거 범위와 접근 가능한 mail_id 검사.
3. 현재 편집 본문을 기준으로 수정. 편집 후 재생성 확인, 실패·늦은 응답에서 편집 보존.
4. 명시적 학습 동의·끄기·기록 삭제·표현 제외 경계. 실제 수집·분석은 미구현.
5. S09/S06 전용 컴포넌트와 합성 응답 검사. 공통 라우터·main/preload는 연결하지 않는다.
6. 적용 전 패치·F0/F1/F4 전달과 검증 결과.

## API 계약

아래 경로는 전용 router를 등록한 테스트 앱에서 검증한다. 일반 app.main에는 미등록이다.
기존 `authorize`를 재사용하고, 저장소의 `session()`에서 사용자를 정한다.
클라이언트가 user_id/account_id를 선택할 수 없다. 기존 loopback·Host·Origin 제한도 유지한다.

- GET `/profile`: `{profile, exists, version}`. 미저장은 빈 기본값·exists=false·version=0.
- PUT `/profile`: `{profile, expected_version, consent_given}`. 이름 필수,
  격식 0~100 정수, 길이 short/normal/long, 보고 표현 bullet/prose.
  보고 섹션은 `highlights/ongoing/issues/next_week`를 중복 없이 모두 포함한 순서다.
  버전 불일치는 409이며 이전 편집을 덮어쓰지 않는다. 새 학습 동의에는 consent_given=true가 필요하다.
- GET/DELETE `/profile/style`: 상태·동의·학습 건수·표현·특징. 삭제는 기록·제외 표현을 지우고
  동의를 꺼 이후 자동 재학습을 막는다. 프로필의 나머지 값은 보존한다.
- POST `/profile/preview`: `{profile}`. 저장 전 값으로 고정된 합성 원문을 사용한다.
  실제 사용자 메일은 읽지 않고 저장도 하지 않는다.
- POST `/drafts`: `{mail_id, direction?}`. 소유 계정의 메일만 읽는다.
- GET `/drafts/{id}`: 소유 초안 재조회.
- PATCH `/drafts/{id}`: `{body, expected_version}`. 사용자가 편집한 본문을 임시 저장한다.
- POST `/drafts/{id}/revise`: `{action, body, expected_version, direction?}`.
  action=shorter/politer/rewrite. 현재 편집 본문 필수. 방향 변경도 이 경로로 재생성한다.
- 초안 응답: `{draft_id, mail_id, directions, selected_direction, body, evidence,
  references, version, profile_version, context_status}`. `evidence`의 span은 **Unicode 코드포인트**
  시작 포함/끝 미포함 위치이며 source=profile.greeting/closing/signature/phrase 또는 mail:{id}다.
  서버는 범위·본문 일치·허용 출처·메일 소유권을 검사한다. 제목·날짜는 모델 출력이 아닌 조회 결과다.
- 학습·AI·관련 메일·F1 분석 준비 부족은 각각 상태로 구분한다. AI 미연결은 503 ai_unavailable,
  잘못된 AI 출력은 502 invalid_ai_output. 가짜 결과로 대체하지 않는다.
- 발송 API·발송 IPC를 구현하거나 호출하지 않는다. S06 보내기는 비활성이다.

## F1 제공자 포트

최신 develop의 `app.ai.interfaces.TextGeneration`을 `app.ai.f2_shared_adapter.SharedDraftAI`로 재사용한다.
F2의 업무 입출력은 `app.ai.f2_port`의 Protocol을 유지한다. 외부 SDK·키·LLM 제공자 구현은 추가하지 않는다.
기본 실행은 여전히 AI 미설정이며, 테스트 제공자는 명시적 테스트 옵션에서만 허용한다.
제공자는 본문 가운데 부분과 방향·근거를 반환하고
서버가 저장된 인사·마무리·서명을 붙인다. 학습 동의가 꺼지면 학습 표현·특징을 입력하지 않는다.
메일은 데이터이며 지시문으로 실행하지 않는다. 합성 테스트 대역은 tests 안에만 둔다.
관련 메일 검색 포트는 ID를 반환하며 서버가 기존 인증된 detail로 다시 확인한다.
F1은 같은 스레드·상대와 의미 유사 상위 3건을 합쳐 중복 없는 ID 최대 50개를 반환한다.
현재 detail은 받은편지함의 받은 메일만 허용하므로 보낸 메일 등의 문맥 읽기는 후속 계약이 필요하다.
F1/F3의 분석·검색 모듈은 추가됐지만 F2의 관련 메일·요청사항 읽기에는 미연결이다.
보낸 메일 수집도 없어 해당 상태는 unavailable이다.

## F4 전달

`F2Repository.report_profile(user_id=서버에서_확인한_ID)`는 저장된 프로필과 버전을 반환한다.
보고 섹션 ID의 표시: highlights=금주 주요 업무, ongoing=진행 중인 업무,
issues=이슈·요청사항, next_week=차주 계획. 순서·report_recipient·report_style을 그대로 사용한다.
미저장일 때 exists=false를 확인하고 사용자 설정을 요청한다. F4 코드와 ReportMail은 변경하지 않는다.

## 연결 승인 전 경계

DB 모델은 `app.db.f2_models`의 별도 metadata, 저장소는 전용 모듈에 둔다.
Alembic·공통 서버 등록·화면 라우팅·IPC 연결·생성 타입 변경은 patches/F2에 준비한다.
패치 적용·공통 라우터 연결·마이그레이션 실행은 아직 하지 않는다.
자세한 실제 검사 결과와 실행 명령은 아래 안내와 별도 검증 보고에 정리했다.

## 현재 결과와 확인 방법

상세 결과는 [F2 검증 보고](F2-verification.md), 전달 문장은 [F0/F1/F4 전달](F2-handoff.md),
공통 파일 연결안은 [적용 전 패치](../../patches/F2/README.md)에 있다.
서버 API·DB·화면은 기능 전용 모듈에서 검증했으며 일반 앱에는 아직 등록하지 않았다.

공통 잠금 파일은 바꾸지 않고 기존 의존성만 사용한다.
프로필 필드는 데이터 문서대로 각각 저장하며 제외 표현·저장 버전을 추가한다.
DB metadata는 공통 Base와 분리하고 승인 전에는 Alembic 이력을 추가하지 않는다.

```bash
# 별도로 만든 테스트 PostgreSQL만 지정한다. 운영 DB·실제 메일은 사용하지 않는다.
cd apps/server
KLOVER_TEST_DATABASE_URL=postgresql+psycopg://postgres@127.0.0.1:55432/klover_f2_test uv run pytest -q
uv run ruff check .
uv run ruff format --check .
```

위 주소는 이번 작업에서 만든 테스트 전용 컨테이너의 주소다. 기존 `.env`에 저장하지 않는다.
컨테이너가 중지된 경우 이 작업의 `klover-f2-test-pg`를 시작하거나 별도의 테스트 DB를 준비한다.
테스트마다 고유 임시 스키마를 만들고 종료할 때 그 스키마만 제거한다.

```bash
# 저장소 루트: 기존 앱 회귀 검사
corepack pnpm --filter desktop typecheck
corepack pnpm --filter desktop lint
corepack pnpm --filter desktop test
corepack pnpm --filter desktop build

# 공통 앱과 분리된 F2 합성 화면
corepack pnpm --filter desktop exec vite --config f2.vite.config.ts
# http://127.0.0.1:5175/ (S09), /#reply (S06), /?ai=unavailable#reply (AI 준비 부족)

# 브라우저 반복 검사: 설치된 Chromium 경로는 해당 환경에 맞춘다.
PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH=/usr/bin/chromium corepack pnpm --filter desktop exec playwright test --config f2.playwright.config.ts
```

F2 화면은 위 별도 주소에서만 연다. 일반 앱에서 곧바로 설정·초안으로 이동할 수 있다고
보고하지 않는다. `?references=yes#reply`는 합성 참고 메일 미리보기 검사다.
초안 ID를 받은 호스트는 `draftId` 또는 `?draft=:draftId`로 임시 저장 내용을 복원한다.

## 수용 기준 대응

| 원래 수용 기준 | 확인한 부분 | 남은 확인 |
| --- | --- | --- |
| 저장한 인사·마무리·서명 적용 | DB 재조회 후 합성 생성·수정에서 문자열과 근거 범위 일치 | 실제 AI 연결 후 통합 |
| 문체·길이 변경 미리보기 3초 이내 | 1초 지연 갱신, 오래된 응답 무시, 합성 화면 갱신 | 실제 AI 지연·품질 미검증 |
| 10초 안에 초안·방향 2~3개 | 계약 검증·타임아웃·합성 응답 | 실제 시간·첫 글자·스트리밍 미구현 |
| 밑줄과 근거 표시 | 코드포인트 범위 검증·프로필 밑줄·수정된 근거 제거 | 실제 AI 근거 정확도 미검증 |
| 참고 메일 제목·날짜 | 소유권 재검증·조회 결과로 표시·미리보기·없으면 숨김 | 실제 관련 메일 검색 미구현 |
| 세 가지 빠른 수정 | 현재 편집 본문·방향·action 전달, 실패/늦은 응답/충돌에서 보존 | 실제 AI 수정 품질 미검증 |
| 자동 발송 없음 | F2 발송 API·발송 호출 없음, 버튼 비활성 | 실제 발송은 이번 범위에서 제외 |
| 학습 끄기·기록 삭제 | 명시적 동의, 결과 미사용, 사용자별 삭제, 제외 표현 차단 | 실제 발송 수집·10건 단위 학습·작업자 미구현 |

S09 취소·내부 나가기 확인·보고 섹션 이동과 1440×900/1280×720 레이아웃은 합성 검사했다.
F4 보고서에 실제로 순서가 적용되는지와 F0 공통 메뉴 이동은 아직 통합 확인 대기다.
