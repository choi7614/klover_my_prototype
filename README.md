# Klover

> 받은 메일을 AI가 바로 읽고 분류·요약·제안까지 해 주는 Windows 데스크톱 메일 앱

**Klover** = 클로버(Clover)의 C를 **K**oscom의 K로. 현재 데모 단계이며 Gmail로 시작합니다.

## 주요 기능

| 번호 | 기능 | 한 줄 설명 |
| --- | --- | --- |
| F0 | 첫 실행·기본 메일함 | Gmail을 대체하는 메일 앱, 과거 메일 없이 빈 받은편지함에서 시작 |
| F1 | 메일 분류·저장 | 도착한 메일을 7개 카테고리로 분류하고 요약·할 일·마감을 추출해 메타데이터·벡터로 저장 |
| F2 | 프로필·답장 초안 | 내 부서·문체·서명으로 '내가 쓴 것처럼' 답장 초안 작성 |
| F3 | 자연어 검색 | "지난달 영업기획팀 예산 메일 중 답 안 한 거" 처럼 말하듯 검색 |
| F4 | 주간 보고 | 한 주의 메일을 업무별로 묶어 내 양식의 보고서로 정리 |
| F5 | AI 스캔 | 메일 수신 즉시 일정 등록·할 일·회신을 Windows 알림으로 제안 |

자세한 내용: [docs/README.md](docs/README.md)

## 구성

```
klover/
├─ docs/          기능 정의서, 디자인 시스템, 구조, 개발 규칙
├─ apps/desktop/  데스크톱 앱 (Electron + React + TypeScript)
├─ apps/server/   서버 (Python FastAPI)
├─ packages/      공유 타입
├─ fixtures/      데모용 가짜 메일
└─ infra/         Docker Compose (PostgreSQL + pgvector)
```

- 데스크톱: Windows 10 이상, 트레이 상주, 시작 프로그램 등록
- 메일 소스: Gmail(1단계) → 사외 웹메일(2단계) → 사내 메일(3단계)

## 시작하기

개발 환경 준비와 실행 방법은 [docs/dev/setup.md](docs/dev/setup.md),
작업 방식(채팅 운영, 브랜치, Codex·Claude 전환)은 [docs/dev/workflow.md](docs/dev/workflow.md)를 보세요.
현재 진행 상황은 [docs/dev/progress.md](docs/dev/progress.md) 현황판에 있습니다.

작업 규칙은 루트의 [AGENTS.md](AGENTS.md) 하나로 관리합니다. GPT Codex는 AGENTS.md를,
Claude Code는 이를 불러오는 [CLAUDE.md](CLAUDE.md)를 자동으로 읽습니다.

## 팀

Koscom CoP — 1인 개발 (GPT Codex·Claude Code를 기능별·공통·통합 채팅으로 나눠 사용)
