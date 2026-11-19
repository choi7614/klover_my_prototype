# F3 구현·검사 결과

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

- [1440px 화면](../../apps/desktop/artifacts/f3-search-1440.png)
- [1280px 화면](../../apps/desktop/artifacts/f3-search-1280.png)
- [좁은 화면](../../apps/desktop/artifacts/f3-search-760.png)
- [빈 결과](../../apps/desktop/artifacts/f3-search-empty.png)

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

- [서버 JUnit](../../artifacts/f3-server.xml)
- [승인 전 패치 JUnit](../../artifacts/f3-proposals.xml)
- [통합 후 F1/F3 전체 서버 JUnit](../../artifacts/f3-integrated-server.xml)

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
