# F1 공통 통합 요청 — 아직 적용하지 않음

> 2026-11-19 갱신: 이 SQL은 Alembic `0007_f1` 제안과 공통 패치로 옮겼다.
> 적용은 [patches/F1/README.md](../../patches/F1/README.md)를 따른다. 아래는 이전 기록이며,
> SQL은 0007 적용 전 F1 검사용으로만 남긴다.

기준: `origin/develop` `0f68ad1`. F1의 일반 파일은 구현되어 있지만 운영 등록은 하지 않았다.
`001_storage.sql`은 분리된 PostgreSQL 16·pgvector 테스트 DB에서만 적용·검사한 초안이다.
기존 개발 DB·실제 메일·키·토큰과 Alembic 이력에는 적용하지 않았다.

## DB 담당자에게 요청할 내용

1. `001_storage.sql`을 검토하고 **새 Alembic revision**으로 옮긴다. 기존 `0001`·`0002`는
   고치지 않는다. 새 revision 번호와 모델 변경은 동시에 작업하는 DB 담당자가 확정한다.
2. 기존 mails의 `(mail_id,user_id,account_id)` 유일 제약과 F1 전용 analysis/chunks/feedback
   테이블의 복합 FK를 추가한다. SQL의 모든 소유권·분류·차원·중복 제약을 유지한다.
3. 공통 ORM 모델 또는 메타데이터에 같은 구조를 반영해 Alembic 자동 비교가 F1 테이블을
   미지의 테이블로 오해하지 않게 한다. 현재 F1 저장소는 SQL로 읽고 써서 공통 models를
   변경하지 않았다. 공통 ORM 반영은 아직 미구현이며 이 SQL만 운영에 먼저 실행하지 않는다.
4. 분석 필드는 부속 테이블에 제안했다. 기존 mails 열 확장 설계와의 최종 선택을 공동
   확정한다. 다른 배치를 택하면 F1 저장소의 SQL도 함께 바꾼다. 이 변경은 원문·토큰·
   수신 시작 시점·기존 열을 삭제하거나 재작성하지 않는다.
5. 실제 임베딩 모델이 정해지면 차원과 검색 인덱스를 결정한다. 현재는 `vector`와 차원
   검사만 둔다. 다른 provider/model/dimensions 벡터를 같은 검색 대상으로 섞으면 안 된다.

## 서버·조회 담당자에게 요청할 내용

- 명시 실행은 `app.pipeline.pending_analysis.process_pending`이다. 제공자는 `app.ai` 경계에서
  주입한다. `app.ai.runtime.load_providers`는 아직 ProvidersNotConfigured를 반환한다.
- 수신 직후 처리/작업 큐 연결은 별도 통합이다. Gmail 커넥터·수신 커서·시작 시점·토큰
  갱신 로직을 F1에서 수정하거나 대체하지 않는다. 원문·계정 접근은 저장소만 통한다.
- `app.api.mail_analysis.create_analysis_router(engine)`는 테스트 앱에서만 연결했다.
  운영 등록에는 공통 앱의 인증·예외·개인 응답 헤더와 함께 검토가 필요하다.
  `PATCH /mails/{mail_id}/category`는 `{category: 기존영문키}`를 받고 소유자는 기존
  authorize 결과에서만 결정한다. 요청으로 user_id/account_id를 받지 않는다.
- 기존 GET /mails 목록·상세 응답은 바꾸지 않았다. summary/category/user_label/priority/
  action_items/needs_reply 등의 응답 확장, 카테고리·스마트 필터, counts, 정렬, 재분석 API,
  OpenAPI·공유 TS 타입 생성은 공통 담당과 후속 연결해야 한다.
- `mail.analyzed`/F5 알림은 아직 발행하지 않는다. 트랜잭션 확정 후 전달할 이벤트와
  유실을 막는 outbox가 필요하다. 현재 반환값은 mail_id·상태·시도 횟수뿐이다.
- F0 화면과 Electron IPC는 이번 변경에 포함하지 않는다.

## 적용·승인 순서

이 문서와 SQL은 승인 대상 결과물이지 실행 지시가 아니다. 사용자의 결과 검토 뒤
F1 브랜치의 로컬 통합·커밋·Push·PR 생성을 묶어 승인받는다. 현재 반영할 다른 기능
브랜치는 지정하지 않았다. 공통 후속 변경이 별도 브랜치로 준비되면 정확한 브랜치와
커밋을 보고하고 F1로 가져올 범위를 승인받는다. develop 병합과 main 병합은 각각 별도다.
