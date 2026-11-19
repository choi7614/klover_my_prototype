# F1 구현·검사 결과

## 양식 요약

> 양식: [status-template.md](status-template.md) · 현황판: [progress.md](progress.md)

| 항목 | 내용 |
| --- | --- |
| 브랜치 | `feat/F1-mail-analysis` |
| 작업 도구 | Claude |
| 상태 | 진행 중 — 새 메일 자동 분석·분석 완료 알림 지점·받은편지함 분류·요약 표시 구현·검사 완료, 커밋·Push 완료, PR 생성 승인 대기. 공통 패치 05~07 미적용 |
| 마지막 커밋 | `369d511` 2026-11-19 — develop(#30) 빨리감기 반영 (이번 단위 커밋은 git log 참조) |
| 기준 develop | `369d511` |
| 미커밋 변경 | 없음 |
| 갱신일 | 2026-11-19 |

## 현재 상태

### 새 메일 자동 분석·분류·요약 표시 (2026-11-19, Claude, F1+F0)

가짜 제공자와 자동 검사로만 확인했다(맥북·실제 DB·API 키·Ollama 미사용). 실제 Gmail·실제 AI 확인은 맥북에서 한다.

- **자동 분석**(`app/pipeline/auto_analysis.py`): 새로고침(`POST /mails/sync`) 저장 뒤 `after_sync`로 '분석 시작' 신호만 주고
  바로 응답한다. 서버 안 작업자 스레드 하나가 pending을 분석한다(요청 안에서 분석·앱 별도 요청 방식과 비교해 가장 단순).
  AI 미설정 → 분석 안 함·pending 유지(가짜 결과 없음). Claude(외부) → 실제 Gmail 본문 전송 안 함·pending 유지.
  실패 → failed+고정 코드, `POST /mails/{id}/analysis/retry`로 다시 분석. 작업자는 DB 오류에도 죽지 않는다.
- **분석 완료 알림 지점**(`app/pipeline/analysis_hooks.py`): `hooks.register(on_analyzed)` →
  `on_analyzed(owner, mail_id, AnalysisResult)`. DB 확정 뒤 done만, 콜백 오류는 격리. F5 코드는 부르지 않는다.
  계약: [F1-handoff.md](F1-handoff.md) '분석 완료 알림 지점'.
- **표시용 조회**: 이미 등록된 F1 라우터에 `GET /mails/analysis/batch?ids=`, `GET /mails/{id}/analysis`,
  `POST /mails/{id}/analysis/retry` 추가. 기존 `/mails` 응답 형식은 그대로. 운영에서 테스트 대역 결과는 pending으로 보인다.
  F5의 `EvidenceSpan`과 이름이 겹치지 않게 표시용 `MailEvidenceSpan`을 따로 두었다(공유 타입 변경은 추가만).
- **화면**(S03, `renderer/features/mail-analysis/`, F0 `mailbox-page.tsx`·`routes.tsx`): 목록에 ◆ 요약 첫 문장 +
  분류 태그(카테고리 토큰 색) + `회신 필요`(danger) + `마감 MM/DD`(warning). 읽기 영역에 AI 요약 박스(요약·내가 할 일·
  마감 MM/DD(요일)·우선순위·이유) + "분류 [태그]". 분석 중 = "AI가 분석하고 있어요…" + 태그 스켈레톤/박스 스켈레톤,
  AI 미설정·외부 차단 = 이유 문구, 실패 = "요약을 만들지 못했어요 · 다시 시도". 분석 대기 중이면 3초마다 다시 확인
  (최대 60회, WebSocket 연결 전 임시). 결과는 mail_id가 같은 메일에만 붙인다. 통로가 없으면 기존 미리보기 모양 그대로.
- 공통 영역은 `patches/F1/05~07`([README](../../patches/F1/README.md)): 05 실행 명령 조립·api.md, 06 공유 타입(추가만),
  07 main/preload `klover.analysis`(batch·retry)·App 전달.
- 이번 범위 아님(후속): 분류 변경 드롭다운(`CategorySelect`, 서버 PATCH는 있음), 근거 문장 강조(`EvidenceHighlight`),
  스마트 보기·카테고리 건수(`/mails/counts`), 중요도순 정렬, WebSocket `mail.analyzed`.

| 검사 (이 환경, 일회용 PostgreSQL 16 + pgvector) | 결과 |
| --- | --- |
| 서버 `ruff check`·`ruff format --check` | 통과 |
| 서버 `pytest` (분리 테스트 DB) | 481 통과 / 24 skip(F5 전용 DB 변수 미지정 등) |
| 서버 `pytest` (DB 없음, CI와 같은 조건) | 360 통과 / 145 skip |
| 새 검사 `tests/f1/test_auto_analysis.py` | 18개(알림 지점·작업자 상태·백그라운드 분석·실패/재시도·외부 차단·조회·HTTP·sync→분석 흐름) |
| `tests/test_mail_sync_api.py` 추가 | 3개(`after_sync` 성공 뒤에만·오류 격리·Gmail 실패 시 미호출) |
| 데스크톱 `lint`·`typecheck`·`test` (기능 브랜치) | 통과, 23개 파일 164개 (새 화면 검사 10개) |
| 패치 05~07 적용 사본 | `git apply --check` 통과, 서버 ruff·pytest 480/24 skip, `gen:api-types` = 06, 데스크톱 lint·typecheck·test 25개 파일 169개 |
| 실제 Gmail·실제 AI·Electron 실제 창·30초 수신→표시 | **미실행** (맥북 필요) |

### 공통 패치 적용 (2026-11-19, 통합 채팅, `integrate/F1-F3-patches`)

- `patches/F1/` 01~04와 `patches/F3/01`을 develop `4725284` 위에 적용했다: 0007(`0007_f1`, F1 분석·청크·피드백 표, pgvector),
  `PATCH /mails/{mail_id}/category` 운영 등록, `anthropic` 의존성·`uv.lock`, `.env.example` AI 항목(값 없음), 공유 타입.
- 패치만으로 AI는 켜지지 않는다. 맥북 `.env`에 `AI_PROVIDER` 등을 설정해야 한다.

| 검사 | 결과 |
| --- | --- |
| 패치 적용 | F1 01→02→03→04, F3 01 순서로 충돌 없음. 0007은 `.pending`과 동일 |
| 의존성 | `anthropic 1.17.0`·`docstring-parser`·`jiter`·`sniffio` 추가만, 기존 버전 변경 없음 |
| 서버 `ruff check`·`ruff format --check` | 통과 |
| 서버 `pytest` | 352 통과, 132 skip (실제 PostgreSQL 필요 — 이 환경에 DB 없음. F1 채팅의 분리 DB 사본 확인은 460 통과·24 skip) |
| `alembic heads` | `0007_f1` 하나 (부모 `0006_f4`) |
| 공유 타입 | `pnpm gen:api-types` 재생성 결과가 패치 04와 동일 |
| 데스크톱 `lint`·`typecheck`·`test` | 통과 (22개 파일 154개) |
| AI 미설정 동작 | `search_ai()` → `(None, None)`, 검색은 503 안내 유지 |

미실행: 실제 DB에 0007 설치(pgvector 필요), 실제 Claude·Ollama 호출.


- 완료(가짜 통신·자동 검사로 확인):
  - `.env`의 `AI_PROVIDER`로 제공자 선택(`app/ai/config.py`, `runtime.py`). 비우면 미연결, 가짜 결과 대체 없음.
  - Claude 어댑터(`app/ai/claude.py`): 공식 anthropic SDK, 기본 `claude-opus-5-5`, 기능별 모델
    (`CLAUDE_MODEL_ANALYSIS` 등), 구조화 출력(JSON 스키마), effort 기본 `low`, 거절 시 다른 모델로
    넘기기 **끔**(비용 예측), 거절·잘림·인증·한도·시간 초과를 고정 오류 코드로.
    `AI_CLAUDE_TEST_DATA_ONLY=true` 확인 없으면 켜지지 않음.
  - Ollama 어댑터(`app/ai/ollama.py`): loopback 주소만, 프록시 무시, 형식 강제(schema/json/none),
    `think` 선택, 시간 초과·연결 실패·5xx 재시도, 모델 없음·연결 실패 안내 문구. 모델 태그는 `.env` 필수.
  - 임베딩: 로컬 Ollama `bge-m3`(1024차원, `EMBEDDING_MODEL`·`EMBEDDING_DIMENSIONS`로 변경 가능).
  - 외부 전송 차단: F1 실행 명령은 Claude + 실제 Gmail 본문(`--allow-gmail-content`)을 DB 열기 전에 거부.
  - 확인 명령 `python -m app.cli.check_ai [--ping]` 추가. 느린 로컬 모델용 시간 제한을 파이프라인에 전달.
  - 0007 제안 이력(`patches/F1/files/0007_f1_analysis.py.pending`)과 비교용 ORM(`app/db/f1_models.py`).
  - 분류 수정 라우터 등록 함수 `register_mail_analysis`(엔진 없으면 503).
- 부분 완료·미통합: 공통 영역 4개 패치(`patches/F1/`) 미적용 — DB 0007, main 등록·run_mail_api 조립,
  anthropic 의존성·uv.lock·.env.example, api-types. 적용 전에는 Claude 경로가 "패키지 미설치"로 미연결.
- 미구현: 실제 모델 호출 확인(맥북), 실제 정확도 85%·30초 성능, 자동 수신 분석 큐, F0 화면 표시,
  GET 응답의 AI 필드·counts·재분석 API, F2~F5 경로별 외부 전송 차단(각 기능 채팅).

## 검사 결과

실제 메일·키·네트워크 호출 없음. DB 검사는 이 작업 환경에 만든 **일회용 PostgreSQL 16 + pgvector**
(`klover_f1_test`, `klover_test`)에서 실행했다. 개발·운영 DB는 쓰지 않았다.

| 검사 | 결과 | 비고 |
| --- | --- | --- |
| 서버 pytest (DB 없음, CI와 같은 조건) | 통과 329 / skip 135 / 실패 0 | DB 검사 skip |
| 서버 pytest (분리 테스트 DB) | 통과 437 / skip 27 / 실패 0 | skip: F5 전용 DB 변수 미지정 24, anthropic 미설치 3 |
| F1 검사만 (분리 테스트 DB) | 통과 145 / skip 3 | 새 검사 54개(설정·Ollama·Claude·CLI·0007·등록) |
| 서버 ruff check / format | 통과 | |
| 4개 패치 적용 사본 | 서버 통과 440 / skip 24, ruff 통과 | anthropic 1.17.0 실제 SDK로 요청 모양 확인(가짜 서버) |
| 패치 사본 api-types 재생성 | 같은 결과 | `git diff --exit-code packages/api-types` |
| 패치 사본 데스크톱 lint·typecheck·test | 통과 (test 133) | 기능 브랜치 데스크톱 코드는 변경 없음 |
| 실제 Claude·Ollama 호출 | **미실행** | 맥북에서 아래 명령으로 확인 |

## 공통 영역 요청

- `patches/F1/01~04`를 순서대로 적용 ([README](../../patches/F1/README.md)). 마이그레이션 번호 `0007`(부모 `0006_f4`) 예약됨.
- 그 밖에 새로 만든 `apps/server/tests/conftest.py`는 모든 서버 검사에서 개발자 `.env`의 AI 설정을
  무시하게 한다(맥북에 `AI_PROVIDER`가 있어도 F4 검사가 '미연결' 기준으로 돌게). 공통 영향이 있어 보고한다.

## 다음 할 일

1. 통합 채팅: `patches/F1/05~07` 적용(05 다음에 F5 콜백 등록 한 줄 가능).
2. 맥북: `.env`에 `AI_PROVIDER=ollama` 등 설정 → 서버·앱 실행 → 새로고침 후 목록에 '분석 중' → 요약·태그가 채워지는지 확인.
3. 후속 단위: 분류 변경 드롭다운, 근거 문장 강조, 스마트 보기·카테고리 건수, 중요도순 정렬, 실제 모델 정확도 측정.

## 맥북 확인 명령 (사용자가 직접)

`.env`는 커밋하지 않는다. 키는 `.env`에만 적는다.

```bash
# 0) 통합 후 최신 코드와 의존성
git pull && cd apps/server && uv sync --locked
# 1) DB 이력 0007 적용(통합 채팅에서 01 패치 적용 후)
uv run alembic upgrade head && uv run alembic current        # 0007_f1 (head)
# 2) Ollama (https://ollama.com 설치 후)
ollama pull bge-m3                    # 임베딩
ollama pull <정한-qwen-모델-태그>      # 예: qwen3:14b — 메모리에 맞게
ollama list
# 3) .env 예시 (로컬)
#   AI_PROVIDER=ollama
#   OLLAMA_MODEL=<위 태그>
#   OLLAMA_THINK=false        # Qwen3의 생각 출력을 끄면 빨라진다. 오류 나면 비운다
# 4) 설정·연결 확인 (메일 내용 없음)
uv run python -m app.cli.check_ai
uv run python -m app.cli.check_ai --ping
# 5) 저장 준비·분석 실행 (기본은 fixture 메일만)
uv run python -m app.cli.analyze_pending check --user-id <id> --account-id <id>
uv run python -m app.cli.analyze_pending run --user-id <id> --account-id <id> --limit 3
# 6) Claude로 바꿔 확인할 때 (.env, 테스트 데이터만)
#   AI_PROVIDER=claude
#   AI_CLAUDE_TEST_DATA_ONLY=true
#   ANTHROPIC_API_KEY=<키>
#   (Ollama는 임베딩용으로 계속 실행)
uv run python -m app.cli.check_ai --ping   # 아주 적은 토큰 비용 발생
```

문제가 생기면: `check_ai --ping` 결과의 `generation_hint`·`embedding_hint`를 확인한다.
JSON 형식 문제가 반복되면 `OLLAMA_FORMAT=json`, 너무 느리면 더 작은 모델이나 `OLLAMA_TIMEOUT_SECONDS`를 늘린다.

## 인수인계 메모

- 멈춘 지점: 자동 분석·표시 단위 구현·검사 완료, 커밋·Push 완료, PR 생성 승인 대기 (2026-11-19)
- 주의: 자동 분석은 로컬 AI일 때 실제 Gmail 메일도 분석한다(외부 전송 없음). Claude면 분석하지 않는다.
  작업자는 서버 프로세스 안 스레드이므로 서버를 끄면 진행 중 메일은 pending/잠금 해제 상태로 남고 다음 새로고침 때 이어진다.
- 이전 메모: 단위 완료, develop 병합 #27
- 실패 중이거나 미실행인 검사: 실제 Claude·Ollama 호출, 맥북 DB 0007 적용 미실행
- 주의할 점: `ProviderIdentity.model`은 분석(analysis)용 모델 이름이다. 기능별로 모델을 바꾸면
  다른 기능 결과의 기록 모델과 다를 수 있다. Claude 경로는 F2~F5에서도 같은 제공자를 쓰므로,
  실제 Gmail을 쓰는 동안에는 `AI_PROVIDER=ollama`로 둔다.

---

## 상세 기록 (기존 내용 보존)

> 확인: 2026-11-19 · 작업 브랜치 `feat/F1-mail-analysis` · 기반 `0f68ad1`

## 완료 — 기능 모듈과 격리 환경에서 확인

- 기존 F4 MailCategory의 영문 키 7종을 재사용한 분석 결과 계약과 엄격한 JSON 검증.
  요약, 요청/마감, 회신 필요, 우선순위/이유, 인물·조직·프로젝트, 일정, 원문 근거 위치.
- 파일 프롬프트, 한국 날짜 기준, 잘못된 응답의 1회 재시도, 최종 failed·고정 오류 코드.
  실패·재분석·저장 오류에서 원문 text/html과 기존 계정/시작 시점/토큰을 보존.
- 본문 단락과 요약의 별도 임베딩 경계. 벡터 개수/차원/유한수/float32 범위/0벡터 검사.
- 복합 FK 소유권, 같은 mail_id 저장, 원자적 성공 저장·실패 상태, 저장 중 오류 롤백,
  행 잠금·SKIP LOCKED, 기본 done 건너뛰기와 명시적 재분석 시 청크 교체.
- 사용자 수정 우선, 성공·실패 재분석 뒤 수정 유지, 청크의 필터 분류 갱신,
  수정 재전송의 중복 방지와 동일 사용자·계정·발신자의 최신 예시만 사용.
- 공통 인증을 재사용하는 분류 수정 라우터를 별도 테스트 앱에서 확인.
  다른 사용자/없는 메일의 같은 404, 미인증/외부 Origin 차단, 소유자 주입 거부.
- 실제 분리 PostgreSQL 저장소와 기존 F4 보고 입력 서비스의 연결.
  받은/보낸 메일과 Asia/Seoul 날짜의 양 끝·사용자 분리를 확인.
- 합성 평가 23건(7종×3 + 연도·시간대 경계 2), 정답 기준과 별도 평가 실행 함수.
  대역 평가의 실제 모델 정확도 값은 None으로 유지.

## 부분 완료와 미통합

- 명시적 pending 실행 함수·CLI는 구현했지만 실제 제공자 로더는 아직 미연결이다.
  `run`은 not_configured로 끝나고 DB도 열지 않는다. 가짜 성공을 저장하지 않는다.
- DB 패치는 테스트 DB에서만 검증했다. 운영 DB·공통 ORM·새 Alembic revision에는
  반영하지 않았다. 부속 테이블 방식은 공통 DB 담당자와 확정할 제안이다.
- 분류 수정 라우터는 운영 app.main에 미등록이다. 기존 메일 GET 응답은 그대로라
  F0 화면에는 AI 결과가 아직 표시되지 않는다.
- F4 DB 읽기 어댑터는 연결 검사만 했고 운영 보고 서비스에 자동 주입하지 않았다.
- 기존 파일 수정 0개, 신규 파일 27개다. 공통 models·Alembic 이력·main·Gmail/조회 API·
  생성 타입·공통 잠금 파일·F0를 보존했다. 사전 검사 시점에는 커밋·Push·PR·로컬 브랜치
  병합을 하지 않았다.

## 미구현·실제 확인 대기

- 실제 LLM/임베딩 어댑터·키 설정·실제 분류/요약/날짜 추출 정확도.
- 실제 모델 분류 정답률 85%와 수신→화면 30초 성능. 테스트 실행 시간과 구분한다.
- 자동 수신 분석/작업 큐 연결, mail.analyzed WebSocket·outbox·F5 이벤트 전달.
- 스마트 보기/counts/정렬/분류 필터·재분석 HTTP 경로·조회 응답 확장·생성 타입·F0 UI.
- HTML 인용·서명 제거 고도화·스레드 묶기. 현재는 기존 수신기가 저장한 body_text를
  보존해 분석하며, 첨부 내용 분석과 과거 메일 일괄 처리는 포함하지 않는다.

실제 Gmail 본문을 AI로 전송하지 않았으며, 자동 검사에는 합성 메일만 사용했다.

## 검사 결과와 재현

분리된 PostgreSQL 16·pgvector 컨테이너의 새 `klover_f1_test` DB와 일회용 스키마를
사용했다. 기존 개발 DB 주소·파일·토큰을 재설정하지 않았다. 테스트 대역 결과는 mode=test다.

| 검사 | 결과 |
| --- | --- |
| 서버 전체 pytest (기존 DB 검사 + F1 DB 검사 활성화) | **190 통과, 실패 0, skip 0** |
| F1 검사 수 | 위 전체 중 **91개** |
| Ruff lint | `ruff check .` 통과 |
| Ruff format | `ruff format --check .` 통과 (76개 Python 파일) |
| CLI 실제 프로세스 | 제공자 미설정 → 종료 1, not_configured, 가짜 성공·DB 접근 없음 |
| 운영 앱 등록 여부 | F1 분류 수정 경로가 기존 앱 OpenAPI에 없음을 검사 |
| 기존 파일 보존 | `git diff --exit-code HEAD --` 변경 없음 |

잠금 파일대로 의존성을 설치한 후, 아래 두 환경 변수를 **새 전용 테스트 DB**로 설정해
`apps/server`에서 `uv run --locked pytest -q`를 실행한다.
`KLOVER_F1_TEST_DATABASE_URL`, `KLOVER_TEST_DATABASE_URL`이다. F1 전용 URL만 지정하면
F1 DB 검사만 활성화되며, 둘 다 없으면 DB 검사들이 skip된다. 기존 DB를 테스트용으로
사용하지 않는다. 상세 기준은 [전달 문서](F1-handoff.md)를 따른다.

## 변경 파일

| 신규 파일 | 목적 |
| --- | --- |
| `apps/server/app/ai/__init__.py` | 공통 AI 패키지 |
| `apps/server/app/ai/interfaces.py` | F2~F5가 재사용할 AI·임베딩 계약 |
| `apps/server/app/ai/runtime.py` | 미설정 상태와 실제 제공자 연결 지점 |
| `apps/server/app/ai/prompts/analyze.md` | 분석 프롬프트 |
| `apps/server/app/schemas/mail_analysis.py` | 분석·분류 수정 계약과 검증 |
| `apps/server/app/pipeline/__init__.py` | 전용 파이프라인 패키지 |
| `apps/server/app/pipeline/analyze.py` | JSON 검증·재시도·오류 처리 |
| `apps/server/app/pipeline/embed.py` | 청크 분리·임베딩·벡터 검증 |
| `apps/server/app/pipeline/pending_analysis.py` | 명시적 pending 배치 실행 |
| `apps/server/app/pipeline/evaluate.py` | 합성 데이터 평가와 대역 구분 |
| `apps/server/app/db/repositories/mail_analysis.py` | 소유권·원자적 저장·수정·F4 읽기 |
| `apps/server/app/api/mail_analysis.py` | 운영 미등록 분류 수정 라우터 |
| `apps/server/app/cli/analyze_pending.py` | 읽기 준비 확인·명시적 실행 CLI |
| `apps/server/tests/f1/__init__.py` | 검사 패키지 |
| `apps/server/tests/f1/conftest.py` | 별도 DB의 일회용 스키마 |
| `apps/server/tests/f1/support.py` | 테스트 전용 AI·임베딩 대역 |
| `apps/server/tests/f1/test_analysis.py` | 분석·날짜·근거·임베딩 검증 |
| `apps/server/tests/f1/test_storage.py` | 실제 DB·중복·격리·실패·F4 검사 |
| `apps/server/tests/f1/test_api.py` | 테스트 앱의 인증·분류 수정 검사 |
| `apps/server/tests/f1/test_cli.py` | 미설정·읽기 확인·실제 프로세스 검사 |
| `apps/server/tests/f1/test_evaluation.py` | 평가 구분·분모·합성 입력 제한 검사 |
| `fixtures/mails/F1-mail-analysis.json` | 합성 메일 23건과 기대 출력·분류 기준 |
| `integration/F1-mail-analysis/001_storage.sql` | 공통 DB 담당자용 미적용 저장 패치 |
| `integration/F1-mail-analysis/README.md` | 필요한 공통 변경과 승인 범위 |
| `docs/dev/F1-analysis-contract.md` | 분석·저장 설계 계약 |
| `docs/dev/F1-handoff.md` | F2~F5 전달 계약과 실행 안내 |
| `docs/dev/F1-analysis-status.md` | 이 결과 보고서 |

2026-11-19 결과 보고 후 사용자가 커밋·Push·PR 생성과 develop 병합을 승인했다.
이 승인은 F1 파일을 저장소에 반영하는 범위다. 위에 적은 운영 DB 패치 적용·공통 ORM·
실제 AI·운영 앱 등록은 별도 후속 구현이며, main 병합은 승인하지 않았다.
