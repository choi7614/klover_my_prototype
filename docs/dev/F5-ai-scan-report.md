# F5 최초 분리 구현·검사 기록

> 아래는 0f68ad1 기준으로 공통 패치 적용을 승인받기 전에 작성한 기록이다.
> 2026-11-19 사용자 승인 후 b147cfd 기반 공통 서버·0005_f5·공유 타입을 통합했다.
> **현재 상태와 통합 검사 결과는 [F5-ai-scan-status.md](F5-ai-scan-status.md)를 따른다.**

현재 브랜치는 **feat/F5-ai-scan**, 기준 커밋은 **0f68ad1**이다.
기존 work 브랜치와 커밋을 보존했다. 원격 정보를 다시 확인했으며 develop 기준은 같고
F0의 원격 후속 작업은 이 브랜치에 가져오지 않았다.
커밋·Push·PR 생성·작업 브랜치의 공통 영역 통합은 아직 하지 않았다.

## 구현 상태

여기서 완료는 **F5 전용 모듈과 분리 검사 범위의 완료**다. 전체 제품 통합 완료를 뜻하지 않는다.

| 요청 범위 | 상태 | 구현·검사한 내용 | 실제 연결 상태 |
| --- | --- | --- | --- |
| F1 결과 → 일정·할 일·회신 제안 | 분리 구현 완료 | 입력 계약, 원본 mail_id·소유 계정·본문 해시·근거 위치 검증 | F1 실입력 어댑터 없음. 독립 AI 제공자를 만들지 않음 |
| 저장·목록·재조회·무시 | 분리 구현 완료 | PostgreSQL 저장·페이지 조회·재연결 후 재조회·무시 기록·유일한 생성 이벤트 | 공통 DB·API에는 적용 전 |
| 승인 경계 | 분리 구현 완료 | 승인 전 실행 없음, 수정값 반영, 타 사용자 거부, 중복·동시 승인, 버전 충돌·실패·불명확 실행 차단 | Calendar 테스트는 pending/simulated/test. 운영 승인으로 저장하지 않음 |
| 앱 할 일 | 분리 구현 완료 | 직접 생성·조회·수정, request_id 중복 제거, 제안 승인과 할 일 생성의 원자적 저장 | F0 스마트 보기·건수·리마인더 연결 없음 |
| Google Calendar | 부분 | 쓰기/freebusy 동의 범위 분리, 계정 검증, 입력·출력·오류, 결정적 event ID와 조회 후 삽입 경계 | 실제 HTTP transport·토큰 연결·쓰기 동의·등록·겹침 조회 미구현/미확인 |
| S04 카드 | 부분 | 근거 강조·수정·승인·무시·연결 부족·실패·재시도·불명확 상태, 반응형 배치 | 합성 검사 화면만 있음. F0 라우터·실제 메일 화면에는 미연결 |
| 놓친 제안·알림 | 준비 범위 완료 | pending/notified 조회, 영속 outbox·event_id·표시 후 ack 계약 | WebSocket·OS 알림·트레이·알림 설정은 F0/서버 연결 대기 |

실제 메일 수신·인증된 조회 기반 코드는 현재 브랜치에 있다. F1 분석기는 없으며 F0의 현재
main/preload/app은 첫 실행 화면과 platform 정보만 제공한다. 트레이·Notification·F5 IPC 연결은 없다.
다른 채팅의 완료를 가정하지 않았다.

## 사용자에게 달라지는 점

공통 앱과 운영 서버의 동작은 아직 바뀌지 않는다. 독립 검사 화면에서는 합성 메일을 보고
근거 문장과 제안 카드를 확인할 수 있다. 제목·한국 시간의 시작/종료·장소·캘린더를 고친 뒤
명시적으로 승인하거나 무시할 수 있다. 본문은 일반 텍스트로 표시해 스크립트를 실행하지 않는다.

테스트 Calendar 결과에는 실제 등록하지 않았다는 문구가 표시된다. 권한·연결 부족이나
외부 실행 실패를 등록 성공으로 표시하지 않는다. 결과가 불명확하면 입력 변경·무시를 막고,
같은 요청을 조회해서 확인한다. 이후 권한 오류가 발생해도 불명확한 요청의 잠금을 풀지 않는다.
프로세스가 실행 중 종료되면 자동 재실행하지 않고 담당자 조정이 필요하다.

제안당 할 일은 하나만 생성하며 승인과 저장을 같은 트랜잭션으로 처리한다. 이미 무시한 제안은
재분석으로 되살리거나 알림 이벤트를 다시 만들지 않는다. 알림의 표시 확인은 조회와 구분한다.

## 검사 결과

실제 Google·메일 발송·OS 알림 없이, 합성 데이터와 새 로컬 PostgreSQL 16 테스트 DB에서 수행했다.

| 검사 | 결과 |
| --- | --- |
| 현재 브랜치 서버 전체 pytest | **131개 통과** — F5 32개 + 기존 99개, 건너뜀 없음 |
| F5 승인·저장 검사 | 재분석/동시 생성, 부정확한 근거·해시·위치 거부, 무시 이력, 영속 재조회, 페이지 경계 통과 |
| 외부 실행 경계 | Gmail/Calendar 읽기 권한으로 쓰기 거부, 동시 승인 1회 실행, timeout 후 동일 ID 조회, 후속 권한 오류의 입력 잠금 유지 통과 |
| 할 일 검사 | 수정 후 승인, 중복·동시 승인 1건 저장, 직접 생성 재시도, 수정 버전·소유권 경계 통과 |
| 화면 Vitest | **14개 통과** — F5 12개 + 기존 2개 |
| F5 Chromium Playwright | **2개 통과** — 수정·겹침·테스트 승인·무시·실패 재시도·안전한 본문·1440/1280 배치 |
| 기존 F0 Chromium Playwright | **2개 통과** — 시작 화면과 작은 창 배치 보존 |
| lint·정적 검사 | 서버 Ruff check/format, 검사 스크립트 Ruff, desktop TypeScript·ESLint 통과 |
| 빌드 | 기존 Electron 앱 빌드와 분리 F5 검사 화면 빌드 통과. Electron/Windows OS 동작 검사는 아님 |
| 적용 전 패치 | 두 파일 git apply --check 통과. 새 임시 복사본에 적용 후 동일 서버 검사 131개 통과 |
| 마이그레이션 보존 | 새 테스트 스키마에서 upgrade 반복·downgrade·재-upgrade, 모델 일치, 합성 기존 메일·계정·수신 커서·암호문 보존 통과 |
| 생성 계약 | 패치 OpenAPI와 앱 생성 결과 일치, 생성 공유 TypeScript의 엄격한 컴파일 통과 |

핵심 명령은 서버 폴더의 `.venv/bin/pytest -q`, `.venv/bin/ruff check .`,
`.venv/bin/ruff format --check .`와 desktop의 `typecheck`, `test`, `lint`, `build`다.
서버 검사는 KLOVER_F5_TEST_DATABASE_URL과 KLOVER_TEST_DATABASE_URL을 새 로컬
`klover_f5_test` DB(이번 환경 포트 32768)로 명시했다. 운영 DB 주소는 사용하지 않았다.
Chromium은 `/usr/bin/chromium`을 지정했다. 패치 검사는
`scripts/f5/verify_patches.py --database-url ...`로 재현했다.

## 확인 방법

저장소 루트에서 다음 명령으로 **별도 합성 화면**을 연다. 공통 앱 라우터는 바꾸지 않는다.

```bash
corepack pnpm --filter desktop exec vite --config f5-preview/vite.config.ts
```

`http://127.0.0.1:5175/f5-preview/`에서 제목·장소 수정, 겹침 확인, 승인 후 테스트 문구,
할 일 무시를 확인할 수 있다. 상단의 등록 실패 검사를 켜면 실패 안내와 재시도를 확인한다.
실제 Gmail 계정·캘린더와 연결되지 않는다.

브라우저 자동 검사는 다음과 같다.

```bash
PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH=/usr/bin/chromium \
  corepack pnpm --filter desktop exec playwright test --config f5.playwright.config.ts
```

검사 스크린샷은 `apps/desktop/artifacts/f5/s04-desktop.png`, `s04-compact.png`에 있다.
새 DB에서 서버·마이그레이션을 재현하는 절차는 [패치 안내](f5-patches/README.md)를 따른다.

## 남은 일과 미확인 외부 연동

- F1의 실제 분석 결과 → F5 입력 변환과 수신 작업자의 재시도 연결.
- 공통 DB·서버 라우터·생성 타입 적용. 현재 실앱의 F5 경로는 아직 등록되지 않음.
- F0의 제한된 main/preload IPC·S04 라우팅·S10 놓친 제안 대화상자·WebSocket·알림·트레이·유형 설정.
- 실제 Calendar HTTP transport와 계정별 권한/캘린더 목록 확인. Calendar 쓰기와 freebusy는 각각 확인 필요.
- F2 답장 초안 실행기, 할 일 리마인더와 스마트 보기 건수, 결재·중요 발신자 제안.
- 본문 변경 후 기존 제안의 교체/철회, 실행 중 프로세스 종료의 운영 조정 절차.
- S04 무시 되돌리기·모든 제안 처리 후 패널 자동 접기 등 후속 화면 동작.
- 30초 Windows 알림·실제 Calendar 등록·실제 겹침·시작 프로그램·Windows 알림 센터 표시: **미실행/미확인**.

OAuth 범위·JSON·암호화 키·연결 계정은 변경하지 않았다. 재동의·실제 Calendar 등록·메일 발송·
OS 알림을 실행하지 않았다. 운영에서 실행하지 않은 것을 approved나 등록 성공으로 표시하지 않았다.
실제 제품 수용 기준은 F5 명세에서 완료로 체크하지 않았다.

## 변경 파일과 목적

공통 파일은 실제 수정하지 않고 patch 파일로만 준비했다. 실제 신규/수정 파일은 아래와 같다.

| 위치 | 파일 | 목적 |
| --- | --- | --- |
| `apps/server/app/api/` | `f5.py` | 기존 인증 의존성을 재사용하는 분리 라우터 |
| `apps/server/app/cli/` | `f5_contract.py` | DB/계정 연결 없이 입력 스키마·OpenAPI 출력 |
| `apps/server/app/db/repositories/` | `f5.py`, `f5_schema.py` | 소유권·저장·상태 전이·잠금·F5 전용 메타데이터 |
| `apps/server/app/pipeline/` | `__init__.py`, `scan.py` | F1 입력에서 제안 후보 연결 |
| `apps/server/app/schemas/` | `f5.py` | 입력·근거·응답·수정·실행 영수증 계약 |
| `apps/server/app/services/` | `f5.py`, `f5_errors.py`, `calendar.py` | 승인 경계·안전한 오류·Calendar 어댑터 |
| `apps/server/tests/f5/` | `__init__.py`, `conftest.py`, `helpers.py`, `test_api.py`, `test_approval_todos.py`, `test_calendar_contract.py`, `test_scan_storage.py` | 분리 DB·합성 앱·서버 검사 |
| `apps/desktop/src/renderer/features/suggestions/` | `types.ts`, `f5-api.d.ts` | 제한 호출 계약·분리 API에서 생성한 기능 전용 타입 |
| 위 기능 폴더 | `evidence-body.tsx`, `suggestion-card.tsx`, `suggestion-reader.tsx` | S04 본문 근거·카드·배치 |
| 위 기능 폴더 | `suggestion-reader.test.tsx`, `testing/synthetic-client.ts`, `preview/main.tsx` | 화면 단위 검사·외부 연결 없는 합성 검사 |
| `apps/desktop/f5-preview/` | `index.html`, `vite.config.ts` | 공통 앱과 분리된 검사 화면 |
| `apps/desktop/` | `f5.playwright.config.ts`, `tests/f5-e2e/suggestions.spec.ts` | F5 브라우저 검사와 스크린샷 |
| `scripts/f5/` | `verify_patches.py` | 임시 복사본에서 패치 적용·기존 데이터 보존 검사 |
| `docs/dev/` | `F5-ai-scan-contract.md`, `F5-handoff.md`, `F5-ai-scan-report.md` | 기능 계약·연결 요청·최종 보고 |
| `docs/dev/f5-contract/` | `openapi.json`, `f1-input.schema.json`, `example-input.json` | 생성한 분리 계약과 합성 입력 예시 |
| `docs/dev/f5-patches/` | `README.md`, `0001-server-and-schema.patch`, `0002-generated-api-types.patch` | 공통 변경의 미적용 초안과 검증 절차 |
| `docs/product/features/` | `F5-ai-scan.md` | 독립 구현 상태·미통합 범위와 관련 문서 링크 |

## 전달 요청과 승인

[F0/F1/공통 서버 전달 문서](F5-handoff.md)에 복사해서 보낼 요청을 정리했다.
F1은 원본 근거를 포함한 입력 어댑터, F0는 제한된 IPC·화면·main 알림·트레이 연결,
공통 서버는 DB/API/공유 타입 패치와 실제 Calendar 권한·transport 경계를 검토해야 한다.

다음 승인 대상은 **feat/F5-ai-scan에서 두 공통 패치의 로컬 적용·재검사·커밋·Push·develop 대상 PR 생성**이다.
다른 기능 브랜치의 통합과 실제 Google/OS 실행은 포함하지 않는다.
develop 병합과 main 병합은 각각 별도 승인 대상이다.
