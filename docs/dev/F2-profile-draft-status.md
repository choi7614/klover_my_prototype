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
- 부분 완료: 초안 생성은 포트·합성 응답까지(AI 미연결 시 503 `ai_unavailable`). 화면은 F2 IPC가 없어 '준비 부족' 상태로 보인다.
- 미구현: 실제 AI 초안 품질, F2용 main/preload IPC 클라이언트, 메일함에서 F2 화면으로 가는 버튼.

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

## 공통 영역 요청

- `patches/F2/` 01~05: 적용 완료(#16). 03은 F0 반영 App에 수동으로 합쳤다.
- 남은 요청: F2용 main/preload IPC 클라이언트를 만들어 `App`의 `f2Client`로 넘긴다(F0 메일 IPC와 같은 방식).

## 다음 할 일

1. F2용 IPC 클라이언트 연결(통합 채팅) 후 실제 화면에서 프로필 저장·초안 흐름 확인
2. 실제 DB에서 `alembic upgrade head`로 0004 적용 확인
3. 실제 AI 어댑터 연결

## 인수인계 메모

- 멈춘 지점: 없음 (공통 패치 적용 완료)
- 주의할 점: 다음 마이그레이션은 0005부터 progress.md 예약 표에서 예약한다.
