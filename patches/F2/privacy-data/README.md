# F2 개인정보·학습 데이터 연결 요청

기준: develop `7668d94aa5f251541d95e17c9ed238fabc52b418` (#41 병합).
이번 파일들은 **미적용**이다. 상위 F2/01~05 역사 패치를 재적용하지 않는다.

1. 기능 코드를 승인된 절차로 통합 작업 브랜치에 가져온다.
2. 아래 세 패치를 함께 `git apply --check`한 뒤 적용한다. 01은 공통 App, 02는 설정 메뉴 연결, 03은 경로 export다.
   `git apply patches/F2/privacy-data/01-app-route.patch patches/F2/privacy-data/02-settings-navigation.patch patches/F2/privacy-data/03-route-export.patch`
3. `/settings/profile` → 개인정보·학습 데이터 → `/settings/privacy` → 내 프로필·문체 복귀를 검사한다. 미저장 프로필은 기존 leave 확인을 따른다.
4. 타입 검사·앱 검사·분리 DB 서버 검사를 다시 실행한다. 새 IPC/main/preload·공유 타입·마이그레이션은 필요 없다.

기존 GET /profile/style의 응답 형식은 유지한다. 동의가 꺼져도 관리 화면용 보관 기록(건수·제외되지 않은 표현·특징)을 반환한다.
초안 내부 repository.style 기본 호출은 동의가 꺼지면 빈 결과를 반환한다. 제외 표현은 GET /profile의 excluded_phrases로 조회한다.
DELETE /profile/style은 현재 사용자의 문체 결과와 제외 표현만 삭제하고 동의를 끈다. 그 외 프로필 항목과 초안·메일·자격 증명은 유지한다.
실제 수집·학습 작업자는 없고 화면은 항상 준비 중으로 표시한다.

통합 시 공통 API 문서에 위 조회 의미를 기록한다. progress.md에는 이번 기능과 미적용 패치·검사 결과를 반영한다.

## 2026-11-25 통합 적용 기록

`integrate/settings-calendar`에서 실제 연결을 적용했다. 겹치는 App/routes는 통합 수정했으며
생성 타입은 공통 생성 명령으로 재생성했다. 이 폴더는 원본 제안 기록이므로 재적용하지 않는다.
최종 develop 반영 상태와 검사는 통합 PR 및 `docs/dev/settings-calendar-integration.md`를 따른다.
