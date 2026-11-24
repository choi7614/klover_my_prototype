# 결정 사항 로그

새 결정은 **맨 위에** 추가한다. 형식: 날짜 · 항목 · 결정 · 이유/출처 · 반영한 문서

| 날짜 | 항목 | 결정 | 이유·출처 | 반영 문서 |
| --- | --- | --- | --- | --- |
| 2026-11-24 | 통합 구현 범위 확정 | 로컬 전용 AI 서버 강제·자동 미리보기 로컬 고정·Claude 제공자 오류 시 로컬 1회 전환. 기간 선택 과거 INBOX 가져오기는 한국 날짜 최대 366일/작업당 10,000건, 중단/재개/중복 방지와 로컬 분석·검색·보고 연결. 기본 수신 시작/커서·기존 데이터 보존. 실제 서비스 미검증·develop 반영 PR #39(사용자 병합 승인 완료) | 사용자의 이 통합 채팅 구현 요청 | dev/local-ai-history-run, dev/verification-local-ai-history |
| 2026-11-24 | 실행 안내·현재 기획 정리 | 앱·서버·PostgreSQL 유지, 클라우드 이전 보류, 사내망 장기 목표. 기본 AI는 로컬이며 필요한 F2/F3/F4만 Claude 선택. 기존 동의·자료/요금 안내·앱 키 입력과 현재 서버 암호화 보관 유지. Claude 실패 후 로컬 1회 재시도와 Claude 선택/호출/검사를 막는 로컬 전용 모드는 개발 예정·미구현. 기본 수신은 시작 이후 유지하되 기간 선택·명시 실행·보존/중복 방지·진행/중단/재시도·로컬 분석/검색/보고 연결을 갖춘 과거 메일 가져오기를 개발 예정으로 확정. 가져오기 자체의 Claude 호출 금지 | 사용자 문서 정리 요청. 코드 구현 승인 아님. PR #37과 실제 코드 대조 | dev/setup, dev/progress, features/planned-mail-history-import, architecture/system |
| 2026-11-20 | 기능별 AI 선택·첫 주 보고 | F2 초안·수정, F3 질의 해석·답변, F4 보고서의 기본 제공자를 앱에서 각각 로컬/Claude로 저장하고 요청별 변경. 자동 F1 분석·F5 제안·임베딩은 로컬 유지. 로컬 운영자가 앱에서 외부 전송·비용을 허용한 경우 세 수동 기능은 실제 메일 사용 가능(기존 Claude 테스트 데이터 제한을 이 범위에서 대체). 키·설정은 서버 로컬 암호화 파일에 저장, 실패 시 다른 제공자로 전환하지 않음. 답장·보고서 화면 진입은 조회만 하고 생성 버튼으로 실행. 첫 주도 시작일부터 오늘까지 확보된 자료로 보고하며 기간·건수·일부 기간 표시. 기존 메일 추가 수집 없음 | 사용자 통합 구현 요청 | features/F2~F4, architecture/api, dev/ai-provider-selection |
| 2026-11-19 | LLM·임베딩 제공자 | LLM은 `.env`의 `AI_PROVIDER`로 **Claude API**(공식 SDK, 기본 `claude-opus-5-5`, 기능별 모델 설정 가능)와 **로컬 Ollama**(Qwen 계열, 모델 태그는 `.env` 필수·미정) 중 선택. 미설정이면 미연결로 멈추고 가짜 결과로 대체하지 않음. 임베딩은 제공자와 관계없이 로컬 Ollama `bge-m3`(1024차원). Ollama는 이 컴퓨터 주소만 허용(외부 전송 없음). Claude는 보안 확인 전까지 테스트 데이터만: `AI_CLAUDE_TEST_DATA_ONLY=true` 확인 필수, F1 실행 명령은 Claude로 실제 Gmail 본문을 보내지 않음. 비용 예측을 위해 Claude 거절 시 다른 모델로 넘기는 기능은 끔, 기본 effort `low`. 2026-10-14 'LLM·임베딩 모델: 현재 외부 API' 결정을 대체 | 사용자 결정(F1 채팅) | features/F1, architecture/system, open-questions 14, dev/F1-analysis-status |
| 2026-11-19 | 받은편지함 새로고침 | 새로고침은 `POST /mails/sync`로 Gmail에서 새 받은 메일을 가져온 뒤 목록을 다시 읽는다(기존 'DB 재조회만' 대체). CLI `gmail_mail sync`와 같은 수신 기능을 재사용해 시작 시점 이후만·중복 방지 규칙 유지. 한 번에 하나만 실행(409), 진행 중 표시·실패 문구·재시도. main/preload 연결 전에는 저장된 목록만 다시 읽고 그렇게 안내. 주기 자동 수신(WebSocket·큐)은 후속 | 사용자 요청(F0 채팅) | features/F0, architecture/api, dev/mail-read-api, dev/F0-mailbox-run |
| 2026-11-19 | 로컬 앱의 실제 메일 열람 | 기존 Google·DB 키와 분리한 로컬 Bearer 인증으로 연결 계정·받은 메일·일반 텍스트 본문을 읽는다. 토큰은 Electron main만 보관하고 제한된 IPC로 화면에 전달. Windows 목표 유지, 맥북 개발 실행을 먼저 확인. Gmail 새 메일 저장·중복 방지는 사용자 확인, 새 조회 API·F0 화면은 실제 맥북 검증 대기 | 사용자의 서버 API 구현 및 F0 전달·맥북 실행 요청 | dev/mail-read-api, dev/F0-mail-api-handoff, architecture/api |
| 2026-11-19 | 새 Gmail 수신 단위 | 기존 연결·시작 시점·키·메일을 보존하며 명령 기반 INBOX 수신·저장·조회·토큰 갱신 구현. 이력 만료는 같은 시작 시점으로 재조회, F0·메일 API·주기 수신은 후속. 실제 새 수신은 맥북에서 별도 확인 | 사용자 구현 요청, 이전 실제 로그인 성공 보고 | dev/gmail-mail-sync, architecture/data-model |
| 2026-11-19 | Gmail 연결 첫 단위 | 맥북 전용 브라우저 로그인·Gmail 읽기 권한·계정 확인과 토큰 암호화 저장부터 구현. 고정 복귀 주소·state·PKCE 적용. 실제 계정 검증은 사용자 맥북에서 별도 진행. 메일 수신·앱용 인증은 후속 단위 | 사용자의 명시적 첫 단위 범위 요청 | dev/google-connection, architecture/api, architecture/data-model, features/F0 |
| 2026-11-18 | 개인 개발 환경과 Gmail 우선 연결 | 맥북의 로컬 PostgreSQL에 최소 사용자·계정·메일 저장소부터 준비하고, 실제 테스트 Gmail의 새 메일 연결을 다음으로 진행. 자동 검사만 합성 데이터 사용. OAuth 복귀 주소는 `http://localhost:8000/auth/google/callback`으로 준비 예정이며 아직 미구현 | 사용자의 개인 Google 프로젝트 준비·실제 Gmail 우선 요청 | dev/local-database, architecture/data-model |
| 2026-11-12 | F4 첫 구현 단위 | 한국 날짜 범위의 메일 조회·분류 제외·스레드/프로젝트 그룹을 먼저 검증. 분석이 미완료인 업무 메일은 조용히 제외하지 않고 준비 실패로 알림 | 앱·DB·F1·F2·AI 구현 부재, F4 단계별 개발 요청 | dev/F4-weekly-report-plan, architecture/data-model, architecture/api |
| 2026-10-20 | 로고 | 네 잎 클로버(하트 모양 잎 4개) + 가운데 보라 ◆(AI) + 소문자 워드마크 `klover` | 디자인 작업 | design/brand |
| 2026-10-20 | 색 체계 | 초록 = 브랜드·실행 버튼(primary #158446), 보라 = AI 전용(#5B4FE0). 모든 글자 대비 4.5:1 이상 | 디자인 작업 | design-system |
| 2026-10-20 | UI 구현 방식 | Tailwind v4 + shadcn/ui + `klover-theme.css` 토큰, Pretendard, lucide 아이콘 | 디자인 작업 | design-system |
| 2026-10-20 | 화면 기준 | 화면 정의서 S01~S10 + Klover 목업이 개발 기준. 설계안 v0.2는 와이어프레임으로 보관. S03 받은편지함을 기준 화면으로 먼저 구현 | 디자인 작업 | design/screens |
| 2026-10-16 | 개발 분담 | 기능 단위로 한 사람이 서버~화면까지 담당 (A: 앱 뼈대·F0 / B: 서버 뼈대·Gmail·DB / C: F1·F5 / D: F2·F3·F4) | 프로젝트 구조 추천안 검토 | overview, dev/workflow |
| 2026-10-16 | 기술 스택 | Electron+React+TS / FastAPI / PostgreSQL+pgvector / Redis+arq | 프로젝트 구조 추천안 | architecture/system |
| 2026-10-16 | 서비스 이름 | Klover | 팀 결정 | overview |
| 2026-10-14 | 앱의 역할 | Gmail을 대체하는 메일 앱. 작성·보내기·보관·삭제·스팸 등 기본 메일 기능 모두 포함 | 설계안 v0.2 | F0 |
| 2026-10-14 | 서버 위치·보관 | 저장소·모델 호출부를 분리해 사내 구축으로 옮길 수 있게 설계. 사용자가 보관 처리한 메일은 삭제 전까지 유지 | 설계안 v0.2 | F1, architecture |
| 2026-10-14 | LLM·임베딩 모델 | 현재 외부 API, 3단계에서 사내 모델로 전환 | 설계안 v0.2 | architecture |
| 2026-10-14 | 과거 메일 범위 | 과거 메일 없이 빈 상태로 시작, 이후 도착하는 메일부터 분석 | 설계안 v0.2 | F0, F1 |
| 2026-10-14 | 카테고리 체계 | 고정 7종으로 시작, 사용자 수정을 학습 | 설계안 v0.2 | F1 |
| 2026-10-14 | 문체 학습 | 첫 실행 때 동의를 받고 켬. 이 앱에서 보낸 메일이 쌓이는 대로 학습 | 설계안 v0.2 | F0, F2 |
| 2026-10-14 | 캘린더·할 일 | 캘린더는 Google Calendar, 할 일은 앱 안에서 관리 | 설계안 v0.2 | F5 |
| 2026-10-14 | 알림 | 앱 실행 중 모든 AI 제안 즉시 알림. 시작 프로그램 등록, 트레이 상주. 꺼져 있던 동안 제안은 다음 실행 때 모아서 표시 | 설계안 v0.2 | F0, F5 |
| 2026-10-14 | 주간 보고 양식 | 개인이 설정 (섹션 순서, 보고 대상, 표현 방식) | 설계안 v0.2 | F2, F4 |
| 2026-10-14 | 검색 결과 형태 | 결과 목록 + AI 답변 요약은 1차, 이어서 질문하기는 2차 | 설계안 v0.2 | F3 |
