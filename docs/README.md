# Klover 문서 지도

2026-11-25 · 실행 기능의 기준은 develop입니다. 처음 사용하는 동료는 [설치 안내](dev/setup.md),
설치 후 실행은 [더블클릭 안내](dev/desktop-launcher.md)를 따르세요. 아래 기능 명세의 미체크 항목과 과거 작업 기록을 현재 구현 상태로 해석하지 마세요.

## 처음 방문한 사람의 순서

1. [루트 README](../README.md): 현재 제공 범위·브랜치·제약
2. [setup.md](dev/setup.md): **새 설치·평소 실행·종료·업데이트·오류 해결의 단일 기준**
3. [현황판](dev/progress.md): 구현·실환경 미검증·미구현·확정 예정·보류/장기 목표
4. [실행 검증](dev/verification-2026-11-24.md) / [통합 전달 사항](dev/integration-followups.md): 근거와 남은 코드 작업

과거 문서/패치의 사용법은 [보관 안내](dev/archive/2026-11-24/README.md)를 먼저 읽는다. 새 설치에 패치를 적용하지 않는다.

- [AI 제공자 선택](dev/ai-provider-selection.md) — 현재 동작·개발 예정·과거 기록 구분

## product — 무엇을 만드나

| 문서 | 내용 |
| --- | --- |
| [features/planned-mail-history-import.md](product/features/planned-mail-history-import.md) | 기간 선택 과거 메일 가져오기 — 구현 범위와 제한 |
| [overview.md](product/overview.md) | 서비스 개요, 기능 목록, 기능 간 연결, 원칙 |
| [decisions.md](product/decisions.md) | 결정 사항 로그 |
| [open-questions.md](product/open-questions.md) | 남은 확인 포인트와 데모 동안의 임시 가정 |
| [features/F0-onboarding-mailbox.md](product/features/F0-onboarding-mailbox.md) | 첫 실행 설정과 기본 메일함 |
| [features/F1-mail-analysis.md](product/features/F1-mail-analysis.md) | 메일 분류 및 Vector DB 저장 |
| [features/F2-profile-draft.md](product/features/F2-profile-draft.md) | 사용자 프로필·개인화와 답장 초안 |
| [features/F3-search.md](product/features/F3-search.md) | 자연어 검색 |
| [features/F4-weekly-report.md](product/features/F4-weekly-report.md) | 주간 보고 만들기 |
| [features/F5-ai-scan.md](product/features/F5-ai-scan.md) | AI 스캔 (수신 즉시 알림과 제안) |

## design — 어떻게 보이나

| 문서 | 내용 |
| --- | --- |
| [design-system.md](design/design-system.md) | 디자인 시스템 v1.0 — 색·글꼴·간격·레이아웃·컴포넌트·상태 규칙 |
| [styleguide.png](design/styleguide.png) | 디자인 시스템 한 장 요약 (원본 `styleguide.html`) |
| [tokens/](design/tokens/klover-theme.css) | 코드용 토큰 — `klover-theme.css`(Tailwind v4 + shadcn), `categories.ts` |
| [brand/](design/brand/README.md) | 로고·앱 아이콘·트레이 아이콘·ICO와 사용 규칙 |
| [screens/](design/screens/README.md) | **화면 정의서 S01~S10 + Klover 목업(HTML·PNG)** — 바이브 코딩 기준 |
| [mockups/](design/mockups/README.md) | 설계안 v0.2 원본 PDF와 쪽별 이미지 (기능 검토용 와이어프레임) |

## architecture — 어떻게 동작하나

| 문서 | 내용 |
| --- | --- |
| [system.md](architecture/system.md) | 전체 구조, 기술 스택, 설계 원칙 |
| [data-model.md](architecture/data-model.md) | 테이블·메타데이터 스키마 |
| [api.md](architecture/api.md) | API·WebSocket 목록 |

## dev — 어떻게 일하나

| 문서 | 내용 |
| --- | --- |
| [progress.md](dev/progress.md) | **개발 현황판** — 기능별 브랜치·작업 도구·상태, 마이그레이션 번호 예약 |
| [handoff-prompts.md](dev/handoff-prompts.md) | Codex ↔ Claude 도구 전환용 프롬프트 모음 |
| [status-template.md](dev/status-template.md) | 기능별 status 문서 양식 |
| [setup.md](dev/setup.md) | 개발 환경 준비·실행 |
| [local-database.md](dev/local-database.md) | DB 참고와 과거 기록. 실행은 setup.md |
| [google-connection.md](dev/google-connection.md) | Google 연결 참고. 최초 준비/로그인은 setup.md |
| [gmail-mail-sync.md](dev/gmail-mail-sync.md) | 새 받은 메일 수신·중복 방지 저장·조회·토큰 갱신 |
| [mail-read-api.md](dev/mail-read-api.md) | 메일 API 참고. 현재 앱용 명령/토큰 준비는 setup.md |
| [F0-mail-api-handoff.md](dev/F0-mail-api-handoff.md) | F0 채팅에 그대로 보낼 서버 연결 요청 |
| [workflow.md](dev/workflow.md) | 1인 개발 채팅 운영, Git 규칙, Codex·Claude 전환 요령 |
| [F4-weekly-report-plan.md](dev/F4-weekly-report-plan.md) | F4 기반 점검, 작은 작업 단위, 수용 기준 진행 상태 |
| [F0-mailbox-status.md](dev/F0-mailbox-status.md) | F0 현재 구현·제약·과거 기록 |
| [F1-analysis-status.md](dev/F1-analysis-status.md) | F1 분석/표시/훅 연결·남은 UI와 실검증 |
| [F2-profile-draft-status.md](dev/F2-profile-draft-status.md) | F2 프로필/초안/개인정보·학습 수집 미구현 |
| [F4-weekly-report-status.md](dev/F4-weekly-report-status.md) | F4 현재 상태·다음 단위 |
| [F5-ai-scan-status.md](dev/F5-ai-scan-status.md) | F5 제안/할 일·Calendar 연결·남은 OS 기능 |
| [F3-search-status.md](dev/F3-search-status.md) | F3 앱/선택 AI·벡터 검색·추가 조건 제한 |
| [F3-search-handoff.md](dev/F3-search-handoff.md) | F0/F1/F2·공통 서버 연결 계약과 확인 방법 |

## 기능 정의서 템플릿

새 기능 문서는 아래 순서를 따른다.

```markdown
# Fn. 기능 이름

> 상태: 초안 | 담당: | 최종 수정: YYYY-MM-DD
> 설계안: 화면·구조 설계안 vX — N쪽

## 1. 목적
## 2. 사용자 시나리오
## 3. 처리 과정 / 동작 규칙
## 4. 데이터·API
## 5. 수용 기준        ← - [ ] 체크리스트. Claude가 완료 여부를 확인하는 기준
## 6. 이번 범위 아님
## 7. 결정 사항 / 남은 확인 포인트
```
