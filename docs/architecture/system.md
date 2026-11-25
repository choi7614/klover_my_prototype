# 시스템 구조 — 현재 구현과 목표

[쉽게 보는 구성도](overview.md) · [설치·실행](../dev/setup.md)

## 로컬 정책·과거 수신 통합 (2026-11-24)

요청 범위의 AI 정책·결과 출처를 공통 실행부에서 관리한다. 자동 미리보기·분석은 로컬,
수동 Claude 실패는 로컬 1회 전환한다. 과거 수신은 전용 스레드와 DB 체크포인트를 사용하며
일반 수신 커서를 공유하지 않는다. [정책·기간·상한·업데이트](../dev/local-ai-history-run.md)를 따른다.

## 현재 구성

앱(Electron+React+TypeScript), 서버(Python FastAPI), PostgreSQL 16+pgvector, 로컬 Ollama를
같은 컴퓨터에서 사용한다. 현재 구성을 유지하며 **클라우드 이전은 보류**, 사내망 적용은 장기 목표다.
설치 파일·다중 사용자 공유 서버를 제공하는 단계는 아니다.

```text
Electron renderer → 제한된 preload IPC → Electron main → 로컬 Bearer API
                                                       ↓
           run_mail_api (FastAPI, 단일 로컬 운영자) → PostgreSQL
                 ↓              ↓                       (메일·분석·프로필·초안·보고·제안)
             Gmail INBOX     로컬 Ollama (생성·bge-m3)
                 └ 서버가 선택한 수동 F2/F3/F4만 Claude API에 직접 요청
                 └ 추가 동의·사용자 승인 시 Calendar API에 직접 요청
```

| 구성 요소 | 현재 코드·상태 |
| --- | --- |
| 데스크톱 | `apps/desktop/src/main`, `preload`, `renderer`. React·Tailwind/shadcn 기반. 실제 의존성은 package.json 기준 |
| 업무 서버 | `apps/server/app/cli/run_mail_api.py`가 저장소·AI·계정·API를 조립. 일반 app.main은 경로·스키마/health 기반일 뿐 같은 실행 상태가 아님 |
| Google 최초 연결 | 별도 `run_google_connection` CLI·브라우저. 앱 연결 버튼은 미구현 |
| 메일 수신 | 앱 새로고침/명시적 CLI, 시작 이후 INBOX·중복 방지. 주기 수신은 없음 |
| 분석 | sync 후 서버 내부 백그라운드 작업자 스레드가 로컬 F1 분석·임베딩 수행. 완료 뒤 로컬 F5 훅으로 제안 저장 |
| 분석 표시 | 앱의 조회·재시도·상태 폴링. WebSocket 푸시 아님 |
| AI | F2/F3/F4는 요청별 `SelectedGeneration`, 자동 F1/임베딩/F5는 로컬만 주입 |
| 검색 | SQL 기간·상대·키워드+선택 AI 해석/답변. F1 로컬 임베딩·호환 벡터 검색 연결, 실패 시 키워드 유지. 반영 상태는 [통합 기록](../dev/F3-memory-search-integration.md) 참조 |
| 주간 보고 | F1 저장소·F2 프로필·선택 AI·0006 보고 저장·앱 연결. 첫 주 생성 지원, 자료·프로필 필요 |
| F5 | F1 결과→제안 변환·S04/할 일·승인 경계. 별도 OAuth 동의·ConnectedCalendar 승인 등록 연결, OS 알림/트레이 없음 |
| 공유 타입 | OpenAPI → `packages/api-types` 자동 생성. 직접 수정 금지 |
| 로컬 DB | Compose의 db 서비스만. Redis/arq·별도 workers·WebSocket은 현재 구현/실행 대상 아님 |

## 데이터·승인·키 경계

1. 앱 새로고침은 서버가 새 메일을 저장한 후 분석 신호를 주고 응답한다. CLI sync는 분석 신호를 주지 않는다.
2. 기본 수신은 계정 `sync_started_at` 이후다. 명시적 가져오기로 저장한 과거 메일도 조회한다. 분석 결과·원문 근거를 저장하고 F2/F3/F4/F5가 이용한다.
3. 기본 AI는 로컬. 필요한 F2 초안·수정, F3 검색·답변, F4 보고만 Claude를 선택하며 최초 외부 전송·비용 동의가 필요하다.
4. 키는 앱에서 입력하고 서버 `.local-secrets/ai-settings.enc`에 암호화 저장한다. `ai-settings.key`는 별도이며 기존 Google `token.key`·DB·메일을 바꾸지 않는다.
5. **프로필 자동 미리보기**: 저장 기본값·요청 선택과 무관하게 서버에서 로컬만 사용한다.
6. 사용자 버튼·동의 없이 메일 발송/Calendar 실행하지 않는다. 현재 메일 발송은 미구현이다. Calendar는 별도 동의/연결과 사용자 승인 후 서버가 등록하며 양방향 동기화는 미구현이다.

로컬 전용 모드는 서버에서도 Claude 생성·연결 검사를 차단한다. 선택적 Claude 모드에서는 제공자 오류·시간 초과에 한해
로컬로 1회 전환한다. 거절·취소·미동의·근거 검증 오류는 전환하지 않으며 기존 형식 보정 재시도와 구분한다.

## 이번 구현과 장기 목표

- [기간 선택 과거 메일 가져오기](../product/features/planned-mail-history-import.md): 기본 수신은 유지하며 명시 실행·진행/중단/재시도·중복 방지·로컬 분석·검색/보고 연결. 명시적 가져오기 표시로 저장·조회·검색·분석 경계를 정비했다. 일반 수신 경계는 유지한다. 가져오기만으로 Claude 호출 금지.
- Claude 실패 시 로컬 1회 자동 재시도, 로컬 전용 모드의 Claude 선택/호출/검사 차단은 PR #39로 develop에 병합됐으며 동료용 main 공유 범위에 포함된다.
- Redis/arq·주기 수신·WebSocket·트레이·설치 파일·다른 메일 소스는 목표 구조이며 현재 설치 명령으로 안내하지 않는다.
- 사내망은 장기 목표. 외부 API 허용은 별도 보안 검토가 필요하고 개인 동의로 대체하지 않는다.

## 유지할 구조 원칙

- 앱은 서버 API만 호출한다. Gmail·LLM·DB를 renderer에서 직접 호출하지 않는다.
- 메일 소스별 코드는 connectors, 모델 호출은 ai 인터페이스, DB 접근은 db/repositories 경계를 따른다.
- AI는 제안하고 근거 메일을 연결한다. 사용자 승인 없는 외부 실행을 추가하지 않는다.

## 원본 설계와 기록

[기존 구조 문서](../dev/archive/2026-11-24/system-before.md)와 [설계안 원본](../design/mockups/README.md)을 보존했다.
그림의 Redis+arq·Windows 토스트·30초 수신은 목표 구조이며 현재 구현을 보증하지 않는다.
Calendar의 현재 범위는 [설정·Calendar 통합](../dev/settings-calendar-integration.md)을 따른다.
