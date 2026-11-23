# 로컬 AI·과거 메일 통합 검증 및 승인 검토

## 작업 기준과 공개 상태

- 작업 브랜치: `integrate/local-ai-mail-history`, 기준 `origin/develop 5e2b7a7`(PR #38 병합).
- 원격 전체 브랜치를 명시해 fetch 후 다시 확인했다. main은 `9575f47`, develop은 `5e2b7a7`이다.
- AGENTS.md·progress·F0~F5 status·통합 후속 요청·기간 선택 가져오기 명세와 실제 코드/PR 이력을 대조했다.
- 기존 작업 브랜치/폴더는 보존했다. 이 문서는 최초 검토 시점의 87개 파일과 검사 결과를 기록한다. 사용자가 이후 커밋·Push·PR 생성과 검사 통과 시 develop 병합을 승인했다. 실제 제출/병합은 아래 후속 기록과 PR 상태를 따른다.
- 사용자 실제 DB·Gmail·Ollama·유료 Claude에는 접근하지 않았다. 외부 서비스 성공을 자동 검사로 대신 주장하지 않는다.

## 구현 결과와 수용 기준

| 범위 | 구현·검사 내용 | 남은 실환경 확인 |
| --- | --- | --- |
| 프로필·Electron | 서버에서 자동 미리보기 로컬 고정. 수동 Claude 선택 보존. 최신 preload 통로·mail.sync·새로고침 합성 fixture로 smoke 기대값 수정. 인증·토큰 비공개·화면 격리 검사 유지 | 실제 Electron 실행은 아래 환경 실패로 미검증 |
| 로컬 전용 | 새 설정은 로컬 전용/로컬 기본. UI 선택·서버 생성·연결 검사 차단. 저장된 Claude 기본값/환경 변수로 생성 우회 금지. 기존 키/설정 보존, Gmail 수신 유지 | 맥북 앱의 정책 저장·재시작 확인 |
| 로컬 재시도 | F2 생성/수정·F3 해석/답변·F4 생성에서 Claude 제공자 오류/시간 초과 후 로컬 한 번. 검색은 남은 단계도 로컬 유지. 실제 AI·고정 사유 표시 및 초안/보고서에 저장 | 실제 제공자 오류/속도/결과 품질 |
| 재시도 제한 | 미동의·취소·안전 거절·형식/근거 검증 오류는 전환하지 않음. 로컬→Claude 전환 없음. 연결 검사는 Claude 자체 성공만 인정. 기존 전체 제한·편집본 보존·소유 계정/근거 검증 유지 | 네이티브 앱에서 요청 취소·오래 걸리는 모델 확인 |
| 명시적 가져오기 | 한국 날짜 양끝 포함, 현재 INBOX만, 최대 366일/작업당 10,000건/25건 페이지. 저장된 진행·중단·재개·실패 후 재시도·중복 방지·오래된 작업 쓰기 차단 | 실제 Gmail 페이지 이동·권한·토큰 갱신 |
| 기존 데이터 | 0008_history의 부모는 0007_f1. 표시 열과 작업 표 추가. 계정·암호문·시작 시점·일반 수신 커서·기존 메일/편집본 보존. 자동 과거 수집 없음 | 사용자 백업·0008 적용은 사용자 PC에서 별도 진행 |
| 기능 연결 | 가져온 과거 메일의 저장→조회/본문→로컬 분석/임베딩·F5→검색/근거 답변→보고 입력 경계 정비. 일반 수신과 가져오기는 다른 작업이며 Gmail 네트워크 대기 중 가져오기 DB 잠금을 보유하지 않음 | 실제 Gmail→Ollama→앱/검색/보고 전체 흐름·대량 처리 성능 |

새 설정이 없는 사용자는 로컬 전용으로 시작한다. 이전 암호화 AI 설정에 mode가 없으면 hybrid로 읽어 기존 선택을 보존한다.
로컬 전용 모드를 켜도 키·기능별 저장 기본값을 지우지 않는다. 요청은 로컬로 제한되며 명시적 Claude 요청은 서버에서 거절한다.
전송 동의·자료 종류·요금 안내는 유지했다. 키는 기존 앱 입력/서버 암호화 파일을 그대로 사용한다.

## 자동 검사

합성 메일·제공자 대역·분리 PostgreSQL 컨테이너(`klover-history-tests`, 포트 55449)의 일회용 스키마만 사용했다.
테스트 DB는 `klover_history_test`, `klover_f5_test`이며 테스트 URL 변수만 지정했다. 사용자 운영 DB는 사용하지 않았다.

| 검사 | 실행 명령 | 결과 |
| --- | --- | --- |
| 서버 전체 | `PYTHONPATH=apps/server apps/server/.venv/bin/python -m pytest -q apps/server/tests` | **590 통과, skip 0** (103.82초) |
| 마지막 경계 보완 | `pytest -q apps/server/tests/f1/test_storage.py apps/server/tests/test_ai_selection.py apps/server/tests/test_history_import.py` | **39 통과**. 과거 메일 분석→보고 입력, SQL→검색 결과/근거 답변, 전환/정책/가져오기 검사 |
| 서버 정적 검사 | `ruff check apps/server`, `ruff format --check apps/server` | 통과, 183개 파일 형식 일치 |
| 앱 단위 | `pnpm --filter desktop test` | **185 통과** |
| 앱 정적 검사 | `pnpm --filter desktop lint`, `pnpm --filter desktop typecheck` | 통과 |
| 앱 빌드 | `pnpm --filter desktop build` | 통과 |
| 합성 Chromium | `pnpm --filter desktop exec playwright test tests/e2e/ai-selection.spec.ts --workers=1` | **4 통과**: AI 설정·답장·첫 주 보고·명시적 가져오기. 테스트 IPC 대역, 실제 Electron/AI/Gmail 아님 |
| API 계약 생성 | `pnpm gen:api-types` | 성공. OpenAPI와 TS 타입을 생성 명령으로 갱신 |
| Electron 검사 문법 | 두 smoke 스크립트 `node --check` | 통과 |
| 네이티브 Electron | `pnpm --filter desktop test:electron` | **환경 실패**: Electron 실행 파일 다운로드 `fetch failed`, 앱/검사 본문까지 실행되지 않음. mail-read 네이티브도 미실행. sandbox를 끄거나 보안 검사를 삭제하지 않음 |
| 문서/변경 범위 | 로컬 문서 참조·파일 범위·`git diff --check` | Markdown 25개·로컬 참조 253개, 누락 0·공백 오류 없음. 스테이징/새 커밋/비밀 파일 변경 없음 |

원격 CI는 새 커밋/PR 생성 전이므로 이번 변경에 대한 결과가 없다. 기존 PR #38의 CI 결과와 구분한다.

## 제한·남은 일

- 실제 Gmail·Ollama·유료 Claude·사용자 DB·macOS/Windows 전체 실행은 미검증이다.
- 가져오기 사전 정확한 대상 건수는 제공하지 않는다. 실제 처리한 건수와 중복/제외·새 저장 건수를 표시한다.
- 작업 상한이면 부분 저장을 보존하고 실패로 표시한다. 기간을 줄여 새 작업을 실행해야 한다.
- 중단은 진행 중 네트워크 요청 이후 반영된다. 이미 저장한 메일의 로컬 분석은 계속될 수 있다.
- Gmail 페이지 토큰이 만료되면 재개 시 기간을 다시 조회하며 중복 저장하지 않는다. 서버 재시작 후 작업은 중단 상태로 복구한다.
- 모델의 형식·근거 오류는 기존 보정/검증을 따르며, Claude→로컬 전환은 제공자 오류에 한정한다.
- 클라우드 이전·사내망·발송·Calendar·설치 파일은 이번 변경에서 추가하지 않았다.

## 승인 후 순서

1. 이번 변경의 로컬 통합·커밋·Push·develop 대상 PR 생성을 묶어서 승인받는다.
2. PR 검사/변경을 확인한 뒤 develop 병합 승인을 별도로 받는다. 기존 브랜치는 보존한다.
3. [맥북 업데이트와 실제 확인](local-ai-history-run.md)을 따른다. 백업 후 0008 적용·서버/앱 재시작·로컬 정책·기간 가져오기·검색/보고를 확인한다.
4. main 반영은 별도 승인이다. 현재 main에는 앱 실행 코드가 없다.

## 변경 파일과 목적

총 87개 파일(수정/신규). 기존 .env·키·DB 파일·브랜치·패치 원문·잠금 파일은 변경하지 않았다.

| 파일 | 목적 |
| --- | --- |
| [README.md](../../README.md) | 최종 구현·제약·설치/업데이트 절차와 기획 모순 정리 |
| [apps/desktop/scripts/smoke-electron.mjs](../../apps/desktop/scripts/smoke-electron.mjs) | 최신 Electron IPC·새로고침 기대값과 합성 서버 보완 |
| [apps/desktop/scripts/smoke-mail-read.mjs](../../apps/desktop/scripts/smoke-mail-read.mjs) | 최신 Electron IPC·새로고침 기대값과 합성 서버 보완 |
| [apps/desktop/src/main/ai-ipc.ts](../../apps/desktop/src/main/ai-ipc.ts) | 로컬 모드 저장/선택 차단·실제 AI/전환 사유 표시 |
| [apps/desktop/src/main/history-ipc.test.ts](../../apps/desktop/src/main/history-ipc.test.ts) | 변경 동작·격리·인증·데이터 보존의 합성 회귀 검사 |
| [apps/desktop/src/main/history-ipc.ts](../../apps/desktop/src/main/history-ipc.ts) | 과거 메일 화면·검증된 제한 IPC·응답 allowlist |
| [apps/desktop/src/main/index.ts](../../apps/desktop/src/main/index.ts) | 기존 앱 보안 경계에 가져오기 IPC·화면 경로 연결 |
| [apps/desktop/src/preload/index.ts](../../apps/desktop/src/preload/index.ts) | 기존 앱 보안 경계에 가져오기 IPC·화면 경로 연결 |
| [apps/desktop/src/renderer/app.tsx](../../apps/desktop/src/renderer/app.tsx) | 기존 앱 보안 경계에 가져오기 IPC·화면 경로 연결 |
| [apps/desktop/src/renderer/env.d.ts](../../apps/desktop/src/renderer/env.d.ts) | 기존 앱 보안 경계에 가져오기 IPC·화면 경로 연결 |
| [apps/desktop/src/renderer/features/ai-settings/ai-choice.tsx](../../apps/desktop/src/renderer/features/ai-settings/ai-choice.tsx) | 로컬 모드 저장/선택 차단·실제 AI/전환 사유 표시 |
| [apps/desktop/src/renderer/features/ai-settings/ai-execution.tsx](../../apps/desktop/src/renderer/features/ai-settings/ai-execution.tsx) | 로컬 모드 저장/선택 차단·실제 AI/전환 사유 표시 |
| [apps/desktop/src/renderer/features/ai-settings/ai-settings-page.tsx](../../apps/desktop/src/renderer/features/ai-settings/ai-settings-page.tsx) | 로컬 모드 저장/선택 차단·실제 AI/전환 사유 표시 |
| [apps/desktop/src/renderer/features/ai-settings/ai-settings.test.tsx](../../apps/desktop/src/renderer/features/ai-settings/ai-settings.test.tsx) | 변경 동작·격리·인증·데이터 보존의 합성 회귀 검사 |
| [apps/desktop/src/renderer/features/mailbox/history-page.test.tsx](../../apps/desktop/src/renderer/features/mailbox/history-page.test.tsx) | 변경 동작·격리·인증·데이터 보존의 합성 회귀 검사 |
| [apps/desktop/src/renderer/features/mailbox/history-page.tsx](../../apps/desktop/src/renderer/features/mailbox/history-page.tsx) | 과거 메일 화면·검증된 제한 IPC·응답 allowlist |
| [apps/desktop/src/renderer/features/mailbox/mailbox-page.tsx](../../apps/desktop/src/renderer/features/mailbox/mailbox-page.tsx) | 메일함 가져오기 이동·기능별 결과 AI 표시/타입 연결 |
| [apps/desktop/src/renderer/features/profile-draft/reply-draft-page.tsx](../../apps/desktop/src/renderer/features/profile-draft/reply-draft-page.tsx) | 메일함 가져오기 이동·기능별 결과 AI 표시/타입 연결 |
| [apps/desktop/src/renderer/features/search/contracts.ts](../../apps/desktop/src/renderer/features/search/contracts.ts) | 메일함 가져오기 이동·기능별 결과 AI 표시/타입 연결 |
| [apps/desktop/src/renderer/features/search/search-page.tsx](../../apps/desktop/src/renderer/features/search/search-page.tsx) | 메일함 가져오기 이동·기능별 결과 AI 표시/타입 연결 |
| [apps/desktop/src/renderer/features/weekly-report/types.ts](../../apps/desktop/src/renderer/features/weekly-report/types.ts) | 메일함 가져오기 이동·기능별 결과 AI 표시/타입 연결 |
| [apps/desktop/src/renderer/features/weekly-report/weekly-report-page.tsx](../../apps/desktop/src/renderer/features/weekly-report/weekly-report-page.tsx) | 메일함 가져오기 이동·기능별 결과 AI 표시/타입 연결 |
| [apps/desktop/src/shared/ai-bridge.ts](../../apps/desktop/src/shared/ai-bridge.ts) | 로컬 모드 저장/선택 차단·실제 AI/전환 사유 표시 |
| [apps/desktop/src/shared/history-bridge.ts](../../apps/desktop/src/shared/history-bridge.ts) | 과거 메일 화면·검증된 제한 IPC·응답 allowlist |
| [apps/desktop/tests/e2e/ai-selection.spec.ts](../../apps/desktop/tests/e2e/ai-selection.spec.ts) | 변경 동작·격리·인증·데이터 보존의 합성 회귀 검사 |
| [apps/desktop/tests/mail-api-fixture.py](../../apps/desktop/tests/mail-api-fixture.py) | 최신 Electron IPC·새로고침 기대값과 합성 서버 보완 |
| [apps/server/app/ai/f2_shared_adapter.py](../../apps/server/app/ai/f2_shared_adapter.py) | 로컬 정책·제공자 선택·로컬 1회 전환·안전한 오류 처리 |
| [apps/server/app/ai/runtime.py](../../apps/server/app/ai/runtime.py) | 로컬 정책·제공자 선택·로컬 1회 전환·안전한 오류 처리 |
| [apps/server/app/ai/selection.py](../../apps/server/app/ai/selection.py) | 로컬 정책·제공자 선택·로컬 1회 전환·안전한 오류 처리 |
| [apps/server/app/api/ai_scope.py](../../apps/server/app/api/ai_scope.py) | 요청별 AI 범위·자동 미리보기 로컬 강제·결과 처리 AI 응답 |
| [apps/server/app/api/ai_settings.py](../../apps/server/app/api/ai_settings.py) | 요청별 AI 범위·자동 미리보기 로컬 강제·결과 처리 AI 응답 |
| [apps/server/app/api/history_import.py](../../apps/server/app/api/history_import.py) | 인증된 기간 작업 API·저장 체크포인트·백그라운드 Gmail 페이지 처리 |
| [apps/server/app/api/profile_draft.py](../../apps/server/app/api/profile_draft.py) | 요청별 AI 범위·자동 미리보기 로컬 강제·결과 처리 AI 응답 |
| [apps/server/app/api/search.py](../../apps/server/app/api/search.py) | 요청별 AI 범위·자동 미리보기 로컬 강제·결과 처리 AI 응답 |
| [apps/server/app/api/weekly_report.py](../../apps/server/app/api/weekly_report.py) | 요청별 AI 범위·자동 미리보기 로컬 강제·결과 처리 AI 응답 |
| [apps/server/app/cli/run_mail_api.py](../../apps/server/app/cli/run_mail_api.py) | 실행 서버에 가져오기 저장소·작업자·API 등록 |
| [apps/server/app/db/models.py](../../apps/server/app/db/models.py) | 기존 메일 표시 열·가져오기 작업 소유자 모델 추가 |
| [apps/server/app/db/repositories/f5.py](../../apps/server/app/db/repositories/f5.py) | 명시적 과거 메일의 소유자/날짜 경계를 조회·분석·검색·보고·제안에 연결 |
| [apps/server/app/db/repositories/history_import.py](../../apps/server/app/db/repositories/history_import.py) | 인증된 기간 작업 API·저장 체크포인트·백그라운드 Gmail 페이지 처리 |
| [apps/server/app/db/repositories/mail.py](../../apps/server/app/db/repositories/mail.py) | 명시적 과거 메일의 소유자/날짜 경계를 조회·분석·검색·보고·제안에 연결 |
| [apps/server/app/db/repositories/mail_analysis.py](../../apps/server/app/db/repositories/mail_analysis.py) | 명시적 과거 메일의 소유자/날짜 경계를 조회·분석·검색·보고·제안에 연결 |
| [apps/server/app/db/repositories/mail_query.py](../../apps/server/app/db/repositories/mail_query.py) | 명시적 과거 메일의 소유자/날짜 경계를 조회·분석·검색·보고·제안에 연결 |
| [apps/server/app/db/repositories/report_source.py](../../apps/server/app/db/repositories/report_source.py) | 명시적 과거 메일의 소유자/날짜 경계를 조회·분석·검색·보고·제안에 연결 |
| [apps/server/app/db/repositories/search.py](../../apps/server/app/db/repositories/search.py) | 명시적 과거 메일의 소유자/날짜 경계를 조회·분석·검색·보고·제안에 연결 |
| [apps/server/app/main.py](../../apps/server/app/main.py) | 실행 서버에 가져오기 저장소·작업자·API 등록 |
| [apps/server/app/schemas/profile_draft.py](../../apps/server/app/schemas/profile_draft.py) | 결과 AI 정보와 명시적 과거 메일 내부 계약 |
| [apps/server/app/schemas/search.py](../../apps/server/app/schemas/search.py) | 결과 AI 정보와 명시적 과거 메일 내부 계약 |
| [apps/server/app/schemas/weekly_report.py](../../apps/server/app/schemas/weekly_report.py) | 결과 AI 정보와 명시적 과거 메일 내부 계약 |
| [apps/server/app/services/history_import.py](../../apps/server/app/services/history_import.py) | 인증된 기간 작업 API·저장 체크포인트·백그라운드 Gmail 페이지 처리 |
| [apps/server/app/services/profile_draft.py](../../apps/server/app/services/profile_draft.py) | 검색 후처리의 과거 메일 허용·초안/보고서 AI 정보 저장 |
| [apps/server/app/services/search.py](../../apps/server/app/services/search.py) | 검색 후처리의 과거 메일 허용·초안/보고서 AI 정보 저장 |
| [apps/server/app/services/weekly_report.py](../../apps/server/app/services/weekly_report.py) | 검색 후처리의 과거 메일 허용·초안/보고서 AI 정보 저장 |
| [apps/server/migrations/versions/0008_history_import.py](../../apps/server/migrations/versions/0008_history_import.py) | 0008 과거 메일 표시/가져오기 작업 추가, 0007 부모 유지 |
| [apps/server/tests/f1/test_pending_migration.py](../../apps/server/tests/f1/test_pending_migration.py) | 변경 동작·격리·인증·데이터 보존의 합성 회귀 검사 |
| [apps/server/tests/f1/test_storage.py](../../apps/server/tests/f1/test_storage.py) | 변경 동작·격리·인증·데이터 보존의 합성 회귀 검사 |
| [apps/server/tests/test_ai_selection.py](../../apps/server/tests/test_ai_selection.py) | 변경 동작·격리·인증·데이터 보존의 합성 회귀 검사 |
| [apps/server/tests/test_google_storage.py](../../apps/server/tests/test_google_storage.py) | 변경 동작·격리·인증·데이터 보존의 합성 회귀 검사 |
| [apps/server/tests/test_history_import.py](../../apps/server/tests/test_history_import.py) | 변경 동작·격리·인증·데이터 보존의 합성 회귀 검사 |
| [apps/server/tests/test_http_server.py](../../apps/server/tests/test_http_server.py) | 변경 동작·격리·인증·데이터 보존의 합성 회귀 검사 |
| [apps/server/tests/test_profile_draft.py](../../apps/server/tests/test_profile_draft.py) | 변경 동작·격리·인증·데이터 보존의 합성 회귀 검사 |
| [apps/server/tests/test_search_api.py](../../apps/server/tests/test_search_api.py) | 변경 동작·격리·인증·데이터 보존의 합성 회귀 검사 |
| [docs/architecture/api.md](../../docs/architecture/api.md) | 최종 구현·제약·설치/업데이트 절차와 기획 모순 정리 |
| [docs/architecture/data-model.md](../../docs/architecture/data-model.md) | 최종 구현·제약·설치/업데이트 절차와 기획 모순 정리 |
| [docs/architecture/system.md](../../docs/architecture/system.md) | 최종 구현·제약·설치/업데이트 절차와 기획 모순 정리 |
| [docs/dev/F0-mailbox-status.md](../../docs/dev/F0-mailbox-status.md) | 현재 작업과 과거 병합 기록·검증/미검증·승인 대기 구분 |
| [docs/dev/F1-analysis-status.md](../../docs/dev/F1-analysis-status.md) | 현재 작업과 과거 병합 기록·검증/미검증·승인 대기 구분 |
| [docs/dev/F2-profile-draft-status.md](../../docs/dev/F2-profile-draft-status.md) | 현재 작업과 과거 병합 기록·검증/미검증·승인 대기 구분 |
| [docs/dev/F3-search-status.md](../../docs/dev/F3-search-status.md) | 현재 작업과 과거 병합 기록·검증/미검증·승인 대기 구분 |
| [docs/dev/F4-weekly-report-status.md](../../docs/dev/F4-weekly-report-status.md) | 현재 작업과 과거 병합 기록·검증/미검증·승인 대기 구분 |
| [docs/dev/F5-ai-scan-status.md](../../docs/dev/F5-ai-scan-status.md) | 현재 작업과 과거 병합 기록·검증/미검증·승인 대기 구분 |
| [docs/dev/integration-followups.md](../../docs/dev/integration-followups.md) | 최종 구현·제약·설치/업데이트 절차와 기획 모순 정리 |
| [docs/dev/local-ai-history-run.md](../../docs/dev/local-ai-history-run.md) | 과거 메일 화면·검증된 제한 IPC·응답 allowlist |
| [docs/dev/progress.md](../../docs/dev/progress.md) | 현재 작업과 과거 병합 기록·검증/미검증·승인 대기 구분 |
| [docs/dev/setup.md](../../docs/dev/setup.md) | 최종 구현·제약·설치/업데이트 절차와 기획 모순 정리 |
| [docs/dev/verification-local-ai-history.md](../../docs/dev/verification-local-ai-history.md) | 이번 검증·제약·승인 경계·전체 파일 목록 기록 |
| [docs/product/decisions.md](../../docs/product/decisions.md) | 최종 구현·제약·설치/업데이트 절차와 기획 모순 정리 |
| [docs/product/features/F0-onboarding-mailbox.md](../../docs/product/features/F0-onboarding-mailbox.md) | 최종 구현·제약·설치/업데이트 절차와 기획 모순 정리 |
| [docs/product/features/F1-mail-analysis.md](../../docs/product/features/F1-mail-analysis.md) | 최종 구현·제약·설치/업데이트 절차와 기획 모순 정리 |
| [docs/product/features/F2-profile-draft.md](../../docs/product/features/F2-profile-draft.md) | 최종 구현·제약·설치/업데이트 절차와 기획 모순 정리 |
| [docs/product/features/F3-search.md](../../docs/product/features/F3-search.md) | 최종 구현·제약·설치/업데이트 절차와 기획 모순 정리 |
| [docs/product/features/F4-weekly-report.md](../../docs/product/features/F4-weekly-report.md) | 최종 구현·제약·설치/업데이트 절차와 기획 모순 정리 |
| [docs/product/features/F5-ai-scan.md](../../docs/product/features/F5-ai-scan.md) | 최종 구현·제약·설치/업데이트 절차와 기획 모순 정리 |
| [docs/product/features/planned-mail-history-import.md](../../docs/product/features/planned-mail-history-import.md) | 과거 메일 화면·검증된 제한 IPC·응답 allowlist |
| [docs/product/open-questions.md](../../docs/product/open-questions.md) | 최종 구현·제약·설치/업데이트 절차와 기획 모순 정리 |
| [docs/product/overview.md](../../docs/product/overview.md) | 최종 구현·제약·설치/업데이트 절차와 기획 모순 정리 |
| [packages/api-types/openapi.json](../../packages/api-types/openapi.json) | 실제 서버 OpenAPI 및 공유 TS 타입 자동 생성 |
| [packages/api-types/src/schema.d.ts](../../packages/api-types/src/schema.d.ts) | 실제 서버 OpenAPI 및 공유 TS 타입 자동 생성 |

## 사용자 승인 후 제출 기록

사용자가 이 통합 채팅에서 87개 파일의 커밋·Push·PR 생성 및 문제없을 때 develop 병합을 승인했다.
검사 결과와 미검증 범위는 위와 같으며 main·기존 브랜치 보존 조건을 유지한다.

코드 커밋 `0a357b3e8addc303e1d9cc5729f2e4460c4c0025`을 Push하고 [PR #39](https://github.com/choi7614/klover_my_prototype/pull/39)을 develop 대상으로 생성했다. 승인된 동일 87개 파일이며 후속 문서 커밋은 제출 기록만 갱신한다. 최종 CI·병합 SHA는 PR 이력을 따른다.
