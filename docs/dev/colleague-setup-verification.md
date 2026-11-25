# 동료용 안내·실행 도구 검증

2026-11-25 · `integrate/colleague-setup` · 기준 develop `9946b87`(#48).
구현·검사 보고 후 커밋·Push·PR 생성과 검사 통과 시 develop 병합을 승인받았다. main은 변경하지 않는다.

## 기존 작업 재사용

- `/workspace/klover-desktop-launcher`의 미커밋 11개 파일을 그대로 보존했다.
- 최신 develop의 별도 worktree에서 실행 스크립트·검사·시작 파일을 재사용했다.
- 기존 브랜치를 초기화하거나 기존 미커밋 문서를 덮어쓰지 않았다.
- 최신 모델·API·마이그레이션과 대조했다. 실행 도구 자체는 DB 이력/앱 기능/API/잠금 의존성을 바꾸지 않는다.

## 수정 내용

- README: develop 받기 → 최초 설치 → 평소 더블클릭 → 현재 제공/미제공 기능 → 확인 수준 순서로 정리.
- setup: OS 공통/별도 명령 구분, head 0009, 설정/Calendar/의미 검색 현황, Windows 바이너리 백업 주의,
  일상 실행/수동 실행/업데이트 구분. 키·계정의 최초 설정은 계속 본인 PC에서 한다.
- 문서 지도·현황판·F0~F5 status·통합 후속 목록을 최신 상태로 정리했다.
  과거 현황판/요청 원문은 archive에, 기능 status 원문은 접힌 과거 기록에 보존했다.
- 실행 도구: `.command`/`.cmd` → Python 공통 실행기. 사전 설치된 도구만 사용하며 자동 설치·마이그레이션 없음.
- Windows 잠금 검사에서 이미 잠긴 바이트를 읽지 않도록 개선했다. Windows에서 없는 POSIX API의 합성 검사도 분리했다.
- 실제 자식 프로세스를 종료하면서 무관한 프로세스를 유지하는 검사 추가.
- Linux/macOS/Windows 단위 검사 워크플로 준비. PR 생성 전이므로 원격 OS별 CI 실행 결과는 아직 없다.

## 검증 결과

- 실행 도구 선택 검사: **20 통과 / 1 skip**. skip은 실제 cmd 시작 파일 검사로 Windows CI에서 실행한다.
- 코드/형식 검사: 서버 Ruff 전체, 실행 도구 Ruff(서버 설정 기준), bash 시작 파일 문법, diff 공백 검사 통과.
- 앱 제품 코드는 변경하지 않아 앱 빌드/전체 테스트를 반복하지 않았다.
- 분리 PostgreSQL을 사용하는 서버 전체: **713 통과 / 1 skip** (98.98초). 생략 항목은 위 Windows 시작 파일 검사다.
- 현재 사용자 안내·현황·status 문서의 로컬 참조 경로 검사 통과. 과거 원문 보관본은 현재 안내와 구분했다.

새 의존성 재설치·실제 사용자 설정 복사·실제 Gmail·Calendar·유료 Claude·Ollama 모델 생성은 수행하지 않았다.

## 한계와 실제 확인

- 이번 실행 도구의 실제 Finder/탐색기→Docker/Ollama→앱 시작·종료는 macOS/Windows 기기에서 미검증이다.
- 기존 사용자 macOS 사용 확인 보고는 이번 실행 도구나 동료 신규 설치 성공을 뜻하지 않는다. Claude 키 연결도 미확인이다.
- Linux 합성/자식 프로세스 검사는 전체 OS/앱 통합 검사를 대신하지 않는다.
- PowerShell·Windows ACL·Docker Desktop·Google 동의/권한·모델 품질·회사망 환경은 동료 환경에서 확인해야 한다.

동료에게는 develop README 링크와 본인 OS 설치 안내를 전달한다. 최초 설정 후 실행 파일을 더블클릭하고,
기존 Gmail 조회·분석·초안·검색·첫 주 보고·선택적 Calendar를 테스트 계정/합성 내용으로 확인한다.
실제 기록 삭제나 기존 DB 초기화로 검증하지 않는다.

## 변경 파일 묶음

- README·docs/README·setup·desktop-launcher: 사용자 시작/실행 안내.
- progress·F0~F5 status·integration-followups·archive: 현재/과거 상태 분리와 근거 보존.
- `Klover-Start.command`, `Klover-Start.cmd`, `scripts/launcher/run.py`: 실행·상태 확인·소유 프로세스 정리.
- `.gitattributes`, `.gitignore`: OS별 줄바꿈과 비공개 실행 잠금 제외.
- `apps/server/tests/test_desktop_launcher.py`, `.github/workflows/launcher.yml`: 합성/자식 프로세스 및 OS별 검사.
