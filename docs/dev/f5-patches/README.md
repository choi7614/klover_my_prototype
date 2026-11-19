# F5 공통 영역 적용 전 패치

두 패치는 **현재 작업 브랜치에 미적용**이다. 새 임시 복사본과 로컬 테스트 DB에서만 적용·검사했다.
대상은 `feat/F5-ai-scan`, 공통 파일 기준은 `origin/develop` **0f68ad1**이다.
먼저 이 브랜치의 F5 전용 모듈이 있어야 한다. 패치만 develop에 단독 적용하는 변경이 아니다.

| 파일 | 대상과 목적 |
| --- | --- |
| `0001-server-and-schema.patch` | 메일 소유자 복합 유일 제약, F5 Alembic 메타데이터·새 0003_f5, 라우터·기본 차단 실행기 등록, 관련 기존 테스트 2개와 DB/API 문서 갱신 |
| `0002-generated-api-types.patch` | 위 앱에서 생성한 공유 OpenAPI·TypeScript 타입. 직접 수정한 타입이 아님 |

첫 패치의 대상 파일은 다음 9개다.

- `apps/server/app/db/models.py`
- `apps/server/migrations/env.py`
- `apps/server/migrations/versions/0003_f5_suggestions.py` (신규, 부모 0002)
- `apps/server/app/main.py`
- `apps/server/app/cli/run_mail_api.py`
- `apps/server/tests/test_postgresql_storage.py`
- `apps/server/tests/test_http_server.py`
- `docs/architecture/api.md`
- `docs/architecture/data-model.md`

두 번째는 `packages/api-types/openapi.json`, `packages/api-types/src/schema.d.ts`다.
기존 인증/메일 조회 API 구현, OAuth 범위·JSON·키·계정, 0001/0002 이력, 잠금 파일,
F0 app/router/main/preload/트레이는 바꾸지 않는다.

## 확인한 결과

`git apply --check` 통과. `scripts/f5/verify_patches.py`가 새 임시 복사본에 두 패치를 적용한 뒤
서버 검사 **131개(F5 32개 포함)**, 마이그레이션/모델 일치, 반복 upgrade,
0002 → F5 upgrade → 0002 downgrade → 재-upgrade를 검사했다.
합성 기존 메일·계정·수신 커서·암호문이 그대로 유지됐으며, 패치의 공유 OpenAPI가 앱의 생성 결과와 일치했다.
생성된 공유 TypeScript 타입의 엄격한 컴파일 검사도 통과했다.

실제 운영 DB·Google·F1 입력·F0 연결을 검사한 결과는 아니다. 검사 중 만든 임시 스키마만 제거했다.

## 재현

저장소 루트에서 수행한다. 먼저 **별도의 로컬 `klover_f5_test` DB**를 준비한다.
스크립트는 루프백 호스트와 이 DB 이름만 허용하며 실제 작업 파일에 패치를 적용하지 않는다.

```bash
git apply --check docs/dev/f5-patches/0001-server-and-schema.patch
git apply --check docs/dev/f5-patches/0002-generated-api-types.patch
uv run --directory apps/server python ../../scripts/f5/verify_patches.py \
  --database-url 'postgresql+psycopg://postgres@127.0.0.1:32768/klover_f5_test'
```

포트는 준비한 테스트 DB에 맞춘다. 이 작업 환경에서는 32768을 사용했다.
실행은 새 임시 폴더 경로와 검사 결과만 보고한다. 운영 `.env`나 Google 설정은 복사하지 않는다.

## 승인 후 작업 순서

1. 적용할 기능 브랜치·원격 develop·기존 변경을 다시 확인한다. 기존 브랜치를 초기화하지 않는다.
2. 다른 기능의 DB 변경이 생겼으면 먼저 Alembic head와 모델 충돌을 검토해 패치를 조정한다.
3. 승인된 범위에서만 F5 작업 브랜치에 적용·재검사하고 공유 타입을 실제 앱에서 재생성한다.
4. 변경 내용을 커밋·Push하고 develop 대상 PR을 생성한다.

이 묶음은 develop 또는 main 병합을 포함하지 않는다. 두 병합은 각각 별도 승인 대상이다.
Calendar는 적용 후에도 기본 차단이며 실제 transport·권한 검토와 별도 허용 전에는 실행하지 않는다.
