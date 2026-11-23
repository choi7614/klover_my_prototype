# 설치·실행 안내 확인 기록

> 2026-11-24(KST) · 작업 `docs/getting-started` · 기능 코드 수정 없음 · 아래 실행 검증은 최초 검토 당시 기록이며 후속 승인 상태는 마지막 절에 기록

## 실제 기준과 근거

- 원격 정보를 갱신하고 파일·커밋·전체 develop 대상 PR을 대조했다.
- `origin/main`: `9575f47155ad7337b68593a2df08bdb6c0d20cac`, 실행 코드 없음.
- `origin/develop`: `f498d2702d1b1592873fe91d973114229c03e098`, PR #37 병합. 이전 통합 점검과 같은 기준이다.
- PR #37의 통합 전 head는 `e32c082646afcd4ae1bb19d820fe6cd09b0fe6e4`이며 '미커밋·묶음 승인 대기' 기록은 현재 상태가 아니다.
- develop 대상 PR #1~#37은 병합 완료이며 기능·공통 패치의 실제 포함 여부는 코드와 대조했다.
- [develop CI 44583287544](https://github.com/choi7614/klover_my_prototype/actions/runs/44583287544): 서버 ruff·pytest, 앱 lint·typecheck·test **두 작업 success** 직접 조회.
  CI 설정상 DB 변수 없는 검사는 skip되며 실 DB/모델/OS 성공을 뜻하지 않는다.
- AGENTS.md·CLAUDE.md·progress·F0~F5 status, 실제 CLI/실행 조립·환경 설정·마이그레이션·API·앱 통로를 읽었다.

## 이번 실행 확인 (과거 검사 건수 재인용 아님)

| 항목 | 명령·방법 | 결과·한계 |
| --- | --- | --- |
| 잠금 의존성 | uv sync --locked, pnpm install --frozen-lockfile | 성공. Debian 13·Node 24.22.1·Python 3.12.14·uv 0.13.6·pnpm 10.34.9·Docker 29.9.2 |
| 분리 DB | 저장소 archive 사본에서 init_local_db, Compose v2의 pgvector/pgvector:pg16, 별도 프로젝트/볼륨/빈 포트 | 새 임의 비밀번호·.env 생성 성공. 기존 DB·키·계정 미사용 |
| migration | alembic upgrade head → current → check_database → upgrade head 반복 | `0007_f1 (head)`, database ok/schema current. 반복 upgrade 성공 |
| 신규 비밀 준비 | 합성 웹 OAuth JSON·합성 계정으로 실제 configure/저장 경계, prepare_mail_api 2회 | 합성 토큰 암호화·API 토큰 생성·권한 600·재실행 시 기존 값 보존 확인. Google 로그인은 아님 |
| 실제 서버 명령 | 실제 run_mail_api --port(분리 포트), /health, check_mail_api | status/session ok, listed 0/detail empty. 합성 계정이며 sync·Google·유료 AI 호출 없음 |
| 서버 정적 검사 | ruff check ., ruff format --check . | 통과, 178개 파일 형식 정상 |
| 서버 전체 검사 | KLOVER_TEST_DATABASE_URL·KLOVER_F1_TEST_DATABASE_URL·KLOVER_F5_TEST_DATABASE_URL을 분리 DB로 지정, pytest -q -rs | **575 통과, skip 0**, 합성 Google·AI 사용 |
| 앱 정적/단위 | pnpm --filter desktop lint, typecheck, test | 통과, **27개 파일·182개 테스트** |
| 앱 빌드 | pnpm --filter desktop build | main/preload/renderer 빌드 성공. Electron 창 성공을 뜻하지 않음 |
| 브라우저 | pnpm --filter desktop test:e2e, 시스템 Chromium 지정 | **5 통과**. 온보딩 2+AI 선택/초안/첫날 보고 3, 합성 IPC |
| 백업 명령 | 분리 합성 DB의 pg_dump -Fc·pg_restore --list | 성공·목록 구조 확인, 내용 비출력. 실제 운영 백업/복구는 미실행 |
| Electron 실행 파일 | pnpm --filter desktop exec electron --version | **실패/환경 차단**: 다운로드 프록시 문제를 환경 설정으로 해소한 뒤 Linux SUID sandbox helper 오류(SIGTRAP). 정상 창 미검증 |

테스트 준비 중 일반 DB명을 F1/F5 변수에 쓰면 안전 가드가 거절하는 것을 확인했다.
이 준비 오류는 DB 이름을 규칙에 맞추어 재검사했다. F1은 `_test`로 끝나는 `klover_docs_test`, F5는
같은 분리 컨테이너의 정확한 이름 `klover_f5_test`로 지정한 최종 결과가 위 575/skip 0이다.

작업용 사본은 /tmp 아래 임시 폴더, Compose 프로젝트는 `klover-docs-check`, 새 볼륨은
`klover-docs-check_postgres_data`, DB 호스트 포트는 빈 포트로 분리했다. 비밀 설정·로그는 임시 사본에만 두고
Git·문서에 복사하지 않았다. 검증 후 이 프로젝트의 DB만 stop했으며 볼륨·기존 작업·브랜치는 삭제하지 않았다.

## 문서 오류와 새 개발 구분

| 이전 안내 문제 | 이번 문서 정리 |
| --- | --- |
| 기본 app.main·Redis/arq·fixture 자동 수신을 현재 실행에 혼합 | 앱용 run_mail_api와 DB/Ollama만 안내. 없는 작업자 명령 제거·과거 원문 보관 |
| F0 실행이 옛 기능 브랜치·개인 폴더·이미 만든 토큰 전제 | develop clone부터 DB·OAuth·API 토큰 생성까지 신규 단계 명시 |
| .env.example 그대로 복사하면 예시 비밀번호 거절 | init_local_db의 무작위 생성 우선. 기존 파일·DB는 덮어쓰지 않음 |
| PR #37이 status/progress에서 미커밋·승인 대기 | 병합 SHA·PR·CI를 확인한 현재 요약으로 갱신, 옛 기록은 접어서 보존 |
| F2/F3/F4 AI·화면, F1→F5가 미연결로 표시 | 코드 조립과 IPC 확인 후 현재 연결/실환경 미검증을 분리 |
| 첫 주 보고와 화면 명세의 1주 대기 모순 | 실제 PR #37의 시작일~오늘·자료 범위 표시로 정리 |
| 기존 공통 패치가 새 적용 요청처럼 보임 | 적용/후속 코드 대체 상태를 표기, 패치 원문은 변경하지 않음 |
| 과거 메일 수집을 보류/영구 제외로 해석 | 기본 수신 제한과 별개로 확정 개발 예정·미구현 문서 작성 |

## 미검증·남은 조건

- 이번에 실제 Google 프로젝트 생성·OAuth 로그인·Gmail 수신/갱신·실제 메일을 사용하지 않았다.
- Ollama 설치·모델 다운로드·실제 생성/임베딩과 Claude 키·모델 가용성·과금·품질·속도를 검증하지 않았다.
- macOS/Windows 신규 사용자 전체·Windows 전용 기능·정상 Electron 창은 미검증이다.
- test:electron/test:mail-read 전체는 미실행. 현재 코드와 옛 기대값의 정적 불일치는 [통합 전달 사항](integration-followups.md)에 기록했다.
- 실제 사용자 DB의 head·데이터 보존·백업 복구는 해당 사용자 환경에서 별도 확인해야 한다.
- 이번 문서는 새 사용자에게 필요한 절차와 제약을 안내할 수 있으나 모든 OS·실서비스의 실행 성공 보장은 아니다.

## 변경 범위와 보관

루트 README·setup을 시작 안내로 만들고, 앱/서버 README·문서 지도·기능 명세·구조·API·데이터·현황을 정리했다.
기존 출처·저작권·라이선스·패치·기록은 보존했다. 새 기획은 현재 구현으로 표시하지 않았다.
소스·잠금 파일·생성 타입·환경 예시·Compose·마이그레이션·패치 파일은 수정하지 않는다.
[보관 목록](archive/2026-11-24/README.md)·[통합 후속 작업](integration-followups.md)을 함께 본다.

## 변경 문서와 이유

| 문서 | 변경 이유 |
| --- | --- |
| [AGENTS.md](../../AGENTS.md) | 앱용 run_mail_api 및 루트 기준 테스트 명령 정정. 규칙은 유지 |
| [README.md](../../README.md) | 처음 방문한 사용자의 시작 안내·브랜치·제약·문서 진입점 |
| [apps/desktop/README.md](../../apps/desktop/README.md) | 실제 통합 범위 반영·실행 절차 setup으로 연결 |
| [apps/server/README.md](../../apps/server/README.md) | 실제 통합 범위 반영·실행 절차 setup으로 연결 |
| [docs/README.md](../README.md) | 설치·현황·검증·원문 기록을 찾는 문서 지도 |
| [docs/architecture/api.md](../architecture/api.md) | 실제 조립/저장/API·현재와 목표 구조의 모순 정리 |
| [docs/architecture/data-model.md](../architecture/data-model.md) | 실제 조립/저장/API·현재와 목표 구조의 모순 정리 |
| [docs/architecture/system.md](../architecture/system.md) | 실제 조립/저장/API·현재와 목표 구조의 모순 정리 |
| [docs/design/screens/S02-inbox-empty.md](../design/screens/S02-inbox-empty.md) | PR #37의 첫 주 보고와 기본 수신/과거 메일 계획 구분 |
| [docs/design/screens/S08-weekly-report.md](../design/screens/S08-weekly-report.md) | PR #37의 첫 주 보고와 기본 수신/과거 메일 계획 구분 |
| [docs/dev/F0-mail-api-handoff.md](F0-mail-api-handoff.md) | 오래된 실행/전달 지시와 현재 상태 구분·setup 연결 |
| [docs/dev/F0-mailbox-run.md](F0-mailbox-run.md) | 오래된 실행/전달 지시와 현재 상태 구분·setup 연결 |
| [docs/dev/F0-mailbox-status.md](F0-mailbox-status.md) | 현재 연결 상태와 실환경 미검증 요약, 옛 검사는 접어 보존 |
| [docs/dev/F1-analysis-status.md](F1-analysis-status.md) | 현재 연결 상태와 실환경 미검증 요약, 옛 검사는 접어 보존 |
| [docs/dev/F1-handoff.md](F1-handoff.md) | 오래된 실행/전달 지시와 현재 상태 구분·setup 연결 |
| [docs/dev/F2-handoff.md](F2-handoff.md) | 오래된 실행/전달 지시와 현재 상태 구분·setup 연결 |
| [docs/dev/F2-profile-draft-status.md](F2-profile-draft-status.md) | 현재 연결 상태와 실환경 미검증 요약, 옛 검사는 접어 보존 |
| [docs/dev/F2-profile-draft.md](F2-profile-draft.md) | 오래된 실행/전달 지시와 현재 상태 구분·setup 연결 |
| [docs/dev/F3-search-handoff.md](F3-search-handoff.md) | 오래된 실행/전달 지시와 현재 상태 구분·setup 연결 |
| [docs/dev/F3-search-status.md](F3-search-status.md) | 현재 연결 상태와 실환경 미검증 요약, 옛 검사는 접어 보존 |
| [docs/dev/F4-proposals/README.md](F4-proposals/README.md) | 적용 또는 대체된 보관 자료·재적용 금지 표기. 패치 원문 보존 |
| [docs/dev/F4-shared-verification.md](F4-shared-verification.md) | 오래된 실행/전달 지시와 현재 상태 구분·setup 연결 |
| [docs/dev/F4-weekly-report-plan.md](F4-weekly-report-plan.md) | 오래된 실행/전달 지시와 현재 상태 구분·setup 연결 |
| [docs/dev/F4-weekly-report-status.md](F4-weekly-report-status.md) | 현재 연결 상태와 실환경 미검증 요약, 옛 검사는 접어 보존 |
| [docs/dev/F5-ai-scan-status.md](F5-ai-scan-status.md) | 현재 연결 상태와 실환경 미검증 요약, 옛 검사는 접어 보존 |
| [docs/dev/F5-handoff.md](F5-handoff.md) | 오래된 실행/전달 지시와 현재 상태 구분·setup 연결 |
| [docs/dev/ai-provider-selection.md](ai-provider-selection.md) | 오래된 실행/전달 지시와 현재 상태 구분·setup 연결 |
| [docs/dev/archive/2026-11-24/F0-mailbox-run-before.md](archive/2026-11-24/F0-mailbox-run-before.md) | 정리 전 실행·현황 원문 보존과 현재 지시 구분 |
| [docs/dev/archive/2026-11-24/README.md](archive/2026-11-24/README.md) | 정리 전 실행·현황 원문 보존과 현재 지시 구분 |
| [docs/dev/archive/2026-11-24/ai-provider-selection-before.md](archive/2026-11-24/ai-provider-selection-before.md) | 정리 전 실행·현황 원문 보존과 현재 지시 구분 |
| [docs/dev/archive/2026-11-24/desktop-readme-before.md](archive/2026-11-24/desktop-readme-before.md) | 정리 전 실행·현황 원문 보존과 현재 지시 구분 |
| [docs/dev/archive/2026-11-24/gmail-mail-sync-before.md](archive/2026-11-24/gmail-mail-sync-before.md) | 정리 전 실행·현황 원문 보존과 현재 지시 구분 |
| [docs/dev/archive/2026-11-24/google-connection-before.md](archive/2026-11-24/google-connection-before.md) | 정리 전 실행·현황 원문 보존과 현재 지시 구분 |
| [docs/dev/archive/2026-11-24/local-database-before.md](archive/2026-11-24/local-database-before.md) | 정리 전 실행·현황 원문 보존과 현재 지시 구분 |
| [docs/dev/archive/2026-11-24/mail-read-api-before.md](archive/2026-11-24/mail-read-api-before.md) | 정리 전 실행·현황 원문 보존과 현재 지시 구분 |
| [docs/dev/archive/2026-11-24/progress-before.md](archive/2026-11-24/progress-before.md) | 정리 전 실행·현황 원문 보존과 현재 지시 구분 |
| [docs/dev/archive/2026-11-24/server-readme-before.md](archive/2026-11-24/server-readme-before.md) | 정리 전 실행·현황 원문 보존과 현재 지시 구분 |
| [docs/dev/archive/2026-11-24/setup-before.md](archive/2026-11-24/setup-before.md) | 정리 전 실행·현황 원문 보존과 현재 지시 구분 |
| [docs/dev/archive/2026-11-24/system-before.md](archive/2026-11-24/system-before.md) | 정리 전 실행·현황 원문 보존과 현재 지시 구분 |
| [docs/dev/f5-patches/README.md](f5-patches/README.md) | 오래된 실행/전달 지시와 현재 상태 구분·setup 연결 |
| [docs/dev/gmail-mail-sync.md](gmail-mail-sync.md) | 오래된 실행/전달 지시와 현재 상태 구분·setup 연결 |
| [docs/dev/google-connection.md](google-connection.md) | 오래된 실행/전달 지시와 현재 상태 구분·setup 연결 |
| [docs/dev/integration-followups.md](integration-followups.md) | 문서로 해결할 수 없는 코드/환경 문제·근거·영향·수정 순서 |
| [docs/dev/local-database.md](local-database.md) | 오래된 실행/전달 지시와 현재 상태 구분·setup 연결 |
| [docs/dev/mail-read-api.md](mail-read-api.md) | 오래된 실행/전달 지시와 현재 상태 구분·setup 연결 |
| [docs/dev/progress.md](progress.md) | 실제 PR #37 병합·구현/예정/보류 구분 및 문서 작업 상태 |
| [docs/dev/setup.md](setup.md) | 신규 설치/기존 업데이트·준비·실행·종료·백업·오류 해결 단일 기준 |
| [docs/dev/verification-2026-11-24.md](verification-2026-11-24.md) | 이번 실제 검사 결과·한계·근거·변경 목록 |
| [docs/product/decisions.md](../product/decisions.md) | 현재 기획·기능 목표/구현 구분·과거 메일 가져오기 개발 예정 명시 |
| [docs/product/features/F0-onboarding-mailbox.md](../product/features/F0-onboarding-mailbox.md) | 현재 기획·기능 목표/구현 구분·과거 메일 가져오기 개발 예정 명시 |
| [docs/product/features/F1-mail-analysis.md](../product/features/F1-mail-analysis.md) | 현재 기획·기능 목표/구현 구분·과거 메일 가져오기 개발 예정 명시 |
| [docs/product/features/F2-profile-draft.md](../product/features/F2-profile-draft.md) | 현재 기획·기능 목표/구현 구분·과거 메일 가져오기 개발 예정 명시 |
| [docs/product/features/F3-search.md](../product/features/F3-search.md) | 현재 기획·기능 목표/구현 구분·과거 메일 가져오기 개발 예정 명시 |
| [docs/product/features/F4-weekly-report.md](../product/features/F4-weekly-report.md) | 현재 기획·기능 목표/구현 구분·과거 메일 가져오기 개발 예정 명시 |
| [docs/product/features/F5-ai-scan.md](../product/features/F5-ai-scan.md) | 현재 기획·기능 목표/구현 구분·과거 메일 가져오기 개발 예정 명시 |
| [docs/product/features/planned-mail-history-import.md](../product/features/planned-mail-history-import.md) | 현재 기획·기능 목표/구현 구분·과거 메일 가져오기 개발 예정 명시 |
| [docs/product/open-questions.md](../product/open-questions.md) | 현재 기획·기능 목표/구현 구분·과거 메일 가져오기 개발 예정 명시 |
| [docs/product/overview.md](../product/overview.md) | 현재 기획·기능 목표/구현 구분·과거 메일 가져오기 개발 예정 명시 |
| [integration/F1-mail-analysis/README.md](../../integration/F1-mail-analysis/README.md) | 적용 또는 대체된 보관 자료·재적용 금지 표기. 패치 원문 보존 |
| [integration/F3-search/README.md](../../integration/F3-search/README.md) | 적용 또는 대체된 보관 자료·재적용 금지 표기. 패치 원문 보존 |
| [packages/api-types/README.md](../../packages/api-types/README.md) | 실제 통합 범위 반영·실행 절차 setup으로 연결 |
| [patches/F0/README.md](../../patches/F0/README.md) | 적용 또는 대체된 보관 자료·재적용 금지 표기. 패치 원문 보존 |
| [patches/F1/README.md](../../patches/F1/README.md) | 적용 또는 대체된 보관 자료·재적용 금지 표기. 패치 원문 보존 |
| [patches/F2/README.md](../../patches/F2/README.md) | 적용 또는 대체된 보관 자료·재적용 금지 표기. 패치 원문 보존 |
| [patches/F3/README.md](../../patches/F3/README.md) | 적용 또는 대체된 보관 자료·재적용 금지 표기. 패치 원문 보존 |
| [patches/F4/README.md](../../patches/F4/README.md) | 적용 또는 대체된 보관 자료·재적용 금지 표기. 패치 원문 보존 |
| [patches/F5/README.md](../../patches/F5/README.md) | 적용 또는 대체된 보관 자료·재적용 금지 표기. 패치 원문 보존 |

최종 문서 검사: 변경/신규 Markdown 67개(과거 원문 보관 12개 포함), 로컬 참조 438개·문서 앵커 2개 누락 0, 코드 블록·줄바꿈·git diff --check 통과. MD 외 변경·새 커밋·스테이징 없음. 완료 직전 원격 main/develop SHA도 같은 기준임을 재확인했다.

## 후속 승인·PR 준비

최초 결과 보고 후 사용자가 문서 변경의 커밋·Push·PR 생성을 승인했다. 최신 원격 develop/main을
재확인하고 문서 범위·참조·형식을 재검증한 뒤 기존 `docs/getting-started` 브랜치에서 제출한다.
앱/서버 코드와 위 실환경 미검증 범위는 그대로이며 새 PR의 GitHub Actions 결과는 PR에서 확인한다.
develop/main 병합과 자동 병합은 이 작업 묶음에 포함하지 않는다. AGENTS.md의 별도 병합 승인 규칙을 따른다.

문서 본문은 `690d6ba`로 커밋·Push했고 [PR #38](https://github.com/choi7614/klover_my_prototype/pull/38)을 develop 대상으로 생성했다. GitHub PR 파일 목록도 Markdown 67개뿐임을 확인했다. 이후 이 문서와 현황판에 PR 번호를 기록하는 문서 커밋을 추가하며, 최신 자동 검사 상태는 PR을 기준으로 확인한다. 병합은 실행하지 않았다.
