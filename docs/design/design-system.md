# Klover 디자인 시스템 v1.1

> 최종 수정: 2026-11-25 (v1.1: 차분한 세이지 톤·잎 모서리·◆ 폐지) | 한눈에 보기: [`styleguide.png`](styleguide.png) (원본 `styleguide.html`)
> 토큰 코드: [`tokens/klover-theme.css`](tokens/klover-theme.css) · 카테고리: [`tokens/categories.ts`](tokens/categories.ts) · 로고: [`brand/`](brand/README.md) · 화면: [`screens/`](screens/README.md)

화면을 만들 때 **이 문서와 토큰 파일의 값만** 쓴다. 새 색·크기·컴포넌트가 필요하면 먼저 이 문서에 추가하고 PR로 공유한다.

## 0. 핵심 원칙 5가지

1. **세이지 녹색 하나, AI는 글자로 구분.** 주요 버튼·사이드바·선택 표시는 차분한 세이지 녹색(primary·sidebar)을 쓴다. AI가 만든 것은 별도 색이 아니라 **"AI 요약" 같은 글자 라벨**과 연한 세이지 면(`ai-subtle`)으로 구분한다. 보라색과 ◆ 기호는 쓰지 않는다(v1.1).
2. **한 화면에 초록 버튼은 하나.** 그 화면에서 가장 중요한 행동(보내기, 저장, 캘린더에 추가)만 초록.
3. **근거를 보여 준다.** AI 요약·답변·보고 항목·제안에는 근거(출처 번호, 강조 문장, 근거 메일)를 붙인다.
4. **조용한 바탕.** 배경은 흰색·연회색, 구분은 1px 선. 그림자는 떠 있는 것(드롭다운, 알림, 대화상자)에만.
5. **shadcn/ui 먼저.** 버튼·입력·탭·대화상자 등은 shadcn/ui를 쓰고, 이 문서의 토큰으로 색만 맞춘다. Klover 전용 컴포넌트(7장)만 직접 만든다.

## 0-1. v1.1 추가 규칙 (2026-11)

- **잎 모서리**: 목록 카드·주요 버튼·AI 요약 면·읽기 패널은 대각선으로 다르게 둥근 `rounded-leaf-sm`(12/3) · `rounded-leaf`(18/6) · `rounded-leaf-lg`(24/8)를 쓴다. 입력창·표 같은 도구 요소는 기존 `rounded-md`.
- **사이드바**: 진한 세이지(`sidebar`) 바탕에 밝은 글자(`sidebar-foreground`, 보조는 `sidebar-muted`). 선택된 메뉴는 흰 면(`sidebar-primary`).
- **메일함 바탕**: `canvas` 위에 흰 카드를 올린다. 그림자는 카드의 얇은 선(`shadow-card`)만.
- **카테고리 색**은 채도를 낮춘 값(2-3)을 쓴다.
- **중립색도 세이지 기운**: `muted`(#F1F4F1)·`accent`(#E8EEE9)·`border`(#E0E7E1)·`input`(#C6D1C9)·`muted-foreground`(#5E6C63)는 차가운 회색이 아니라 세이지 쪽으로 기운 회색이다.
- **모든 화면의 공통 틀**: 좌측 이동 영역(메일함·첫 실행 단계·프로필/개인정보 설정 메뉴)은 진한 세이지 사이드바, 내용 바탕은 `canvas`, 그 위에 흰 `rounded-leaf` 카드·패널을 올린다. 첫 실행·답장 초안의 큰 내용 패널은 `rounded-leaf-lg`. 진한 사이드바 위의 로고는 `klover-logo-white.svg`.
- **버튼**은 `rounded-leaf-sm`(Button 컴포넌트가 기본 적용). 선택된 항목의 검정색 채움은 쓰지 않고 `primary`를 쓴다.
- 로고 마크 가운데의 보라색 마름모는 브랜드 자산이므로 그대로 둔다(사용자 결정).
- 시안은 화면 방향 비교 자료(C′ 순한 톤)를 따른다.

## 1. 적용 방법 (Claude Code에게 그대로 전달)

```text
1. apps/desktop 에 Tailwind CSS v4 + shadcn/ui 설치 (npx shadcn@latest init)
2. docs/design/tokens/klover-theme.css 내용을 src/renderer/styles/globals.css 에 넣는다
   (shadcn init이 만든 :root, @theme inline 블록은 이 파일로 교체)
3. 글꼴: npm i pretendard → main.tsx 에서 import "pretendard/dist/web/variable/pretendardvariable-dynamic-subset.css"
4. 아이콘: npm i lucide-react
5. docs/design/tokens/categories.ts 를 src/renderer/lib/categories.ts 로 복사
6. 로고·아이콘: docs/design/brand/ 의 SVG·PNG·ICO 를 apps/desktop/resources/ 로 복사
```

코드 규칙:

- 색은 토큰 클래스만: `bg-primary` `text-ai` `bg-ai-subtle` `border-ai-border` `bg-cat-work-bg` `text-muted-foreground` …
- 금지: `bg-[#1F9D55]` 같은 임의 값, 인라인 style 색상, Tailwind 기본 팔레트(`bg-green-600`, `text-purple-500`) 직접 사용
- 글자 크기: `text-caption` `text-body` `text-title` `text-heading` `text-display` 5개만

## 2. 색

### 2-1. 의미 토큰 (화면 코드에서 쓰는 이름)

| 토큰 (Tailwind 클래스) | 값 | 쓰임 |
| --- | --- | --- |
| `primary` / `primary-foreground` | `#158446` / 흰색 | 주요 버튼 (새 메일, 보내기, 저장, 캘린더에 추가) — 흰 글자 대비 4.75:1 |
| `primary-hover` | `#116B39` | 주요 버튼 hover |
| `selected` / `selected-foreground` | `#ECF8F1` / `#116B39` | 선택된 메일 행, 선택된 메뉴 |
| `selected-bar` | `#5FA383` | 선택한 메일 카드의 2px 테두리 |
| `canvas` | `#F5F7F4` | 메일함 바탕. 목록 카드와 읽기 패널(흰색)이 올라간다 |
| `ai` / `ai-foreground` | `#2F5645` / 흰색 | AI 실행 버튼(답장 초안 만들기), 선택된 AI 칩 |
| `ai-subtle` | `#F1F0FD` | AI 요약 박스·AI 칩 배경 |
| `ai-border` | `#C8C3F7` | AI 박스·칩 테두리 |
| `ai-text` | `#2F5645` | 목록의 AI 한 줄 요약, AI 박스 제목 |
| `ai-highlight` | `#E9E6FD` | 본문 속 근거 문장 배경 (+ 아래 2px `ai` 밑줄) |
| `foreground` | `#14171C` | 본문 |
| `muted-foreground` | `#646B77` | 날짜, 보조 설명 |
| `muted` / `sidebar` | `#F5F6F8` | 사이드바, 필터·근거 패널 배경 |
| `accent` | `#ECEEF1` | hover 배경 |
| `border` / `input` | `#E1E4E8` / `#C9CED5` | 구분선 / 입력창 테두리 |
| `ring` | `#3DAE6F` | 키보드 포커스 링 |
| `warning` · `warning-subtle` · `warning-border` | `#B45309` · `#FFF7EB` · `#F5C98A` | 일정 겹침, 마감 임박 |
| `danger` · `danger-subtle` · `danger-border` | `#B91C1C` · `#FEF2F2` · `#F9C6C6` | 회신 필요, 미회신 N일, 삭제 버튼 글자 |
| `destructive` | `#DC2626` | 삭제 확인 대화상자의 빨간 버튼 |

### 2-2. 원색 팔레트

| 이름 | 50 | 100 | 200 | 300 | 400 | 500 | 600 | 700 | 800 | 900 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| clover | ECF8F1 | D2EFDE | A6DEBD | 6FC795 | 3DAE6F | **1F9D55** 로고 | **158446** 버튼 | 116B39 | 0E552E | 0B4426 |
| sage | F5F7F4 | E4EEE7 | C9DBCF | 9CC8AE | 5FA383 | — | **3A7D5D** 버튼 | **2F5645** 사이드바·AI | 254536 | — |
| violet (폐지) | F1F0FD | E3E1FB | C8C3F7 | A39BF0 | 7E74E8 | 5B4FE0 | 4B3FCC | 3D33A8 | — | — |
| gray | F5F6F8 | ECEEF1 | E1E4E8 | C9CED5 | 9AA1AC | 646B77 | 4B5361 | 353B46 | 22262E | 14171C |

원색은 토큰을 정의할 때만 쓴다. 화면 코드는 2-1의 의미 토큰을 쓴다.

### 2-3. 카테고리 7종

| 카테고리 | 키 | 글자 | 배경 | 사이드바 점 | 대비 |
| --- | --- | --- | --- | --- | --- |
| 업무 요청 | `work_request` → `cat-work` | `#2B56A6` | `#E8EEF7` | `#6F93C9` | 5.9 |
| 회의·일정 | `meeting` → `cat-meeting` | `#2F6B47` | `#E5F1E9` | `#6FAE8A` | 4.5 |
| 결재·승인 | `approval` → `cat-approval` | `#9A4E22` | `#F8EDE3` | `#D79A6B` | 4.7 |
| 보고·공유 | `report_share` → `cat-report` | `#7A5A1E` | `#F6F0DF` | `#C9A95A` | 5.3 |
| 공지 | `notice` → `cat-notice` | `#4B5563` | `#F0F1F3` | `#A3A8B0` | 6.8 |
| 외부·고객 | `external` → `cat-external` | `#A23A55` | `#F8E8EC` | `#CC7C8B` | 5.4 |
| 뉴스레터·광고 | `newsletter` → `cat-newsletter` | `#5F6672` | `#F5F6F8` | `#C9CED5` | 4.8 |

상태 태그: `회신 필요`·`미회신 N일` = danger, `마감 MM/DD` = warning, `일정 제안` = ai.

## 3. 글자

- 글꼴: **Pretendard Variable** (한 가지만). 숫자는 기본(비례폭), 표의 숫자 열만 `tabular-nums`.

| 토큰 | 크기 / 줄 높이 / 굵기 | 쓰임 |
| --- | --- | --- |
| `text-display` | 28 / 36 / 700 | 첫 실행·빈 화면 큰 제목, 주간 보고 표지 |
| `text-heading` | 20 / 28 / 700 | 화면 제목, 메일 읽기 제목 |
| `text-title` | 16 / 24 / 600 | 카드·패널 제목, 섹션 제목 |
| `text-body` | 14 / 20 / 400 | 기본 글자, 목록, 버튼 (버튼은 600) |
| `text-caption` | 12 / 16 / 400 | 날짜, 태그, 보조 설명 |

- 메일 본문 읽기 영역만 15px / 26px (긴 글 가독성).
- 굵기는 400·500·600·700만.

## 4. 간격 · 모양 · 그림자 · 움직임

- 간격: 4의 배수 — 4 · 8 · 12 · 16 · 24 · 32 (Tailwind `1 · 2 · 3 · 4 · 6 · 8`)
- 모서리: 태그·칩 6 (`rounded-sm`), 버튼·입력·카드 8 (`rounded-md`), 대화상자·알림 12 (`rounded-lg`), 칩(알약형) `rounded-full`
- 테두리: 1px `border`. 강조 카드(선택된 제안)는 `ai-border` + 바깥 3px `ai-subtle` 링
- 그림자: `shadow-pop`(드롭다운·팝오버·대화상자), `shadow-toast`(Windows 알림 모양)만
- 움직임: 150ms `ease-standard`. 패널 열기·hover 색 변화에만. AI 생성 중에는 깜빡임 대신 스켈레톤(회색 막대) 사용

## 5. 레이아웃

```
┌ 타이틀바 36 ─────────────────────────────────────────────────────────────┐
├ 상단 바 56: [로고 188] [검색 아이콘 + 자연어 검색창 (최대 720, Ctrl K)]  [🔔 계정 아바타] ┤
├ 사이드바 220 ┬ 메일 목록 360 ┬ 메일 읽기 (나머지, 본문 최대 760) ─────────────┤
│ 새 메일      │ 목록 머리 44  │ 도구 줄 44: [답장 초안 만들기][답장][보관]… │
│ 메일함       │ 날짜 구분     │ 제목 · 발신 정보                              │
│ 스마트 보기  │ 메일 한 줄 ×N │ AI 요약 박스 · 분류                           │
│ AI 카테고리  │               │ 본문 (근거 문장 강조)                         │
│ 도구         │               │ (F5 제안이 있으면 오른쪽 제안 패널 340)       │
└──────────────┴───────────────┴───────────────────────────────────────────────┘
```

- 최소 창 크기 1280 × 720. 기본 1440 × 900.
- 1280px 이하에서는 메일 목록을 320으로 줄이고, 제안 패널은 본문 아래로 내린다.
- 전체 화면(검색·주간 보고·설정·답장 초안)은 목록+읽기 영역을 대신 쓰고, 사이드바는 유지한다(설정은 설정 메뉴로 교체).

## 6. 기본 컴포넌트 (shadcn/ui + 토큰)

| 컴포넌트 | shadcn | Klover 규칙 |
| --- | --- | --- |
| Button | `button` | 변형 6개: `default`(primary) · `secondary`(흰 바탕+테두리) · `ghost` · `ai`(진한 세이지) · `ai-outline`(연한 세이지) · `danger-outline`. 크기 sm 28 / md 36 / lg 44. 아이콘 16px, 글자와 간격 6 |
| Input · Textarea | `input` `textarea` | 높이 36, 테두리 `input`, 포커스 `ring` 2px |
| Select | `select` | 오른쪽 chevron-down 16px |
| Toggle | `switch` | 켬 = primary |
| Checkbox | `checkbox` | 켬 = primary |
| Segmented | `toggle-group` | 선택 = foreground 바탕 + 흰 글자 (짧게/보통/자세히, 개조식/서술형) |
| Slider | `slider` | 채움 = primary |
| Tabs | `tabs` | 밑줄형, 선택 = primary 2px |
| Dialog | `dialog` | 폭 560, 모서리 12, 하단 버튼 줄 `muted` 배경 |
| Dropdown · Popover | `dropdown-menu` `popover` | `shadow-pop` |
| Tooltip | `tooltip` | 진회색 바탕, 12px |
| Toast (앱 안) | `sonner` | 하단 가운데, 4초 |
| Skeleton | `skeleton` | AI 분석·생성 중 표시 |
| Sidebar | `sidebar` | 폭 220, 항목 높이 34, 선택 = `selected` 바탕 + `selected-foreground` 글자 |

## 7. Klover 전용 컴포넌트

`apps/desktop/src/renderer/components/` 에 만든다. 같은 것을 두 번 만들지 않는다. 모양은 `styleguide.png`를 기준으로 한다.

| 컴포넌트 | 모양 | 쓰는 화면 |
| --- | --- | --- |
| `CategoryTag` | 높이 20, 패딩 6, `rounded-sm`, 12px 500, 카테고리 색 | S03 S04 S07 |
| `StatusTag` | 같은 크기, 상태 색 (회신 필요·마감·미회신·일정 제안) | S03 S04 S07 |
| `MailListItem` | 패딩 12/16, 1줄 보낸 사람+시간, 2줄 제목, 3줄 AI 요약(ai-text 13px), 4줄 태그. 안 읽음 = 초록 점 + 굵게, 선택 = 카드에 `selected-bar` 2px 테두리, 분석 중 = 요약 자리에 "AI가 분석하고 있어요…" + 태그 스켈레톤. 카드는 흰 바탕 + `rounded-leaf` + `shadow-card`, 간격 8 | S03 S04 |
| `AiSummaryBox` | `ai-subtle` 면(테두리 없음), `rounded-leaf`, 패딩 14/16. 머리 "AI 요약", 아래 구분선 + 내가 할 일·마감·우선순위 | S03 |
| `CategorySelect` | "분류 [업무 요청 ▾] 틀렸다면 눌러서 바꿔 주세요" | S03 |
| `EvidenceHighlight` | 본문 근거 문장: `ai-highlight` 바탕 + 2px `ai` 밑줄 | S03 S04 |
| `ProfileUnderline` | 초안 속 프로필 반영 부분: 2px `ai-border` 밑줄 | S06 |
| `AiChip` | 높이 30 알약형, `ai-subtle`+`ai-border`. 키(12px ai-text 600)+값+× . 선택형은 선택 시 `ai` 바탕 흰 글자. "+ 조건 추가"는 점선 | S06 S07 |
| `CitationBadge` | 18×18, 흰 바탕+`ai-border`, 번호 11px 700. 누르면 해당 메일로 | S07 |
| `EvidenceBadge` | "근거 N" 20 높이. 선택 시 `ai` 바탕 | S08 |
| `SuggestionCard` | 흰 카드, 머리 = 유형 아이콘+이름(유형 색), 내용, 경고 박스(warning), 버튼 줄. 가장 중요한 제안은 `ai-border` + 링 | S04 S10 |
| `ConflictWarning` | `warning-subtle` 바탕, `warning-border`, ⚠ 아이콘 14 + 12px | S04 S10 |
| `ResultCard` | 번호 배지(ai 22×22) + 보낸 사람·날짜 + 제목 + 인용(왼쪽 2px 선, 일치 단어 강조) + 태그 + 맞는 이유 + [답장 초안] | S07 |
| `ReadinessList` | 기능 이름 + 상태(● 바로 사용 초록 / ○ 대기 회색) | S02 |
| `EmptyState` | 112 둥근 사각(clover-50) 안 마크 64, heading + 설명 + 버튼 | S02, 검색 결과 없음 |
| `WizardSteps` | 번호 원 26: 완료 = primary 채움+✓, 현재 = primary 테두리+4px 링, 대기 = 회색 테두리 | S01 |

## 8. 아이콘

- lucide-react, 기본 16px, 선 굵기 1.8. 사이드바·버튼 16, 빈 화면 24 이상.
- 정해진 짝: 받은편지함 `Inbox` · 보낸편지함 `Send` · 임시보관함 `File` · 보관 `Archive` · 삭제 `Trash2` · 스팸 `Ban` · 답장 `Reply` · 회신 필요 `Reply` · 마감 `Clock` · 할 일 `SquareCheck` · 일정 `Calendar` · 주간 보고 `FileText` · 설정 `Settings` · 새 메일 `PenLine` · 알림 `Bell` · 경고 `TriangleAlert` · 다시 만들기 `RefreshCw` · 복사 `Copy` · 내보내기 `Download` · 끌어서 순서 변경 `GripVertical`
- AI 표시는 기호가 아니라 **"AI 요약"·"AI 제안" 같은 글자 라벨**로 한다(◆는 v1.1에서 폐지).

## 9. 상태 표현

| 상태 | 표현 |
| --- | --- |
| 불러오는 중 | 목록·카드 자리에 `Skeleton` (회색 막대). 전체 화면 스피너는 쓰지 않는다 |
| AI 생성 중 | 해당 영역에 "AI가 ○○을 만들고 있어요…" + 스켈레톤. 초안·답변은 글자가 생기는 대로 보여 준다(스트리밍) |
| AI 실패 | 영역 안에 회색 안내 "요약을 만들지 못했어요 · [다시 시도]". 원문은 항상 보인다 |
| 비어 있음 | `EmptyState` (아이콘/마크 + 한 줄 설명 + 할 수 있는 행동 버튼) |
| 오프라인·서버 연결 끊김 | 상단 바 아래 높이 32 띠(`warning-subtle`): "서버에 연결할 수 없어요. 다시 연결하는 중…" |
| 비활성 | 투명도 40%, 커서 기본 |

## 10. 접근성

- 글자 대비 4.5:1 이상 (토큰 값은 모두 확인함). 색만으로 의미를 전달하지 않는다 — 태그에는 항상 글자가 있다.
- 모든 동작은 키보드로 가능: `Ctrl K` 검색, `Ctrl N` 새 메일, `R` 답장, `E` 보관, `Del` 삭제, `J/K` 다음/이전 메일, `Esc` 닫기.
- 포커스 링은 지우지 않는다(`ring` 2px).
- 아이콘만 있는 버튼에는 툴팁과 `aria-label`.

## 11. 문구 톤

- 존댓말, 짧게, "~해요"체는 안내에, "~습니다"체는 제목·상태에. 예: "받은편지함이 비어 있습니다", "이렇게 이해했어요"
- 버튼은 동사로 끝낸다: "캘린더에 추가", "답장 초안 만들기", "다시 만들기"
- AI 결과에는 단정 대신 근거: "35일째 답이 없습니다 [3]"
- 앱 이름은 항상 "Klover" (로고만 소문자 klover)

## 12. 이번 버전에 없는 것

- 다크 모드 (토큰 구조는 준비됨 — `.dark` 블록만 추가하면 됨)
- 고대비 모드, 글자 크게 보기 설정
- 애니메이션 가이드 상세
