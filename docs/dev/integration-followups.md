# 다음 통합 작업

2026-11-25 · 공유 준비 기준 develop `f3c09f7`(#49). 이미 반영된 패치는 다시 적용하지 않는다.

## 현재 작업

README·설치·더블클릭 실행 정리는 #49로 병합됐다. [실행 도구 검증/제한](colleague-setup-verification.md).
main 공유용 안내와 구성도는 코드와 함께 #51로 반영했다. [공유 버전 점검](main-sharing-verification.md).

## 실제 확인이 필요한 것

- 동료의 새 macOS/Windows 설치 → Google 연결 → 로컬 모델 → 앱 실행.
- 더블클릭 실행·중복 방지·종료·Windows 파일 권한·Finder PATH.
- 별도 테스트 Calendar의 실제 동의·등록·해제, 실제 Claude 키/비용/응답 품질.
- 자연어 질문의 실제 관련도·속도와 기존 F1 벡터/모델 호환성.

## 후속 개발 후보

- F2 관련 메일 검색·F1 요청 추출 활용, F5 회신 제안→F2 초안.
- 앱 안 알림함부터 OS 알림·트레이·시작 프로그램으로 확장.
- 주기 수신·추가 검색 필터·메일 정리·실제 문체 학습은 각각 별도 범위로 결정.
- 설치형 exe/dmg와 자동 업데이트는 후속 개발 후보.

## 구조 정리 후보 (import-linter 동결 목록)

서버 계층 규칙은 `uv run --locked --directory apps/server lint-imports`로 검사하며 CI에서도 돈다.
처음 도입할 때 이미 있던 위반 8건은 `apps/server/pyproject.toml`의 `ignore_imports`에 동결했다(새 위반만 막음).
고칠 때마다 그 줄을 지워 규칙을 조인다.

- 저장소가 서비스 쪽 오류·포트 정의를 가져다 씀 7건: `f5_errors`, `report_ports`, `search_rules`, `search_ports`, `pipeline.embed`.
  정의를 하위 계층(예: `app/schemas`)으로 옮기면 해소된다.
- `ai/search_semantic`이 SQL 저장소를 직접 만듦 1건: 실행 명령의 조립 코드로 옮기면 해소된다.
- API 파일마다 DB 오류→HTTP 오류 변환이 응답 코드·문구가 달라 한 곳으로 합치면 앱이 받는 응답이 바뀐다.
  합치려면 앱 쪽 오류 처리와 함께 별도 작업으로 한다.
- 프런트 기능 폴더의 생성 타입(`profile-draft/api-schema.generated.d.ts`, `suggestions/f5-api.d.ts`)이
  `packages/api-types`와 겹친다. 통합 채팅에서 하나로 합친다.

[과거 개발 요청](archive/2026-11-25/before-colleague-integration-followups.md)은 당시 기록이다.
자동 프로필 미리보기 로컬 고정·로컬 전용·Claude→로컬 재시도·과거 메일·Calendar·의미 검색은 이미 반영됐다.
