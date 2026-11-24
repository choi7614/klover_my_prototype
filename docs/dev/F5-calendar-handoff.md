# F5 Calendar 연결·명시적 일정 승인 인수인계

2026-11-25 · Codex · 작업 브랜치 `feat/F5-ai-scan`

## 기준과 제출 상태

- 원격 develop `7668d94aa5f251541d95e17c9ed238fabc52b418`, PR #41 병합을 API로 확인했다.
- 기존 F5 원격/로컬 HEAD `b85e2eb5e6980e7ec1900346bb5d0a27eb47b93a`를 재사용했다. 기존 브랜치와 작업을 삭제·초기화하지 않았다.
- 사용자 승인 후 최신 develop `7668d94`를 기능 브랜치에 로컬 통합했다(`f5046d7`). 공통 패치는 미적용이다. 별도 검증 사본에서 기능 파일과 공통 변경안을 함께 검사했다.
- 사용자 묶음 승인으로 구현 `7634286`·로컬 통합 `f5046d7`을 커밋했다. Push 및 [PR #44](https://github.com/choi7614/klover_my_prototype/pull/44) 제출 완료. 구현/검사 제출 커밋은 `b5071c9`이며 최종 문서 커밋 HEAD·자동 검사는 PR을 따른다. develop/main 병합은 하지 않는다.
- 작업 원본 `/workspace/klover_my_prototype`. 검증 사본 `/tmp/klover-f5-calendar-base`. 사본에만 있는 필요한 공통 변경은 전부 `patches/F5/calendar/*.patch`에 보관했다. 사본을 직접 운영에 사용하지 않는다.

## 구현한 흐름

1. 인증된 `GET /calendar/connection`으로 현재 Gmail 계정 이메일·소유 캘린더 ID/이름/시간대·연결 오류를 표시한다.
2. 사용자 클릭 → 신뢰한 main frame IPC → main이 고정 `http://localhost:8000/auth/google`을 브라우저로 연다. 화면이 보낸 임의 URL은 받지 않는다.
3. 기존 브라우저 폼의 Host/loopback/Origin·CSRF·state·PKCE·일회성/10분 제한을 그대로 재사용한다. 브라우저의 Google 추가 동의가 끝나도 일정은 등록하지 않는다.
4. 기존 Gmail 읽기 범위를 유지하며 `include_granted_scopes=true`로 Calendar 권한을 추가한다. Google profile 이메일과 기존 DB Gmail 계정을 모두 확인한다. 다른 계정은 거부한다.
5. 기존 `token.key`/Fernet 방식으로 **별도 Calendar 표**에 토큰을 저장한다. 기존 GoogleCredential·MailAccount·수신 시작일/커서·메일은 쓰지 않는다. refresh 응답에 새 refresh_token이 없으면 원래 Calendar refresh_token을 유지한다.
6. S04에서 현재 계정과 캘린더를 보고 제목·시작·종료·UTC 차이·장소를 수정한다. 겹침 확인은 조회만 수행한다. 날짜/캘린더를 수정하면 이전 겹침 결과를 지운다.
7. 사용자가 **캘린더에 추가**를 누른 요청만 기존 F5 claim/버전/소유자 검사와 실행 어댑터를 거친다. 자동 분석·제안 생성에는 실행기를 주입하지 않는다.
8. 제안 ID에서 계산한 고정 event ID와 요청 해시를 Google private extendedProperties에 기록한다. 재시도는 조회부터 한다. 중복(409)도 재조회한다. 시간 초과로 결과가 불명확하면 pending/uncertain으로 유지하고 입력·캘린더 변경을 잠근다.
9. 확인된 실제 어댑터 영수증만 approved/succeeded/live로 저장한다. 등록 거절·권한 부족·만료·통신 실패·불명확 결과를 고정 오류 코드로 구분한다. 테스트 DB에서 MockTransport로 live 경계를 검사한 결과는 실제 사용자 일정 등록을 의미하지 않는다.
10. 연결 해제는 `POST /calendar/disconnect`로 로컬 Calendar 자격 증명만 제거한다. Google revoke나 일정 삭제 API는 호출하지 않는다. Gmail 연결·이미 등록된 일정·Google 계정의 부여 권한은 남는다.

## 권한과 범위

| 범위 | 용도 |
| --- | --- |
| 기존 `gmail.readonly` | 기존 계정 확인·Gmail 기능 보존 |
| `calendar.events.owned` | 사용자가 소유한 캘린더 일정의 등록·동일 event ID 재조회 |
| `calendar.calendarlist.readonly` | 캘린더 이름/ID/시간대/소유자 목록 표시 |
| `calendar.events.freebusy` | 겹치는 시간 범위만 조회, 제목·참석자는 읽지 않음 |

전체 Calendar 권한은 요청하지 않는다. 공유 캘린더의 writer 권한은 현재 지원하지 않는다.
일정 요청은 참석자 없이 `sendUpdates=none`으로 보낸다. 메일/초대 발송·OS 알림·트레이·시작 프로그램·양방향 동기화는 구현하지 않았다.
UTC 차이는 한 번짜리 일정의 명시적 오프셋이다. 지역별 일광절약시간 자동 계산·반복 일정은 제공하지 않으며 사용자가 날짜에 맞는 오프셋을 고른다.

## 변경 파일 지도

- `app/connectors/google_calendar.py`: Calendar 목록·조회·등록·freebusy, 고정 오류 변환. HTTP transport 주입 가능.
- `app/services/calendar.py`: 기존 어댑터에 owned 최소 범위·권한 만료/명시적 등록 거절 오류 추가.
- `app/services/f5_calendar.py`: 현재 DB 계정·실제 소유 캘린더 확인 후 기존 어댑터 호출.
- `app/db/repositories/f5_calendar.py`: 별도 Calendar 표 ORM·암호화 저장·갱신·로컬 해제. Gmail 저장소의 암호화 키 처리 재사용.
- `app/api/f5_calendar.py`, `f5_calendar_consent.py`: 기존 Bearer 인증 API와 브라우저 추가 동의 조립.
- `app/api/f5.py`: Calendar 응답에도 no-store 적용.
- `app/cli/run_calendar_connection.py`: 같은 동의 화면의 별도 CLI 실행 경로. 업무 서버와 동시에 8000 포트를 사용하지 않는다.
- `renderer/features/suggestions/calendar-connection.tsx`: 계정·권한 상태·연결/재조회/해제 화면.
- 같은 폴더의 `mail-suggestions.tsx`, `types.ts`, `ipc-client.ts`, `suggestion-card.tsx`: 연결 상태/선택 목록·시간대·오류 안내.
- `tests/f5/test_calendar_live.py`, `test_calendar_migration.py`, 화면 테스트: 가짜 Google·분리 DB·승인/재시도/거절/해제 보존 검사.
- `scripts/f5/verify_calendar_patches.py`: 기준 소스의 별도 사본과 공통 파일 해시를 확인하고 패치 적용 검사.

## 아직 적용하지 않은 공통 패치

최신 develop 기준 `patches/F5/calendar/`의 **03→08** 순서다. 과거 `patches/F5/01,02`는 이미 적용된 기록이므로 다시 적용하지 않는다.

| 파일 | 목적 |
| --- | --- |
| `03-oauth.patch` | 기존 OAuth에 선택적 추가 범위·동의 화면 문구 주입. Gmail refresh는 추가 동의 후 Google이 반환하는 범위 합집합에서 gmail.readonly를 확인하고 원본 refresh_token 유지 |
| `04-database.patch` | 새 `0009_f5_calendar`(부모 `0008_history`)·F1 비교 metadata 등록·과거 0007 비교 검사에서 후속 표 제외 |
| `05-server.patch` | app.main 라우터·run_mail_api 실어댑터/브라우저 동의 조립·API 경로 검사 갱신 |
| `06-desktop.patch` | main/preload 제한 IPC 3개·고정 브라우저 열기·신뢰한 화면/임의 인수 거절 검사 |
| `07-settings.patch` | `/settings/calendar`와 캘린더 설정 링크 |
| `08-generated-api-types.patch` | 사본에서 OpenAPI export + openapi-typescript로 재생성한 공유 타입. 직접 편집 아님 |

0008_history가 실제 최신 이력임을 확인하고 0009를 progress에 예약했다. 통합 직전 번호 충돌·원격 변경·baseline.json 해시를 다시 확인한다.
공통 잠금 파일·설정·main/preload·공유 타입·실제 마이그레이션은 기능 작업 폴더에서 직접 수정하지 않았다.

## 검사와 미검증

제출 브랜치 자체는 서버 **650 통과/skip 4**(공통 OAuth·0009 미적용 4개), 앱 **195 통과**, Ruff/lint/typecheck 통과다. 공통 변경안을 적용한 사본의 최종 결과: 서버 전체 **654 통과/skip 0**, 앱 전체 **195 통과**, Ruff·lint·typecheck·빌드·패치 재구성 검사 통과. F5 status에도 기록했다. 검사 DB는 이 작업에서 새로 만든 Docker PostgreSQL16+pgvector의
`klover_f5_test`이며 모든 계정·메일·키·응답은 합성이다. 실제 사용자 DB, 실제 Gmail·Google Calendar·유료 AI·Ollama에 접근하지 않았다.

- 서버 전체 회귀와 새 F5 검사: 암호문/Gmail 계정 보존·권한 오류·반복/동시 승인·시간 초과 후 재시도·명시적 거절·인증/Origin 거부·OAuth 취소/replay·0009 반복 upgrade/downgrade.
- 앱: 연결 상태/이메일/캘린더·사용자 클릭 전 외부 열기/해제 없음·UTC 차이와 종료 수정·S04 기존 승인/오류·토큰 비노출 경계.
- Chromium의 기존 S04 합성 화면 2개 통과. 검증 사본 node_modules 심볼릭 링크로 일부 폰트 요청이 차단되었으므로 글꼴 시각 품질 확인은 미완료.
- Linux Electron 생산 빌드는 성공. 네이티브 Electron 창·브라우저 실제 Google 동의·Google 실제 범위 반환/재동의/refresh·맥북 키체인/브라우저·사용자 DB 이력·실제 일정 등록은 **미검증**이다.
- 프로세스 종료로 executing에 남은 기존 F5 요청의 자동 복구는 이번 범위에 추가하지 않았다. 수동으로 pending으로 되돌려 재실행하지 말고 고정 event ID를 먼저 대조해야 한다.

## 통합 후 맥북 확인 절차 (이번 작업에서는 실행 안 함)

1. 통합 PR 승인/적용 후 별도 테스트용 Google 계정·캘린더에서 확인한다. 기존 DB·token.key·설정은 먼저 백업하고 초기화하지 않는다.
2. migration head가 0009_f5_calendar인지 확인하고 명시적으로 upgrade한다. 기존 Gmail 계정·메일 건수·sync_started_at·수신 커서가 유지되는지 비교한다. 암호문/키/토큰을 화면이나 로그에 출력하지 않는다.
3. 기존 Gmail 읽기·새로고침이 작동하는지 확인한다. 업무 서버를 기본 8000 포트로 실행하고 앱의 캘린더 설정을 연다.
4. 추가 동의 클릭 후 브라우저 계정 이메일을 확인한다. 먼저 거절해 미연결/취소가 보이고 Gmail이 유지되는지 확인한다. 다시 동의해 기존 Gmail 읽기와 위 3개 Calendar 범위만 요청되는지 확인한다.
5. 앱에서 연결 상태 다시 확인 → 같은 이메일·소유 캘린더 이름/ID·시간대 확인. 공유 writer 캘린더가 선택 목록에 없는지 확인한다.
6. 합성 원문/근거를 가진 일정 제안을 준비한다. 자동 분석/조회/동의만으로 일정이 생기지 않는지 확인한다. 제목·날짜·종료·오프셋·캘린더를 수정한다. 겹침 확인과 수정 후 이전 경고 해제를 확인한다.
7. 캘린더에 추가를 한 번 눌러 Google 일정의 수정 값과 참석자 없음 확인. 빠른 중복 클릭/같은 제안 재요청에도 event ID 하나만 있는지 확인한다. 실계정 네트워크 조작/타임아웃 재현은 테스트 캘린더에서만 수행한다.
8. Calendar 추가 권한을 철회한 상태/연결 실패/등록 거절에서 성공 표시가 없는지 확인한다. Google 쪽 전체 앱 권한 철회는 Gmail도 취소할 수 있으므로 로컬 Calendar 해제와 구분한다.
9. 앱 Calendar 연결 해제 후 기존 일정이 남고 Gmail 읽기·새 메일·토큰 갱신이 유지되는지 확인한다. 앱 해제는 Google 서버의 동의 자체를 철회하지 않는다.

## 통합 채팅에 전달

F5 Calendar 기능 파일과 최신 develop `7668d94` 기준 공통 패치 03~08을 준비했다. 작업 폴더는 `/workspace/klover_my_prototype`, 브랜치는 `feat/F5-ai-scan`, 구현 커밋은 `7634286`, develop 로컬 통합은 `f5046d7`이다. 구현/검사 제출 커밋은 `b5071c9`, PR은 #44다. 최종 문서 커밋 HEAD·자동 검사 결과는 PR을 따른다.
origin/develop `7668d94`의 기능 브랜치 로컬 통합은 완료했다. 이 패치를 통합 채팅에서 적용·공유 타입 재생성·전체 재검사해야 실제 앱에 연결된다. 현재 브랜치에서 실운영 연결 완료라고 보고하지 않는다.
기존 F1 분석→제안 훅은 이미 develop에 있고 이번 자동 실행 변경은 없다. F0에는 Calendar 설정 경로/제한 IPC만 요청하며 OS 알림·트레이·메일 발송은 요청하지 않는다.
실제 Google·맥북·사용자 DB는 미검증이다. 커밋·Push·PR은 사용자 묶음 승인 범위이며 develop/main 병합은 별도 승인 대상이다.
