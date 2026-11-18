# F1 → F2~F5 전달 계약과 확인 방법

> 2026-11-19 · F1 기능 브랜치 로컬 구현 · 운영 통합 전

## 공통 AI·임베딩 호출 (F2·F3·F4·F5 공통)

`app.ai.interfaces`를 재사용한다. 기능별로 SDK나 가짜 기본 제공자를 만들지 않는다.

```python
from app.ai.interfaces import EmbeddingRequest, GenerationRequest

raw_json = await llm.generate(GenerationRequest(
    purpose="weekly_report",  # analysis / draft / search / weekly_report / scan
    system_prompt=prompt_file.read_text(encoding="utf-8"),
    user_prompt=input_json,
    response_schema=output_model.model_json_schema(),
))
vectors = await embeddings.embed(EmbeddingRequest(texts=("텍스트",), purpose="query"))
```

- 반환 JSON은 각 기능의 출력 모델로 검증한다. F1은 `AnalysisResult`를 쓴다.
- `.identity`는 provider/model/mode(`live` 또는 `test`), 임베딩은 `.dimensions`도 제공한다.
- 제공자 어댑터의 오류는 `ProviderCallError` 같은 고정 오류로 전달하고 외부 본문·키·
  메일 내용·응답 원문을 메시지나 로그에 넣지 않는다. 호출자는 타임아웃을 둔다.
- 실제 제공자는 미구현이다. `load_providers()`는 `ProvidersNotConfigured`로 중단하며
  fixture 응답으로 대체하지 않는다. 대역은 `tests/f1/support.py`에만 정의했다.

## F2·F3

- `mail_id`, 소유 user_id/account_id, 원문 및 분석 결과는 F1 저장 경계로 연결한다.
- F3는 본문(kind=body)과 요약(kind=summary), received_at, 유효 category를 쓸 수 있다.
  반드시 user_id/account_id + embedding provider/model/dimensions를 제한한다.
  이 작업은 검색 API·인덱스·검색 품질을 구현하거나 검증한 것이 아니다.
- 사용자 분류 변경 시 모든 청크의 필터 category도 갱신한다. 재분석해도 user_label은 남는다.

## F4

`F1ReportMailRepository(AnalysisRepository(...))`가 기존 `ReportMailRepository`를 구현한다.
`list_received_and_sent(user_id, start_at, end_before)`는 기존 ReportMail을 반환한다.
영문 분류 키, 받은/보낸 메일, 한국 날짜의 반개방 경계, 원문·thread_id·entities·mail_id를
유지한다. 유효 분류는 user_label 우선이다. pending/failed를 임의 요약으로 대체하지 않는다.
분리 DB에서 기존 `prepare_weekly_report_input`과 실제로 연결해 검사했다.
운영 보고 서비스에 자동 주입하지 않았다. 프로필·보고 생성은 F4/F2 담당 범위다.

## F5

AnalysisResult의 action_items/events/needs_reply/priority/entities/evidence_spans와 mail_id가
입력 계약이다. Calendar 쓰기·제안 생성·사용자 승인·알림·이벤트 전달을 대신 구현하지
않았다. 분석 저장과 이벤트 연결은 [공통 통합 요청](../../integration/F1-mail-analysis/README.md)을 따른다.

## 검사와 평가

`apps/server`에서 기존 환경과 잠금 파일을 유지한 채 실행한다.

```bash
uv sync --locked
uv run --locked pytest tests/f1
uv run --locked ruff check .
uv run --locked ruff format --check .
uv run --locked python -m app.cli.analyze_pending --help
```

DB 검사는 별도 `KLOVER_F1_TEST_DATABASE_URL`을 명시해야 한다. DB 이름이 `_test`로 끝나야
하며, 테스트가 만든 `f1_test_<무작위>` 스키마 안에서 공통 마이그레이션과 미적용 SQL을
검사하고 그 스키마만 정리한다. 실제 개발 DB 주소를 넣지 않는다. 원래 서버의 DB 검사도
실행하려면 `KLOVER_TEST_DATABASE_URL` 역시 같은 **분리 테스트 DB**로 지정한다.
변수를 주지 않은 경우 DB 검사는 skip이며 통과로 해석하지 않는다.

평가 데이터는 `fixtures/mails/F1-mail-analysis.json`의 합성 23건이다. 일곱 분류 각각 3건과
연도·시간대 경계 2건, 요청·회신·마감·일정의 기대 출력 및 분류 사유를 포함한다.
첨부 내용은 범위에 넣지 않았다. 정답 JSON을 반환하는 대역 테스트는 계약 검사다.
`evaluate_synthetic`는 잘못된 응답도 전체 건수에 포함한다. mode=test이면 모델 정확도를
반드시 None으로 반환한다. 실제 제공자 평가와 30초 수신→화면 성능은 아직 측정하지 않았다.

현재 CLI의 `run`은 제공자가 없어 not_configured(종료 코드 1)를 반환하고 DB도 열지 않는다.
`check`는 내용 없이 저장 준비 상태·pending 건수만 읽으며 제공자 준비 완료를 뜻하지 않는다.
기본 실행 대상은 fixture 계정이다. 향후 실제 Gmail 본문 분석은 별도 명시적 승인 후
`--allow-gmail-content`를 사용해야 한다. 이번 작업에서는 실행하지 않았다.
