# F2 프로필·답장 초안 — 상태

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
