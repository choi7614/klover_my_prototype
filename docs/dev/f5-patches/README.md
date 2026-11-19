# F5 공통 영역 통합 패치 기록

두 패치는 **사용자 승인 후 현재 작업 브랜치에 적용했다.** 최초 0f68ad1 초안은 이전 커밋에 보존하고,
최신 `origin/develop` **b147cfd**의 F0·F1·F2·F3를 유지하도록 조정했다.
대상은 `feat/F5-ai-scan`이다. 운영 DB에 실제 마이그레이션을 실행한 기록은 아니다.
먼저 이 브랜치의 F5 전용 모듈이 있어야 한다. 패치만 develop에 단독 적용하는 변경이 아니다.

| 파일 | 대상과 목적 |
| --- | --- |
| `0001-server-and-schema.patch` | 메일 소유자 복합 유일 제약, F5 Alembic 메타데이터·새 0005_f5, 라우터·기본 차단 실행기 등록, 관련 기존 통합 테스트와 DB/API 문서 갱신 |
| `0002-generated-api-types.patch` | 위 앱에서 생성한 공유 OpenAPI·TypeScript 타입. 직접 수정한 타입이 아님 |

첫 패치의 대상 파일은 다음 11개다.

- `apps/server/app/db/models.py`
- `apps/server/migrations/env.py`
- `apps/server/migrations/versions/0005_f5_suggestions.py` (신규, 부모 0004_f2)
- `apps/server/app/main.py`
- `apps/server/app/cli/run_mail_api.py`
- `apps/server/tests/test_postgresql_storage.py`
- `apps/server/tests/test_http_server.py`
- `apps/server/tests/test_f2_pending_migration.py`
- `apps/server/tests/test_mail_read_api.py`
- `docs/architecture/api.md`
- `docs/architecture/data-model.md`

두 번째는 `packages/api-types/openapi.json`, `packages/api-types/src/schema.d.ts`다.
기존 인증/메일 조회 API 구현, OAuth 범위·JSON·키·계정, 0001~0004 이력, 잠금 파일,
F0 app/router/main/preload/트레이는 바꾸지 않는다.

## 확인한 결과

두 패치의 역방향 `git apply --reverse --check` 통과(이미 적용한 상태 확인).
`scripts/f5/verify_patches.py`는 새 임시 복사본에서 적용 전/후 상태를 구분하고,
서버 검사 **343개(F5 32개와 기존 F1/F2/F3 포함)**, 마이그레이션/모델 일치, 반복 upgrade,
0004_f2 → 0005_f5 → 0004_f2 downgrade → 재-upgrade를 검사했다.
합성 기존 메일·계정·수신 커서·암호문·F2 프로필·F3 검색 기록이 유지됐고 공유 OpenAPI도 앱 생성 결과와 일치했다.
생성된 공유 TypeScript 타입의 엄격한 컴파일 검사도 통과했다.

실제 운영 DB·Google·F1 입력·F0 연결을 검사한 결과는 아니다. 검사 중 만든 임시 스키마만 제거했다.

## 재현

저장소 루트에서 수행한다. 먼저 **별도의 로컬 `klover_f5_test` DB(PostgreSQL 16+pgvector)**를 준비한다.
스크립트는 루프백 호스트와 이 DB 이름만 허용하며 실제 작업 파일에 패치를 적용하지 않는다.

```bash
git apply --reverse --check docs/dev/f5-patches/0001-server-and-schema.patch
git apply --reverse --check docs/dev/f5-patches/0002-generated-api-types.patch
uv run --directory apps/server python ../../scripts/f5/verify_patches.py \
  --database-url 'postgresql+psycopg://postgres@127.0.0.1:32769/klover_f5_test'
```

포트는 준비한 테스트 DB에 맞춘다. 이 작업 환경에서는 32769를 사용했다.
실행은 새 임시 폴더 경로와 검사 결과만 보고한다. 운영 `.env`나 Google 설정은 복사하지 않는다.

## 적용·후속 작업

1. 최신 develop을 F5 브랜치에 가져왔고 공통 적용·검사를 마쳤다. 기존 브랜치와 이력을 초기화하지 않았다.
2. 마이그레이션은 progress.md의 0005를 예약한 뒤 0004_f2 다음에 추가했다. 0001~0004는 변경하지 않았다.
3. 실제 앱에서 `pnpm gen:api-types`로 공유 타입을 재생성했다. 기존 F2/F3와 메일 동기화 경로도 포함한다.
4. 사용자가 승인한 커밋·Push·develop 대상 PR과, 문제가 없으면 develop 병합을 진행한다.

main 병합은 별도 승인 대상이다. Calendar는 기본 차단이며 실제 transport·권한 검토와
별도 허용 전에는 실행하지 않는다. F0 main/preload/app과 기존 OAuth·수신 코드는 수정하지 않았다.
