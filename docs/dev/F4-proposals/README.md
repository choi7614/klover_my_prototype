# F4 공통 변경 제안 — 미적용

> 보관 기록 (2026-11-24, 현재 develop f498d27): 이 패치/제안은 기존 통합 PR 등에서 적용되었거나 후속 구현으로 대체됐다. **현재 설치·업데이트에 재적용하지 않는다.** 과거 기준·명령은 이력이며 현재 절차는 [setup.md](../setup.md)를 따른다. 원본 패치 파일은 수정하지 않았다.

> **이전 기준의 보관 기록입니다. 적용하지 마세요.** 최신 제안은
> [patches/F4](../../../patches/F4/README.md)입니다. 이 폴더의 0003 저장 제안은
> 현재 이력과 맞지 않으며 기존 라우터·생성 타입 패치도 최신 코드에 적용되지 않습니다.

> `develop@0f68ad1` 기준. 사용자 승인 전 기존 공통 파일에 적용하지 않는다.

| 패치 | 변경 대상 | 목적 | 현재 검증 |
| --- | --- | --- | --- |
| [01-register-routes.patch](01-register-routes.patch) | `apps/server/app/main.py` | 새 F4 라우터의 경로·OpenAPI 등록 | `git apply --check` 통과 |
| [02-report-storage.patch](02-report-storage.patch) | `apps/server/app/db/models.py`, 신규 `migrations/versions/0003_create_weekly_reports.py` | 사용자 FK·선택 키 유일성·버전·JSONB 스냅샷을 가진 보고 테이블 | 적용 가능성·Python 문법 검사 통과, 실제 마이그레이션 미실행 |
| [03-generated-api-types.patch](03-generated-api-types.patch) | `packages/api-types/openapi.json`, `src/schema.d.ts` | 등록을 가정한 OpenAPI와 자동 생성 TypeScript 타입 | 적용 가능성·생성 타입 컴파일 통과 |

기능 전용 구현 파일들이 먼저 존재해야 한다. 01번을 적용해도 운영 서비스는 자동으로
생기지 않는다. `application.state.weekly_reports`에 검증된 실제 저장소·프로필·AI 포트를
주입하기 전에는 503으로 닫혀 있다. 테스트 대역으로 자동 대체하지 않는다.
02번은 기존 `0001`·`0002` 이력을 수정하지 않는다. 승인 시점의 최신 공통 DB 작업과
마이그레이션 번호가 겹치는지 다시 확인해야 한다. 계정·키·기존 메일을 이관·삭제하지 않는다.

03번은 임시 파일에 기능 라우터의 OpenAPI를 만든 뒤 기존 `openapi-typescript`로 생성했다.
공통 생성 파일은 직접 편집하지 않았다. 같은 이름의 메일 연락처 스키마가 생기면서
기존 연락처 참조가 모듈 이름으로 구별되지만 기존 메일 JSON 필드는 바꾸지 않는다.
패치에 반영할 때 다시 생성하고 F0 타입 검사를 실행해야 한다.

공통 의존성 추가가 없어 `uv.lock`, `pnpm-lock.yaml`, package 설정 변경 제안은 없다.
F0 진입부·라우트·Electron main/preload는 패치에도 넣지 않았다. 전송 연결은 F0 담당의
기존 인증 IPC 설계에 맞춰 별도로 적용한다. 임시 검토 프록시는 운영 연결 방법이 아니다.

현재 패치 파일의 적용 가능성만 검사하는 명령:

```bash
git apply --check docs/dev/F4-proposals/01-register-routes.patch
git apply --check docs/dev/F4-proposals/02-report-storage.patch
git apply --check docs/dev/F4-proposals/03-generated-api-types.patch
```
