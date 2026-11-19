# F4 공통 연결 패치 — 실제 파일에는 미적용

> 기준 develop: `9ac5421` · 원본 SHA-256은 [baseline.json](baseline.json)

기존 F4 브랜치는 최신 develop과 로컬 통합했지만 아래 공통 변경은 이 디렉터리의
패치에만 들어 있다. feature 코드 병합이 운영 등록·DB 설치·앱 진입 완료를 뜻하지 않는다.
이전 `docs/dev/F4-proposals/`의 0003 패치는 보관 기록이며 사용하지 않는다.

| 순서 | 패치 | 적용 대상·행동 |
| --- | --- | --- |
| 1 | [01-server-registration.patch](01-server-registration.patch) | app.main의 F4 경로 등록, run_mail_api의 WeeklyReportRuntime 조립 |
| 2 | [02-report-storage.patch](02-report-storage.patch) | 공통 ORM과 신규 0006_f4 이력. 기존 이력·사용자·메일·계정·키 보존 |
| 3 | [03-screen-ipc.patch](03-screen-ipc.patch) | 제한된 F4 main/preload 통로 5개, 인증된 `/report/weekly` 진입, 기존 F0/F2/F3 보존 |
| 4 | [04-generated-api-types.patch](04-generated-api-types.patch) | 최신 전체 OpenAPI에서 F4를 추가해 자동 생성한 타입 |
| 5 | [05-shared-documents.patch](05-shared-documents.patch) | 공통 API·데이터 모델 문서 반영 |

## 연결 계약과 적용 전 확인

- 메일은 F1 `F1ReportMailRepository(AnalysisRepository(...))`를 재사용해 인증된
  user_id/account_id로 제한한다. F1 저장 구조는 아직 운영 미설치 상태다. 통합 채팅에서
  F1 저장 SQL의 적용 상태부터 확인한다. F4가 원문을 임의 분석하거나 pending/failed를 숨기지 않는다.
- 프로필은 F2 `F2Repository.report_profile`의 ProfileState를 읽는다. 영어 섹션 키는 F4
  경계에서 표시 이름으로 바꾸며 F2 순서·문체·대상을 유지한다. 빈 보고 대상은 입력을 요청한다.
- 생성은 공통 TextGeneration과 GenerationRequest(purpose=weekly_report)만 사용한다.
  실제 제공자는 여전히 없다. 미설정은 503이며 가짜 기본 응답으로 대체하지 않는다.
- 대역은 분리된 테스트 DB·명시적 허용에서만 연결한다. 저장한 대역 보고서도 기본 운영
  런타임에서는 거부한다. 실제 Gmail의 외부 AI 전송 실험과 30초 성능 측정은 하지 않았다.
- 마이그레이션 제안은 `0006_f4`, 현재 down_revision은 `0005_f5`다. 실제 적용 직전
  progress.md의 예약과 Alembic head를 확인한다. F1 이력이 먼저
  반영되는 등 head가 바뀌면 이 패치를 다시 생성·검사한다. 이 패치와 F1 패치가 각각 다른
  head를 만드는 상태로 동시에 적용하지 않는다.
- 03은 화면에 토큰·임의 주소·파일 접근 권한을 주지 않는다. main에서 기존 readLocalAPI·
  trustedMailSender를 재사용하고 정해진 메서드·상대 경로와 입력 모양만 허용한다.
- 패키지·잠금 파일 변경은 없다. Word·발송·예약·메일 외 데이터도 추가하지 않는다.

## 재생성·검사

서버와 JS 의존성을 기존 잠금 파일대로 설치한 뒤 저장소 루트에서:

```bash
apps/server/.venv/bin/python scripts/f4/prepare_integration.py
git apply --check patches/F4/01-server-registration.patch
git apply --check patches/F4/02-report-storage.patch
git apply --check patches/F4/03-screen-ipc.patch
git apply --check patches/F4/04-generated-api-types.patch
git apply --check patches/F4/05-shared-documents.patch
```

생성기는 임시 복사본에서만 공통 파일을 편집하고 OpenAPI·타입을 생성한다. 실제 원본에는
패치 파일과 baseline.json만 쓴다. `--validation-dir <없던 경로>`를 지정하면 제안 합본을
별도 공간에 남겨 타입·IPC·마이그레이션 검사를 할 수 있다. 이 경로에 별도의 node_modules를
설치해 검사하고, 운영 DB 주소를 사용하지 않는다.

01은 F4 등록 부재 보호 검사도 등록 확인 검사로 바꾼다. 실제 기능 브랜치에서는 등록
부재 검사가 계속 통과해야 한다. 제안 합본은 검사 제외 없이 전체 pytest를 실행한다.

초기 기준 `b147cfd`에서 발견했던 공통 검사 3건은 최신 develop의 F5 병합에서 이미
수정됐다. 중복 수정 패치는 최종 제안에 포함하지 않는다. 기존 F5 경로·저장소·공유 타입과
마이그레이션을 보존한 상태에서 F4만 추가하도록 패치를 다시 생성했다.
