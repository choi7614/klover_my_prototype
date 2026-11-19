# 개발 현황판

> 갱신: 2026-11-19 · 기준: `origin/develop@9ac5421` · F4 PR #22 검사 기록 · 갱신 도구: Codex

**도구를 바꾸기 전·이어받은 직후 이 표부터 갱신한다.** 규칙은 [AGENTS.md](../../AGENTS.md)의 '도구 전환과 인수인계'.
도구 전환용 프롬프트 모음: **[handoff-prompts.md](handoff-prompts.md)** · status 문서 양식: [status-template.md](status-template.md)

- **작업 도구**: 지금 그 브랜치를 만지고 있는 도구 (`Codex` / `Claude` / `없음`). `없음`이 아니면 다른 도구는 손대지 않고 사용자에게 확인한다.
- **상태**: `미착수` / `진행 중` / `WIP 저장`(한도 등으로 중단) / `PR 대기` / `develop 병합` / `main 병합`

## 기능별 현황

| 기능 | 브랜치 | 작업 도구 | 상태 | 마지막 커밋 | 다음 할 일 | status 문서 | 갱신일 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| F0 첫 실행·메일함 | `feat/F0-mailbox` | 없음 | develop 병합 (#17), 공통 패치 01~05 적용 ([#18](https://github.com/choi7614/klover_my_prototype/pull/18)) | `438b29d` 2026-11-19 | 맥북 실제 Gmail 새로고침·F2·F3 화면 흐름 확인, 작성·보관·삭제 | [F0-mailbox-status.md](F0-mailbox-status.md) | 2026-11-19 |
| F1 분류·저장 | `feat/F1-mail-analysis` | 없음 | develop 병합 (#11) | `34ebcbc` 2026-11-18 | 실제 LLM·임베딩 어댑터 연결, 저장 SQL·라우터 운영 반영(통합 채팅) | [F1-analysis-status.md](F1-analysis-status.md) | 2026-11-19 |
| F2 프로필·답장 초안 | `feat/F2-profile-draft` | 없음 | develop 병합 (#13), 공통 패치(#16)·IPC 연결([#19](https://github.com/choi7614/klover_my_prototype/pull/19)) | `c7bfb65` 2026-11-19 | 맥북 실제 앱 확인, 실제 DB 0004 적용 확인, 실제 AI 어댑터 연결 | [F2-profile-draft-status.md](F2-profile-draft-status.md) | 2026-11-19 |
| F3 자연어 검색 | `feat/F3-search` | 없음 | develop 병합 (#12), F0 진입(#17)·IPC 연결([#19](https://github.com/choi7614/klover_my_prototype/pull/19)) | `deeda1c` 2026-11-19 | 실제 모델 어댑터(의미 검색·답변), 보낸 메일 열기 계약, 맥북 실제 앱 확인 | [F3-search-status.md](F3-search-status.md) | 2026-11-19 |
| F4 주간 보고 | `feat/F4-weekly-report` | 없음 | 기능 코드·검사 완료 ([#22](https://github.com/choi7614/klover_my_prototype/pull/22)), 공통 패치 미적용 | `1576fc8` (코드, 이후 인계 문서는 PR 최신 커밋 참조) | 공통 패치 01~05 적용·F1 운영 저장·실제 AI·앱 진입 연결은 별도 통합 | [F4-weekly-report-status.md](F4-weekly-report-status.md) | 2026-11-19 |
| F5 AI 스캔 | `feat/F5-ai-scan` | 없음 | develop 병합 ([#20](https://github.com/choi7614/klover_my_prototype/pull/20), `72fb8e4`) | `79cc6ff` 2026-11-19 | F1 입력·F0 화면/알림 연결, 운영 DB 0005 적용 확인, 실제 Calendar는 별도 승인 | [F5-ai-scan-status.md](F5-ai-scan-status.md) | 2026-11-19 |

## 공통·통합 작업

| 작업 | 브랜치 | 작업 도구 | 상태 | 마지막 커밋 | 다음 할 일 | 갱신일 |
| --- | --- | --- | --- | --- | --- | --- |
| 규칙 단일화·인수인계·CI | `chore/agent-guidelines` | 없음 | develop 병합 ([#14](https://github.com/choi7614/klover_my_prototype/pull/14), `f282640`) | `ae4d00b` 2026-11-19 | 후속: 문서 담당 표기 정리(1인 개발) PR | 2026-11-19 |
| F0 PR 갱신·F2 공통 패치 적용 | `integrate/F2-patches` | 없음 | develop 병합 ([#16](https://github.com/choi7614/klover_my_prototype/pull/16)) | `d726783` 2026-11-19 | F1 저장 SQL을 0005로 옮기기(요청 시) | 2026-11-19 |
| F0 공통 패치 적용 | `integrate/F0-patches` | 없음 | develop 병합 ([#18](https://github.com/choi7614/klover_my_prototype/pull/18)) | `57256d8` 2026-11-19 | F2·F3 main/preload IPC 연결 | 2026-11-19 |
| F2·F3 main/preload 통로 | `integrate/F2-F3-ipc` | 없음 | develop 병합 ([#19](https://github.com/choi7614/klover_my_prototype/pull/19)) | `e0e68ae` 2026-11-19 | 맥북 실제 앱 확인, 실제 AI 어댑터 연결 | 2026-11-19 |
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
| 0006 | 주간 보고 스냅샷 | F4 | 제안 예약·미적용 (`0006_f4`, parent `0005_f5`; 실제 적용 전 최신 head 확인) | `patches/F4/files/0006_weekly_reports.py.pending` |

## 이 표를 갱신하는 때

- 도구를 넘기기 전(작업 도구 → `없음` 또는 넘겨받을 도구, 다음 할 일)
- 이어받은 직후(작업 도구 → 자신)
- `[WIP] 인수인계` 커밋 직후(상태 → `WIP 저장`)
- PR 생성·병합 직후(상태·마지막 커밋)
