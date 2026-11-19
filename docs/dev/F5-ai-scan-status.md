# F5 AI 스캔 — 상태

## 양식 요약

> 양식: [status-template.md](status-template.md) · 현황판: [progress.md](progress.md)

| 항목 | 내용 |
| --- | --- |
| 브랜치 | `feat/F5-ai-scan` |
| 작업 도구 | 없음 |
| 상태 | develop 병합 — 앱 연결 단위 [#25](https://github.com/choi7614/klover_my_prototype/pull/25) (`841f782`), 공통 패치 01~02 적용 ([#28](https://github.com/choi7614/klover_my_prototype/pull/28), `integrate/F5-patches`) |
| 마지막 구현 커밋 | `7b96be1` — 앱 제안·할 일 화면 연결과 main/preload 공통 패치 (CI 통과) |
| 병합 커밋 | `72fb8e4` — 승인된 PR #20 병합 |
| 기준 develop | `420078e` (F4 공통 패치까지 포함, fast-forward 로컬 통합) |
| 미커밋 변경 | 없음 (이 현황 갱신도 커밋·Push) |
| 갱신일 | 2026-11-19 |

## 현재 상태

### 공통 패치 적용 (2026-11-19, 통합 채팅, `integrate/F5-patches`)

- `patches/F5/` 01 → 02를 develop `5971346` 위에 적용했다. `baseline.json`의 대상 파일 12개가 현재 develop과 모두 같아 그대로 적용했다.
- 이제 앱에서 보인다: 메일을 열면 S04 제안 패널, 사이드바 '할 일' 메뉴와 `/todos` 화면.
- 통로는 `klover:suggestions:*` 8개만 추가됐다. 기존 메일 4·F2 10·검색·주간 보고 5개 통로와 메일함·검색·답장 초안·주간 보고 경로는 그대로다.
- 토큰은 main(`readLocalAPI`)에서만 읽고 화면에는 `{ ok, data | error.code }`만 넘긴다.
- 캘린더·회신 승인 버튼은 꺼져 있다(`calendarReady`·`replyReady` 기본 false, 운영 화면에서 켜지 않음). 승인·무시·할 일 추가·완료 요청은 버튼 클릭 처리 함수 안에서만 실행된다.
- 검사: 데스크톱 lint·typecheck·build 통과, Vitest 22개 파일 154개 통과(F5 브랜치 기록과 같음). 서버·DB·공유 타입·잠금 파일은 바꾸지 않았다.
- 미실행: Electron 실제 창, 실제 DB의 0005 설치. 제안을 만드는 쪽(F1 결과→F5 입력)이 아직 없어 실제 앱에서는 제안 목록이 비어 있는 것이 정상이다.

### 이전 단위 (2026-11-19, Claude): 앱에서 F5 API 쓰기

- 완료(F5 브랜치): `features/suggestions/ipc-client.ts`(통로 → `F5Client`, 통로 없으면 '준비 중'),
  `mail-suggestions.tsx`(메일 ID로 제안 조회 → `SuggestionReader`, 없으면 S03 모양 유지),
  `todo-list.tsx`(할 일 진행 중/완료 목록·완료 표시·직접 추가), `SuggestionReader`에 메일 머리 `header` 자리 추가, 테스트 3개 파일.
- 적용 전 패치(`patches/F5/`): 01 main/preload 통로 8개(`klover:suggestions:*`)와 `shared/f5-bridge.ts` 인수 검사,
  02 공통 App `/todos` 경로·F0 메일함 S04 패널·사이드바 '할 일' 메뉴. **통합 채팅 적용 전에는 앱에 보이지 않는다.**
- 승인 경계: 캘린더·회신 승인 버튼은 꺼 둔 채(`calendarReady=false`, `replyReady=false`). 버튼을 누르기 전에는 아무 요청도 실행하지 않는다.
- 이번 범위 아님(미구현): `/suggestion-events`·OS 알림·트레이·WebSocket·S10 놓친 제안, Calendar 실제 연결,
  회신→F2 초안 실행, 사이드바 '할 일' 건수, **F1 결과→F5 입력 변환(F1 채팅의 AI 제공자 작업과 겹쳐 보류)**.
- 할 일 목록은 전용 화면 명세·목업이 없어 디자인 시스템 기준의 단순 목록으로 만들었다(사용자 승인).

### 이전 단위까지

- 완료: 일정·할 일·회신 제안 입력 계약, 원본 mail_id·소유 계정·본문 해시·근거 위치 검증,
  영속 저장·목록·재조회·무시 이력, 중복 생성·중복/동시 승인 방지, 앱 할 일 CRUD.
- 완료: 사용자 승인 후 공통 라우터·실행 저장소 조립·공유 타입 등록, 0004_f2 뒤 0005_f5 추가.
  기존 F2·F3 메타데이터와 경로를 유지했다. **운영 DB의 실제 마이그레이션은 실행하지 않았다.**
- 부분 완료·미통합: Calendar 쓰기/freebusy 권한·입출력·오류·결정적 event ID 경계,
  S04 전용 컴포넌트와 합성 화면, 놓친 제안 조회와 durable outbox·표시 확인 계약.
- 미구현/미연결: F1 실입력 변환·수신 분석 연결, F0의 S04 라우팅·제안 IPC·S10 알림/트레이·WebSocket,
  실제 Calendar HTTP transport·추가 동의·등록·겹침 조회, F5 회신 제안→F2 실행 연결, 할 일 리마인더.

Calendar 기본 실행기는 차단된다. 테스트 결과는 pending/simulated/test이며 실제 등록 성공으로
표시하지 않는다. 외부 결과가 불명확하면 후속 권한 오류가 나도 입력·캘린더 변경 잠금을 유지한다.
메일 발송 경로는 없다. 실제 Calendar·Gmail·OS 알림을 실행하지 않았고 OAuth 범위·계정·키는 바꾸지 않았다.

현재 develop에 있는 F1 AnalysisResult·공통 AI 인터페이스, F0 메일함·동기화, F2·F3 API/IPC를 확인했다.
F1과 F5 계약 사이에는 행동 키·근거 인용·본문 해시 등의 변환이 남아 있다. 다른 채팅의 완료를 가정하지 않는다.

## 검사 결과

이번 단위(앱 연결):

| 검사 | 결과 | 비고 |
| --- | --- | --- |
| 데스크톱 lint·typecheck·Vitest (브랜치만) | 통과 / **143개 통과** | 패치 미적용 상태 |
| 데스크톱 lint·typecheck·Vitest (패치 01·02 적용) | 통과 / **154개 통과** | 적용 후 되돌림, `git apply --check` 통과 |
| Electron 빌드 (패치 적용) | 통과 | 실제 앱 창·실서버 연결 확인은 **미실행**(클라우드 환경, 실제 계정 없음) |
| 서버 pytest | 미실행 | 서버 코드 변경 없음. PR CI에서 확인 |

이전 단위(#20):

| 검사 | 결과 | 비고 |
| --- | --- | --- |
| 서버 pytest | **343 통과 / skip 0 / 실패 0** | 새 PostgreSQL 16+pgvector DB, 공통·F1·F5 DB 검사 포함 |
| 서버 Ruff·format | 통과 | 공통 통합 검사, 검사 스크립트 포함 |
| 데스크톱 lint·typecheck·Vitest | 통과 / **106개 통과** | 기존 F0·F2·F3와 F5 포함 |
| 브라우저 | **4개 통과** | F5 2개, 기존 F0 2개, 1440/1280 화면 |
| Electron 빌드·F5 검사 화면 빌드 | 통과 | 실제 OS 알림/트레이 동작 검사 아님 |
| 공유 타입 생성·typecheck | 통과 | `pnpm gen:api-types`로 재생성 |
| 통합 패치 재검증 | 통과 | 새 임시 복사본의 동일 343개 검사, OpenAPI 일치 |
| 마이그레이션 보존 | 통과 | 0004_f2 → 0005_f5 반복 upgrade·downgrade·재-upgrade. 합성 기존 메일·계정·수신 커서·암호문·F2 프로필·F3 검색 기록 보존 |
| GitHub Actions | [PR #20 CI 통과](https://github.com/choi7614/klover_my_prototype/actions/runs/44470201568) | 서버·데스크톱 두 작업 통과. DB 검사는 CI에서 skip될 수 있어 위 로컬 결과와 구분 |

검사 DB: 이 작업 전용 `klover_f5_test`, 루프백 포트 32769. 기존 DB·메일 계정은 사용하지 않았다.
검사 당시 환경 변수는 KLOVER_TEST_DATABASE_URL, KLOVER_F1_TEST_DATABASE_URL,
KLOVER_F5_TEST_DATABASE_URL을 모두 이 DB로 지정했다.

## 공통 영역 요청

- 적용 완료(승인된 범위): DB 소유자 제약·0005_f5·서버 등록·공유 타입.
  [패치 기록](f5-patches/README.md)에 b147cfd 대비 변경을 보관했다. F2·F3 마이그레이션 비교를 보존했다.
- 다음 통합 요청: [F0/F1/공통 서버 전달 문서](F5-handoff.md). F0 main/preload/app은 이번 변경으로 수정하지 않았다.
- F1 저장 SQL의 Alembic 전환 후보 번호는 현황판의 다음 빈 번호(현재 0006)를 확인한다.
- 실제 Calendar transport와 계정별 권한 확인·OS 연결은 별도 요청으로 진행한다.

## 다음 할 일

0. 통합 채팅에서 `patches/F5/` 01→02 적용, 맥북 실제 앱에서 메일 제안 패널·할 일 화면 확인.
1. F1 결과 변환과 F0 화면·알림 연결을 별도 단위로 구현·검사한다.
2. 운영 DB의 0005_f5 실제 적용은 사용자 환경에서 별도로 확인한다.
3. 실제 권한과 실행 코드 확인 후에만 Calendar 동의/실제 실행을 별도로 검토한다. main 병합은 승인 범위가 아니다.

## 인수인계 메모

- 멈춘 지점: 앱 연결 단위 PR #25 CI 통과·develop 병합 완료. 공통 패치 `patches/F5/`는 통합 채팅 적용 대기.
- 이전: 구현·로컬 통합 검사·GitHub CI 통과, PR #20 develop 병합 완료.
- 미실행: 실제 LLM·Google Calendar·메일 발송·OS 알림/트레이·운영 DB 마이그레이션.
- 주의: F5 테스트 성공은 실제 Calendar 등록 성공이 아니다. 실행 중 프로세스 종료는 담당자 조정 대상이다.
- 상세: [계약](F5-ai-scan-contract.md), [최초 분리 개발 기록](F5-ai-scan-report.md),
  [생성 입력/HTTP 계약](f5-contract/openapi.json), [합성 화면](../../apps/desktop/f5-preview/index.html).
