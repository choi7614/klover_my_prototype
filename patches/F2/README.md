# F2 적용 전 패치 — 아직 미적용

최초 기준은 `origin/develop` 0f68ad1이며, 승인 후 최신 `9244454`의 F1/F3를 가져와 다시 생성했다.
`feat/F2-profile-draft`는 가져온 공통 파일을 직접 수정하지 않는다.
이 폴더는 검토용이다. 패치 생성·`git apply --check`는 적용·병합·커밋을 하지 않는다.
실제 적용은 결과 보고 후 묶음 승인을 받은 범위에서만 진행한다.

| 패치 | 영향 | 현재 확인 범위 |
| --- | --- | --- |
| 01-database | F3 이력 뒤의 새 F2 Alembic 0004_f2, env.py metadata 등록 | 전용 DB의 임시 스키마에서 upgrade/downgrade·metadata 일치 검사 |
| 02-server-registration | app.main의 router 등록, 로컬 실행 명령의 F2 저장소 주입 | 전용 테스트 앱에서 기존 authorize 재사용. 운영 앱은 미등록 |
| 03-screen-routes | 공통 App에 F2 두 화면 export 연결 | 기능 컴포넌트는 합성 검사 완료. 공통 App은 미연결 |
| 04-generated-api-types | 등록 후 OpenAPI에서 자동 생성할 공유 타입 | 실제 공유 파일은 보존, F2 전용 생성 타입으로 컴파일 검사 |
| 05-shared-documents | API·DB 문서에 적용 범위 설명 | 기존 문서는 보존 |

DB의 기존 `models.py`와 두 Alembic 이력은 수정하지 않는다. F2 모델은 전용 metadata를
사용하므로 공통 모델에 import를 추가할 필요가 없다. 추가 의존성이 없어 공통 잠금 파일도 바꾸지 않는다.

03은 현재 App 기준의 검토용 연결이다. F0의 실제 메일함 경로와 인증 IPC 클라이언트를
`App`의 `mailboxPath`·`f2Client`로 주입해야 한다. 기본값은 기존 첫 실행 경로·명시적인
준비 부족 클라이언트다. **실제 메일함/IPC 연결 완료를 뜻하지 않는다.**
main/preload·메일함·디자인 토큰은 건드리지 않는다. F0가 자신의 변경과 함께 IPC를 연결해야 한다.
F2Client에는 발송·토큰·임의 URL·임의 IPC 기능이 없다. CORS 허용으로 우회하면 안 된다.

패치 적용 전에 최신 원격과 F0·DB·F1의 변경을 확인한다. 0004 리비전 번호와 App 형태가 달라지면
순서·상위 리비전·연결 내용을 다시 조정하고 검사해야 한다. 기존 이력을 덮어쓰면 안 된다.

재생성 (서버·외부 AI·Gmail 접속 불필요):

```bash
uv run --directory apps/server python -m app.cli.export_f2_openapi --output /tmp/klover-f2-openapi.json
packages/api-types/node_modules/.bin/openapi-typescript /tmp/klover-f2-openapi.json -o /tmp/klover-f2-schema.d.ts
python scripts/f2/prepare_integration_patches.py --openapi /tmp/klover-f2-openapi.json --types /tmp/klover-f2-schema.d.ts
git apply --check patches/F2/01-database.patch patches/F2/02-server-registration.patch patches/F2/03-screen-routes.patch patches/F2/04-generated-api-types.patch patches/F2/05-shared-documents.patch
```

공통 파일에 적용하지 않은 상태이므로 일반 서버·앱의 F2 수용 기준은 아직 통합 확인 대기다.
