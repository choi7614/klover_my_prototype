# 개발 현황판

> 갱신: 2026-11-24 · 코드 기준 `origin/develop f498d27`(PR #37) · 갱신 도구: Codex

설치·실행의 기준은 [setup.md](setup.md). 개발 규칙은 [AGENTS.md](../../AGENTS.md).
원격 `main 9575f47`은 실행 코드가 없고 `develop`에 실행 코드가 있다. PR #37은 병합 완료이며 승인 대기가 아니다.
CI [44583287544](https://github.com/choi7614/klover_my_prototype/actions/runs/44583287544)의 서버·앱 작업 성공을 직접 확인했다. DB 검사가 skip되는 CI와 실제 모델 검증을 구분한다.

## 현재 구현·자동 검사와 실환경 확인

| 기능 | 현재 develop 구현 | 미구현·미검증 | 상세 |
| --- | --- | --- | --- |
| F0 첫 실행·메일함 | 목록·본문·Gmail 새로고침·분석 표시·F2~F5 화면/IPC 연결 | Google/다음 버튼·5단계 완료·메일 쓰기·주기 수신·Windows 기능 미구현 | [status](F0-mailbox-status.md) |
| F1 분석·저장 | 0007 분석·임베딩·자동 분석·앱 표시·F5 훅 연결 | 분류 수정 UI·근거 강조·건수·WebSocket 미구현, 실제 정확도·속도 미검증 | [status](F1-analysis-status.md) |
| F2 프로필·초안 | 저장·초안/수정·선택 AI·인용·대기 시간 보완 | 관련 메일·문체 학습 수집·발송 미구현, 프로필 자동 미리보기의 Claude 호출 주의 | [status](F2-profile-draft-status.md) |
| F3 검색 | 기간·상대·키워드·선택 AI 해석/답변·최근 검색·앱 연결 | 의미 벡터·조직/미회신/분류/첨부 필터·보낸 메일 열기 미구현 | [status](F3-search-status.md) |
| F4 보고 | F1 입력·F2 프로필·0006 저장·API/앱·선택 AI·첫 주 생성 | Word·발송·예약 미구현, 실제 모델 품질·속도 미검증 | [status](F4-weekly-report-status.md) |
| F5 제안 | 0005 제안/할 일·S04/할 일 화면·F1 변환/훅 연결 | 실제 Calendar·회신 실행·OS 알림·트레이·S10 미구현 | [status](F5-ai-scan-status.md) |

## 확정된 개발 예정 (아직 미구현)

- **과거 메일 가져오기**: 사용자가 기간을 선택해 명시적으로 시작. 기존 계정·키·메일과 중복 방지를 보존하고 진행·중단·재시도 제공. 로컬 분석 후 검색·보고에 연결. 가져오기 자체로 Claude 자동 호출 금지. [계획](../product/features/planned-mail-history-import.md).
- **Claude 실패 후 로컬 1회 자동 재시도**: 동일 요청의 로컬 대체 실행·결과 출처·실패/편집 보존을 설계·구현해야 한다.
- **로컬 전용 모드**: 앱 선택뿐 아니라 서버 호출·연결 검사·프로필 미리보기까지 Claude를 차단해야 한다. 현재 로컬 기본값/전송 동의와 구분한다.

## 보류·장기 목표

- 현재 앱·서버·PostgreSQL 유지. 클라우드 이전은 보류.
- 사내망 적용·외부/사내 메일 소스 확장은 장기 목표. 현재 제공 기능으로 안내하지 않는다.

## 공통·통합 작업

| 작업 | 브랜치·도구 | 실제 상태 | 다음 단계 |
| --- | --- | --- | --- |
| 기존 공통 패치·AI 선택 통합 | 기존 통합 브랜치 보존 · 없음 | #14~#37의 해당 PR 병합 완료. 패치는 적용 또는 후속 코드로 대체되어 재적용 금지 | [통합 후속 작업](integration-followups.md) |
| 설치·실행 문서 정리 | `docs/getting-started` · 없음 | 문서 검증 완료·PR 준비. 사용자 커밋·Push·PR 생성 승인. 앱·서버 기능 코드 변경 없음 | develop 대상 PR 검사 확인. develop/main 병합은 별도 승인 |

다른 기능 브랜치에는 이번 작업에서 손대지 않았다. 이전 브랜치·커밋·검사 건수는 [과거 현황판](archive/2026-11-24/progress-before.md)에 보존했다.
기능 브랜치의 작업 도구는 이전 현황판에서 모두 없음이며, PR #37 통합도 병합 완료다. 이어받을 때 원격 status를 다시 확인한다.
도구 전환 규칙은 AGENTS.md와 [인수인계 문구](handoff-prompts.md)를 따른다.

## 마이그레이션 번호 예약

새 Alembic 이력을 만들기 전에 이 표에 번호를 **예약**하고, 실제 적용은 통합 채팅에서 한다.
번호가 겹치면 나중에 예약한 쪽이 번호와 `down_revision`을 다시 맞춘다.

| 번호 | 내용 | 기능 | 상태 | 위치 |
| --- | --- | --- | --- | --- |
| 0001 | 초기 메일 저장 구조 | 공통 | 적용(develop) | `apps/server/migrations/versions/0001_create_initial_mail_storage.py` |
| 0002 | Google 자격 증명 | 공통 | 적용(develop) | `.../0002_google_credentials.py` |
| 0003 | 최근 검색 기록 | F3 | 적용(develop) | `.../0003_search_runs.py` |
| 0004 | 프로필·초안 저장 | F2 | 적용(develop, #16) | `.../0004_profile_draft.py` (revision `0004_f2`) |
| 0005 | AI 제안·할 일·알림 outbox | F5 | 적용(develop, #20), 운영 DB 적용 미확인 | `apps/server/migrations/versions/0005_f5_suggestions.py` (부모 `0004_f2`) |
| 0006 | 주간 보고 스냅샷 | F4 | 적용(develop, #23), 운영 DB 적용 미확인 | `apps/server/migrations/versions/0006_weekly_reports.py` (revision `0006_f4`, 부모 `0005_f5`) |
| 0007 | F1 분석·청크·분류 피드백 저장 | F1 | 적용(develop, #30), 운영 DB 적용 미확인 (pgvector 필요) | `apps/server/migrations/versions/0007_f1_analysis.py` (revision `0007_f1`, 부모 `0006_f4`) |


## 검사 해석

- 이번 명령·결과는 [검증 기록](verification-2026-11-24.md)에 둔다. 과거 575/182 등의 건수와 구분한다.
- 이전 사용자 macOS의 DB·Google·CLI·일부 초안 성공 보고는 신규 사용자 전체 검증이 아니다.
- Google 로그인·실제 Gmail·Ollama·유료 Claude·Windows/macOS 전체 실행은 이번에 하지 않는다.
