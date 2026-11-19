# F3 공통 패치 — 적용 전

> 2026-11-19 `feat/F3-search` (기준 develop `420078e`). 이 폴더는 검토용이며, 적용은 **통합 채팅**에서 한다.

| 패치 | 대상(공통 영역) | 내용 |
| --- | --- | --- |
| 01-search-ai-wiring | `apps/server/app/cli/run_mail_api.py` | `load_providers()`로 받은 공통 `TextGeneration`을 `SharedQueryParser`·`SharedSearchAnswerer`로 감싸 `SearchService`에 주입 |

## 동작

- 실제 제공자가 있으면(F1의 `app/ai/runtime.py`가 `.env`로 Claude API 또는 로컬 Qwen(Ollama)을 고름) 검색 질문 해석·답변이 켜진다.
- 제공자가 없거나 `identity.mode`가 `live`가 아니면 `ProvidersNotConfigured`를 잡아 해석기·답변기를 비워 둔다.
  이때 검색은 지금처럼 `503 parser_unavailable`로 안내한다(가짜 결과로 대체하지 않음).
- F3 코드는 제공자를 직접 고르지 않는다. 쓰는 이름: `TextGeneration`, `GenerationRequest`,
  `ProviderCallError`, `ProvidersNotConfigured`, `load_providers()`.

## 적용 순서·주의

1. F1 채팅의 `app/ai/runtime.py` 제공자 선택 변경이 develop에 들어간 뒤 적용하는 것을 권장한다
   (먼저 적용해도 제공자 없음으로 503이 유지되어 동작은 지금과 같다).
2. `load_providers()`의 반환 형태(`(TextGeneration, TextEmbedding)`)가 바뀌면 `search_ai()`를 맞춘다.
3. 저장소 루트에서 `git apply --check patches/F3/01-search-ai-wiring.patch` 후 적용하고,
   `cd apps/server && uv run ruff check . && uv run pytest`를 실행한다.

검사: 기능 브랜치에서 패치를 임시 적용해 `ruff check` 통과, `search_ai()`가 현재 `(None, None)`을 돌려줌을 확인했고,
원래 파일로 되돌린 뒤 `git apply --check` 통과를 확인했다.
