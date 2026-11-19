# F4 후속 구현·검사 보고

> 2026-11-19 · 검토 기준: `develop@0f68ad18ef924a5659ec52980d8e91cf83df2143`
> 검토 폴더: `/workspace/klover-f4-review` (브랜치를 만들지 않은 별도 작업 폴더)
> 반영 대상: 기존 `feat/F4-weekly-report` · 아직 통합·커밋·Push·PR 생성 없음

## 구현 상태

| 요청 | 구현·검사 결과 | 남은 연결 |
| --- | --- | --- |
| 기존 첫 단위 보존 | `prepare_weekly_report_input`, ReportMail, 저장소 계약과 21개 기존 검사를 그대로 사용. 한국 날짜 양 끝·사용자 분리·수정 분류 우선·공지/뉴스레터 제외·연결 그룹·범위 계산 유지 | 없음 |
| F1·F2 입력 | 기본 메일용 SQL 어댑터, 소유자별 분석·프로필 읽기 포트. PostgreSQL에서 받은/보낸 메일과 한국 날짜 경계 확인. DB pending/failed를 분석 포트가 임의 done으로 덮지 못함 | F1 분석 열·실제 조회 구현, F2 실제 프로필 저장소는 현재 develop에 없음 |
| 생성 결과 검증 | 섹션 이름·순서, 비어 있지 않은 본문, 고유 항목 ID, 항목당 실제 대상 근거 1개 이상 확인. 제외·다른 사용자·기간 밖·없는 ID와 중복 근거 거부 | 실제 모델이 문장 의미를 메일에 맞게 썼는지의 품질 평가는 별도 |
| 생성·저장·재조회·제외 목록 | 새 F4 라우터와 저장소 구현. 동일 선택 저장본 재사용, 소유자가 다르면 404, 읽기·수정 응답 캐시 금지. 실제 기존 인증 검사를 재사용 | 운영 app.main 등록·운영 DB DDL은 미적용 |
| S08 기능 화면 | 기간·양식·대상·본문·근거 원문·범위·제외 목록·빈 상태·준비 상태·오류 표시 | F0 공통 라우트·사이드바·IPC 미연결 |
| 편집·복사·재생성 | 편집 저장, 근거를 선택한 새 항목 추가, 편집본 복사, 수정 시 재생성 확인, 실패 시 편집본 보존. 저장 버전 충돌과 동시 수정도 보호 | 실제 Electron 진입 후 확인 필요 |
| 위험·빈 상태 | 빈/모두 제외, pending/failed, AI 없음·실패·시간 초과·잘못된 응답, 프로필 없음, 사용자 격리, 늦게 도착한 이전 계정 응답, 재조회 검사 | 실제 F1/F2/AI 환경에서 통합 검사 필요 |

단계별 결과는 검토용 테스트 대역으로 만들며 `test_double` 표시가 DB·API·화면에 남는다.
실제 AI 제공자 구현은 만들지 않았고 실제 Gmail 본문을 외부 AI에 보내지 않았다.
새 F4 라우터는 테스트·검토 앱에만 등록했다. 실제 앱의 API·OpenAPI는 그대로다.

보고서는 생성 시점의 대상 메일·프로필 스냅샷과 함께 저장한다. 편집의 근거는 그 보고서의
대상 메일 집합에서만 선택한다. 재생성은 현재 대상 메일을 다시 조회한다. 생성·검증·저장이
실패하거나 다른 저장이 먼저 끝나면 기존 저장본을 덮지 않는다.

## 변경 파일과 목적

기존 파일 변경은 F4 진행 기록인 `docs/dev/F4-weekly-report-plan.md`의 후속 상태 추가뿐이다.
그 밖에는 아래 기능 파일을 새로 작성했다.

| 파일 | 목적 |
| --- | --- |
| `apps/server/app/schemas/weekly_report.py` | 프로필·요청·생성 결과·편집·저장 문서 계약 |
| `apps/server/app/services/report_ports.py` | F1 분석과 F2 프로필 연결 포트 |
| `apps/server/app/services/weekly_report.py` | 기본값·준비 상태·생성 검증·저장본 재사용·편집·재생성 |
| `apps/server/app/db/repositories/report_source.py` | 기존 DB 기본 메일 조회와 분석 입력 결합 |
| `apps/server/app/db/repositories/weekly_report.py` | 기능 테이블 계약, 사용자별 조회와 버전 비교 저장 |
| `apps/server/app/ai/__init__.py`, `ai/weekly_report.py`, `ai/prompts/weekly_report.md` | F4 AI 연결 경계와 프롬프트. 실제 제공자는 없음 |
| `apps/server/app/api/weekly_report.py` | 기존 인증을 재사용하는 기능 라우터. 운영 등록은 없음 |
| `apps/server/app/testing/__init__.py`, `testing/weekly_report.py` | 명시적으로 선택하는 가짜 프로필·생성 대역 |
| `apps/server/app/cli/review_weekly_report.py` | 가짜 메일·별도 SQLite·임시 검토 토큰 전용 서버. 표식 없는 기존 파일·DB 재사용 거부 |
| `apps/server/tests/test_weekly_report.py`, `test_weekly_report_ports.py` | 서비스·API·저장·포트·실패·동시성·PostgreSQL 검사 |
| `apps/desktop/src/renderer/features/weekly-report/types.ts`, `client.ts` | 기능 계약·제한된 전송 포트·복사 형식·근거 검사 |
| `apps/desktop/src/renderer/features/weekly-report/weekly-report-page.tsx` | F0 진입부에 의존하지 않는 S08 컴포넌트 |
| `apps/desktop/src/renderer/features/weekly-report/weekly-report-page.test.tsx` | 편집·복사·실패 보존·근거·계정 변경 검사 |
| `apps/desktop/src/renderer/features/weekly-report/preview/index.html`, `preview/main.tsx` | 독립 검토 화면 진입 |
| `apps/desktop/vite.weekly-report.config.ts`, `scripts/review-weekly-report.mjs` | 임시 가짜 계정 토큰을 Node에서만 전달하는 검토 실행기 |
| `apps/desktop/playwright.weekly-report.config.ts`, `tests/e2e-f4/weekly-report.spec.ts` | 기존 F0 설정과 분리된 S08 브라우저 검사 |
| `fixtures/reports/F4-weekly-report.json` | 서버 테스트 대역에서 만든 합성 화면 검사 데이터 |
| `docs/dev/F4-review-contract.md`, 이 보고서 | 내부 연결·저장 경계, 실행·검증·승인 기록 |
| `docs/dev/F4-proposals/README.md`, `01-register-routes.patch`, `02-report-storage.patch`, `03-generated-api-types.patch` | 공통 등록·DDL·생성 타입의 미적용 제안 |

F0 진입부·main/preload·공통 컴포넌트·스타일·기존 API·DB 모델·마이그레이션 이력·
공유 타입·package 설정·잠금 파일은 수정하지 않았다. 계정·Google 키·메일·수신 코드도 보존했다.

## 실행한 검사

| 검사 | 결과 |
| --- | --- |
| `apps/server`: `pytest -q` | **144개 통과**. 기존 공통 서버·인증·Gmail 대역·DB 검사와 F4 포함 |
| 실제 PostgreSQL 16 | 본 작업이 만든 임시 컨테이너의 임시 스키마만 사용. F4 메일 경계·소유자·분석 포트·보고 JSONB 저장 재조회 확인 |
| `ruff check .`, `ruff format --check .` | 통과 |
| `pnpm --filter desktop test` | **19개 통과** (기존 F0 포함) |
| `pnpm --filter desktop typecheck`, `lint` | 통과 |
| F4 전용 Playwright | **4개 통과**. 실제 로컬 API·검토 DB를 통해 원문·제외 목록·편집·복사·저장·새로고침·실패 보존·근거 추가·1280 화면 검사 |
| 기존 `pnpm --filter desktop test:e2e` | **2개 통과**, F0 첫 화면 회귀 확인 |
| `pnpm --filter desktop build` | 기존 앱 빌드 통과. F4 진입이 빌드에 연결됐다는 의미는 아님 |
| `uv sync --locked`, `pnpm install --frozen-lockfile` | 성공, 공통 잠금 파일 변경 없음 |
| 공통 패치 3개 `git apply --check` | 모두 통과, 실제 적용하지 않음 |
| 제안 OpenAPI → TypeScript 생성·컴파일 | 임시 파일에서 성공, 공통 생성 파일 보존 |
| 기존 F4 작업 폴더와 보호 파일 diff | 기존 폴더 clean·HEAD `7a67137` 유지. 첫 단위·공통 보호 파일 차이 없음 |

브라우저의 AI 실패는 응답을 실패로 바꾸어 검사했다. 서버에서는 대역 예외·시간 초과·
잘못된 근거를 별도로 검사했다. 테스트 실행 시간은 실제 모델의 30초 생성 성능 측정이 아니다.

## 사용자가 확인할 방법

별도 검토 폴더에서 실행한다. 기존 F4 작업 폴더에서 브랜치를 전환하지 않는다.

```bash
cd /workspace/klover-f4-review/apps/server
uv sync --locked
cd /workspace/klover-f4-review
corepack pnpm install --frozen-lockfile
node apps/desktop/scripts/review-weekly-report.mjs
```

브라우저 주소: `http://127.0.0.1:5174/features/weekly-report/preview/`.
처음에 가짜 메일 전체 12건 = 업무 9건 + 제외 3건(6개 업무)이 보인다. 배지를 눌러 근거를
읽고 본문을 편집해 복사·저장·새로고침할 수 있다. 별도 검토 DB만 쓰고 운영 DB·실제
메일·Google 키를 읽지 않는다. 위 실행기는 매 실행 시 새로운 검토 폴더를 만든다.
저장 유지·재조회는 같은 실행 중 새로고침과 저장소 재생성 검사로 확인했다.

Cloud에서 기본 캐시 경로를 쓸 수 없으면 명령 앞에
`UV_CACHE_DIR=/tmp/klover-uv-cache`, `COREPACK_HOME=/tmp/klover-corepack`을 각각 지정한다.
화면 기록은 로컬 `artifacts/F4-weekly-report.png`, `artifacts/F4-preserved-edit.png`에 있다.

브라우저 검사를 다시 실행하려면 검토 서버를 종료한 뒤:

```bash
cd /workspace/klover-f4-review
PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH=/usr/bin/chromium \
  corepack pnpm --filter desktop exec playwright test --config playwright.weekly-report.config.ts
```

## 미실행·미통합과 이유

- **운영 DB 등록·마이그레이션:** 사용자 요청에 따라 미적용 패치만 준비했다.
  실제 사용자 DB에 명령을 실행하지 않았다. 임시 스키마 검사와 운영 등록은 구분한다.
- **공통 서버 등록·공유 타입 적용:** 승인 전 미적용. 검토 앱에서만 경로를 등록했다.
- **F1 실제 분석 연결:** 현재 메일 DB에는 상태 열만 있고 분류·요약·프로젝트 결과와 공통 AI
  인터페이스가 없다. 누락 결과를 임의 작성하지 않고 준비 실패로 처리한다.
- **F2 실제 프로필 연결:** 실제 프로필 저장소·API가 없다. 테스트 대역으로만 기본값을 검증했다.
- **실제 AI 생성·사실성·30초 성능:** 실제 제공자가 없고 실제 Gmail 전송 실험도 금지되어 있어
  실행하지 않았다. ID 검증이 문장 의미까지 보증한다고 표시하지 않는다.
- **F0 화면 진입·Electron IPC·Windows/macOS 앱 통합:** 공통 진입부를 수정하지 않는 조건이므로
  미통합이다. 기존 F0 화면 검사·빌드와 S08 독립 브라우저 검사를 각각 실행했다.
- Word·메일 발송·예약 생성·메일 외 데이터는 이번 요청에서 제외했다. 원 명세의 공휴일 표시나
  제외 목록에서의 재포함 동작도 이번 검토에 넣지 않았다. F4 전체 수용 기준 완료로 표시하지 않는다.

## F0·F1·F2와 공통 서버에 전달할 요청

이 내용은 전달용 초안이다. 다른 채팅이나 팀 채널에 자동 전송하지 않았다.

| 대상 | 전달할 요청 |
| --- | --- |
| F0 | `/report/weekly` 진입에 `WeeklyReportPage`를 연결하고 기존 로컬 인증을 가진 Electron main에서만 F4 API를 호출해 주세요. Renderer에는 토큰·임의 URL 권한을 주지 말고 기능 전송 포트를 제한해 주세요. 계정 변경 시 client를 교체하거나 화면을 새로 마운트해 주세요. 기존 메일함·온보딩·계정 진입부는 보존해 주세요. |
| F1 | `ReportAnalysisPort.read_for_report(user_id, mail_ids)`에 소유자별 status/category/user_label/summary/entities를 연결해 주세요. DB 상태와 분석 결과가 함께 done일 때만 업무 입력으로 쓸 수 있습니다. 기존 메일 ID·시간대·스레드 계약을 유지하고 공통 AI 인터페이스의 실제 파일·호출 형식을 공유해 주세요. |
| F2 | `ReportProfilePort.get_report_profile(user_id)`에 name/title/org/report_sections/report_recipient/report_style을 연결해 주세요. 섹션 이름은 중복 없이 순서를 유지하고, 없으면 None을 반환해 주세요. 승인된 실제 계약이 생기면 F4 임시 포트를 그 계약으로 맞추겠습니다. |
| 공통 서버·DB | `F4-proposals`의 등록·테이블·생성 타입 패치를 검토해 주세요. 승인 시점의 마이그레이션 head를 확인하고 실제 F1/F2·AI 포트를 주입하기 전에는 503 상태를 유지해 주세요. 기존 `/health`·메일 인증·Gmail 연결·수신·키 파일은 변경하지 말아 주세요. |

## 승인 후 반영할 범위

이번 보고의 묶음 승인 대상은 **최신 상태 재확인 → 기존 F4 브랜치에 기존 원격 F4와
검사 기준 develop을 보존하는 로컬 통합 → 검토한 F4 기능 코드·문서 반영 → 커밋·Push →
develop 대상 새 초안 PR 생성**이다. 공통 등록·DB·생성 타입 패치의 **실제 적용은 포함하지 않는다**.
패치 파일 자체는 검토 자료로 포함한다. 변경 범위는 이 보고서와 변경 파일 목록에 한정한다.

현재 원격 F4 `ba541e8`은 검토 기준 develop의 조상이다. 승인 시 최신 원격 상태가 달라졌으면
덮어쓰거나 강제 Push하지 않고 차이·필요한 재검사를 보고한다. `develop` 병합과 `main` 병합은
이 묶음 승인과 분리하여 각각 별도 승인받는다.
