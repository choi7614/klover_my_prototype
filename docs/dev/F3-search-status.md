# F3 자연어 검색 — 현재 상태

2026-11-25 · 코드 기준 develop `9946b87`(#48).

- 구현·연결: 약어/동의어 확장·월 구간 해석·키워드/로컬 벡터 결합·근거 답변·제한 안내 연결(#47/#48).
- 남은 범위: 조직/미회신/분류/첨부 조건·보낸 메일 열기는 미완료. 실제 모델 정확도·지연·벡터 호환성은 확인 필요.
- 기존 사용자의 macOS 사용 확인 보고(API 키 제외)와 신규 사용자/실제 모델 전체 검증은 구분한다.
- 현재 실행·업데이트는 [setup](setup.md), 실행 도구 작업/검사는 [이번 검증](colleague-setup-verification.md)을 따른다.

<details>
<summary>과거 작업·제출 기록 — 당시의 미적용/승인 대기는 현재 상태가 아님</summary>

> **2026-11-25 제출 완료:** 코드 `23f63ef` 커밋·Push, [PR #48](https://github.com/choi7614/klover_my_prototype/pull/48) 제출. 작업 도구 없음.
> 사용자 develop 병합 승인 있음. 최종 검사·병합 상태는 PR #48을 따른다. 아래 승인 대기/미커밋 설명은 검토 당시 기록이다.

# F3 자연어 검색 — 최신 상태

> 2026-11-25 · `integrate/F3-memory-search` · 작업 도구 없음(검사 완료·승인 대기)

- 실제 기준: PR #47 병합 `origin/develop 5b5d0c6` 확인. 이전 기능 브랜치는 보존했다.
- 패치 01의 `build_semantic_search(engine)`를 실행 조립부에 연결했다.
- 패치 02는 `pnpm gen:api-types`로 재생성했고 두 생성 파일 모두 패치와 정확히 일치했다.
- 분리 PostgreSQL·합성 모델로 서버 693/skip 0, 앱 215, 검색 Chromium 2, 실제 HTTP→앱 IPC 통로 1 통과. 정적 검사·타입·빌드 통과.
- 실제 Gmail·유료 AI·사용자 DB 미접근. 기존 데이터·벡터·브랜치 삭제/재생성 없음.
- 실제 모델 품질·5초 성능·네이티브 Electron 창은 미검증이다.
- 미커밋·미Push이며 신규 PR 없음. 커밋·Push·PR 생성과 develop 반영 승인을 기다린다. main 제외.
- 변경 파일·검사 방법·실환경 확인: [통합 기록](F3-memory-search-integration.md).

<details>
<summary>이전 제출·검사 기록 (현재 실행 지시 아님)</summary>

> 2026-11-25 제출 갱신: 사용자 승인으로 구현 `63c25df` 커밋·Push, PR #47 제출 완료. 미커밋 작업 없음(이 문서 갱신도 제출). develop 병합 승인 있음; 최종 병합 상태는 PR #47을 따른다. 공통 패치 01~02는 미적용이며 운영 의미 검색은 미통합. 아래 승인 대기/미커밋 설명은 제출 전 기록이다.

> **2026-11-25 기억 검색 개선:** `feat/F3-memory-search`, `/workspace/f3-memory-search`, 기준 develop `7b48c68`.
> 기능 구현·합성/분리 DB 검사 완료, 미커밋·미Push·신규 PR 없음(승인 대기). 공통 의미 검색 조립/생성 타입 패치는 미적용이다.
> 서버 689/skip 0·앱 215·합성 Chromium 2·정적 검사/빌드 통과. 실제 모델 정확도·5초 성능은 미검증이다.
> 최신 범위·검사·미검증·통합 요청은 [기억 검색 인수인계](F3-memory-search-handoff.md)를 우선한다. 아래는 이전 제출 기록이다.

# F3 자연어 검색 — 현재 상태

## 현재 상태 — 2026-11-24 통합 작업

- 작업: `integrate/local-ai-mail-history` · 작업 도구 없음(제출 완료) · 기준 `origin/develop 5e2b7a7`(PR #38).
- 로컬 전용 차단·Claude 실패 후 로컬 1회 전환·실제 AI 표시를 연결했다. 가져온 과거 메일은 SQL 조회와 결과 정렬/근거 답변 모두 허용한다. 의미 벡터 검색·추가 조건·보낸 메일 열기는 기존 미완료 범위다.
- 서버 590개(분리 PostgreSQL, skip 0), 앱 185개, 합성 Chromium 4개 통과. Ruff·lint·typecheck·빌드 결과는 [통합 검증 기록](verification-local-ai-history.md)을 따른다.
- 실제 사용자 DB·Gmail·Ollama·유료 Claude·네이티브 Electron은 미실행이다.
- 기존 기능 브랜치·키·메일·설정은 보존했다. 코드 `0a357b3`을 커밋·Push하고 [PR #39](https://github.com/choi7614/klover_my_prototype/pull/39)을 develop 대상으로 제출했다. 사용자 develop 병합 승인도 받았다. 최종 병합 이력은 PR 상태를 따른다. main은 별도 승인이다.
- 다음 할 일: PR 자동 검사 확인 후 승인된 develop 병합, [맥북 업데이트/실기 확인](local-ai-history-run.md). 이미 반영된 과거 공통 패치는 재적용하지 않는다.

<details>
<summary>PR #38 당시 요약 — 이번 작업 전 기준</summary>

> 2026-11-24 · 실제 기준 `origin/develop f498d27` · PR #37 병합 확인 · 이번 작업은 문서만 수정

## 현재 구현과 남은 일

- 구현·자동 검사 완료: 기간·상대·키워드 조회, 질문 해석·근거 답변의 선택 AI, 최근 검색·F0 진입·실제 IPC가 연결됨(#19·#30·#37).
- 남은 일·실환경 제한: 의미 벡터 어댑터·조직/미회신/분류/첨부 필터·보낸 메일 열기 계약은 미구현. 실제 모델의 정확도·5초 성능은 미검증.
- 새 설치·평소 실행·업데이트는 [setup.md](setup.md), 공통 확인 수준은 [현황판](progress.md)·[이번 검증](verification-2026-11-24.md)을 따른다.
- 과거의 '미연결/미커밋/승인 대기'는 아래 당시 기록이다. PR #37과 기존 공통 패치는 이미 병합되어 재적용하지 않는다.
- 확정된 개발 예정: 기간 선택 과거 메일 가져오기, Claude→로컬 1회 자동 재시도, 로컬 전용 모드. 모두 현재 미구현이며 이번에 코드를 변경하지 않는다.

</details>

<details>
<summary>이전 기능 브랜치·검사·인수인계 기록 (현재 실행 지시 아님)</summary>

# F3 구현·검사 결과

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
| 브랜치 | `feat/F3-search` |
| 작업 도구 | 없음 |
| 상태 | develop 병합 ([#24](https://github.com/choi7614/klover_my_prototype/pull/24)), 공통 패치 01 적용 (통합 채팅 `integrate/F1-F3-patches`) |
| 마지막 커밋 | `1478e70` 2026-11-19 — [F3] 공통 AI 연결용 질문 해석기·답변기 추가 |
| 기준 develop | `420078e` |
| 미커밋 변경 | 없음 |
| 갱신일 | 2026-11-19 |

## 현재 상태

- 완료(이번 단위, 2026-11-19): 공통 `TextGeneration`만 쓰는 질문 해석기·답변기.
  - `app/ai/search_adapter.py`: `SharedQueryParser`, `SharedSearchAnswerer`. 제공자(Claude API·로컬 Qwen)를 직접 고르지 않는다.
  - 프롬프트: `app/ai/prompts/search_parse.md`, `search_answer.md`.
  - 로컬 모델 대비: JSON 코드 블록 표시는 벗겨 내고, 형식·근거 인용 오류는 **응답 원문 없이 오류 안내만 붙여 1번 재시도**.
    제공자 오류·시간 초과는 재시도하지 않는다. 전체 대기는 `SearchService.model_timeout`(기본 10초) 안.
  - 실패 안내는 기존 코드만 사용: 해석 `parse_failed`(422)·`parse_unavailable`(503)·`parser_unavailable`(503),
    답변 `invalid_answer`·`answer_failed`·`answer_unavailable`. 가짜 결과로 대체하지 않는다.
  - `app/services/search.py`: 제공자 미연결(`ProvidersNotConfigured`)을 `parser_unavailable`/`answer_unavailable`로,
    재시도 후 형식 실패(`ModelOutputInvalid`, `search_ports.py`)를 `invalid_answer`로 정확히 안내.
- **운영 서버 연결(통합 채팅, `integrate/F1-F3-patches`)**: `patches/F3/01`을 적용해 `run_mail_api.py`가 `load_providers()`로
  해석기·답변기를 주입한다. 맥북 `.env`에 `AI_PROVIDER`(claude 또는 ollama)를 설정하면 검색이 켜지고,
  설정이 없으면 지금처럼 `503 parser_unavailable`이다(적용 후 확인: `search_ai()` → `(None, None)`).
- 이전 완료: 검색 계약·한국 날짜 해석, 격리 조회, 순위 결합·근거 검증, S07 화면, 서버 경로, 0003, F0 진입·IPC 통로.
- 미구현: 의미 검색(벡터) 어댑터, 보낸 메일 열기, 실제 모델 정확도·5초 성능 확인.

## 검사 결과

| 검사 | 결과 |
| --- | --- |
| `uv run pytest tests/test_search_ai_adapter.py` (가짜 제공자, 신규 20개) | 20 통과 |
| `uv run pytest` (서버 전체) | 298 통과, 129 skip(실제 DB 필요) |
| `uv run ruff check .` / `ruff format --check .` | 통과 |
| 패치 01 임시 적용 후 `ruff check`·`search_ai()` 호출 | 통과, 제공자 없음 → `(None, None)` |
| `git apply --check patches/F3/01-search-ai-wiring.patch` | 통과 |
| 실제 Claude API·로컬 Qwen 호출 | **미실행** (맥북·API 키 없음) |
| 데스크톱 검사 | 미실행 (앱 코드 변경 없음) |

신규 검사 범위: 공통 계약 사용·질문/날짜만 전송, 코드 블록 허용, 1회 재시도·잘못된 응답 미재전송, 2회 실패 시 중단,
제공자 오류 무재시도, 시험용 제공자 운영 차단, 서비스 연결 전체 흐름, 해석 실패 코드 4종(형식·제공자 오류·미연결·시간 초과),
지어낸 인용 → 재시도 → `invalid_answer`, 다른 메일 ID 재시도 복구, 답변 제공자 실패 코드, 결과 밖 메일 미전송.

## 공통 영역 요청

- **새 요청**: `patches/F3/01-search-ai-wiring.patch` — `run_mail_api.py`에 해석기·답변기 주입(통합 채팅). [README](../../patches/F3/README.md)
- F1 채팅과 겹치는 파일은 건드리지 않음: `app/ai/runtime.py`, `app/ai/interfaces.py`, `.env` 예시, `uv.lock`.
- 남은 요청: 보낸 메일 상세 열기 계약(공통 서버).

## 다음 할 일

1. F1 runtime(Claude/Qwen 선택) develop 반영 후 통합 채팅에서 패치 01 적용
2. 맥북에서 실제 제공자로 질문 해석·답변 정확도·5초 성능 확인(특히 로컬 Qwen 형식 준수율)
3. 의미 검색 어댑터 연결, 맥북 실제 앱 확인

## 인수인계 메모

- 멈춘 지점: 없음 (단위 완료)
- 주의할 점: 재시도는 1회뿐이다(`MAX_ATTEMPTS = 2`). 로컬 모델이 자주 실패하면 프롬프트를 먼저 조정한다.
  합성 화면은 `vite.search.config.ts` 전용 설정으로 실행. `artifacts/`는 커밋 대상 아님.

---

## 상세 기록 (기존 내용 보존)

> 2026-11-19 · `feat/F3-search` · 통합 기준 `4fef3fe` · **서버 등록 완료, 실제 모델·F0 화면 미연결**

요청한 여섯 범위의 독립 구현과 검사를 마친 뒤, 사용자 승인으로 최신 `develop`의 F1 계약과
F3 공통 패치를 통합했다. 서버 경로·최근 검색 마이그레이션·공유 타입을 반영했다.
F0 진입점·기존 인증/메일 API·수신/키·공통 모델·잠금 파일은 보존했다. 실제 사용 중인 DB는 변경하지 않았다.

## 사용자가 확인할 수 있는 동작

- 질문 해석 결과를 기간·상대·대상·주제로 검증한다. 한국 기준 날짜를 주입해 지난달·이번 주·
  어제와 연도·윤년·자정 경계를 검사했다.
- 현재 저장된 정보로 기간·상대 이름/주소·받은/보낸·키워드를 검색한다. 사용자, 같은 사용자의
  다른 계정, 사용 시작일 이전의 메일은 전체/일부 일치와 벡터 후보 재조회에서 모두 제한한다.
- 키워드·벡터 포트 결과의 중복 청크를 제거하고 순위를 합친다. 전체 조건 만족과 일부 만족을
  분리하며, 아직 없는 조직·회신·분류·첨부 조건을 지원되는 것처럼 처리하지 않는다.
- 답변의 원문 발췌와 `mail_id`를 검사한다. 0건·잘못된 인용·해석 실패·모델 미연결/실패를
  구별한다. 일부 일치 메일을 전체 일치 답변의 근거로 사용하지 않는다.
- 조건을 고치거나 지운 뒤 재검색하고 최근 질문을 다시 검색할 수 있다. 취소를 무시한 이전
  요청의 성공·오류 응답과 계정 변경 전 결과가 새 화면을 덮어쓰지 않는다.
- S07 전용 화면에 칩·결과·근거 번호·로딩·빈 상태·오류·필터·최근 검색을 구현했다.
  실제 F0/F2 창 대신 메일/초안 열기 계약을 합성 화면에서 확인했다.

합성 화면은 `corepack pnpm --filter desktop exec vite --config vite.search.config.ts` 실행 후
`http://127.0.0.1:5183`에서 확인한다. `빈 결과`, `해석 오류`, `답변 오류`를 입력하면 각 상태를
볼 수 있다. 구체적인 계약과 재현 명령은 [전달 문서](F3-search-handoff.md)를 따른다.

검사 화면:

- 1440px 화면 (당시 로컬 산출물: `../../apps/desktop/artifacts/f3-search-1440.png`, Git 미포함)
- 1280px 화면 (당시 로컬 산출물: `../../apps/desktop/artifacts/f3-search-1280.png`, Git 미포함)
- 좁은 화면 (당시 로컬 산출물: `../../apps/desktop/artifacts/f3-search-760.png`, Git 미포함)
- 빈 결과 (당시 로컬 산출물: `../../apps/desktop/artifacts/f3-search-empty.png`, Git 미포함)

이미지와 실행 보고서는 로컬 `artifacts` 산출물이며 커밋 대상에서 제외했다.

## 검사 결과

독립 검사에는 PostgreSQL **16.2**, 통합 회귀 검사에는 새 **PostgreSQL 16 + pgvector**
컨테이너의 전용 테스트 DB·일회용 스키마를 사용했다. 운영 볼륨을 연결하지 않았다.
사용 중인 Gmail DB·키·메일을 읽거나 바꾸지 않았다. 실제 Gmail 내용을 외부 AI로 보내지 않았다.

| 검사 | 최종 결과 |
| --- | --- |
| 통합 후 서버 전체 `pytest -q` | **249 통과**, 실패·오류·skip 0. F1 91개·F3 59개 포함 |
| 통합 전 서버 검사 | 158 통과, 실패·오류·skip 0 |
| 패치 적용 전 `pytest tests/f3_proposal_checks.py -q` | **3 통과**, 실패·오류·skip 0. 통합 직전에도 재검사 |
| 데스크톱 `pnpm --filter desktop test` | **19 통과**. F3 신규 검사 17개 포함 |
| F3 Playwright/실제 Chromium | **2 통과**. 1440/1280/760px, 근거 이동·열기 계약·조건 변경·빈/오류 상태 |
| 데스크톱 TypeScript·ESLint | 통과 |
| F3 Python Ruff·format 검사 | 통과 |
| F3 독립 Vite 빌드 | 통과 |
| 패치·생성 타입 | 사전 적용 검사, 실제 소스 반영, `pnpm gen:api-types` 재생성·TypeScript 검사 통과 |
| 기존 코드 보존 | 통합 전 공통 파일 14개를 해시 대조. 통합 후 승인된 공통 변경만 반영 |

서버 검사는 실제 로컬 HTTP 프로세스에 Node `fetch`로 요청해 인증·단계 순서·정답 ID 3개·
근거 번호·재검색·최근 검색·소유자 주입 거부를 확인했다. 이때 해석/답변 포트는 합성 응답이다.
실제 서버 연결 검사와 실제 모델의 검색 정확도 검사를 구분한다.

DB 패치 검사는 독립 테스트 복사본에 적용해 새 이력의 반복 적용·되돌리기·모델 일치를
확인하고, 기존 합성 메일·계정 시작 상태·Google 암호문이 보존되는지 검사했다.
서버 등록 패치도 복사본에서 검사했으며 미설정 기본 앱이 가짜 검색 성공을 반환하지 않는다.

초기 검사 중 발견한 검사 코드의 타입 오류, 독립 Vite 루트의 유틸리티 누락, 빌드 산출물의
ESLint 포함 문제를 수정했다. 위 표는 수정 후 결과다.

로컬 상세 보고서:

- 서버 JUnit (당시 로컬 산출물: `../../artifacts/f3-server.xml`, Git 미포함)
- 승인 전 패치 JUnit (당시 로컬 산출물: `../../artifacts/f3-proposals.xml`, Git 미포함)
- 통합 후 F1/F3 전체 서버 JUnit (당시 로컬 산출물: `../../artifacts/f3-integrated-server.xml`, Git 미포함)

## 변경 파일

승인 전에는 신규 파일 37개로 구성했다. 승인 후 기존 공통 파일을 추가로 반영했으며,
아래 경로는 저장소 루트를 기준으로 한다.

| 영역·파일 | 목적 |
| --- | --- |
| `apps/server/app/schemas/search.py` | 요청·해석·조건·결과·근거 계약 |
| `apps/server/app/services/search_rules.py` | 한국 날짜, 조건 지원 여부, 명시적 삭제·변경 규칙 |
| `apps/server/app/services/search_ports.py` | F1과 연결할 해석·답변·의미 검색 포트 |
| `apps/server/app/services/search.py` | 단계별 검색·결합·순위·답변 근거 검증 |
| `apps/server/app/db/repositories/search.py` | 실제 PostgreSQL의 격리된 조건·키워드 조회 |
| `apps/server/app/db/repositories/search_recent.py` | F3 전용 최근 검색 저장 매핑·조회 |
| `apps/server/app/api/search.py` | 공통 인증을 사용하는 미등록 F3 라우터 |
| `apps/desktop/src/renderer/features/search/contracts.ts` | 화면·서버·F0/F2 연결 계약과 응답 검증 |
| `apps/desktop/src/renderer/features/search/use-search.ts` | 재검색·최근 검색·취소·오래된 응답 방지 |
| `apps/desktop/src/renderer/features/search/search-page.tsx` | 기능 전용 S07 화면 |
| `apps/desktop/src/renderer/features/search/search.css` | 기존 의미 토큰을 사용하는 F3 스타일 |
| `apps/desktop/src/search/search-http-client.ts` | F0 main용 로컬 HTTP/NDJSON 어댑터 |
| `apps/desktop/src/renderer/features/search/search-page.test.tsx` | 화면·조건·근거·계정 전환·동시 요청 검사 |
| `apps/desktop/src/search/search-http-client.test.ts` | 주소·토큰 전달 경계, UTF-8·잘못된 응답 검사 |
| `apps/desktop/vite.search.config.ts`, `playwright.search.config.ts` | F0 설정을 보존하는 전용 실행·브라우저 검사 |
| `apps/desktop/tests/f3/index.html`, `preview.tsx`, `preview.css` | 앱 미통합 합성 화면 진입점 |
| `apps/desktop/tests/f3/synthetic-client.ts`, `e2e/search.spec.ts` | 테스트 대역·실제 브라우저 시나리오 |
| `apps/server/tests/search_support.py`, `search_http_app.py` | 합성 데이터·대역·독립 HTTP 테스트 앱 |
| `apps/server/tests/test_search_contract.py`, `test_search_service.py` | 날짜·지원 조건·순위·근거·오류 검사 |
| `apps/server/tests/test_search_repository.py`, `test_search_api.py`, `test_search_integration.py` | DB 격리·인증·실제 로컬 HTTP 검사 |
| `apps/server/tests/f3_proposal_checks.py` | 승인 전 패치 검사. 기본 테스트 수집과 분리 |
| `integration/F3-search/01-storage.patch` | 최근 검색 테이블·공통 메타데이터/모델 검사 제안 |
| `integration/F3-search/02-server-registration.patch` | 공통 서버 등록·저장소 조립·등록 경로 검사 제안 |
| `integration/F3-search/03-shared-api-types.patch` | 실제 OpenAPI에서 생성한 공유 타입 변경 제안 |
| `integration/F3-search/baseline.json`, `README.md` | 보존 기준과 패치 검토 안내 |
| `scripts/f3/prepare_integration.py` | 공통 파일을 수정하지 않는 패치 생성기 |
| `docs/dev/F3-search-handoff.md`, `F3-search-status.md` | 연결 요청·검사·변경 사항 보고 |
| `apps/server/app/main.py`, `app/cli/run_mail_api.py` | 승인된 검색 경로 등록·저장소 조립 |
| `apps/server/migrations/env.py`, `migrations/versions/0003_search_runs.py` | F3 메타데이터·새 최근 검색 이력 |
| `apps/server/tests/test_http_server.py`, `test_postgresql_storage.py` | 등록 경로·공동 메타데이터 검사 갱신 |
| `packages/api-types/openapi.json`, `src/schema.d.ts` | 실제 등록 앱에서 재생성한 공유 계약 |
| `docs/README.md`, `docs/architecture/api.md`, `data-model.md`, `docs/product/features/F3-search.md` | 등록·데이터·남은 수용 기준 상태 반영 |

F0 app/router·main/preload·메일함, 공통 모델, 기존 Alembic 이력, 기존 인증/메일 API·
Gmail 수신/연결/키·잠금 파일은 보존했다. 새 Alembic 이력과 서버 등록·공유 타입은 승인 범위로 반영했다.

## 미확인 항목과 연결 요청

- **F1**: 공통 호출 계약에 맞는 실제 해석·임베딩·답변 어댑터 연결이 남았다. 현재 의미 검색은
  기본 비활성이다. 원래 명세의 조직·미회신 예시 질문, 실제 모델 정확도와 첫 결과 5초 성능은
  미확인이다. 현재 답변은 검증 가능한 원문 발췌형이며 자유 요약 품질은 검증하지 않았다.
- **F0**: 제한된 main/preload IPC, `SearchPage` 화면 슬롯과 검색 진입, 실제 메일 열기 연결이
  남았다. 현재 상세 API는 받은편지함만 읽으므로 보낸/보관 메일 상세 계약도 필요하다.
- **F2**: `openDraft({mail_id, source:'F3'})`를 실제 S06에 연결해야 한다. 초안 생성·발송은
  실행하지 않았다.
- **공통 서버/DB**: 패치 01~03의 소스 반영을 마쳤다. 실제 사용 환경의 DB 마이그레이션은
  실행하지 않았다. 실제 Gmail 원문의 외부 AI 전송과 F1 운영 저장 SQL 적용은 이번 범위에 없다.
- **제품 흐름**: 실제 Gmail 데이터의 앱 검색, Windows/Electron 전체 흐름과 실제 모델의
  토큰 단위 스트리밍은 아직 검사하지 않았다.

## 현재 브랜치와 승인 범위

- 현재 브랜치: `feat/F3-search`. 기존 `work`와 원격 `main`은 보존했다.
- 마지막 원격 확인: `origin/develop@4fef3fe`에 F1 공통 계약·분석 모듈 추가. 실제 제공자는
  미설정이며 F1 저장 SQL도 미적용임을 파일로 확인했다. 사용자 승인으로 F3에 로컬 통합했다.
- F1 추가는 신규 파일만으로 구성되어 F3의 공통 패치 대상과 겹치는 수정이 없다.
- 2026-11-19 사용자가 로컬 통합·커밋·Push·PR과 문제없을 경우 `develop` 병합까지 승인했다.
  통합 후 재검사에서 249개가 모두 통과했다. PR은 F3 기능·등록 범위이며 실제 AI 연결 완료를 뜻하지 않는다.
- `main` 병합은 승인 범위에 포함하지 않는다.

</details>

</details>

</details>
