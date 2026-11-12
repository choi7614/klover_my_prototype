# Klover 문서 지도

사람과 Claude Code가 함께 읽는 기준 문서다. **코드와 문서가 다르면 문서를 먼저 고친 뒤 코드를 맞춘다.**

## product — 무엇을 만드나

| 문서 | 내용 |
| --- | --- |
| [overview.md](product/overview.md) | 서비스 개요, 기능 목록·담당, 기능 간 연결, 원칙 |
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
| [setup.md](dev/setup.md) | 개발 환경 준비·실행 |
| [workflow.md](dev/workflow.md) | 역할 분담, Git 규칙, Claude Code 사용 요령 |
| [F4-weekly-report-plan.md](dev/F4-weekly-report-plan.md) | F4 기반 점검, 작은 작업 단위, 수용 기준 진행 상태 |

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
