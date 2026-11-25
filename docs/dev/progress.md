# 개발 현황판

2026-11-25 · 동료용 첫 공유 버전 **main `6c43e30` (#51)** · 개발 통합은 develop.

| 기능 | 구현·연결 | 남은 범위 | 상세 |
| --- | --- | --- | --- |
| F0 | Gmail 목록/본문·새로고침·과거 INBOX·설정/기능 이동 | 최초 앱 로그인 완료·메일 쓰기/정리·주기 수신 | [status](F0-mailbox-status.md) |
| F1 | 로컬 분석·분류 변경·벡터 저장·재시도·F5 훅 | 근거 강조·스마트 보기/건수·실제 품질/속도 | [status](F1-analysis-status.md) |
| F2 | 프로필·초안·수정·개인정보·학습 동의/기록 관리 | 관련 메일/분석 요청 활용·실제 학습 수집·발송 | [status](F2-profile-draft-status.md) |
| F3 | 자연어·확장·키워드/벡터 결합·근거·앱 연결 | 추가 조건·보낸 메일 열기·실제 관련도/지연 | [status](F3-search-status.md) |
| F4 | 첫 주 보고·근거·편집/저장/복사·이동 보존 | Word·예약·발송·실제 품질/속도 | [status](F4-weekly-report-status.md) |
| F5 | 제안/할 일·Calendar 추가 동의/승인 등록 | 회신 실행·앱/OS 알림·트레이/시작·리마인더 | [status](F5-ai-scan-status.md) |

## 공유 버전과 저장소 정리

- 동료용 안내는 #50으로 develop에 반영했고 앱·서버·DB 설정·실행 파일과 함께 #51로 main에 반영했다.
- 저장소 정리 작업은 `docs/repository-tidy`에서 진행한다. 초기 디자인 이미지를 문서 아래 보관하고, 패치·통합 자료에는 폴더 안내를 추가한다.
- [공유 버전 점검](main-sharing-verification.md) / [실행 도구 검사](colleague-setup-verification.md).

## 반영 이력과 확인 수준

- #39 로컬 정책/재시도/과거 메일, #40~#41 F2/F1 안정화, #42~#46 개인정보/보고/Calendar/설정 통합 완료.
- #49 동료 설치 안내·더블클릭 실행 도구 병합(`f3c09f7`). 세 OS 실행 도구 CI와 서버·앱 CI 통과.
- #47~#48 자연어·의미 검색 및 공통 연결 완료. 패치 폴더는 기록이며 다시 적용하지 않는다.
- 최근 통합 검사 기록: 서버693/skip0·앱215. 해당 작업 당시 합성/분리 DB 결과이며 이번 재실행과 구분한다.
- 기존 사용자 macOS 사용 확인 보고(API 키 입력 제외). 새 동료 설치·두 OS 더블클릭·실제 Claude 품질/요금은 미검증.
- [설치/실행](setup.md) / [다음 개발](integration-followups.md) / [이전 현황판](archive/2026-11-25/before-colleague-progress.md).

## 마이그레이션 번호 예약

기존 0001~0009는 develop에 반영되어 있다. 새 번호는 원격 실제 이력 확인 후 이 표에 예약한다.
개인 PC 설치 여부는 `alembic current`와 `check_database`로 별도 확인한다.

| 번호 | revision / 부모 | 내용 | 상태 |
| --- | --- | --- | --- |
| 0001 | 0001 / 없음 | 초기 메일 저장 | develop |
| 0002 | 0002 / 0001 | Google 자격 증명 | develop |
| 0003 | 0003_search_runs / 0002 | 최근 검색 | develop |
| 0004 | 0004_f2 / 0003_search_runs | 프로필·초안 | develop |
| 0005 | 0005_f5 / 0004_f2 | 제안·할 일·이벤트 | develop |
| 0006 | 0006_f4 / 0005_f5 | 주간 보고 | develop |
| 0007 | 0007_f1 / 0006_f4 | 분석·벡터·피드백 | develop |
| 0008 | 0008_history / 0007_f1 | 명시적 과거 메일 가져오기 | develop |
| 0009 | 0009_f5_calendar / 0008_history | Calendar 별도 암호문 | develop |
