# F2·F4·F5 설정과 Calendar 통합

2026-11-25 · `integrate/settings-calendar` · 기준 develop `7668d94`.
사용자가 검사·수정·로컬 통합·커밋·Push·PR 생성 및 문제없을 때 develop 병합을 승인했다. main은 제외한다.

## 범위와 원본

- F2 PR #42 `3caacd5`: 개인정보·학습 데이터 관리, 동의와 삭제 범위 안내, 비활성 기록 조회.
- F4 PR #43 `c1ec90b`: 첫 주·대상 기간·오류 안내, 화면 이동 중 편집본 보존.
- F5 PR #44 `1ddc0bf`: 별도 Calendar 암호화 자격 증명, 추가 동의, 소유 캘린더 조회·일정 편집·명시적 승인 등록.
- 세 head를 별도 통합 브랜치에서 merge하여 원본 커밋과 브랜치를 보존했다.
- F2 privacy 01~03, F4 finish 06, F5 calendar 03~08의 변경 의도를 통합 적용했다.
  App/routes 설정 메뉴 충돌은 세 기능을 함께 연결하도록 조정했다. 생성 API 타입은 `pnpm gen:api-types`로 재생성했다.
- 세 PR은 통합 PR이 develop에 병합되면 포함된 커밋 기준으로 함께 반영된다. 미완성 연결 상태만 먼저 병합하지 않는다.

## 공통 변경과 추가 수정

- 설정에서 주간 보고·개인정보·Calendar로 이동/복귀. 미구현 메일 계정 관리·알림/시작은 준비 중으로 비활성 유지.
- 인증된 세션에서만 개인정보·프로필·Calendar 설정 진입. 계정별 화면 key와 보고서 편집본 scope 전달.
- 추가 검사에서 같은 화면의 scope가 바뀔 때 이전 편집본이 새 계정 캐시에 저장될 수 있음을 재현했다.
  편집본의 원래 연결/계정을 확인해 저장하고, 늦은 요청도 현재 계정이 같은 경우에만 반영한다.
- main/preload의 제한 Calendar IPC, 고정 localhost 동의 주소, 서버 등록/실행 조립, 추가 OAuth 범위 연결.
- `0009_f5_calendar`(부모 `0008_history`)는 Calendar 암호문 표 하나를 추가한다. 기존 Gmail 행·커서·메일을 변경하지 않는다.
- Calendar 해제는 로컬 Calendar 암호문만 제거한다. Google 전체 권한 취소나 기존 일정 삭제는 하지 않는다.
- 일정 등록은 사용자 승인 후 고정 event ID로 수행한다. 참석자/초대 발송은 없다.

## 검증과 한계

- 합성 사용자·가짜 Google HTTP 응답·분리 PostgreSQL에서 서버 **655 통과 / skip 0**.
- 앱 최종 전체 **209 통과(32개 파일)**, F4 Chromium **4 통과**, F5 Chromium **2 통과**.
- Ruff check/format(196개 파일)·앱 lint/typecheck·생산 빌드·git diff --check 통과.
- 설정 경로·인증 차단·계정 격리 신규 검사 포함. 계정 전환 재현 검사는 수정 전 실패/수정 후 통과.
- 테스트 DB는 `klover-history-tests`, localhost 55449의 `_test` DB만 사용했다.
- 실제 사용자 DB·Gmail·Google Calendar·유료 AI·Ollama·맥북 Electron은 접근/실행하지 않았다.
- 실제 Google 동의·권한 반환·일정 등록은 아래 맥북 확인이 남는다. 자동 검사는 실계정 성공을 보장하지 않는다.
- OS 알림·시작 프로그램·실제 문체 학습 수집·메일 발송·반복 일정·양방향 동기화는 범위 밖이다.

## 맥북 업데이트와 확인

1. 앱·서버를 종료한다. [setup.md 10절](setup.md)의 방법으로 DB와 `.env`/`.local-secrets`를 함께 백업한다.
2. 저장소 폴더에서 `git status --short --branch`를 확인한다. 로컬 변경이 없고 develop일 때 setup 9절 업데이트를 따른다.
3. `alembic upgrade head`, `alembic current`, `python -m app.cli.check_database`를 실행한다.
   head는 `0009_f5_calendar` 하나다. DB 초기화·키 재생성·downgrade는 하지 않는다.
4. 기존 방식으로 서버와 앱을 실행한다. Gmail 목록·본문·새로고침이 유지되는지 먼저 확인한다.
5. 설정 → 개인정보·학습 데이터: 프로필·동의·기록 조회. 실제 수집·학습은 준비 중이라는 안내를 확인한다.
   기록 삭제는 되돌릴 수 없으므로 기존 사용자 데이터로 시험하지 말고 별도 테스트 자료에서만 확인한다.
6. 설정 → 주간 보고: 프로필·보고 대상을 준비하고 분석 완료 메일로 생성한다. 편집 후 설정으로 이동·복귀해 내용 보존,
   저장·복사·근거·실제 대상 기간을 확인한다. 앱 종료 전에는 저장한다.
7. 설정 → 캘린더 연결 → 추가 동의. Google 프로젝트의 Calendar API가 사용 설정되어 있고 테스트 사용자가 등록되어야 한다.
   기존 웹 OAuth 클라이언트와 `http://localhost:8000/auth/google/callback`을 사용한다.
8. 기존 Gmail과 같은 Google 계정을 선택해 소유 일정 쓰기·캘린더 목록·겹침 조회 추가 권한을 확인하고 동의한다.
   브라우저 연결 완료 후 앱에서 연결 상태 다시 확인을 누른다. 연결만으로 일정이 등록되지는 않는다.
9. 별도 테스트 캘린더/테스트 메일의 일정 제안에서 제목·시각·오프셋·종료·캘린더를 확인하고 명시적으로 승인한다.
   실제 등록·중복 방지·해제 후 Gmail/기존 일정 보존을 확인한다. 날짜에 맞는 UTC 차이를 직접 선택한다.

Google 계정 권한을 Google 웹사이트에서 전체 철회하면 Gmail에도 영향이 있을 수 있다. 앱의 Calendar 해제와 구분한다.
세부 기능별 확인은 [F2](F2-privacy-data.md), [F4](F4-app-finish-handoff.md), [F5](F5-calendar-handoff.md)를 참고한다.
