# F3 기억 검색 — 적용 전 공통 변경안

기준: `origin/develop 7b48c68` (PR #46), 2026-11-25.
기능 작업: `feat/F3-memory-search`, `/workspace/f3-memory-search`.
**두 패치 모두 미적용이다. 운영 의미 검색 연결은 아직 미통합이다.**
루트의 과거 `01-search-ai-wiring.patch`는 이미 반영된 기록이므로 재적용하지 않는다.

| 순서 | 파일 | 목적 |
| --- | --- | --- |
| 1 | `01-server-wiring.patch` | 공통 `run_mail_api.py`가 로컬 임베딩 기반 F3 의미 검색을 조립하도록 한다. `SelectedGeneration`·인증·기존 기능 조립은 유지한다. |
| 2 | `02-generated-types.patch` | 실제 새 OpenAPI에서 생성한 `original_terms`·검색 제한 안내·벡터 적용 범위 계약. JSON/TS를 직접 편집하지 않았다. |

통합 채팅에서 최신 develop의 변경을 대조하고 적용·재검사한다. 이번 브랜치의 공통 원본 파일은 수정하지 않았다.
DB 모델·이력·인덱스 변경이나 데이터 재생성은 필요하지 않다. 현재 0009까지의 이력·예약 표를 확인했다.

```sh
git apply --check patches/F3/memory-search/01-server-wiring.patch patches/F3/memory-search/02-generated-types.patch
```

타입은 아래와 같이 임시 경로에 생성한 결과와 기존 공통 파일의 차이다. 공통 파일에 바로 덮어쓰지 않는다.

```sh
uv run --locked --directory apps/server python -m app.cli.export_openapi --output /tmp/f3-memory-openapi.json
pnpm --filter @klover/api-types exec openapi-typescript /tmp/f3-memory-openapi.json -o /tmp/f3-memory-schema.d.ts
```

질의 임베딩은 F1 `load_embedding`·`EmbeddingRequest(purpose="query")`·벡터 검증을 사용한다.
로컬 생성 모델/임베딩 설정이 없거나 Ollama 연결이 실패하면 가짜 벡터를 쓰지 않고 제한을 표시한다.
저장 모델 태그·제공자·차원·live/test와 F1 분석 완료/메타데이터 일치를 모두 검사한다.
현재 F1은 모델 파일의 digest를 저장하지 않아 동일 태그의 실제 가중치 변경은 구별할 수 없다.
기존 벡터를 삭제하거나 다시 생성하지 않는다.

실제 모델 품질·5초 성능·네이티브 앱 검사는 미실행이다. 상세 검사와 다음 작업은
[인수인계](../../../docs/dev/F3-memory-search-handoff.md)를 따른다.
