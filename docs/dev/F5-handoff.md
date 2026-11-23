# F5 연결 요청 — F0·F1·공통 서버

> 과거 전달·검사 기록을 포함한다. 2026-11-24 현재 API/IPC·F1 입력·F4 AI 통합은 PR #37까지 반영됐다. 미연결·패치 적용 요청은 당시 기록이며 현재 작업 상태는 [progress.md](progress.md)와 각 status, 실행은 [setup.md](setup.md)를 따른다. 기존 패치를 재적용하지 않는다.

이 문서는 전달용 요청이다. 다른 채팅에 메시지를 보내거나 해당 브랜치를 가져오지 않았다.
기준 브랜치 `feat/F5-ai-scan`, 최초 생성 기준 0f68ad1, 승인 후 통합 기준 `origin/develop` b147cfd.
최신 develop의 F0·F1·F2·F3 작업을 보존해 가져왔고 F5 공통 DB/API/타입을 적용했다.
현재 상태와 검사는 [F5 현황](F5-ai-scan-status.md)을 따른다.
[F5 계약](F5-ai-scan-contract.md)과 [실제 입력 스키마](f5-contract/f1-input.schema.json)를 함께 본다.

## F1 담당에게

### 분석 완료 알림 지점(on_analyzed)에 F5 연결하기 (2026-11-19 추가)

F1 결과 → F5 제안 변환·생성은 F5 브랜치에 구현했다(`app/pipeline/scan_analysis.py`, `F5Service.scan_from_analysis`).
F1 파일은 고치지 않았고, 콜백 연결 코드도 만들지 않았다. **통합 채팅에서 아래 한 가지만 연결하면 된다.**

```python
from app.ai.runtime import load_generation
from app.db.repositories.f5 import F5Repository
from app.services.f5 import AnalysisScanHook, F5Service

# 조립(예: pending 분석 실행 명령이나 서버 시작 시 한 번)
on_analyzed = AnalysisScanHook(
    F5Service(F5Repository(engine)),
    llm,                       # F1이 쓰는 것과 같은 공통 TextGeneration (purpose=scan으로 호출됨)
    allow_gmail=allow_gmail,   # F1의 --allow-gmail-content 값과 같게
)

# F1 분석 저장 트랜잭션이 '확정된 뒤'에 호출한다 (async)
outcome = await on_analyzed(work.mail, result)   # AnalysisMail, AnalysisResult
```

- 콜백 모양: `async (mail: AnalysisMail, result: AnalysisResult) -> AnalysisScanOutcome`.
  소유자는 `mail.user_id`·`mail.account_id`(F1이 DB에서 잠가 읽은 신뢰 컨텍스트)에서 가져온다.
- **예외를 던지지 않는다.** 실패하면 `status="failed"`와 고정 코드(`provider_error`, `timeout`,
  `invalid_response`, `external_transfer_blocked`, `provider_not_configured`, `not_found` 등)를 돌려준다.
  F5 실패가 이미 저장된 F1 분석을 되돌리지 않게 하기 위해서다. 실패한 메일은 수동 명령으로 다시 만들 수 있다.
- 반드시 F1 저장 트랜잭션 **밖에서(확정 후)** 부른다. F5는 별도 트랜잭션으로 저장하고, 같은 메일을 다시 넣어도
  제안·알림 이벤트를 중복으로 만들지 않는다(근거 위치 기반 `action_key`). 그래서 재시도해도 안전하다.
- 제안할 것(일정·할 일·회신 필요)이 없으면 AI를 부르지 않고 `nothing_to_suggest`를 돌려준다.
- 실제 Gmail 본문은 `allow_gmail=True`이고 **외부 전송이 없는 제공자(로컬 Ollama)** 일 때만 AI에 보낸다
  (open-questions 14). Claude 제공자로는 `external_transfer_blocked`.
- 테스트 대역(mode=test) 제공자는 기본 거부한다(`allow_test_provider`는 검사 전용).
- 수동 실행: `uv run python -m app.cli.f5_scan --user-id U --account-id A --mail-id M [--allow-gmail-content]`
  — F1이 저장한 성공 분석(`f1_mail_analysis`, `analysis_status=done`)을 읽어 같은 경로로 제안을 만든다.
  출력은 상태·건수·건너뛴 이유 개수뿐이며 본문·근거 문장·키를 출력하지 않는다.

### 계약 차이와 처리 방식

| F1 `AnalysisResult` | F5 `ScanInput` 요구 | 처리 |
| --- | --- | --- |
| 행동 키 없음 | 재분석에도 유지되는 `action_key` | 근거 위치로 만든다: `유형-sha256(start:end)[:32]`. 문구가 바뀌어도 같은 문장이면 같은 제안 |
| `evidence_spans`가 종류(action/due/event)만 있고 어느 항목의 근거인지 연결 없음 | 제안마다 정확한 근거 | AI(`purpose=scan`, `ai/prompts/scan.md`)에게 항목별 근거 문장을 **원문 그대로 인용**하게 하고, F5가 원문에서 직접 찾아 위치를 정한다. F1 위치는 같은 문장이 여러 번 나올 때 우선순위 힌트로만 쓴다 |
| 인용문 없음 | `quote == body_text[start:end]` | F5가 찾은 위치에서 잘라 넣는다 |
| 본문 해시 없음 | `body_sha256` | 저장된 원본 `body_text`의 UTF-8 SHA-256 |
| 위치 단위: Python 문자열 인덱스 | Unicode 코드 포인트 | 같은 단위(Python `str`), 변환 없음 |
| 일정 `end` 없음 가능 | `end` 필수 | **지어내지 않고 건너뜀**(`event_end_unknown`) |
| 일정 `location` null 가능 | 문자열 | 빈 문자열 |
| `needs_reply`(참/거짓)만 | 회신 이유 + 근거 | `needs_reply=true`일 때만 AI가 이유 한 문장과 회신 요청 문장을 인용. false인데 회신을 주면 형식 위반 |
| 제목 길이 제한 없음 | 300자 이하 | 넘으면 건너뜀(`title_too_long`) |

- 제안 **내용**(일정 제목·시각·장소, 할 일 제목·마감)은 F1 결과를 그대로 쓴다. AI는 내용을 바꾸지 못한다.
- 형식 위반(JSON 아님, 다른 mail_id, 없는 index, 중복 index, 추가 키)이나 원문에 없는 인용·빠진 근거가 있으면
  **한 번 다시 묻는다**(`retry_reason` 고정 코드만 전달). 두 번째에도 형식 위반이면 아무 제안도 만들지 않고
  `invalid_response`, 형식은 맞지만 일부 근거가 원문에 없으면 그 항목만 버리고 이유를 기록한다.
- 로컬 모델이 붙이는 `<think>` 블록·코드 블록 표시는 공통 `clean_json_text`로 걷어낸다.
- 같은 유형의 두 항목이 같은 문장을 가리키면 다음 같은 문장 위치를 쓰고, 없으면 뒤 항목을 건너뛴다(`duplicate_evidence`).

### 이전 요청(유지)

1. 공통 AI 제공자·분석기는 F1 담당 코드를 사용한다. F5는 공통 `TextGeneration`만 쓰며 자체 SDK·가짜 기본 제공자가 없다.
2. 일정에는 시간대가 있는 시작·종료가 모두 필요하다. 추정 불가한 종료·날짜를 임의로 만들지 않는다.
3. 같은 행동 재입력은 최초 저장값과 사용자 처리 상태를 유지하고, 이벤트를 다시 만들지 않는다.
   본문 변경·행동 철회·이미 만든 제안의 교체 정책은 후속 합의 대상이다.

## F0 담당에게

공통 app/router·main/preload·트레이는 이번 작업에서 수정하지 않았다.

- S04는 `src/renderer/features/suggestions/suggestion-reader.tsx`의 `SuggestionReader`를 사용한다.
  `mailId`, 원본 `body`, 소유 메일의 `suggestions`, 제한된 `SuggestionsClient`, `onChange`를 전달한다.
  메일 변경 시 `key={mailId}`로 새 상태를 만들고, 처리 결과는 같은 제안 ID만 갱신한다.
  서버가 확인한 실제 Calendar 연결·권한·캘린더 목록이 없으면 `calendarReady=false`를 유지한다.
  F2가 연결될 때만 `replyReady`를 켠다. 본문은 React 텍스트로 렌더링하며 HTML을 실행하지 않는다.
- `SuggestionsClient`의 `get`, `approve`, `dismiss`, `conflicts`를 제한된 IPC로 제공해 달라.
  승인에는 현재 `version`과 수정한 payload를 보낸다. Renderer에 API 토큰·Google 토큰·임의 URL 호출 권한을 주지 않는다.
  main은 기존 메일 API의 루프백·Bearer 정책을 유지한다. F5 전용 생성 타입은
  `features/suggestions/f5-api.d.ts`이며 공유 타입 반영은 적용 전 패치에 있다.
- 알림 계약은 `f5.notification.v1`이다. 이벤트는 `event_id`, `name=suggestion.created`,
  `suggestion_id`, `mail_id`, `type`, `created_at`을 포함한다. 본문·토큰은 이벤트에 없다.
  현재 `GET /suggestion-events`는 outbox 조회 계약이고 실제 WebSocket 송수신기는 없다.
- main은 사용자·계정·event_id를 기준으로 표시 이력을 보존하고 재전달을 중복 제거한다.
  표시 직전 제안을 재조회해 `pending`인지 확인한다. 무시·처리한 제안을 다시 띄우지 않는다.
  같은 메일은 가장 중요한 제안 하나로 묶고, 1분에 3건 초과 시 묶음 알림을 사용한다.
  알림 유형 설정·일시 중지·트레이 배지·Windows AppUserModelID는 F0 담당이다.
- 실제 표시 뒤에만 `POST /suggestion-events/{event_id}/ack`를 호출한다. 조회만으로 표시 완료를 기록하지 않는다.
  전송과 표시 사이 장애에서 정확히 한 번 알림을 보장하지 않으므로 main 쪽 영구 중복 제거가 필요하다.
  설정에서 끈 유형은 OS 알림과 놓친 제안 표시 모두에서 필터링한다.
- 시작 시 `GET /suggestions?status=pending&notified=false`를 페이지 끝까지 읽어 S10 놓친 제안에 연결한다.
  나중에 보기는 상태를 바꾸지 않는다. 무시는 명시적 사용자 동작으로만 요청한다.
- 토스트 클릭은 메일 열기, 승인 버튼은 사용자 동작을 확인한 뒤 승인 API 호출로 연결한다.
  시작·재연결·목록 조회·이벤트 수신만으로 승인하거나 메일을 보내면 안 된다.
  이번 작업의 실제 OS 알림·트레이·자동 시작 검사는 **미실행**이다.
- `/todos?status=open`은 앱 할 일과 건수 연결에 사용할 수 있다. 리마인더 작업자는 아직 없다.

## 공통 서버 담당에게

1. [통합 패치 기록](f5-patches/README.md)의 두 파일은 사용자 승인 후 공통 파일에 적용했다.
   기존 F2·F3 경로와 모델을 보존했으며 실제 운영 DB 변경은 실행하지 않았다.
2. 새 메일 소유자 유일 제약과 `f5_suggestions`, `f5_todos`, `f5_suggestion_outbox`,
   `f5_dismissals`를 추가했다. 기존 Alembic 0001~0004는 보존하며 후속 `0005_f5`(부모 0004_f2)를 쓴다.
   F1 등 다른 마이그레이션이 추가됐다면 head·부모 이력을 다시 조정하고 검사해야 한다.
   FK가 메일 삭제를 제한하므로 향후 메일 삭제/보관 정책도 함께 검토해야 한다.
3. 기존 인증 의존성을 재사용하는 F5 라우터와 기본 차단 실행기를 등록했다.
   승인된 통합은 현재 로컬 API 토큰의 소유 계정으로 제한한다. 기존 인증·메일 API 구현 자체는 바꾸지 않았다.
   실제 Google HTTP transport·동의 추가·토큰 로더·주기 수신 연결은 이 패치에 없다.
4. Calendar transport에는 실제 사용자/계정, 검증한 동의 범위, 허용된 캘린더를 연결해야 한다.
   Gmail 읽기 권한·콘솔 API 활성화는 Calendar 쓰기 동의가 아니다. 기존 OAuth JSON·키·계정·범위는 그대로 보존한다.
   쓰기와 freebusy 권한을 각각 확인하고, freebusy 응답으로 제목을 만들어 내지 않는다.
5. `find`는 결정적 event ID를 조회하고, `insert`는 같은 ID와 request_hash를 외부 이벤트의
   private extended properties에 저장·검증해야 한다. 409는 조회 후 일치 여부로 처리한다.
   전송 후 타임아웃은 `uncertain`이며 다른 내용·다른 캘린더로 바꾸어 재시도할 수 없다.
   프로세스가 `executing` 상태에서 종료된 경우 담당자 조정 절차가 추가로 필요하다.
6. 실제 권한과 실행 코드 확인·별도 사용자 허용 전에는 차단 실행기를 유지한다.
   테스트 결과를 실제 승인·등록 성공으로 표시하지 않는다.

## 별도로 남은 통합 확인

실제 F1 입력, 기존 Gmail 수신과의 연결, `/ws` 푸시, F0 화면·main IPC·알림·트레이,
알림 유형 설정, Calendar 동의·실제 쓰기·겹침 조회, F2 초안 실행, 할 일 리마인더,
결재·중요 발신자 제안은 미통합/미구현이다. 30초 알림 성능과 Windows 알림 센터 표시는 미확인이다.
