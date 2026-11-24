# F1 메일 요약 실패 진단·재요청 보완

2026-11-25 · `integrate/F1-summary-diagnostics` · 기준 `origin/develop 42b319b`(PR #40).
2026-11-25 사용자가 검토한 11개 파일의 커밋·Push·PR 생성 및 검사 통과 후 develop 병합을 승인했다.
최종 커밋·검사·병합 이력은 이 변경을 포함하는 PR에서 확인한다. main은 별도 승인이다.

## 확인한 것과 확인하지 못한 것

- 사용자가 맥북에서 제공한 집계: 분석 완료 18건, 실패 25건. 실패는 `invalid_response` 24건,
  `provider_error` 1건. `check_ai` 설정은 로컬 `qwen3:8b`, `bge-m3`, 1024차원이다.
- 설정 확인은 연결/생성 검사가 아니다. 기존 실패 코드에는 세부 사유가 없어서 과거 24건의
  JSON·스키마·근거 오류를 소급해 구분할 수 없다. 모델 용량 부족이나 시간 초과로 단정하지 않는다.
- 별도 F2의 `근거 문구와 생성 본문의 불일치`는 답장 결과 검증 사유다. F1 집계와 같은 원인이라는
  증거는 없고 이번 변경은 F2 검증을 수정하지 않는다.
- 이번 확인은 실제 원격 코드·PR #40 병합 상태·합성 응답에 근거한다. 실제 Gmail·사용자 DB·
  실제 Ollama/Qwen·유료 AI는 호출하지 않았다.

## 변경

- 기존 F1 검증은 유지하고 실패 사유를 고정 코드로 구분한다. 로그에는 코드와 시도 번호만 기록한다.
  사용자/메일 ID·제목·본문·키·모델 원문·동적 JSON 필드명·예외 메시지는 기록하지 않는다.
- 형식 오류 재요청은 기존처럼 한 번만 한다. 이제 고정 보정 지시를 사유에 맞게 보낸다.
  이전 AI 원문을 재전송하거나, 잘못된 항목을 삭제/변환해 통과시키지 않는다.
- 프롬프트에 필수 항목·문자 위치 범위·요약 길이 안내를 보강한다. 원문 길이는 서버가 계산한다.
- 앱 본문의 실패 영역에서 기존 네 가지 실패 코드를 쉬운 안내로 구분한다. 임의 문자열은 표시하지 않는다.
- 기존 DB/API 실패 코드와 API 타입은 그대로다. 세부 사유는 **새로 실행한 서버 로그**에만 남는다.
  새 마이그레이션·의존성·main/preload 변경은 없다. 기존 성공 결과·메일·초안·프로필은 건드리지 않는다.
- 자동 분석은 계속 로컬이며 제공자 전환·무한 재시도·실패 메일 일괄 재분석을 추가하지 않는다.

| 새 로그 사유 | 뜻 |
| --- | --- |
| `json_invalid` | JSON 객체를 읽지 못함 |
| `schema_missing` / `schema_extra` / `schema_invalid` | 필수 항목 누락 / 추가 항목 / 자료형 등 |
| `summary_invalid` | 빈 요약·길이·줄 수 오류 |
| `category_invalid` | 허용된 분류값이 아님 |
| `actions_invalid` / `events_invalid` | 요청·마감 / 일정 형식·시각 오류 |
| `evidence_invalid` / `mail_id_mismatch` | 원문 근거 위치 / 메일 ID 불일치 |
| `response_size_or_type` / `input_too_large` | 응답 형식·크기 / 입력 크기 제한 |
| `timeout` / `ollama_timeout` | 호출 대기 시간 초과 |
| `ollama_unreachable` / `ollama_model_not_found` | 로컬 연결 실패 / 모델 없음 |
| `ollama_bad_request` / `ollama_error` / `ollama_invalid_response` / `provider_failed` | 제공자 요청·서비스·응답 오류, 나머지 고정 오류 |
| `source_invalid` | 나머지 원문 검증 실패 |

여러 검증 오류가 동시에 있으면 대표 사유 하나를 기록한다. `attempt=1` 뒤 보정 성공이 가능하므로
이 로그 한 줄만으로 최종 실패라고 판단하지 않는다. 최종 상태는 앱의 분석 결과를 확인한다.

## 검사

- 수정 전 새 합성 검사 18개 실패: 세부 진단/보정 지시 부재 재현이며 서로 다른 18개 제품 결함은 아니다.
- 수정 후 F1 분석·임베딩 계약 및 신규 진단 선택 검사 77개 통과.
- 분리 PostgreSQL·합성 응답으로 서버 전체 **638 통과 / skip 0**(84.93초).
- 데스크톱 전체 **29개 파일·192개 검사 통과**(42.84초). 기존 요약·목록·재시도·IPC·인증 검사 포함.
- Ruff check/format(187개 파일), 데스크톱 lint/typecheck, `git diff --check` 통과.
- 기존 잠금 의존성을 재사용했다. 사용자 DB·Gmail·유료 AI·실제 모델·맥북 Electron 검사는 미실행이다.
- 테스트 대역의 보정 성공은 실제 Qwen의 품질 개선이나 기존 실패 24건 복구를 입증하지 않는다.

## 맥북에서 확인하기 — 승인·병합 후

1. 앱과 서버를 종료하고 [setup.md의 업데이트](setup.md)를 따른다. 이번 변경만으로 새 DB 이력은 없다.
2. 기존 설정 그대로 서버와 앱을 다시 켠다. Ollama와 DB도 실행 중이어야 한다.
3. 받은편지함에서 **요약에 실패한 메일 한 건**을 열고 `다시 시도`를 한 번 누른다.
4. 성공하면 요약·분류가 보인다. 계속 실패하면 서버 터미널에서 아래 모양의 줄만 확인한다.

```text
F1 analysis rejected reason=summary_invalid attempt=2
```

5. 공유할 때는 `F1 analysis rejected reason=… attempt=…` 줄만 보낸다.
   메일 본문·전체 터미널·키·AI 응답은 보낼 필요가 없다. 이 진단 결과로 다음 수정 범위를 결정한다.
   기존 실패 25건을 자동으로 일괄 재시도하거나 모델/임베딩 차원을 바꾸지 않는다.

## 파일별 역할

- `app/pipeline/analysis_diagnostics.py`: 고정 사유·보정 문구·안전한 로그
- `app/pipeline/analyze.py`: 엄격 검증 유지, 진단·한 번의 보정 연결
- `app/ai/prompts/analyze.md`: 형식·근거 범위 안내
- `tests/f1/test_analysis_diagnostics.py`: 합성 오류·재시도·취소·비밀 정보 비기록 검사
- `renderer/features/mail-analysis/analysis-view.tsx`, `mail-analysis.test.tsx`: 실패 안내·화면 검사
- 이 문서와 F1 status·기능 명세·progress·setup: 현재 범위·한계·업데이트 후 확인 방법
