# Calendar 공통 적용 전 변경안

기준: 원격 develop `7668d94` (PR #41). **미적용**. 상세: [F5 Calendar 인수인계](../../../docs/dev/F5-calendar-handoff.md).

기능 파일을 먼저 가져온 뒤 03→04→05→06→07→08 순서로 검토·적용한다.
과거 상위 폴더의 01/02는 이미 병합된 기록이므로 다시 적용하지 않는다.
`baseline.json`은 공통 원본 해시·새 파일 부재·기능 파일 목록을 포함한다.

```bash
python scripts/f5/verify_calendar_patches.py
```

위 명령은 별도 임시 사본에서만 해시/적용을 확인하고 위치를 출력한다. 현재 브랜치나 운영 DB를 바꾸지 않는다.
타입은 사본에서 서버 OpenAPI export와 openapi-typescript로 생성했다. 통합 후 공통 `pnpm gen:api-types`로 동일 결과를 확인한다.
DB 예약 0009_f5_calendar, 부모 0008_history는 통합 직전 원격 이력/번호 예약을 다시 확인한다.

## 2026-11-25 통합 적용 기록

`integrate/settings-calendar`에서 실제 연결을 적용했다. 겹치는 App/routes는 통합 수정했으며
생성 타입은 공통 생성 명령으로 재생성했다. 이 폴더는 원본 제안 기록이므로 재적용하지 않는다.
최종 develop 반영 상태와 검사는 통합 PR 및 `docs/dev/settings-calendar-integration.md`를 따른다.
