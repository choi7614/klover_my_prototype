> **2026-11-25 제출 완료:** 코드 `23f63ef` 커밋·Push, [PR #48](https://github.com/choi7614/klover_my_prototype/pull/48) 제출. 작업 도구 없음.
> 사용자 develop 병합 승인 있음. 최종 검사·병합 상태는 PR #48을 따른다. 아래 승인 대기/미커밋 설명은 검토 당시 기록이다.

# F3 의미 검색 — 공통 연결·검증 결과

> 2026-11-25 · `integrate/F3-memory-search` · 작업 도구 없음(검사 완료·승인 대기)
> 미커밋·미Push, 신규 PR 없음. develop/main 변경 없음.

## 실제 기준과 변경

- `choi7614/klover_my_prototype`의 원격 전체 브랜치를 갱신했다. PR #47의 병합 커밋은
  `5b5d0c65149f19a1683e6895809ead2b1efdc25b`이며 최신 `origin/develop`과 같다.
- 이 커밋에는 의미 검색 어댑터·화면이 있지만 실행 조립과 공유 타입은 아직 패치로만 있었다.
  같은 기준에서 별도 통합 브랜치를 만들었다. 기존 작업·브랜치·패치 원본은 보존했다.
- 기능 구현의 설계·상한·기존 검사 이력은 [기능 인수인계](F3-memory-search-handoff.md)를 따른다.

| 변경 파일 | 목적 |
| --- | --- |
| `apps/server/app/cli/run_mail_api.py` | 패치 01 그대로 import와 `semantic=build_semantic_search(engine)` 두 줄 추가. 기존 인증·선택 AI·다른 기능 조립 유지 |
| `packages/api-types/openapi.json`, `packages/api-types/src/schema.d.ts` | `pnpm gen:api-types`로 재생성. 원래 표현·검색 경고·벡터 적용 범위 계약 추가. 패치 02와 두 파일 모두 바이트 단위 일치 |
| `apps/server/tests/test_run_mail_api_search.py` | 실제 실행 명령의 검색 조립·JSON/NDJSON·로컬 임베딩·실패 시 키워드 유지 회귀 검사 4개 |
| F3 명세·status·인수인계·현황판·패치 안내 | PR #47의 과거 미적용 기록과 이번 적용 상태 구분 |
| `docs/architecture/api.md`, `system.md`, `docs/dev/setup.md` | 의미 검색 미연결/미지원 안내를 이번 연결·제한에 맞춤 |

공유 타입은 직접 편집하지 않았다. DB 모델·마이그레이션·인덱스·잠금 파일·앱 기능 코드는 변경하지 않았다.
새 운영 DB나 벡터 재생성이 필요한 변경이 아니다. 기존 F1 저장 벡터를 읽는다.

## 안전하게 검사한 범위

- 새 Compose 프로젝트 `klover-f3-check-56d1f8`, 새 전용 DB 볼륨, 별도 loopback 포트,
  `klover_f3_test`/`klover_f5_test`와 검사별 임시 스키마를 사용했다. 기존 DB/볼륨에는 접속하지 않았다.
  검사 후 이번 전용 컨테이너만 정지했고 볼륨은 보존했다.
- DB 비밀번호·API 토큰은 테스트 전용으로 별도 비공개 임시 폴더에 두고 출력하지 않았다.
  Google 설정·질문 해석/답변·임베딩은 모두 합성 대역이다. 실제 Gmail·Ollama 모델·유료 AI를 호출하지 않았다.
- 실행 조립 검사는 운영의 live 필터까지 확인하기 위해 합성 제공자와 합성 벡터의 메타데이터만
  live로 맞췄다. 실제 제공자를 사용했다는 뜻이 아니다. 운영에서 테스트 모드를 허용하는 변경도 없다.
- 새 회귀 검사에서는 Claude가 설정된 상황에도 질의 임베딩 로더가 로컬 Ollama를 선택하는지 확인했다.
  임베딩 정상/미설정/호출 실패/모델 불일치를 각각 검사했다.
- 실제 pgvector 검색으로 키워드+벡터 결합·중복 제거·모델/차원/모드/분석 상태·사용자/계정/기간 격리,
  명시적 과거 가져오기·정확한 문서 번호·후보 상한을 확인했다. 질의 전후 합성 벡터 값이 같았다.
- 미설정·실패·모델 불일치 때는 키워드 결과를 유지하고 제한 안내를 반환했다.
  미인증 거부·원래 표현·한국 날짜 범위·근거 인용·JSON/NDJSON의 경고/적용 범위 일치도 확인했다.

## 검사 결과

| 검사 | 결과 |
| --- | --- |
| 서버 전체 pytest (위 분리 DB 지정) | **693 통과, 실패/오류/skip 0** (PR #47 기준 689 + 신규 4) |
| 서버 Ruff check / format check | 통과 |
| 데스크톱 Vitest | **215 통과** |
| 앱 lint·typecheck / 공유 타입 strict typecheck | 통과 |
| Electron 생산 빌드 | 통과 (앱 창 실행 검사는 아님) |
| F3 Chromium 합성 화면 | **2 통과**, 1440/1280/760px·근거 이동·메일/초안 연결 계약·빈 결과·오류 |
| 실제 서버→앱 HTTP/IPC 통로 | **1 통과**, 별도 일회성 합성 연결 검사 |
| 생성 타입과 패치 02 비교 | 두 파일 정확히 일치 |
| 변경 문서의 로컬 링크·diff 공백 검사 | 링크 82개 경로 확인·오류 없음, `git diff --check` 통과 |

앱 통로 검사는 실제 실행 명령으로 조립한 FastAPI를 별도 loopback 포트에 띄웠다.
분리 DB의 키워드+벡터 결과가 실제 NDJSON을 거쳐 앱 원본의 토큰 파일 읽기 → HTTP 클라이언트 →
`registerSearchIPC` → 화면 전달 이벤트로 이어지는지 확인했다. 검색 경고·적용 범위·원래 표현·
근거·최근 검색이 통과했고 화면 이벤트에 토큰이 없었다. Electron의 WebContents는 합성 대역이며
실제 앱 창 전체 흐름 검증과 구분한다. 이 검사용 스크립트·번들은 저장소 밖에만 만들었다.

검사 명령은 [공통 규칙](../../AGENTS.md)과 [설치 안내의 개발 검사](setup.md#12-개발자용-안전한-검사)를 따른다.
추가 실행:

```sh
# 반드시 새 분리 DB의 테스트 URL을 지정한 환경에서 실행한다. 비밀번호를 출력하지 않는다.
uv run --locked --directory apps/server pytest tests/test_run_mail_api_search.py tests/test_search_memory.py tests/test_search_semantic_repository.py
pnpm gen:api-types
pnpm --filter @klover/api-types typecheck
pnpm --filter desktop exec playwright test --config playwright.search.config.ts
```

이 환경의 JUnit·일회성 연결 검사 기록은 `/tmp/klover-f3-integration-h_t6__s4/`에 있다(커밋 대상 아님).
자동 검사에는 DB URL이 없으면 실제 DB 검사가 skip될 수 있으므로 이 로컬 분리 DB 결과와 구분한다.

## 미검증·실환경 확인

- 실제 모델의 약어/동의어 이해·검색 관련도·기본 유사도 0.5의 적합성·5초 성능은 미검증이다.
- 사용자의 기존 벡터와 현재 로컬 모델 태그·차원·모드의 호환성은 사용자 DB에 접근하지 않아 미검증이다.
  같은 태그라도 실제 모델 가중치가 바뀌었는지는 현재 F1에 digest가 없어 구분할 수 없다.
- 실제 Gmail·Claude·네이티브 Electron 창·사용자 Mac/Windows는 미검증이다.

승인 후 develop에 반영되면 [설치 안내](setup.md)의 기존 사용자 업데이트 절차로 코드를 받고
서버와 앱을 재시작한다. 이번 변경 자체에 추가 DB 초기화·마이그레이션·벡터 재생성은 없다.
기존 데이터에서 기억나는 주제와 기간으로 검색하고 원래 표현/확장어·결과 출처·근거·제한 안내를 확인한다.
Claude 선택 여부와 관계없이 질의 임베딩은 로컬이다. 벡터 누락/모델 불일치 안내가 나오면
기존 벡터를 삭제하지 말고 모델 태그·차원·일반 오류 코드만 확인한다. 실제 메일·키·토큰은 공유하지 않는다.

## 다음 승인·통합 순서

종료 전 원격을 다시 갱신했고 develop은 계속 `5b5d0c6`이었다.
`integrate/F3-memory-search` → develop의 기존 PR은 GitHub 조회 결과 없었다.

1. 이 결과를 검토한 뒤 이번 변경의 커밋·Push·develop 대상 PR 생성을 묶어서 승인받는다.
2. 같은 통합 브랜치의 기존 PR이 생겼으면 재사용한다. 제출 후 GitHub 검사·변경 범위를 다시 확인한다.
3. develop 병합은 별도 승인 후 진행한다. main 반영·기존 브랜치 삭제·Force Push·Sync fork는 하지 않는다.
4. 남은 개발은 조직/미회신/분류/첨부 필터·보낸 메일 열기이며 이번 범위에 추가하지 않았다.
   실제 모델 품질·지연·기존 벡터 호환성은 위 실환경 확인 항목으로 넘긴다.
