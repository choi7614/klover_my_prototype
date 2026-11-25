# F2 로컬 초안 생성 안정화 — 검증·인수인계

> **2026-11-25 갱신:** 아래 `body_quote_missing`·`source_quote_missing` 등 근거 문구 검증 사유는 더 이상 없다.
> AI가 근거 문구를 글자 그대로 베끼게 하는 방식이 Claude·로컬 모델 모두에서 자주 실패해(받은 메일 문구를 본문 칸에 넣음,
> 공백·따옴표 차이 등) 방식을 바꿨다. 이제 AI는 본문·방향만 만들고 근거는 서버가 본문과 입력 메일을 비교해 계산한다.
> 아래 표와 '근거를 삭제하지 않는다' 설명은 이전 방식의 기록이다. 남은 사유: JSON·항목·본문/방향·방향 불일치·제외 표현·원문 복사·수정 명령.

## 현재 상태

- 작업: `feat/F2-local-draft-stability`, Codex, 기준 `origin/develop fff7993`(PR #39 병합).
- 구현·합성/분리 DB 검사 완료. 최초 검토 시 미커밋·미Push·PR 없음으로 보고했으며, 이후 2026-11-25 사용자가 커밋·Push·PR 생성 및 develop 병합을 승인했다. 제출/병합 이력은 후속 기록과 해당 PR 상태를 따른다.
- main/develop 및 기존 기능 브랜치·작업 폴더는 보존했다. 사용자 DB·메일·키·프로필을 변경하지 않았다.

## 조사 근거와 범위

기존 오류 `invalid_ai_output`의 안내는 JSON·스키마·근거 문구/출처/원문 인용·방향·제외 표현·원문 복사를
모두 같은 문장으로 안내했다. 따라서 과거 맥북 화면의 문구만으로 실제 실패 원인을 확정할 수 없다.
첫인사/마무리를 저장했을 때 개선됐다는 사용자 보고는 참고했으며, 실제 메일·모델 응답은 수집하지 않았다.

확인한 기존 기록:

- PR #35, 코드 `e97459e`: 답장 작성자/수신자 구분, 원문 그대로 반환·수정 코드를 답장 방향으로 반환하는 결과 차단.
- PR #36, 코드 `7d2c259`: 서버 초안 120초·미리보기 30초, 앱 AI 요청 150초와 시간 초과 안내.
- PR #37, 코드 `e32c082`: 숫자 근거 위치 대신 인용 문구를 받고 서버가 정확한 위치를 계산.
- PR #39, 코드 `0a357b3`, 병합 `fff7993`: 로컬 전용·요청별 선택·제공자 실패 후 로컬 전환. 로컬 호출당 65초 상한.

이번 작업은 F2 검증과 진단만 수정한다. 전체 120초/미리보기 30초/로컬 호출 65초/앱 150초 상한,
로컬 전용·자동 미리보기 로컬 강제·취소·Claude 선택 및 전환 정책은 변경하지 않는다.
DB 이력·공유 API 타입·앱 main/preload·의존성·저장소 구조 변경은 없다.

## 재현한 문제와 수정

1. **반복 문구의 유효한 근거를 겹친 것으로 잘못 거절**
   - 본문에 같은 문구가 두 번 있고 각 문구의 출처와 원문 인용이 모두 정확한 합성 응답을 만들었다.
   - 기존 코드는 `body.find(text)`가 돌려준 첫 위치를 모든 근거에 사용해 겹침 검사에서 실패했다.
   - 수정 후 출처/원문 인용을 확인하고 아직 배정하지 않은 정확한 본문 위치를 찾는다. 근거를 버리지 않는다.
   - 동일 문구가 실제로 한 번뿐인데 근거를 두 번 반환하면 계속 실패한다. 인사/마무리 유무 모두 검사했다.
2. **실패 종류가 같은 안내에 가려짐**
   - 고정 사유만 로그/화면 안내에 사용한다. JSON, 항목/자료형, 빈 본문/방향 구성, 본문 문구,
     출처, 원문 인용, 학습 표현, 겹침/범위, 요청 방향, 제외 표현, 원문 복사, 수정 코드 등을 구분한다.
   - 기존 HTTP 502·`invalid_ai_output`은 유지한다. 앱은 기존 오류 표시 통로로 고정 한국어 사유를 보여준다.
   - 제공자 오류도 허용 목록의 코드만 기록한다. 알 수 없는 코드나 외부 예외 문장은 기록하지 않는다.
3. **동일한 보정 문장으로 재요청**
   - 입력에 허용한 근거 출처 목록을 명시하고 실패 사유에 맞는 고정 보정 지시를 한 번 보낸다.
   - AI가 잘못 반환한 원문은 재전송·로그·DB에 저장하지 않는다. 총 두 번까지이며 전체 대기 상한은 늘리지 않는다.

원문 정확 일치·소유자·학습 동의·제외 표현·방향·겹침 검사를 끄지 않았다.
공백/줄바꿈을 임의로 맞추거나 근거를 삭제해 잘못된 결과를 성공으로 만들지 않는다.
기존 계약상 근거 없는 일반 답장 응답의 빈 evidence 허용은 그대로다. 모든 주장의 의미적 사실성까지 자동 증명하는 검사는 아니다.

## 안전한 진단 읽기

서버 터미널에는 아래 형태의 **고정 사유·시도 번호·작업 종류**만 출력한다.

```text
F2 output rejected reason=source_quote_missing attempt=1 operation=create
F2 output rejected reason=source_quote_missing attempt=2 operation=create
F2 provider failed reason=ollama_model_not_found operation=revise
```

`operation`은 create/revise/preview 중 하나다. 모델명·사용자명·메일 ID·제목·본문·키·AI 원문·검증 예외 상세는 기록하지 않는다.
Pydantic 검증 오류도 입력값/문맥을 제외한 오류 종류만 검사하며 필드명·입력값을 로그에 넣지 않는다.
한 번 실패하고 다음 시도에서 성공할 수도 있으므로 로그 한 줄만 보고 최종 실패라고 판단하지 않는다.
최종 실패 시 앱의 오류 문구에 고정 사유가 함께 나오고 기존 편집 화면은 유지된다.

| 사유 예 | 뜻 |
| --- | --- |
| json_invalid / schema_invalid | JSON 또는 응답 항목·자료형이 계약과 다름 |
| body_quote_missing | 근거 text가 생성 본문에 없음 |
| source_not_allowed | 접근할 수 없는 메일·금지된 출처 또는 미리보기의 메일 근거 |
| source_quote_missing | 원문에 없는 인용. 띄어쓰기/줄바꿈을 임의로 보정하지 않음 |
| evidence_overlap | 정확히 배정할 수 있는 서로 다른 본문 위치가 부족하거나 겹침 |
| direction_mismatch / edit_code_as_direction | 요청 방향 불일치 또는 shorter 등 수정 명령을 방향으로 반환 |
| incoming_echo | 답장 대신 수신 원문을 그대로 반환 |
| ollama_unreachable / ollama_model_not_found / ollama_timeout | 로컬 연결·모델·응답 시간 오류, 형식 보정 재시도 대상 아님 |

## 검사 결과

실제 Gmail·유료 AI·사용자 DB·실제 Ollama를 사용하지 않았다. 합성 제공자·합성 메일·분리 PostgreSQL의 일회용 스키마만 사용했다.

| 검사 | 결과 |
| --- | --- |
| 수정 전 새 재현 검사 16개 | 14 실패/2 통과. 반복 문구 오거절 및 새 사유 진단 부재를 확인(14개 모두 별도 기능 결함이라는 뜻은 아님) |
| F2 검증·보정·대기/취소 선택 검사 | **54 통과** |
| 분리 DB 포함 서버 전체 | **620 통과, skip 0**, 75.09초 |
| 실제 HTTP/분리 DB 보존 | 실패 안내 전달·기존 초안/편집본·버전·프로필 동일·새 초안 미저장, 생성/수정 모두 통과(서버 전체에 포함) |
| 기존 앱 F2 통신·화면 선택 검사 | **29 통과**. 앱 소스는 변경하지 않았으며 현재 develop과 코드가 동일한 기존 작업 폴더의 설치된 의존성으로 실행 |
| Ruff check / format --check | 통과 |
| 전체 앱 빌드·전체 앱 검사 | 미실행. 앱 소스·타입·의존성 변경 없음; 필요한 F2 검사만 선택 실행 |
| 실제 Qwen/Claude·Gmail·맥북 Electron | 미실행. 실제 모델의 개선 효과·정확도·생성 속도·과거 화면 오류의 정확한 원인은 미확인 |

재현/선택 명령(프로젝트 루트):

```bash
PYTHONPATH=apps/server apps/server/.venv/bin/python -m pytest -q \
  apps/server/tests/test_f2_local_draft_stability.py \
  apps/server/tests/test_f2_shared_adapter.py \
  apps/server/tests/test_f2_generation_timeout.py
```

전체 서버 검사는 분리 테스트 URL 변수 `KLOVER_TEST_DATABASE_URL`, `KLOVER_F1_TEST_DATABASE_URL`,
`KLOVER_F5_TEST_DATABASE_URL`을 테스트 전용 컨테이너 `klover-history-tests:55449`의 `_test` DB로만 지정했다.
일반 사용자의 `.env`나 DB 주소를 테스트에 사용하지 않는다. 테스트용 컨테이너는 검사 후 중지한다.

```bash
PYTHONPATH=apps/server apps/server/.venv/bin/python -m pytest -q apps/server/tests
apps/server/.venv/bin/python -m ruff check apps/server
apps/server/.venv/bin/python -m ruff format --check apps/server
pnpm --filter desktop exec vitest run \
  src/main/f2-client.test.ts \
  src/renderer/features/profile-draft/profile-draft.test.tsx
```

## 변경 파일과 목적

| 파일 | 목적 |
| --- | --- |
| [f2_output_diagnostics.py](../../apps/server/app/ai/f2_output_diagnostics.py) | 고정 실패 사유·한국어 안내·보정 지시·비공개 로그 |
| [f2_shared_adapter.py](../../apps/server/app/ai/f2_shared_adapter.py) | 정확한 반복 문구 위치 배정·안전한 실패 구분·1회 보정 |
| [draft.md](../../apps/server/app/ai/prompts/draft.md) | 허용 출처·정확한 인용·중복/겹침·보정 응답 계약 명시 |
| [profile_draft.py](../../apps/server/app/services/profile_draft.py) | 서비스 검증에서도 고정 사유 제공, 저장 전 거절·기존 시간 제한 유지 |
| [test_f2_local_draft_stability.py](../../apps/server/tests/test_f2_local_draft_stability.py) | 재현·비밀 로그 차단·보정·취소/시간 제한·보존 검사 |
| [test_profile_draft.py](../../apps/server/tests/test_profile_draft.py) | 실제 HTTP/분리 DB에서 오류 표시와 데이터 보존 검사 |
| [progress.md](progress.md) | 현재 작업 브랜치·도구·검증·승인 대기 기록 |
| [F2 status](F2-profile-draft-status.md) | 최신 develop/PR 대조·이번 변경/미검증/다음 행동 |
| [F2 기능 명세](../product/features/F2-profile-draft.md) | 실패 안내와 반복 문구 검증의 구현 계약 연결 |
| 이 문서 | 원인·검증·제약·안전한 재확인 방법 |

## 승인·병합 후 맥북 확인

1. 2026-11-25 사용자가 커밋·Push·PR 생성 및 develop 병합을 승인했다. PR 검사 성공을 확인한 후 병합한다. main은 별도 승인이다.
2. develop 병합 후 기존 백업을 유지하고 [setup.md의 업데이트](setup.md#9-기존-사용자--업데이트)를 따른다. 이번 단위의 새 DB 이력은 없다.
3. 서버/앱을 다시 시작하고 답장 AI를 로컬로 선택한다. 첫인사/마무리는 빈 값과 저장한 값 모두 확인할 수 있다.
4. 실제 메일 사용 여부는 사용자가 결정한다. 외부 전송 없는 로컬 검사부터 초안 생성·더 짧게/더 정중하게·직접 편집·저장/재조회를 확인한다.
5. 실패하면 앱의 고정 사유와 `F2 ... reason=...` 줄만 공유한다. 실제 메일/키/AI 원문은 보내지 않는다.
6. 반복 문구 오거절 외의 실제 모델 실패는 이번 사유를 기준으로 후속 보완한다. 모델 교체나 근거 검증 해제를 성공 조건으로 삼지 않는다.

## 제출 기록 (2026-11-25)

코드 커밋 `69e195e164f680967a9b4fac9fc91e3fd7e06383`을 Push하고 [PR #40](https://github.com/choi7614/klover_my_prototype/pull/40)을 develop 대상으로 생성했다. 승인된 동일 10개 파일이며 후속 문서 커밋은 제출 기록만 갱신한다. 최종 CI·병합 SHA는 PR 이력을 따른다.
