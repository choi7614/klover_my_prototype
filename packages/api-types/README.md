# Klover API 타입

서버 OpenAPI에서 자동 생성한 TypeScript 선언이다. 현재 `/health`, `/auth/session`,
`/mails`, `/mails/{mail_id}`의 GET 계약을 제공한다. 설계에만 있는 쓰기·AI API는 포함하지 않는다.
인증·로컬 실행과 필드 의미는 [API 목록](../../docs/architecture/api.md)을 따른다.

저장소 루트에서 생성·검사한다.

```bash
corepack pnpm gen:api-types
corepack pnpm --filter @klover/api-types typecheck
```

생성 순서:

1. uv가 `apps/server`에서 실제 `app.main.app`의 OpenAPI를 내보낸다.
2. openapi-typescript가 JSON에서 `src/schema.d.ts`를 만든다.

`openapi.json`과 `src/schema.d.ts`는 직접 수정하지 않는다. API 변경 후 재생성해
함께 검토한다. 이 패키지는 타입만 제공하며 서버 호출이나 외부 연결을 실행하지 않는다.
