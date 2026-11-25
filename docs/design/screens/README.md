# Klover 화면 정의서

> **v1.1 안내 (2026-11-25):** 아래 화면 정의서 본문은 v1.0 기준이다. 디자인 시스템 v1.1에서 **보라색·◆ 기호가 폐지**되어 AI 표시는 "AI 요약" 같은 글자 라벨과 연한 세이지 면으로 바뀌었다. 정의서 본문의 ◆는 "AI 글자 라벨"로, 보라는 "진한 세이지"로 읽는다. 목업 PNG(S01~S10)와 styleguide는 2026-11-25에 v1.1로 다시 만들었다. 앱 화면은 [디자인 시스템 0-1절](../design-system.md)의 공통 틀(진한 세이지 사이드바·`canvas` 바탕·흰 잎 모서리 카드)로 통일되어 있어, 목업과 다른 부분은 앱 화면과 디자인 시스템을 기준으로 한다.

> v1.0 · 2026-10-20 · 기준: 기능 정의서 F0~F5, [디자인 시스템](../design-system.md)

바이브 코딩으로 화면을 만들 때 **한 화면 = 정의서 1개 + 목업 1장**을 Claude Code에 함께 준다.

```text
docs/design/screens/S03-inbox.md 를 읽고, mockups/png/S03-inbox.png 처럼 화면을 만들어줘.
색·크기·컴포넌트는 docs/design/design-system.md 를 따르고, 데이터는 일단 fixture로 채워줘.
```

## 화면 목록

| ID | 화면 | 기능 | 정의서 | 목업 |
| --- | --- | --- | --- | --- |
| S01 | 첫 실행 설정 (5단계) | F0 | [S01-onboarding.md](S01-onboarding.md) | [S01-onboarding.png](mockups/png/S01-onboarding.png) |
| S02 | 빈 받은편지함 | F0 | [S02-inbox-empty.md](S02-inbox-empty.md) | [S02-inbox-empty.png](mockups/png/S02-inbox-empty.png) |
| S03 | 받은편지함 (AI 분류) — **기준 화면** | F0·F1 | [S03-inbox.md](S03-inbox.md) | [S03-inbox.png](mockups/png/S03-inbox.png) |
| S04 | 메일 읽기 + AI 제안 | F5 | [S04-mail-suggestions.md](S04-mail-suggestions.md) | [S04-mail-suggestions.png](mockups/png/S04-mail-suggestions.png) |
| S05 | 새 메일 작성 | F0 | [S05-compose.md](S05-compose.md) | [S05-compose.png](mockups/png/S05-compose.png) |
| S06 | 답장 초안 | F2 | [S06-reply-draft.md](S06-reply-draft.md) | [S06-reply-draft.png](mockups/png/S06-reply-draft.png) |
| S07 | 자연어 검색 | F3 | [S07-search.md](S07-search.md) | [S07-search.png](mockups/png/S07-search.png) |
| S08 | 주간 보고 | F4 | [S08-weekly-report.md](S08-weekly-report.md) | [S08-weekly-report.png](mockups/png/S08-weekly-report.png) |
| S09 | 설정 · 내 프로필·문체 | F2 | [S09-settings-profile.md](S09-settings-profile.md) | [S09-settings-profile.png](mockups/png/S09-settings-profile.png) |
| S10 | Windows 알림 · 트레이 · 놓친 제안 | F0·F5 | [S10-notifications-tray.md](S10-notifications-tray.md) | [S10-notifications-tray.png](mockups/png/S10-notifications-tray.png) |

목업 원본은 `mockups/*.html`(브라우저로 열면 보임), 이미지는 `mockups/png/*.png`. 목업 위 노란 번호는 각 정의서의 "구성 요소" 번호와 같다.

> `../mockups/`(설계안 v0.2 PDF와 쪽별 이미지)는 **기능 검토용 와이어프레임**이다. 화면을 만들 때는 이 폴더의 Klover 목업을 기준으로 한다.

## 화면 이동

```text
앱 첫 실행 ──▶ S01 첫 실행 설정 ──완료──▶ S02 빈 받은편지함 ──메일 도착──▶ S03 받은편지함
                                                                            │
  S03 메일 클릭 ─▶ 읽기 영역 (일정 제안 있으면 S04 형태)                     │
  S03 [새 메일] / Ctrl N ─────────────▶ S05 작성                            │
  S03·S04·S07 [◆ 답장 초안 만들기] ───▶ S06 답장 초안 ──보내기──▶ S03       │
  상단 검색창 Enter / Ctrl K ─────────▶ S07 검색 ──결과 클릭──▶ S03(해당 메일)
  사이드바 '주간 보고' ───────────────▶ S08                                  │
  사이드바 '설정' ────────────────────▶ S09 (설정 메뉴로 다른 설정 화면)      │
  앱이 켜져 있을 때 AI 제안 ──────────▶ S10-B Windows 알림 ──메일 열기──▶ S04
  다음 실행 때 놓친 제안 있음 ────────▶ S10-A 놓친 제안 대화상자
  트레이 아이콘 우클릭 ───────────────▶ S10-C 트레이 메뉴
```

라우트(앱 안 주소) 제안:

| 라우트 | 화면 |
| --- | --- |
| `/onboarding/:step` | S01 |
| `/mail/:box` (`inbox`·`sent`·`draft`·`archive`·`spam`) | S02·S03 |
| `/mail/smart/:view` (`reply`·`due`·`todo`) · `/mail/category/:key` | S03 (필터된 목록) |
| `/mail/:box/:mailId` | S03·S04 (선택된 메일) |
| `/compose` · `/compose/:draftId` | S05 |
| `/reply/:mailId` | S06 |
| `/search?q=` | S07 |
| `/report/weekly` | S08 |
| `/settings/:section` (`profile`·`report`·`accounts`·`calendar`·`notifications`·`privacy`) | S09 등 |

## 공통 레이아웃

모든 메인 화면은 같은 틀을 쓴다 (`mockups/assets/shell.js`가 목업에서 이 틀을 그림).

| 영역 | 크기 | 내용 |
| --- | --- | --- |
| 타이틀바 | 높이 36 | Windows 기본 타이틀바 모양. 앱 아이콘 16 + "Klover" + 최소화·최대화·닫기. **닫기 = 트레이로 숨김** |
| 상단 바 | 높이 56 | 로고(높이 26) · 자연어 검색창(◆, 최대 720, `Ctrl K` 표시) · 알림 종(안 본 제안 수 배지, 보라) · 계정 이메일 · 아바타 |
| 사이드바 | 폭 220 | [새 메일] primary 버튼 / 메일함 5 / 스마트 보기 3 / AI 카테고리 7 / 도구(주간 보고, 설정) |
| 본문 | 나머지 | 화면마다 다름 |

사이드바 항목: 높이 34, 아이콘 16 + 이름 + 오른쪽 건수(12px). 선택 = `selected` 바탕, 글자 `selected-foreground` 600. AI 카테고리는 아이콘 대신 8px 색 점.

## 모든 화면 공통 규칙

- 데이터가 없을 때·불러올 때·AI가 실패했을 때 모양은 [디자인 시스템 9장](../design-system.md#9-상태-표현)을 따른다.
- 발송·캘린더 등록은 항상 사용자가 버튼을 눌러야 실행된다. 자동 실행 금지.
- 날짜 표기: 목록 `09:12` / `어제` / `10/14`, 본문·카드 `10/16(금)`, 상세 `10월 14일 (화) 09:12`
- 사람 표기: `이름 직급 (부서)` — 예: 박지훈 과장 (영업기획팀)
- 예시 데이터: 홍길동 과장(경영지원본부 재무팀) 시나리오 — `fixtures/mails/`와 같은 내용을 쓴다.

## 화면 정의서에서 새로 필요해진 것

화면을 정의하면서 기존 문서에 없던 항목이 생겼다. 해당 작업 채팅이 `docs/architecture/api.md`·`data-model.md`에 먼저 추가한 뒤 구현한다.

| 항목 | 화면 | 작업 채팅 |
| --- | --- | --- |
| `GET /status/readiness` (사용 시작일, 보낸 메일 수 → 기능 준비 상태) | S02 | 통합 |
| `mails.evidence_spans` (요약·할 일·마감을 뽑은 본문 위치) | S03 | F1 |
| 메일 임시 저장 API, `GET /contacts?q=` (받는 사람 자동완성) | S05 | 통합 |
| `drafts.evidence[]` 위치 형식 (밑줄 표시용) | S06 | F2 |
| `PATCH /reports/weekly/{id}` (편집 내용 저장) | S08 | F4 |
| 트레이 아이콘 '새 제안' 배지 버전 | S10 | F0 |
| 키보드 단축키 (`Ctrl K`·`Ctrl N`·`J/K`·`E`·`R`·`Del`) | 공통 | F0 |

## 정의서 형식

각 화면 정의서는 아래 순서를 따른다. 새 화면을 추가할 때도 같은 형식으로 쓴다.

```markdown
# Sxx. 화면 이름
> 기능 · 라우트 · 목업
## 1. 목적
## 2. 진입 · 나가기
## 3. 레이아웃            (영역별 크기)
## 4. 구성 요소           (목업 번호와 같은 번호, 컴포넌트 이름, 데이터)
## 5. 동작                (누르면 무슨 일이 생기나)
## 6. 상태                (불러오는 중 · 비어 있음 · 오류 · AI 생성 중)
## 7. 문구                (화면에 들어가는 글자 그대로)
## 8. 데이터 · API
## 9. 완료 체크리스트
```
