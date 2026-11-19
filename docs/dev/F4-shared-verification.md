# F4 최신 develop 연결 검사 — 2026-11-19

## 결과와 보존 범위

기존 `feat/F4-weekly-report`의 WIP `c061a46`과 후속 코드를 보존하고 최신 develop
`9ac5421`까지 로컬 통합했다. #2의 첫 단위 네 파일은 develop과 차이가 없다.
첫 통합 충돌은 `app/ai/__init__.py`, F4 status, progress였고 공통 AI는 develop 원본을
선택했다. F5 추가 통합의 progress 충돌도 다른 기능 행·0005_f5 이력을 보존해 정리했다.
원래 `/workspace/klover-f4-review` 미커밋 사본 32개는 건드리지 않았다.

공통 DB·Alembic·app.main·실행 조립·App·main/preload·공유 타입·잠금 파일은
실제 최신 develop과 같다. **F4 운영 등록·DB 설치·앱 진입은 미통합**이다.
main·실제 계정·키·메일·수신 기능을 보존했다.

## 실제 연결과 변경 파일

| 파일·영역 | 변경 목적 |
| --- | --- |
| `app/db/repositories/report_profile.py` | 실제 F2 report_profile 읽기·섹션 키 변환·기본값 보존 |
| `app/services/weekly_report_runtime.py` | 실제 F1/F2·F4 저장소·공통 AI를 인증된 사용자·계정으로 조립 |
| `app/ai/weekly_report.py`, 프롬프트 | 공통 TextGeneration·GenerationRequest 재사용. 자체 제공자·가짜 기본 응답 없음 |
| `app/services/weekly_report.py`, `app/schemas/weekly_report.py` | 계정별 분리·빈 F2 대상 입력·대역 결과 운영 차단 |
| `app/api/weekly_report.py` | 기존 인증·계정 재사용, 소유자 주입 거부, 중복 등록 방지 |
| `features/weekly-report/ipc-client.*`, `types.ts`, `client.ts` | 다섯 동작 전송 포트·연결 실패 전달 |
| `weekly-report-page.tsx`, 화면 검사 | 빈 F2 대상 입력 전 생성하지 않음·대역 결과 표시 |
| `test_weekly_report_adapters.py`, `test_weekly_report_shared_storage.py` | 실제 F1/F2 DB와 공통 AI 대역으로 생성·재조회·격리·실패 검사 |
| `test_weekly_report_pending_migration.py`, `test_weekly_report_ports.py` | 제안 이력 반복·기존 메일 보존·FK 호환 저장 검사 |
| `scripts/f4/prepare_integration.py`, `patches/F4/` | 원본 보존형 패치·공유 타입 자동 생성 |
| F4 plan·contract·status·progress | 최신 실제 계약·검사·미통합 범위·0006 예약 |

기존 WIP의 생성·저장·검증·화면·fixture는 계속 사용한다. 전체 변경은 PR의 develop 대비
diff로 확인한다. 오래된 `docs/dev/F4-proposals/` 패치는 보관 기록이며 적용하지 않는다.

## 검사 결과

| 검사 대상 | 결과 |
| --- | --- |
| 기능 브랜치 서버 전체, F1/F5 포함 분리 PostgreSQL | **406 통과, skip 없음** |
| 서버 Ruff 검사·포맷 | 통과 |
| 데스크톱 lint·typecheck·단위 검사 | **127 통과**, lint·typecheck 통과 |
| F4 브라우저 | 4 통과: 근거·제외·편집·복사·저장·재조회·재생성 확인/취소·실패 보존·새 항목 근거·빈 기간 |
| 기존 F0 브라우저 | 2 통과 |
| 데스크톱 빌드 | 통과. 실제 앱 F4 진입 등록 완료를 뜻하지 않음 |
| 공통 패치 적용 임시 사본 서버 전체 | **406 통과, skip 없음** |
| 공통 패치 사본 lint·typecheck·단위 검사·빌드 | **133 통과**, lint·typecheck·빌드 통과 |
| 제안 Alembic | 단일 head `0006_f4`, upgrade/downgrade 반복·모델 일치·기존 메일 보존 통과 |
| 패치 01~05 | git apply --check 통과, 실제 공통 파일 미적용 |
| 생성 API 타입 | 전체 최신 F0/F2/F3/F5 + F4에서 임시 생성·컴파일 |

DB는 이 작업이 만든 PostgreSQL16+pgvector 컨테이너의 `klover_f4_test`·`klover_f5_test`
안의 일회용 스키마만 사용했다. 합성 메일을 실제 F1 분석 저장소에 저장하고 실제 F2
프로필을 읽어 공통 AI **테스트 대역**을 호출했다. 실제 모델 생성·정확도·30초 성능
측정이 아니다. 운영 DB와 실제 Gmail에는 접근하지 않았다.

초기 b147cfd의 공통 검사 실패 3건을 F4 없는 develop 사본에서도 재현했다. 최신 F5
병합에서 이미 수정돼 중복 패치를 제거하고 전체 재검사를 통과했다.

## 확인한 계약

- 한국 날짜 양 끝·받은/보낸 메일·수정 분류 우선·공지/뉴스레터 제외·업무 묶기·범위 집계·빈 메일.
- 분석 pending/failed·운영에서 허용하지 않는 대역 분석은 준비 실패. 임의 요약·제외 수 은폐·AI 호출 없음.
- 실제 F2 프로필 부재·섹션 순서·문체·대상·빈 조직·빈 대상의 입력 처리.
- 공통 AI 요청 목적·JSON 스키마·포함 메일만 전달, 미설정·실패·잘못된 JSON/근거 처리.
- 근거 없는 항목·타 사용자·기간 밖·제외·없는 ID 거부, 저장된 문서 근거 재검증.
- 사용자·같은 사용자의 다른 계정에 대한 조회·편집·제외 조회 격리.
- 편집·복사·재생성 확인/취소, AI·검증·저장 실패·동시 수정 때 편집본 보존.
- 제안 IPC main frame 신뢰 검사·다섯 동작·고정 경로·소유자/주소 주입 거부,
  main 전용 토큰·리디렉션 금지·오류 원문 비노출.

## 미실행·미통합과 전달 요청

- 공통 서버: 패치 01~05 적용은 별도 통합 작업이다. 기존 실행·수신·다른 기능 조립을
  보존해 등록하고 운영 DB에는 자동 마이그레이션하지 않는다.
- F1: 실제 분석 실행·공통 AI 제공자 연결과 F1 저장 SQL의 정식 이력·설치 상태를 확인한다.
  인터페이스는 재사용했지만 실제 제공자와 운영 설치는 없다.
- F2: 현재 네 섹션 키·순서·문체·빈 대상 허용 계약을 유지한다. 실제 설치 DB의 0004 적용 여부 확인.
- F0: 패치 03의 `/report/weekly`·main/preload 적용 후 실제 설치 앱 검사. 기존 공통 진입 파일은 보존.
- 실제 모델 사실성·30초 성능은 제공자가 없어 미실행이다. 실제 Gmail 전송 실험은 하지 않았다.
  공휴일 표시 후속 검증·설치된 Windows/Mac 앱 검사도 완료로 표시하지 않는다.
- Word·메일 발송·예약 생성·메일 외 데이터는 사용자 지정 범위 밖이라 구현하지 않았다.

## 인계 메모

[PR #22](https://github.com/choi7614/klover_my_prototype/pull/22)에 기존 기능 브랜치를 Push했다. 코드 커밋 `1576fc8`의
GitHub CI 서버·데스크톱 작업은 모두 성공했다. CI는 DB 검사를 skip하므로 위 전용 DB
406개 결과와 구분한다. 인계 문서 커밋도 같은 CI를 통과한 뒤 병합한다.
공통 보호 파일·첫 단위 네 파일은 최신 develop과 차이가 없고 원래 검토 폴더는 HEAD
`0f68ad1`·미커밋 파일 32개 그대로다. 커밋 전 민감 파일명·키/토큰 패턴과 합성 fixture를
확인했다. 이 작업용 임시 검증 사본·테스트 DB 컨테이너만 검사 후 정리한다.
