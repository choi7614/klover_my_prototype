# F3 자연어 검색 — 구현 상태와 연결 요청

> 과거 전달·검사 기록을 포함한다. 2026-11-24 현재 API/IPC·F1 입력·F4 AI 통합은 PR #37까지 반영됐다. 미연결·패치 적용 요청은 당시 기록이며 현재 작업 상태는 [progress.md](progress.md)와 각 status, 실행은 [setup.md](setup.md)를 따른다. 기존 패치를 재적용하지 않는다.

> 기준: 2026-11-19 · 작업 브랜치 `feat/F3-search` · 시작 커밋 `0f68ad1`
> 상태: **공통 서버·저장소·생성 타입 등록, 실제 모델·F0 화면 연결 대기**

이 문서는 이번 F3 작업의 실제 범위와 연결 계약을 설명한다. 제품 수용 기준은
[F3 명세](../product/features/F3-search.md), 화면 기준은 [S07](../design/screens/S07-search.md)이다.
공통 AI·임베딩 계약은 F1 담당이며 `4fef3fe`를 통해 현재 브랜치에 반영했다.
실제 제공자는 미연결이고 F2 초안 기능도 없다.
기존 Google 계정·키·메일·수신 코드와 F0 진입점은 변경하지 않았다.

최종 원격 확인 중 `origin/develop`이 `4fef3fe`로 전진했고 F1 공통 AI 계약과 분석 모듈이
추가된 것을 실제 파일로 확인했고, 사용자 승인 후 F3 브랜치에 통합했다.
원격의 `app.ai.runtime.load_providers()`도 여전히 미설정 예외를 반환하며,
F1 벡터 저장 SQL은 미적용 제안이다. 따라서 F1 전체나 실제 모델·벡터 준비를 완료로 가정하지 않는다.
새 F1 커밋은 기존 공통 파일을 수정하지 않아 현재 F3 패치와 겹치는 수정은 없다.

## 구현된 범위

| 요청 단위 | 구현·검사 범위 | 연결 후 남은 확인 |
| --- | --- | --- |
| 질의 계약 | 구조화 조건·주제·확장어 검증, 한국 날짜 기준의 지난달/이번 주/어제 변환 | 실제 LLM의 한국어 해석 정확도 |
| 저장소 | 기간·상대 이름/주소·받은/보낸·키워드, 사용자/계정/사용 시작 시점 격리 | 실제 Gmail 데이터에 대한 제품 연결 |
| 결과 결합 | 키워드/벡터 포트 결과의 중복 제거·RRF 순위·전체/일부 일치 구분 | 실제 임베딩·pgvector 어댑터 |
| 답변 | 결과 메일의 원문 발췌와 유효한 `mail_id`만 인용, 0건·잘못된 인용·모델 실패 구분 | F1 모델 어댑터와 자유 요약 품질 |
| 재검색 | 서버가 보관한 해석 재사용, 명시적 조건 수정/삭제, 최근 검색 사용자·계정 격리 | F0 main의 제한된 IPC 연결 |
| 화면 | S07 조건 칩·필터·결과·근거·로딩·빈 상태·오류, 오래된 응답 무시 | 실제 앱 라우트·메일 상세·F2 초안 연결 |

운영용 가짜 해석기·벡터 검색·답변 생성기는 추가하지 않았다. 합성 구현은
`apps/server/tests/`와 `apps/desktop/tests/f3/`에만 있다. 실제 Gmail 원문이나
계정 정보를 테스트에 사용하거나 외부 AI에 보내지 않았다.

## 현재 저장 구조에서 지원하는 조건

- 기간: 한국 날짜의 `start` 포함, `end_before` 미포함. DB에는 시간대가 있는 시각으로 전달한다.
- 상대 이름: 받은 메일은 `from_name`, 보낸 메일은 `to[].name`의 대소문자 무시 부분 일치.
- 상대 주소: 받은 메일은 `from_addr`, 보낸 메일은 `to[].addr`의 대소문자 무시 전체 일치.
- 대상: `received`, `sent` 또는 둘 다. 보낸 메일 수신·저장 파이프라인은 아직 없으므로
  보낸 메일 검색은 합성 행으로 검사했다.
- 키워드: 제목·일반 텍스트 본문의 부분 일치. 확장어도 키워드로 표시한다.
  `%`, `_`, 역슬래시는 문자 그대로 검색하며 SQL 인수로 전달한다.
- 받은편지함·보낸편지함·보관함에 저장된 메일만 읽고 임시보관·스팸·휴지통은 제외한다.

조직, 회신 필요/회신 여부, 카테고리, 첨부파일 여부는 아직 저장하지 않는다.
해당 조건을 요청하면 `unsupported_filter`로 알린다. 값이 `false`여도 무시하지 않는다.
화면의 관련 필터는 사용할 수 없다는 안내를 표시한다. 분석 상태 `pending`을
회신 여부나 분류 값으로 대신 쓰지 않는다.

따라서 원래 명세의 **“영업기획팀 + 아직 회신 안 함” 예시 질문은 아직 완성되지 않았다.**
지원하는 조건의 합성 질문에서 정답 메일 3건을 찾는 검사와 구분한다.

## 질의·날짜 계약

`app/schemas/search.py`와 `app/services/search_rules.py`가 검증 기준이다.

```json
{
  "filters": {
    "period": {"relative": "last_month"},
    "counterparty": {"kind": "address", "value": "budget@example.invalid"},
    "directions": ["received", "sent"]
  },
  "topic": "예산",
  "expansions": ["예산 재배정", "예산 전용"]
}
```

- 모델 출력의 상대 기간은 `last_month`, `this_week`, `yesterday` 중 하나다.
  명시적 기간은 `{start, end_before}` 날짜다.
- `SearchService(clock=...)`에 날짜 또는 시간대가 있는 시각을 주입한다.
  시각은 `Asia/Seoul` 날짜로 바꾼다. 시간대 없는 시각은 거부한다.
- 이번 주는 월요일부터 다음 월요일 직전이다. 지난달은 전월 첫날부터 이번 달 첫날 직전이다.
- 빈 해석, 알 수 없는 필드, 뒤집힌 기간, 중복 대상, 주제 없는 확장어는 성공으로 처리하지 않는다.
- 날짜 변환 검사는 LLM이 한국어를 실제로 이해했다는 의미가 아니다.

## 검색·재검색·최근 검색 API 계약

`app/api/search.py`의 라우터를 공통 앱에 등록했다. 기본 `app.main:app`은 연결 계정·제공자
미설정 상태에서 검색 성공을 반환하지 않는다. `run_mail_api`에도 F3 저장소를 조립했으며
실제 해석 포트가 연결되기 전 새 자연어 검색은 503으로 알린다.

```json
POST /search
{
  "query": "지난달 예산 관련 메일",
  "search_id": "이전 응답의 32자리 ID (재검색 때만)",
  "overrides": {"period": null, "topic": "문서-123"}
}
```

- 최초 검색은 `query`와 선택적 `overrides`를 받는다. `user_id`, `account_id`, `parsed`를
  클라이언트에서 받지 않는다. 기존 Bearer 인증 저장소의 `session()`으로 소유 계정을 확인한다.
- 재검색은 보관된 해석을 `search_id`로 찾고 같은 질문인지 확인한다. 다른 사용자나
  다른 계정의 ID는 404다. 임의의 해석 결과를 요청에 넣어 우회할 수 없다.
- 생략한 조건은 유지하고, `null`은 삭제한다. 삭제/변경한 주제의 확장어는 함께 제거한다.
  여러 조건을 빠르게 바꿔도 화면은 누적 `overrides`를 전송한다.
- 재검색의 상대 날짜 기준은 최초 해석 날짜를 유지한다. 최근 검색을 클릭하면 질문을
  새로 검색하므로 클릭한 날의 한국 날짜로 다시 해석한다.
- `GET /search/recent`는 해당 사용자·계정의 최근 질문 3개를 반환한다. 같은 질문은 한 번만
  표시한다. 조회 인수로 소유자나 계정을 바꿀 수 없다.
- 최근 검색은 F3 전용 `search_runs` 테이블에 저장한다. 검색 코드가 테이블을 자동 생성하지 않는다.

JSON 응답은 `SearchResponse`다. 결과에는 `mail_id`, 번호, 점수, 이유, 인용 부분,
일치 단어, 미충족 조건, 출처 종류, 제목·발신자·날짜·대상이 있다.
`semantic_enabled`는 이번 질의에서 실제 벡터 포트를 사용했는지 나타낸다.

`Accept: application/x-ndjson` 요청은 아래 순서로 한 줄씩 전달한다.

1. `parsed`: 해석 결과, `search_id`, 한국 기준 날짜
2. `results`: 전체 조건 만족 목록, 일부 만족 목록, 의미 검색 사용 여부, 결과 제한 여부
3. `answer` 또는 `answer_error`: 검증된 발췌 답변 또는 답변 실패

스트림 도중 실패하면 `error` 프레임을 보낸다. 이미 시작된 스트림의 HTTP 상태는 200일 수
있으므로 소비자는 프레임의 오류도 확인해야 한다. JSON 요청은 해석 미연결 503,
잘못된 입력/미지원 조건 422, 다른 소유자의 이전 검색 404로 처리한다.

인증·Host·loopback·Origin 거부 규칙은 기존 메일 API의 `authorize`를 재사용한다.
CORS를 추가하지 않았다. 개인 응답에는 `Cache-Control: no-store`를 붙이며, 오류에
질문·메일·모델 예외 상세·토큰을 포함하지 않는다.

## 저장소·순위·근거 규칙

`SQLSearchRepository`는 모든 조회와 벡터 후보의 원문 재조회에 다음 제한을 적용한다.

- 메일의 `user_id`와 `account_id`가 인증된 범위와 같아야 한다.
- 메일 계정 행의 실제 소유자도 같아야 한다.
- `received_at`은 전달된 시작 시점과 DB 계정 행의 시작 시점 모두 이후여야 한다.
  오래된 범위 객체로 조회 시작일을 넓힐 수 없다.

기간·상대·대상은 수정 가능한 검색 조건이다. 사용자·계정·사용 시작일은 일부 일치 검색에서도
완화하지 않는다. 주제가 있으면 키워드 또는 실제 벡터 후보로 관련성을 먼저 확인한다.
구조화 조건이 모두 맞으면 전체 일치, 일부가 틀리면 미충족 조건을 표시한 일부 일치다.

각 검색 출처의 순위를 `1 / (60 + 순위)`로 합친다. 같은 메일의 여러 벡터 청크는 한 번만
반영한다. 범위 밖 ID와 중복은 순위 계산 전에 제거한다. 같은 점수는 최신 시각·메일 ID로
안정적으로 정렬한다. 최종 번호는 전체 목록부터 일부 목록 순서로 한 번만 부여한다.

기본 후보는 키워드 전체/일부 각각 최대 100건, 최종 표시는 각각 20건이다. 벡터 포트에는
40건까지 요청한다. 제한을 넘으면 `truncated`로 알리며 전체 검색 건수라고 주장하지 않는다.
현재 키워드 검색은 기존 열의 부분 일치를 사용하며 실데이터 규모의 인덱스·성능 검증은 남아 있다.

답변 포트에는 **최종 전체 일치 메일만** 전달한다. 일부 일치와 범위 밖 메일은 제외한다.
현재 답변 계약은 원문 발췌형이며 각 항목의 `mail_id`가 결과에 있고 `quote`가 그 메일의
제목 또는 본문에 실제로 포함되는지 검사한다. 출처 번호는 서버가 결과 번호로 만든다.
임의 생성 문장을 검증된 요약으로 반환하지 않는다.

- 전체 결과 0건: 모델을 부르지 않고 “찾은 메일이 없습니다”, 빈 출처를 반환한다.
- 답변 포트 없음: 결과 목록과 `answer_unavailable`을 반환한다.
- 모델 호출 실패/시간 초과: 결과 목록과 `answer_failed`를 반환한다.
- 잘못된 ID·원문에 없는 인용문·잘못된 출력 형식: 결과 목록과 `invalid_answer`를 반환한다.

## F0에 전달할 연결 요청

F0의 공통 app/router·main/preload·메일함은 이번 작업에서 수정하지 않았다.

1. 화면 슬롯에 `SearchPage`를 연결한다. `initialQuery`와 `autoSearch`로 상단 검색창 진입을
   처리한다. `identityKey`는 인증된 `user_id:account_id`처럼 계정마다 달라야 한다.
   계정 변경 시 결과·최근 검색·진행 중 요청 상태를 새로 만든다.
2. `SearchClient.search(request, signal)`의 비동기 프레임과 `recent(signal)`을 제한된 IPC로
   제공한다. 요청 ID와 취소를 전달하고 Renderer에는 API 토큰을 전달하지 않는다.
3. Node 전용 어댑터는 `apps/desktop/src/search/search-http-client.ts`의
   `createSearchHTTPClient(baseURL, token)`이다. 허용된 로컬 HTTP 주소만 받고,
   리다이렉트를 거부하며 UTF-8 스트림과 응답 크기를 검사한다. F0 main에서만 조립한다.
4. `navigation.openMail({mail_id, direction, source:'F3'})`를 메일 선택에 연결한다.
   현재 공통 상세 API는 받은편지함만 읽는다. 보낸/보관 메일 상세 열기가 필요하면
   공통 서버 담당과 별도 계약을 확장해야 한다.
5. `navigation.backToInbox()`와 `navigation.openDraft({mail_id, source:'F3'})`를 연결한다.
   콜백을 주지 않으면 메일/초안 버튼은 비활성이다. 콜백 호출 검사는 실제 창을 연 검사와 구분한다.

화면은 응답 단계 순서를 확인한다. `AbortController`로 이전 요청을 취소하고 요청 번호도
비교하므로 취소를 무시한 오래된 결과·오류가 새 화면을 덮어쓰지 않는다. 계정 변경도 같은
규칙을 적용한다. 근거 번호는 해당 카드로 이동해 1초 강조하고, 제목은 F0 메일 열기 계약을 호출한다.

## F1에 전달할 연결 요청

공통 SDK·AI 프롬프트·임베딩 모델·벡터 저장 구조는 이번 F3 작업에서 만들지 않았다.
아래 포트는 `app/services/search_ports.py`에 정의했다.

원격 `4fef3fe`에서 확인한 공통 계약은 `TextGeneration.generate(GenerationRequest)`와
`TextEmbedding.embed(EmbeddingRequest)`다. 공통 계약의 로컬 통합을 마쳤고,
실제 제공자가 준비되면 이 경계로 F3 포트를 조립해야 한다.
생성 요청은 `purpose='search'`와 F3 출력 스키마를, 질의 임베딩은
`purpose='query'`를 사용한다. 모델의 provider/model/mode와 임베딩 차원을 함께 확인한다.
공통 SDK나 제공자 구현을 F3에서 복제하지 않는다.

- `QueryParser.parse(query, reference_date) -> ParseOutput`: 질문만 받는다. 상대 날짜의 기준은
  전달된 한국 날짜다. 조직·미회신 조건을 해석에서 생략하거나 이름 조건으로 바꾸지 않는다.
  실패하면 예외 또는 유효하지 않은 출력으로 명시하고 가짜 해석을 성공 반환하지 않는다.
- `SemanticSearch.ready`: 실제 임베딩과 저장 벡터의 모델/버전/차원이 맞고 검색 기반이 준비된
  경우에만 참이어야 한다. 기본값은 포트 없음이다.
- `SemanticSearch.search(scope, parsed, limit) -> RankedHit[]`: 같은 소유 범위와 조건으로 검색하고
  중복 가능한 청크 결과를 메일 ID와 유한한 0~1 점수로 반환한다. F3는 ID를 다시 격리 조회한다.
- `SearchAnswerer.answer(query, parsed, mails) -> AnswerDraft`: 수정된 유효 조건과 최종 결과만 받는다.
  최대 8개의 `{mail_id, quote}`를 고른다. 자유 요약으로 확장하려면 근거 보장 계약과 검사를
  별도로 추가해야 한다.

F1 메타데이터가 들어오면 조직·회신·분류·첨부 조건의 실제 열/상태와 조회 계약을 전달해 주어야
한다. 새 정보가 있다는 이유로 F3가 자동으로 해당 조건을 지원하도록 만들지 않았다.
실제 Gmail 내용을 외부 AI에 보내는 연결은 이번 승인 범위에 없다.

원격 F1 제안의 저장 이름은 `f1_mail_analysis`, `f1_mail_chunks`다. 향후 의미 검색은
사용자/계정/사용 시작일에 더해 `embedding_provider`, `embedding_model`,
`embedding_dimensions`, `embedding_mode`도 일치시켜야 한다. 운영에서는 test 벡터를
의미 검색 성공으로 사용하지 않는다. 해당 SQL을 실제 DB에 적용하거나 실제 임베딩을
만든 것은 이번 F3 작업에 포함하지 않았다. `entities.orgs`만으로 상대 부서나 내가 회신했는지를
확정할 수는 없으므로 별도 메타데이터 계약이 필요하다.

## F2와 공통 서버에 전달할 연결 요청

- F2: `openDraft({mail_id, source:'F3'})`를 받아 S06을 연다. 서버에서 해당 메일의 소유권을
  다시 확인한다. 현재는 창 열기 요청만 검사했으며 초안 생성·발송은 실행하지 않았다.
- 공통 서버: F3 라우터를 등록하고 기존 로컬 인증 계정에서 검색 범위를 구성한다.
  최근 검색 테이블은 현재 `0002` 이후의 새 이력으로만 추가한다. 다른 기능의 새 이력이
  생겼다면 revision/부모를 다시 확인하고 기존 이력을 덮어쓰지 않는다.
- 공유 타입: 서버 등록을 반영한 실제 OpenAPI에서 재생성했고 `packages/api-types`에 반영했다.
- 공통 DB 모델, 기존 인증·메일 API, Gmail 수신/연결/키, 잠금 파일은 수정하지 않았다.

## 적용 전 패치

승인 전 검토·검사를 마친 패치는 [`integration/F3-search`](../../integration/F3-search/README.md)에
적용 기록으로 보관했다. 사용자 승인 후 아래 변경을 F3 브랜치 소스에 반영했다.

1. `01-storage.patch`: F3 최근 검색 테이블, 별도 메타데이터 등록, 공통 모델 일치 검사 보완
2. `02-server-registration.patch`: 공통 앱의 라우터 등록과 로컬 실행 앱의 저장소 조립
3. `03-shared-api-types.patch`: 위 API의 실제 OpenAPI·생성 TypeScript 타입

02 반영 후에도 AI 포트는 기본 미연결이다. 새 자연어 검색은 503으로 알리고 가짜 모델을
조립하지 않는다. F0 화면 연결도 자동으로 생기지 않는다. 운영 DB에는 아무 패치도 적용하지 않았다.

## 확인 방법

저장소의 기존 설치 방법대로 `corepack pnpm install --frozen-lockfile`, 서버의
`uv sync --locked`를 먼저 수행한다. 새 패키지나 공통 잠금 파일 변경은 필요하지 않다.

합성 화면만 확인하려면 저장소 루트에서 실행한다.

```bash
corepack pnpm --filter desktop exec vite --config vite.search.config.ts
```

`http://127.0.0.1:5183`에서 검색을 누른다. 처음 질문은 합성 메일 3건을 표시한다.
`빈 결과`, `해석 오류`, `답변 오류`로 상태를 확인할 수 있다. 위쪽의 검사 표시가 있는
전용 화면이며 실제 Gmail/API 연결 상태와 무관하다.

```bash
corepack pnpm --filter desktop typecheck
corepack pnpm --filter desktop lint
corepack pnpm --filter desktop test
corepack pnpm --filter desktop exec playwright test --config playwright.search.config.ts
corepack pnpm --filter desktop exec vite build --config vite.search.config.ts
```

별도 Chromium을 쓰는 환경에서는 기존 방식대로 `PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH`를
지정한다. 독립 빌드 산출물은 저장소 루트 `artifacts/f3-preview`에 쓴다.

서버 검사는 `apps/server`에서 실행한다. PostgreSQL 검사는 기존 테스트 계약의
`KLOVER_TEST_DATABASE_URL`과 `KLOVER_F1_TEST_DATABASE_URL`에 **합성 데이터용 별도 테스트 DB**를
지정해야 한다. F1 검사는 DB 이름이 `_test`로 끝나고 pgvector를 사용할 수 있어야 한다.
없으면 해당 DB 검사는 건너뛰므로 전체 통과와 구분한다. `.env`나 사용 중인 메일 DB를 사용하지 않는다.

```bash
uv run pytest -q
uv run ruff check app/api/search.py app/db/repositories/search*.py app/schemas/search.py app/services/search*.py tests/*search*.py tests/f3_proposal_checks.py
```

다음은 통합 전 독립 복사본에서만 사용하는 승인 전 검사 명령이다.
현재처럼 적용을 마친 소스에서는 생성기가 보관된 패치를 덮어쓰지 않고 중단한다.

```bash
# 저장소 루트: 공통 파일을 바꾸지 않고 제안 패치 생성
apps/server/.venv/bin/python scripts/f3/prepare_integration.py
# apps/server: 승인 전 상태에서만 명시적으로 실행
uv run pytest -q tests/f3_proposal_checks.py
```

승인 전 검사는 기본 pytest 수집에서 분리했다. 공통 파일이 실제로 통합된 이후에는
일반 서버 검사·생성 타입 검사·모델 일치 검사로 새 상태를 확인한다.

## 제품 수용 기준의 남은 일

- 상대 날짜 변환, 지원 조건의 합성 정답 3건, 칩 수정/삭제 재검색, 이유 표시,
  근거 번호·결과 번호 일치, 0건 처리, 오류·오래된 응답 방지는 독립 검사했다.
- 원래 예시의 조직·미회신 조건과 실제 의미 검색은 F1 연결 후 확인해야 한다.
- 실제 자연어 모델의 검색 정확도, 자유 요약의 근거 품질, 첫 결과 5초 성능은 미측정이다.
- F0 실제 메일 열기, F2 실제 초안 창, Windows/Electron 전체 흐름은 미연결·미검사다.
- 결과·근거를 한 단계씩 전달하는 스트림은 검사했다. 실제 모델의 토큰 단위 답변 스트리밍은
  미구현이며, 현재는 검증을 끝낸 답변을 한 프레임으로 전달한다.
- 2026-11-19 사용자가 F3 로컬 통합·커밋·Push·PR과 문제없을 경우 `develop` 병합을 승인했다.
  `origin/develop@4fef3fe`를 F3 브랜치에 통합하고 공통 패치를 적용했다.
  최종 검사와 반영 결과는 [구현·검사 보고](F3-search-status.md)를 따른다.
- F1의 운영 DB SQL 적용과 실제 메일의 외부 AI 전송은 이 승인 범위에 포함하지 않는다.
  `main` 병합은 별도 승인 대상이다.
