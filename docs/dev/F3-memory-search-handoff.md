> **2026-11-25 제출 갱신:** 사용자가 이번 변경의 커밋·Push·PR 생성과 검사 통과 후 develop 병합을 승인했다.
> 제출을 진행하며 최종 반영 상태는 `integrate/F3-memory-search` → develop PR을 따른다. 아래 승인 대기/미커밋 설명은 검토 당시 기록이다.

> **최신 상태 (2026-11-25):** PR #47이 `develop 5b5d0c6`에 병합됐음을 실제 커밋으로 확인했다.
> 공통 패치 01~02는 별도 `integrate/F3-memory-search` 작업 트리에 적용·검사 완료, 커밋·Push·PR·develop 반영 승인 대기다.
> 아래는 PR #47 기능 제출 당시의 기록이며, 최신 검사·확인 절차는 [공통 통합 기록](F3-memory-search-integration.md)을 따른다.

<details>
<summary>PR #47 기능 구현·제출 당시 인수인계 (보존 기록)</summary>

> 2026-11-25 제출 갱신: 사용자 승인으로 구현 `63c25df` 커밋·Push, PR #47 제출 완료. 미커밋 작업 없음(이 문서 갱신도 제출). develop 병합 승인 있음; 최종 병합 상태는 PR #47을 따른다. 공통 패치 01~02는 미적용이며 운영 의미 검색은 미통합. 아래 승인 대기/미커밋 설명은 제출 전 기록이다.

# F3 기억이 불완전해도 찾는 검색 — 인수인계

> 2026-11-25 · 작업 도구 Codex · 검사 완료/승인 대기 · 공통 조립 미통합

## 브랜치·보존 상태

- 작업 폴더 `/workspace/f3-memory-search`, 브랜치 `feat/F3-memory-search`.
- 기준/현재 HEAD `7b48c68f8cf507abce3278b9edbd6a61671e53a1` (`origin/develop`, PR #46 병합).
- 원격 기존 `feat/F3-search@1478e70`은 develop의 조상이다. 기존 브랜치를 보존하고 별도 신규 F3 브랜치를 최신 develop에서 만들었다.
- 원본 `/workspace/klover_my_prototype`는 `work@9575f47`, 변경사항 없음. 다른 worktree 없음.
- 이번 변경 전부 미커밋·미Push. 신규 PR 없음. develop/main 변경 없음.
- 실행 환경 연결 실패가 복구된 뒤 작업했다. Mac 여부는 Cloud 명령 실행과 관계없다.

## 구현

1. 기존 선택 AI의 한 번의 질문 해석에서 핵심 주제·원래 표현·확장어·조건을 받는다. HFT 전용 운영 분기/사전은 없다. 원래 표현 최대 4개, 확장어 최대 8개/각 200자. 질문 밖 원래 표현·너무 넓은 확장어·모르는 발신자 조건은 검증 실패로 기존 1회 형식 보정을 사용한다.
2. 한국 기준 날짜를 주입한다. 지난달/이번 주/어제 규칙을 유지하고 월 초(1~10일)/중순(11~20일)/말(21~말일)을 서버에서 확정한다. 연도 없는 월은 기준 월 이하의 가장 최근 연도, 명시 연도는 그대로 쓴다. 인식한 단일 월 구간을 모델이 임의로 넓히면 거부한다.
3. 기간을 키워드·벡터 모두에서 적용한다. 기간 밖 메일을 일부 일치에 섞던 이전 동작도 제거했다. 발신자/대상 일부 일치는 기존 구분을 유지한다. 문서 번호·금액의 정확한 토큰은 벡터나 확장어로 희석하지 않는다.
4. F1의 `f1_mail_chunks`를 읽는 pgvector 검색을 추가했다. 원본 계정·사용자·DB/요청 시작 시점과 명시적 과거 가져오기 제한을 재사용한다. F1 분석 완료·LLM/임베딩 모드·제공자·모델·차원을 확인하며 호환되지 않는 행은 제외한다.
5. 기존 RRF 결합·메일별 중복 제거·근거 검증을 유지한다. 의미 검색의 근거 청크도 실제 원문에 있는 경우만 화면 발췌에 쓴다. 답변 입력은 상위 8건, 각 본문 4,000자/제목 500자/발신자 이름 200자로 제한하고 인용은 정식 원문으로 재검증한다. 근거가 부족하면 빈 인용으로 답변을 보류할 수 있다.
6. 의미 검색 실패/시간 초과는 키워드 결과와 별도 안내를 반환한다. 임베딩 누락·호환 불일치·후보 상한과 적용 건수를 표시한다. 취소는 삼키지 않는다. 최근 검색·조건 삭제/수정·계정 변경·늦은 응답 차단은 유지한다.
7. S07에 원래 검색어·자동 확장어·실제 한국 날짜 범위·저장된 메일만 검색한다는 안내를 추가했다. 의미 검색 제한과 답변 실패 때도 실제 AI 안내를 표시한다. 추가 확인창은 없다.

선택 AI는 기존 `SelectedGeneration`을 그대로 재사용한다. 형식 보정과 별개인 Claude→로컬 1회 전환도 공통 구현만 사용하며, 전환 후 답변까지 로컬을 유지한다. 외부 전송 동의·자료/비용 안내·로컬 전용 차단을 우회하지 않는다. 새 로그를 추가하지 않았다.

## 벡터 구조와 상한

0007 모델/마이그레이션과 분리 DB의 실제 인덱스를 대조했다. 벡터는 차원 미고정이며 `vector_dims` 검사와 사용자/계정/기간 B-tree 인덱스가 있다. HNSW/IVFFlat 인덱스는 없다.

DB/인덱스 변경 없이 범위 내 최신 청크 **최대 2,000개**를 코사인 거리로 비교한다. 초과하면 누락 가능성을 화면에 알린다. 기본 최소 유사도는 0.5이며 실제 모델로 교정하지 않은 기준이다. 조회는 일관된 읽기 전용 트랜잭션이고 각 DB 문장은 2초, 질문 임베딩은 10초 상한이다. 벡터 결과는 기본 40건, 최종 전체/일부 결과는 각각 20건이다. 기존 모델 단계 대기 상한을 유지한다.

모델 태그·차원이 같아도 실제 모델 파일이 바뀌었는지는 현 F1 저장 항목에 digest가 없어 확인 불가다. 이를 해결하려고 DB나 기존 벡터를 임의 변경하지 않았다.

## 변경 파일

| 경로 | 목적 |
| --- | --- |
| `apps/server/app/schemas/search.py` | 월 구간·원래 표현·검색 제한/적용 범위 계약 |
| `apps/server/app/services/search_rules.py` | 한국 날짜·원래 표현·정확한 번호/금액 규칙 |
| `apps/server/app/ai/search_adapter.py`, `ai/prompts/search_parse.md`, `search_answer.md` | 선택 AI의 일반 확장·원문 검증·답변 보류 |
| `apps/server/app/ai/search_semantic.py` | F1 로컬 임베딩 포트·검증 재사용 |
| `apps/server/app/db/repositories/search.py`, `search_semantic.py` | 기간/정확한 토큰·격리된 읽기 전용 벡터 조회 |
| `apps/server/app/services/search.py`, `search_ports.py` | 결합·실패 시 키워드 유지·근거/적용 범위 |
| `apps/server/tests/test_search_memory.py`, `test_search_semantic_repository.py` | 신규 합성 계약·모델 대역·실제 pgvector/HTTP 검사 |
| `apps/server/tests/test_search_service.py`, `test_search_repository.py` | 기간 밖 후보 제외·의미 실패 정책 반영 |
| `apps/desktop/src/renderer/features/search/contracts.ts`, `use-search.ts` | 새 응답 검사·실제 AI/검색 제한 상태 |
| `apps/desktop/src/renderer/features/search/search-page.tsx`, `search.css`, `search-page.test.tsx` | S07 안내·합성 화면 검사 |
| `apps/desktop/tests/f3/synthetic-client.ts` | 기간 밖 일부 일치를 만들던 대역을 기간 내 대상 불일치로 수정 |
| `patches/F3/memory-search/01-server-wiring.patch`, `02-generated-types.patch`, `README.md` | 공통 적용 전 변경안 |
| `patches/F3/README.md`, F3 명세·S07 정의·status·현황판·이 문서 | 현재/과거 기록과 통합 요청 구분 |

공통 서버 조립·main/preload·라우터·DB 모델/이력·공유 타입·잠금 파일의 원본은 수정하지 않았다. 기존 계정·키·메일·수신·검색 기록·분석 결과는 변경하지 않았다.

## 검사

- 실제 Gmail·사용자 DB·유료 Claude·Ollama 모델에는 접근하지 않았다. 로컬에서 새 컨테이너와 `klover_test`/`klover_f5_test`, 일회용 스키마만 사용했다.
- 서버 최종 전체 검사: **689 통과, 실패·오류·skip 0**. 신규 검색 검사 34개(일반 계약/가짜 AI 27, 실제 pgvector/HTTP 7) 통과. 최종 JUnit은 `/tmp/f3-memory-server.xml`(커밋 대상 아님).
- 앱 전체 **215 통과**, TypeScript·ESLint 통과. Electron 생산 빌드 통과(앱 실행 검사가 아님).
- 합성 Chromium **2 통과**, 1440/1280/760px 배치·근거 이동·메일/초안 연결 계약·오류/빈 상태 확인. 추가 화면 단위 검사로 확장어/기간/의미 실패 표시를 확인했다.
- Ruff check/format, `git diff --check`, 두 패치의 `git apply --check` 통과.
- 중간 전체 실행은 F5 전용 DB 미지정으로 41개 skip, 이후 잘못된 DB 이름으로 41개 setup 오류가 있었다. 전용 `klover_f5_test`를 새로 만들어 수정한 최종 결과를 사용한다. 제품 코드를 이 문제 때문에 바꾸지 않았다.

재현: `apps/server`의 `uv run --locked pytest -q`. `KLOVER_TEST_DATABASE_URL`, `KLOVER_F1_TEST_DATABASE_URL`은 새 `klover_test`, `KLOVER_F5_TEST_DATABASE_URL`은 새 `klover_f5_test`를 지정해야 한다. 실제 사용자 DB를 지정하지 않는다.
앱: `pnpm --filter desktop typecheck`, `lint`, `test`, `build`.
브라우저: `PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH=/usr/bin/chromium pnpm --filter desktop exec playwright test --config playwright.search.config.ts`.

**대역의 정답 검색/실제 SQL·HTTP 검사를 실제 모델의 이해력·확장 정확도·의미 관련도·5초 성능으로 보고하지 않는다.** 모호한 약어의 문맥 판별·과잉 확장/발신자 추측 방지의 실제 모델 품질·네이티브 Electron 전체 흐름은 미검증이다.

## 공통 패치와 연결 요청

- `patches/F3/memory-search/01-server-wiring.patch`: 공통 CLI 조립에 `build_semantic_search(engine)` 주입. **미적용**.
- `patches/F3/memory-search/02-generated-types.patch`: 임시 경로에 실제 OpenAPI/TS를 생성해 만든 공유 타입 변경안. **미적용**. 통합 시 최신 원본에서 재생성한다.
- DB 마이그레이션 패치: **없음**. 기존 벡터의 삭제·재생성도 없음.
- F1: 기존 API/임베딩 저장을 그대로 재사용. 실제 로컬 모델 태그/차원 설정과 저장된 벡터의 일치, 실제 모델 품질·유사도 기준 보정이 남는다. 자동 재분석 요청 없음.
- F0: 기존 검색 진입·IPC·받은 메일 열기를 유지한다. 추가 main/preload/라우터 변경 요청 없음. 보낸 메일 열기 미구현은 기존 제한이다.
- F2: 기존 답장 초안 열기 계약 유지. 관련 메일 자동 검색·문체 학습·발송은 추가하지 않았다.
- 공통 서버: 두 패치 적용 후 전용 DB·새 타입으로 회귀 검사하고 운영에서 의미 검색이 실제 주입되는지 확인해야 한다. 적용 전 앱의 새 안내/키워드 개선은 가능하나 운영 벡터 경로는 미통합이다.

## 다음 할 일과 승인

1. 이 변경·검사 보고 후 커밋·Push·PR 생성을 묶어서 승인받는다. 현재는 승인 전이라 실행하지 않았다.
2. 통합 채팅에서 최신 develop과 공통 패치를 대조·적용·재검사한다. 기능 브랜치의 기존 이력과 다른 작업 폴더는 보존한다.
3. 승인된 범위에서 PR을 제출하고 CI 결과를 확인한다. develop 병합은 명시 승인 범위에서만, main은 별도 승인이다.
4. 이후 사용자 실환경에서 로컬/Claude의 실제 품질·지연·벡터 모델 호환성을 확인한다. 이번 작업 중 실제 메일의 외부 전송은 하지 않는다.

</details>
