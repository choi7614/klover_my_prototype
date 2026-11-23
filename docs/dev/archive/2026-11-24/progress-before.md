> 과거 현황판: 정리 전 원문. 현재 상태는 [progress.md](../../progress.md)를 따른다.

# 개발 현황판

> 갱신: 2026-11-20 · 기준: `origin/develop@e5f7efd` · 갱신 도구: Codex

**도구를 바꾸기 전·이어받은 직후 이 표부터 갱신한다.** 규칙은 [AGENTS.md](../../../../AGENTS.md)의 '도구 전환과 인수인계'.
도구 전환용 프롬프트 모음: **[handoff-prompts.md](../../handoff-prompts.md)** · status 문서 양식: [status-template.md](../../status-template.md)

- **작업 도구**: 지금 그 브랜치를 만지고 있는 도구 (`Codex` / `Claude` / `없음`). `없음`이 아니면 다른 도구는 손대지 않고 사용자에게 확인한다.
- **상태**: `미착수` / `진행 중` / `WIP 저장`(한도 등으로 중단) / `PR 대기` / `develop 병합` / `main 병합`

## 기능별 현황

| 기능 | 브랜치 | 작업 도구 | 상태 | 마지막 커밋 | 다음 할 일 | status 문서 | 갱신일 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| F0 첫 실행·메일함 | `feat/F0-mailbox` | 없음 | develop 병합 (#17), 공통 패치 01~05 적용 ([#18](https://github.com/choi7614/klover_my_prototype/pull/18)). F1 분류·요약 표시는 `feat/F1-mail-analysis`에서 F0 파일 변경([#33](https://github.com/choi7614/klover_my_prototype/pull/33)) | `438b29d` 2026-11-19 | 맥북 실제 Gmail 새로고침·F2·F3 화면 흐름 확인, 작성·보관·삭제 | [F0-mailbox-status.md](../../F0-mailbox-status.md) | 2026-11-19 |
| F1 분류·저장 | `feat/F1-mail-analysis` | 없음 | develop 병합 ([#33](https://github.com/choi7614/klover_my_prototype/pull/33), `905398b`), 공통 패치 05~07 적용(`integrate/F1-auto-analysis`, F5 훅 등록 포함) | `f0d0034` 2026-11-19 | 맥북 `AI_PROVIDER=ollama`로 새로고침→분석→S03 분류·요약→S04 제안 확인, 분류 변경 드롭다운·근거 강조·WebSocket(후속) | [F1-analysis-status.md](../../F1-analysis-status.md) | 2026-11-19 |
| F2 프로필·답장 초안 | `feat/F2-profile-draft` | 없음 | develop 병합 (#13), 공통 패치(#16)·IPC(#19)·AI 연결([#31](https://github.com/choi7614/klover_my_prototype/pull/31)) | `c7bfb65` 2026-11-19 | 맥북 실제 AI로 초안 확인, 관련 메일 검색(related) 연결, 초안→보내기(F0) | [F2-profile-draft-status.md](../../F2-profile-draft-status.md) | 2026-11-19 |
| F3 자연어 검색 | `feat/F3-search` | 없음 | develop 병합 ([#24](https://github.com/choi7614/klover_my_prototype/pull/24)), 공통 패치 01 적용 ([#30](https://github.com/choi7614/klover_my_prototype/pull/30)) | `1478e70` 2026-11-19 | 맥북 실제 제공자로 검색 확인, 의미 검색(bge-m3) 연결, 보낸 메일 열기 계약 | [F3-search-status.md](../../F3-search-status.md) | 2026-11-19 |
| F4 주간 보고 | `feat/F4-weekly-report` | 없음 | develop 병합 ([#22](https://github.com/choi7614/klover_my_prototype/pull/22)), 공통 패치 01~05 적용 ([#23](https://github.com/choi7614/klover_my_prototype/pull/23)) | `565929f` 2026-11-19 | 맥북 0006 설치·진입 확인, F1 저장(0007)·실제 AI 연결 후 생성 확인 | [F4-weekly-report-status.md](../../F4-weekly-report-status.md) | 2026-11-19 |
| F5 AI 스캔 | `feat/F5-ai-scan` | 없음 | develop 병합 ([#32](https://github.com/choi7614/klover_my_prototype/pull/32), `d9257c0`), F1 분석 완료 지점에 `AnalysisScanHook` 연결(F1 패치 05, `integrate/F1-auto-analysis`) | `b85e2eb` 2026-11-19 | 맥북 로컬 AI로 새 메일→제안 자동 생성·S04 확인, 알림·트레이(S10) | [F5-ai-scan-status.md](../../F5-ai-scan-status.md) | 2026-11-19 |

## 공통·통합 작업

| 작업 | 브랜치 | 작업 도구 | 상태 | 마지막 커밋 | 다음 할 일 | 갱신일 |
| --- | --- | --- | --- | --- | --- | --- |
| 규칙 단일화·인수인계·CI | `chore/agent-guidelines` | 없음 | develop 병합 ([#14](https://github.com/choi7614/klover_my_prototype/pull/14), `f282640`) | `ae4d00b` 2026-11-19 | 후속: 문서 담당 표기 정리(1인 개발) PR | 2026-11-19 |
| F0 PR 갱신·F2 공통 패치 적용 | `integrate/F2-patches` | 없음 | develop 병합 ([#16](https://github.com/choi7614/klover_my_prototype/pull/16)) | `d726783` 2026-11-19 | F1 저장 SQL을 0005로 옮기기(요청 시) | 2026-11-19 |
| F0 공통 패치 적용 | `integrate/F0-patches` | 없음 | develop 병합 ([#18](https://github.com/choi7614/klover_my_prototype/pull/18)) | `57256d8` 2026-11-19 | F2·F3 main/preload IPC 연결 | 2026-11-19 |
| F2·F3 main/preload 통로 | `integrate/F2-F3-ipc` | 없음 | develop 병합 ([#19](https://github.com/choi7614/klover_my_prototype/pull/19)) | `e0e68ae` 2026-11-19 | 맥북 실제 앱 확인, 실제 AI 어댑터 연결 | 2026-11-19 |
| F4 공통 패치 적용 | `integrate/F4-patches` | 없음 | develop 병합 ([#23](https://github.com/choi7614/klover_my_prototype/pull/23)) | `5bf3cb0` 2026-11-19 | F1 저장(0007)·실제 AI 연결 | 2026-11-19 |
| F5 공통 패치 적용 | `integrate/F5-patches` | 없음 | develop 병합 ([#28](https://github.com/choi7614/klover_my_prototype/pull/28)) | `0af5876` 2026-11-19 | F1 결과→F5 입력 변환 | 2026-11-19 |
| F1·F3 공통 패치 적용 | `integrate/F1-F3-patches` | 없음 | develop 병합 ([#30](https://github.com/choi7614/klover_my_prototype/pull/30)) | `8e4e267` 2026-11-19 | F2 초안 AI 연결, 자동 분석·표시 | 2026-11-19 |
| F2 답장 초안 AI 연결 | `integrate/F2-ai` | 없음 | develop 병합 ([#31](https://github.com/choi7614/klover_my_prototype/pull/31)) | `3da516a` 2026-11-19 | 맥북 실제 AI 확인 | 2026-11-19 |
| F1 자동 분석 공통 패치 05~07 적용 | `integrate/F1-auto-analysis` | 없음 | develop 병합 (#34, `dbdf236`) | `138db45` 2026-11-19 | 맥북 실기에서 메일 목록·본문·요약·분류·제안 표시 확인, 나머지 흐름 후속 | 2026-11-19 |
| F2 답장 작성 관점 보완 | `fix/F2-reply-perspective` | 없음 | develop 병합 (#35, `d0ec68a`) | `e97459e` | 맥북 초안 재검증, 이후 Claude API 합성 연결 확인 | 2026-11-20 |
| F2 로컬 AI 대기 시간 | `fix/F2-generation-timeout` | 없음 | develop 병합 (#36, `e5f7efd`) | `7d2c259` | 맥북 재검증, 후속 AI 제공자 선택 통합 | 2026-11-20 |
| F0·F2·F3·F4 AI 선택·첫 주 보고 | `integrate/ai-provider-selection` | Codex | 진행 중 (구현·검사 완료, 묶음 승인 대기) | 미커밋, 기준 `e5f7efd` | 서버 575/skip 0·앱 182·브라우저 3·정적 검사/빌드 통과. 승인 후 PR·CI 확인, 문제 없으면 develop 병합(사용자 조건부 승인) | 2026-11-20 |
| 공통 서버·DB·Gmail 기반 | `feat/server-foundation` 외 4개 | 없음 | develop 병합 (#4~#9) | `b24f9d6` 2026-11-18 | 추가 작업 없음 | 2026-11-19 |

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

## 이 표를 갱신하는 때

- 도구를 넘기기 전(작업 도구 → `없음` 또는 넘겨받을 도구, 다음 할 일)
- 이어받은 직후(작업 도구 → 자신)
- `[WIP] 인수인계` 커밋 직후(상태 → `WIP 저장`)
- PR 생성·병합 직후(상태·마지막 커밋)
