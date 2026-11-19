# F1 분석·저장 계약

> 2026-11-19 · `feat/F1-mail-analysis` · 기준 `origin/develop`의 `0f68ad1`

이번 범위는 분석 계약 → 검증·재시도 → 청크·임베딩 → 원자적 저장 → 명시적 pending
실행 → 합성 데이터 검사다. 공통 models·Alembic·main·메일 API·생성 타입·잠금 파일·F0는
수정하지 않는다. `integration/F1-mail-analysis/001_storage.sql`은 **미적용 검토용 패치**다.
운영 DB에 자동 적용하지 않으며, 기존 수신·토큰·수신 시작 시점은 바꾸지 않는다.

## 입출력과 담당 경계

- 공통 AI 호출: `app.ai.interfaces.TextGeneration.generate(GenerationRequest)` → JSON 문자열.
  `TextEmbedding.embed(EmbeddingRequest)` → 입력 순서의 벡터 배열. 둘 다 비동기이고
  provider/model/mode(`live`/`test`)를 명시한다. F2~F5는 이 경계를 재사용한다.
- 분석 출력: `app.schemas.mail_analysis.AnalysisResult`. `mail_id`, 기존 `MailCategory` 7종,
  1~2줄 summary, action_items(text/due), needs_reply, priority/reason,
  entities(projects/orgs/people), events(title/start/end/location), evidence_spans.
  날짜는 YYYY-MM-DD, 일정 시각은 오프셋을 포함한다. 알 수 없는 마감은 null이다.
  상대 날짜의 기준은 메일 수신 시각의 Asia/Seoul 날짜다. 원문 내 근거 위치는 Python
  문자열 인덱스이며 `[start,end)`다. 반환 mail_id와 근거 위치를 입력과 대조한다.
- JSON 계약 위반은 같은 메일에 총 2회까지 호출한다. 재시도 요청에는 고정 오류 코드만
  추가하며 외부 응답이나 검증 예외 내용을 복사하지 않는다. 최종 실패는 failed와 고정
  failure_code로 저장한다. body_text/body_html은 모든 경로에서 보존한다.
- 제공자 미설정 또는 기본 실행에서 test 제공자를 넘긴 경우에는 DB에 쓰지 않는다.
  테스트 대역 구현은 tests/f1 아래에만 둔다. 격리 테스트의 결과도 mode=test로 구별한다.
- 공통 저장소의 받은 메일을 사용자·계정·수신 시작 시점으로 제한하고 행 잠금과
  SKIP LOCKED로 가져온다. 재실행 시 done은 건너뛰며 명시적 reanalyze만 재분석한다.
- metadata/chunks/feedback은 복합 소유권 FK와 같은 mail_id로 연결한다. 성공 결과와
  본문·요약 벡터, mails.analysis_status를 하나의 트랜잭션으로 바꾼다. 저장 중 실패는
  전부 롤백한다. 청크는 재처리 때 교체하고 `(mail_id,kind,seq)`를 유일하게 한다.
- 사용자 수정은 user_label에 별도 저장한다. 유효 분류는 항상 user_label ?? category다.
  AI 결과 갱신·실패는 user_label을 덮어쓰지 않는다. 수정 이력은 같은 사용자·계정·
  발신자만 프롬프트 예시로 사용하고, 벡터 필터의 category에도 유효 분류를 반영한다.
- 벡터는 모델을 고정하지 않은 vector 형식이다. 차원·유한수·0벡터·입력 개수·모델 정보를
  검증한다. F3는 user_id/account_id 및 embedding provider/model/dimensions를 제한해야 한다.
- F4용 실제 DB 읽기 어댑터는 기존 ReportMail과 ReportMailRepository 계약을 구현한다.
  받은/보낸 메일, 사용자·계정, `[start_at,end_before)` 경계를 보존한다.
- F5에는 검증된 분석 결과와 mail_id를 전달할 수 있다. 제안 생성·Calendar·WebSocket은
  이 작업에서 대신 구현하지 않는다. 원자적 outbox와 운영 이벤트 연결은 공통 통합 사항이다.

실제 AI 제공자는 아직 선택·연결하지 않았다. 실제 정확도 85%, 30초 성능, 날짜 의미 추출
정확도는 실제 모델 호출 전까지 미확인이다. 원 명세의 수용 기준은 완료 처리하지 않는다.

F1 전용 분류 수정 라우터는 테스트 앱에서만 연결했다. 운영 경로·기존 GET 응답·공유 타입은
변경하지 않았다. 같은 분류 수정 요청의 재전송은 이력을 중복 추가하지 않으며, 프롬프트는
메일별 최신 사용자 수정 예시만 참고한다. 상세 실행·전달 계약은 [F1-handoff.md](F1-handoff.md),
DB·서버 등록 요청은 [통합 요청](../../integration/F1-mail-analysis/README.md)을 따른다.
