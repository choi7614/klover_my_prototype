# F4 공통 연결 계약

> 2026-11-19 · 기준 `develop@9ac5421` · 기존 F4 브랜치로 로컬 통합

첫 단위의 스키마·서비스·저장소·검사 파일은 원본 그대로다. 운영 공통 파일은
최신 develop을 보존하며 새 변경은 [patches/F4/](../../patches/F4/README.md)에만 둔다.

## 입력·인증·AI 경계

- F1: `F1ReportMailRepository(AnalysisRepository(engine, user_id, account_id))`로 받은/보낸
  메일과 분석을 읽는다. 한국 날짜·수신 시작 경계·사용자 수정 분류를 우선하며
  pending/failed를 요약하거나 제외 수에 숨기지 않는다.
- F2: `F2Repository.report_profile`의 `ProfileState.exists`를 확인한다. 섹션 키만 표시
  이름으로 바꾸고 순서·문체·대상을 유지한다. 조직은 빈 값을 허용하고 빈 대상은 입력받는다.
- AI: 공통 `TextGeneration.generate(GenerationRequest)`에 `purpose="weekly_report"`,
  F4 프롬프트·JSON 스키마·포함 메일만 전달한다. 제외 메일·user_id는 보내지 않는다.
  `load_providers` 미설정이면 생성을 거부한다. 별도 SDK·키·가짜 기본 응답은 없다.
- 대역: 명시적 검사 모드만 허용하고 저장·API·화면의 `test_double` 표시를 유지한다.
  운영 런타임은 대역 분석을 pending으로 취급하며 저장된 대역 보고서도 거부한다.
- 인증: 기존 Bearer·Host·Origin·LocalSession을 재사용한다. 사용자·계정은 요청에서
  받지 않는다. 운영 등록은 미통합이며 테스트·검토 앱에서만 명시적으로 등록한다.

## 저장·근거·편집

`weekly_reports(report_id, user_id, selection_key, revision, payload)`에 저장한다.
선택 키에 계정·기간·프로필·문체·대상을 포함하고 사용자+선택 키는 유일하다. payload에는
계정·대상 메일·프로필·검증 문서를 보관한다. 수정은 버전 비교 후 갱신하며 조회·제외 조회·
편집 때 사용자와 계정을 다시 확인한다. 다른 소유자는 404다.

같은 선택의 저장본을 재사용하고 재생성은 현재 메일을 다시 읽는다. AI·검증·저장 실패와
동시 수정 때 기존 편집본을 보존한다. `GET /reports/weekly/options`, `POST /reports/weekly`,
`GET /reports/weekly/{id}`, `/excluded`, `PATCH /reports/weekly/{id}`만 제공한다.

섹션 이름·순서는 프로필과 같고 항목마다 비어 있지 않은 본문·실제 대상 mail_id가 필요하다.
제외·다른 사용자·기간 밖·없는 ID·중복 근거·중복 항목을 거부한다. ID 검증이 문장 의미까지
보증하지는 않는다. 실제 모델의 사실성·30초 성능은 별도다.

S08 기능 화면은 정해진 다섯 IPC 동작을 받는다. 실제 main/preload·앱 경로는 패치에만
있다. Renderer에 URL·토큰·파일·임의 HTTP 권한을 주지 않는다. 검토 실행기는 합성 메일·
별도 SQLite·임시 토큰만 사용하며 운영 DB·Gmail에 연결하지 않는다. Word·발송·예약·메일
외 입력은 이번 범위 밖이다. 최신 검사 결과는 [F4-shared-verification.md](F4-shared-verification.md).
