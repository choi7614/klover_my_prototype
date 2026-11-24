# Klover

## 로컬 정책·과거 메일 가져오기 (2026-11-24)

자동 프로필 미리보기는 로컬만 사용합니다. AI 로컬 전용 모드와 Claude 실패 후 로컬 1회 전환,
기간 선택 과거 INBOX 가져오기를 작업 브랜치에 구현했습니다(PR #39 제출·사용자 병합 승인 완료). 실제 외부 AI·Gmail 검증은 남아 있습니다.
기존 사용자는 **0008 DB 업데이트가 필요**합니다. [업데이트와 확인 절차](docs/dev/local-ai-history-run.md)를 따르세요.

## 처음 방문했다면

**[설치·실행 안내 → docs/dev/setup.md](docs/dev/setup.md)**

실행 코드는 현재 **`develop`**에 있습니다. 2026-11-24 확인 기준 `develop 5e2b7a7`(PR #38)에 비해
`main 9575f47`에는 실행 코드가 없습니다. 저장소가 비공개라면 소유자에게 접근 권한을 받고 GitHub 인증을 먼저 준비하세요.

```bash
git clone --branch develop --single-branch https://github.com/choi7614/klover_my_prototype.git
cd klover_my_prototype
```

이후 [setup.md](docs/dev/setup.md)의 **새 사용자 설치**를 따르세요. 필요한 도구·DB 설정 생성·Google 프로젝트와
OAuth JSON·Ollama 모델·앱 API 토큰 준비까지 포함합니다. 기존 사용자는 같은 문서의 **업데이트**를 사용하고
DB·암호화 키·메일을 초기화하지 마세요. 설치·평소 실행·종료·오류 해결은 이 문서 한 곳이 기준입니다.

## 현재 범위와 확인 수준

| 구분 | 내용 |
| --- | --- |
| 구현·자동 검사 완료 | CLI Google 연결, 사용 시작 이후 INBOX 수신·중복 방지, 앱 목록·본문·새로고침, 로컬 분석 표시, 프로필, F2 초안, F3 검색·답변, F4 첫 주 보고, F5 제안·앱 할 일, 기능별 AI 설정 |
| 실환경 미검증 | 신규 사용자의 Google→실제 모델→Electron 전체 흐름, 실제 Claude·Ollama 품질·속도, Windows 고유 동작. 자동 검사는 실서비스 성공을 보장하지 않음 |
| 미구현 | 앱 안 Google 연결·5단계 완료, 메일 작성·발송·보관·삭제, 주기 수신, 벡터 의미 검색, 실제 Calendar, OS 알림·트레이, 설치 파일 배포 등 |
| 보류·장기 목표 | 클라우드 이전은 보류. 사내망 적용·다른 메일 소스는 장기 목표 |

완성된 Gmail 대체 제품은 아닙니다. Windows 10 이상이 제품 목표이며 이번 검사는 Linux 자동 검사 중심입니다.
macOS의 일부 연결 성공은 과거 사용자 보고이고, OS별 검증 범위는 [setup.md](docs/dev/setup.md)를 보세요.
**최초 Google 연결은 CLI가 필요합니다.** 앱 첫 화면의 Google 연결·다음 버튼은 아직 비활성입니다.

기본 수신은 사용 시작 이후 메일입니다. '과거 메일 없이 시작'은 기본 동작이며,
기간 선택 [과거 메일 가져오기](docs/product/features/planned-mail-history-import.md)는 명시적 실행으로 사용할 수 있으며 실제 Gmail 검증은 남아 있습니다.

## AI와 데이터

- 현재 앱·서버·PostgreSQL 구성을 유지합니다. 기본 AI는 로컬 Ollama, 임베딩은 로컬 bge-m3입니다.
- 필요한 F2 초안·수정, F3 검색·답변, F4 보고 요청만 Claude를 선택합니다. 최초 외부 전송 동의와 전송 자료·API 요금 안내가 있습니다.
- 키는 앱 AI 설정에서 입력하고 현재 서버에 암호화 저장합니다. Claude 구독과 API 요금은 별도입니다.
- 키·토큰·실제 메일을 Git·문서·채팅에 공유하지 마세요. DB와 암호화 키는 함께 보존합니다.

## 문서 찾기

- [문서 지도](docs/README.md): 기능 명세·UI 목업·구조 문서
- [현황판](docs/dev/progress.md): 현재 구현·미검증·예정과 F0~F5 status
- [이번 실행 검증](docs/dev/verification-2026-11-24.md): 코드·PR·검사 근거와 한계
- [통합 개발 전달 사항](docs/dev/integration-followups.md): 코드 수정이 필요한 작업
- [AGENTS.md](AGENTS.md) / [개발 절차](docs/dev/workflow.md): 개발 채팅 공통 규칙

## 출처·저작권·라이선스

설계안 원본은 [와이어프레임](docs/design/mockups/README.md), 로고 등의 출처·사용 규칙은
[브랜드 자료](docs/design/brand/README.md), 앱 브랜드 리소스는 [desktop resources](apps/desktop/resources/README.md)를 보세요.
기존 출처·저작권·라이선스 표기는 유지했습니다. 이번 기준 커밋에는 저장소 전체의 LICENSE 파일이 없습니다.
공개·재배포 허용을 뜻하지 않으므로 이용 조건은 소유자에게 확인하세요.
