# F2 프로필·답장 초안 — 현재 상태

## 현재 작업 — F2 로컬 초안 안정화 (2026-11-24)

- 브랜치 `feat/F2-local-draft-stability` · Codex · 기준 `origin/develop fff7993`(PR #39 **병합 완료**).
- 기존 #35 작성자/원문 복사 검증, #36 서버 120초·미리보기 30초/앱 150초, #37 인용 문구 위치 계산, #39 로컬 선택/전환을 대조했다.
- 같은 문구의 근거 위치를 모두 첫 번째 위치에 배정하던 오거절을 합성 재현 후 수정했다. 출처·원문 정확 일치·겹침 검증은 유지한다.
- JSON/항목·방향·근거/제공자 실패를 비밀 정보 없는 고정 사유로 구분한다. 1회 보정에도 AI 원문을 되돌려 보내지 않는다.
- 검사: 서버 **620 통과/skip 0**, F2 선택 **54 통과**, 기존 동일 앱 코드 F2 통신·화면 **29 통과**, Ruff 통과. 생성/수정 실패·시간 초과·취소에도 초안/편집본·프로필 보존을 확인했다.
- 실제 Qwen·유료 Claude·Gmail·맥북 실행은 미검증이다. 사용자가 겪은 오류의 정확한 원인을 실제 응답 없이 확정하지 않는다.
- 2026-11-25 사용자가 검토한 10개 파일의 커밋·Push·PR 생성과 develop 병합을 승인했다. 제출 절차를 진행하며 기존 계정/키/DB·브랜치와 작업 폴더를 보존한다. main은 별도 승인이다.
- 다음 행동과 안전한 사유 확인: [F2 안정화 검증/인수인계](F2-local-draft-stability.md).


## PR #39 통합 기록 — 2026-11-24

- 작업: `integrate/local-ai-mail-history` · 작업 도구 없음(제출 완료) · 기준 `origin/develop 5e2b7a7`(PR #38).
- 자동 프로필 미리보기는 서버에서 로컬 고정이다. 수동 초안·수정은 선택 AI를 유지하며 Claude 제공자 실패 시 로컬 1회 전환한다. 로컬 전용 모드 차단·결과 AI 표시·편집본/근거 검증을 연결했다. 관련 메일·문체 학습·발송은 이번 범위 밖이다.
- 서버 590개(분리 PostgreSQL, skip 0), 앱 185개, 합성 Chromium 4개 통과. Ruff·lint·typecheck·빌드 결과는 [통합 검증 기록](verification-local-ai-history.md)을 따른다.
- 실제 사용자 DB·Gmail·Ollama·유료 Claude·네이티브 Electron은 미실행이다.
- 기존 기능 브랜치·키·메일·설정은 보존했다. 코드 `0a357b3`을 커밋·Push하고 [PR #39](https://github.com/choi7614/klover_my_prototype/pull/39)을 develop 대상으로 제출했다. 사용자 develop 병합 승인도 받았다. 최종 병합 이력은 PR 상태를 따른다. main은 별도 승인이다.
- 다음 할 일: PR 자동 검사 확인 후 승인된 develop 병합, [맥북 업데이트/실기 확인](local-ai-history-run.md). 이미 반영된 과거 공통 패치는 재적용하지 않는다.

<details>
<summary>PR #38 당시 요약 — 이번 작업 전 기준</summary>

> 2026-11-24 · 실제 기준 `origin/develop f498d27` · PR #37 병합 확인 · 이번 작업은 문서만 수정

## 현재 구현과 남은 일

- 구현·자동 검사 완료: 프로필·초안 저장소/API/앱 IPC·선택 AI·초안 수정·편집 보존·인용 검증·대기 시간 보완은 병합됨(#16·#19·#31·#35·#36·#37).
- 남은 일·실환경 제한: 관련 메일 의미 검색·실제 문체 학습 수집·초안 발송은 미구현. 프로필 자동 미리보기는 답장 기본값이 Claude이면 외부 전송/과금 가능. 실모델 품질·속도 미검증.
- 새 설치·평소 실행·업데이트는 [setup.md](setup.md), 공통 확인 수준은 [현황판](progress.md)·[이번 검증](verification-2026-11-24.md)을 따른다.
- 과거의 '미연결/미커밋/승인 대기'는 아래 당시 기록이다. PR #37과 기존 공통 패치는 이미 병합되어 재적용하지 않는다.
- 확정된 개발 예정: 기간 선택 과거 메일 가져오기, Claude→로컬 1회 자동 재시도, 로컬 전용 모드. 모두 현재 미구현이며 이번에 코드를 변경하지 않는다.

</details>

<details>
<summary>이전 기능 브랜치·검사·인수인계 기록 (현재 실행 지시 아님)</summary>

# F2 프로필·답장 초안 — 상태

## 최신 통합 작업 (2026-11-20, Codex)

- 기준 develop `e5f7efd`(PR #36 포함), 작업 `integrate/ai-provider-selection`.
- 이 아래의 이전 기능 브랜치·검사·미연결 설명은 당시 기록이다. 이번 구현과 검증은
  [AI 선택 안내](ai-provider-selection.md)를 우선한다.
- AI 설정/서버 실행/공유 타입/main·preload와 세 기능의 제공자 선택을 함께 연결한다.
  자동 분석·임베딩·제안은 로컬, 수동 초안·검색·보고서는 저장 기본값/요청 선택을 사용한다.
- 첫 주 보고 생성, 본문 인용 기반 답장 근거 검증도 포함한다. DB 마이그레이션은 없다.
- 검사: 분리 DB 포함 서버 575 통과/skip 0, 앱 182·Chromium 합성 화면 3 통과, lint·typecheck·Ruff·빌드 통과. 실제 Claude/맥북 검사는 미실행.
- 현재 미커밋 작업이 이 통합 브랜치에 있다. 커밋·Push·PR 생성은 묶음 승인 대기이며,
  기존 기능 브랜치는 변경하지 않는다. 맥북·실제 Claude 검사는 별도로 남는다.


## 양식 요약

> 양식: [status-template.md](status-template.md) · 현황판: [progress.md](progress.md)

| 항목 | 내용 |
| --- | --- |
| 브랜치 | `feat/F2-profile-draft` |
| 작업 도구 | 없음 |
| 상태 | develop 병합 (#13), 공통 패치 적용 ([#16](https://github.com/choi7614/klover_my_prototype/pull/16)) |
| 마지막 커밋 | `c7bfb65` 2026-11-19 — [F2] 프로필·초안 분리 구현과 공통 AI 계약 연결 |
| 기준 develop | `7a9d4dd` (통합 채팅 `integrate/F2-patches`) |
| 미커밋 변경 | 없음 (원격 기준) |
| 갱신일 | 2026-11-19 |

## 현재 상태

### 로컬 AI 대기 시간 수정안 (2026-11-20, Codex)

- 기준 develop `d0ec68a`(PR #35 포함), 작업 브랜치 `fix/F2-generation-timeout`.
  초안 생성·다시 쓰기의 전체 서버 제한을 8초에서 120초, 프로필 미리보기는 2초에서 30초로 조정한다.
- 앱 main은 AI 요청을 기존 90초 대신 150초 기다려 서버의 오류 응답을 받을 여유를 둔다.
  일반 조회·저장의 15초 제한은 유지한다. 응답 본문 수신 중 제한 초과도 시간 초과로 구분한다.
- Ollama·Claude 제공자의 시간 초과는 `ai_timeout`(504)으로 안내한다.
  생성 화면에는 최대 2분 대기를 안내하며, 제한 초과 시 호출 취소·기존 편집본 보존을 검사한다.
- 속도 개선이나 모델 품질 보장은 아니다. 기존 10초 생성 성능 목표의 실제 달성 여부는 미확인이다.
  실제 맥북·Ollama·Claude·Gmail 재검증은 후속이다. DB·키·메일·기존 초안·공유 API 형식은 변경하지 않는다.
- 생성 지연·취소 검사는 짧게 환산한 시계와 합성 AI를 사용한다. 커밋·Push·PR 생성 전 로컬 검토 단계다.
- 검사: 관련 서버 pytest 43개 통과·실제 PostgreSQL 필요 24개 skip, 서버 Ruff check·format
  165개 파일 통과. 앱 lint·typecheck 및 테스트 173개 통과. 90초를 넘는 응답 수신,
  요청/본문 수신 중 150초 초과 안내, AI 취소·편집본 보존을 확인했다.
  실제 모델 속도나 맥북 실행을 검사한 결과와 구분한다.

### 맥북 초안 품질 점검·수정안 (2026-11-19, Codex)

- 사용자 화면에서 초안 생성은 완료됐으나 수신 원문의 관점으로 다시 쓰고,
  답장 방향에 `shorter`·`politer` 수정 코드가 표시되는 사례를 확인했다.
  이 화면은 생성 실패/시간 초과 사례가 아니다. 기존 8초 제한은 이번에 변경하지 않는다.
- `fix/F2-reply-perspective`의 로컬 수정안: AI 입력에 프로필 작성자와 원문 발신자(답장 수신자)를
  구분하고, 프롬프트에 최초 회신과 기존 답장 수정의 차이·확인되지 않은 사실 생성 금지를 명시했다.
  원문을 공백만 바꿔 그대로 반환하거나 수정 코드를 답장 방향으로 반환하면 오류로 처리한다.
  의미가 비슷한 모든 재서술을 자동 판별하는 검사는 아니며 실제 모델 품질 재확인은 필요하다.
- 합성 제공자 기준 관련 검사 37개 통과, PostgreSQL 필요 검사 24개 skip. 변경 Python 파일의
  Ruff·형식 검사 통과. 실제 Gmail·Ollama·Claude 호출은 실행하지 않았다.
- DB·API 형식·앱 통신·기존 초안·프로필은 변경하지 않았다. 인사·마무리·서명은 여전히
  사용자 프로필을 그대로 붙이므로, 맥북 프로필에 본인의 정보가 들어 있는지 확인해야 한다.
- PR #35로 develop에 병합됐다(`d0ec68a`). 맥북 초안 품질 재검증을 먼저 하고
  Claude API의 합성 데이터 연결 검증을 이어간다.

- 완료: 프로필(기본 정보·문체·서명·보고 양식) 저장·검증, 세 가지 수정·편집 보존, 학습 동의·삭제 경계, S09/S06 전용 화면 합성 검사.
- 통합(#16): 마이그레이션 `0004_f2`, `app.main` 라우터 등록, 로컬 실행 명령의 F2 저장소 조립, App 화면 경로(`/settings/profile`, `/reply/:mailId`, 돌아가기 `/mail/inbox`), 공유 API 타입 재생성, api·data-model 문서.
- 통합(`integrate/F2-F3-ipc`): F2용 main/preload 통로 10개(`klover:f2:*`, 발송 없음) → 서버 경로 1:1 연결. 화면 `F2Client`가 실제 서버를 부른다.
  메일함 [설정]·[답장 초안 만들기] 진입은 F0 #17에서 연결됨.
- AI 연결(통합 채팅, `integrate/F2-ai`): 서버 실행 명령(`run_mail_api.py`의 `draft_ai()`)이 공통 AI 제공자(`load_providers()`)를
  `SharedDraftAI`로 감싸 `F2Context.ai`에 넣는다. `.env`에 `AI_PROVIDER`(claude 또는 ollama)를 설정하면 초안 생성이 켜지고,
  설정이 없거나 검사용 제공자이면 지금처럼 503 `ai_unavailable`이다(`tests/test_run_mail_api_ai.py`).
  관련 메일 검색(`related`)은 아직 연결하지 않았다(F1 의미 검색 후속).
- 프로필 저장·불러오기·학습 기록 삭제는 실제로 동작(실제 앱 확인은 미실행).
- 미구현: 실제 AI 초안 품질.

상세 구현·검사 기록: [F2-verification.md](F2-verification.md) · 설계: [F2-profile-draft.md](F2-profile-draft.md) · 연결 요청: [F2-handoff.md](F2-handoff.md)

## 검사 결과

[F2-verification.md](F2-verification.md) 참조 (서버 pytest 299 통과 — 테스트 DB 사용, 데스크톱 39 통과, Playwright 7 통과).

공통 패치 적용 후 (2026-11-19, 통합 채팅, `integrate/F2-patches`):

| 검사 | 결과 |
| --- | --- |
| 서버 `ruff check`·`ruff format --check` | 통과 |
| 서버 `pytest` | 209 통과, 90 skip (실제 PostgreSQL 필요 — 이 환경에 DB 없음, 미실행) |
| `alembic heads` | `0004_f2` 하나 (상위 `0003_search_runs`) |
| 데스크톱 `lint`·`typecheck`·`test` | 통과 (65개) |
| `packages/api-types` typecheck | 통과 |
| 실제 DB의 0004 upgrade/downgrade, Electron 실행 | 미실행 (DB·화면 환경 없음) |

공유 타입은 `pnpm gen:api-types`로 재생성했다. 패치 04와의 차이는 422 응답 설명 문구뿐이다.

F2·F3 IPC 연결 후 (2026-11-19, 통합 채팅, `integrate/F2-F3-ipc`):

| 검사 | 결과 |
| --- | --- |
| 데스크톱 `lint`·`typecheck` | 통과 |
| 데스크톱 `test` | 11개 파일 94개 통과 (새 통로 검사 14개 추가) |
| 데스크톱 `build`(electron-vite) | 통과, preload는 `electron`만 불러옴 |
| 서버 `ruff check`·`pytest` | 통과, 221 통과·90 skip (서버 변경 없음, 실제 PostgreSQL 필요 검사 미실행) |

미실행: 실제 서버·Electron 창에서 프로필 저장·초안 만들기.

## 공통 영역 요청

- `patches/F2/` 01~05: 적용 완료(#16). 03은 F0 반영 App에 수동으로 합쳤다.
- F2용 main/preload IPC: 연결 완료(`integrate/F2-F3-ipc`). `src/main/f2-client.ts`·`f2-ipc.ts`, `src/shared/f2-bridge.ts`, `src/renderer/bridges/f2-ipc-client.ts`.

## 다음 할 일

1. 맥북 실제 앱에서 프로필 저장·초안 흐름 확인
2. 실제 DB에서 `alembic upgrade head`로 0004 적용 확인
3. 실제 AI 어댑터 연결

## 인수인계 메모

- 멈춘 지점: 없음 (공통 패치 적용 완료)
- 주의할 점: 다음 마이그레이션은 0005부터 progress.md 예약 표에서 예약한다.

</details>
