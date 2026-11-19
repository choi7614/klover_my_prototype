# 기능별 AI 선택 — 맥북 사용·검증 안내

기준: `origin/develop@e5f7efd` · 작업 `integrate/ai-provider-selection` · 2026-11-20 Codex.
로컬 구현·검사 단계이며 커밋·Push·PR 생성은 사용자 묶음 승인 대기다. 이번 단위 develop 병합은
사용자가 문제 없으면 진행하도록 조건부 승인했다. main·기존 브랜치는 보존한다.

## 동작

| 기능 | 처리 |
| --- | --- |
| 자동 분류·태그·메일 요약·임베딩·F5 제안 | 항상 기존 로컬 Ollama. bge-m3 차원 유지 |
| 답장 초안·수정 | 저장 기본값 또는 요청 선택. 생성 버튼으로 시작, 실패 시 편집본 보존 |
| 자연어 검색 | 해석·근거 답변을 같은 제공자로 처리. 검색 결과만 답변 입력으로 전달 |
| 주간 보고서 | 제공자 선택, 첫 주부터 생성. 첫 주 기본은 시작일~오늘, 기존 주간 기본은 지난 업무 주 |

선택을 생략한 이전 API 호출은 저장 기본값을 따른다. 최초에는 기존 AI_PROVIDER(없으면 로컬)를 이어받는다.
Claude는 앱에서 전송·비용을 허용한 뒤에만 호출한다. 장애 시 다른 제공자로 전환하지 않는다.
키·설정은 서버의 새 암호화 파일에만 저장한다. 기존 OAuth·메일 API·DB 키는 변경하지 않는다.
앱에는 등록 여부만 반환한다. 키 입력은 저장 시 지우며 브라우저 저장소에 보관하지 않는다.
모델 ID는 Anthropic Console에서 계정에 제공되는 ID를 사용한다. 기존 서버 모델 설정을 유지하며,
앱에서 ID를 변경하면 세 수동 기능의 Claude 모델에 공통 적용한다. 자동 분석에는 영향 없다.
연결 검사 결과는 저장하지 않으며 검사한 시점의 합성 생성 성공만 의미한다.

## 답장 본문·근거 보완

사용자는 첫인사·마무리 저장 후 자기 관점의 답장이 나오는 것을 확인했다. 과거 오류의 정확한
분기는 실제 응답을 수집하지 않아 확정하지 않았다. 실제 메일을 로그나 검사 데이터로 수집하지 않는다.
기존 모델의 숫자 위치 계산은 인용문(text/source/source_quote) 출력으로 바꾸고 서버가 Unicode
위치를 계산한다. 원문 인용·메일 ID·학습 표현·겹침·선택 방향·제외 표현을 검증한다.
고정 인사/마무리/서명은 계속 서버가 붙인다. 빈 인사·마무리도 허용한다.
잘못된 결과만 최대 한 번 다시 묻고 오류 응답 원문은 재전송하지 않는다. 제공자 오류·시간 초과는
이 형식 재시도 대상이 아니며 다른 제공자 전환도 없다. 기존 공개 evidence 좌표/저장 형식은 유지한다.

## 병합 후 맥북 실행

지금 실행할 단계가 아니라, 승인 후 develop에 반영됐다고 안내받은 뒤 진행한다.

1. 실행 중인 서버와 앱 터미널에서 각각 Control+C로 종료한다. Ollama와 Docker는 유지한다.
2. 프로젝트 터미널에서 실행한다.

```bash
cd ~/Projects/klover-taeho-dev
git status --short --branch
```

미커밋 파일이 있으면 덮어쓰지 말고 먼저 확인한다. 깨끗하면 다음을 실행한다.

```bash
git switch develop
git pull --ff-only origin develop
uv sync --locked --directory apps/server
corepack pnpm install --frozen-lockfile
docker compose --env-file .env -f infra/docker-compose.yml up -d --wait
uv run --locked --directory apps/server python -m app.cli.run_mail_api
```

이번 단위에는 DB 마이그레이션이 없다. 기존 0007_f1과 데이터·키를 보존한다.
새 터미널에서 앱을 연다.

```bash
cd ~/Projects/klover-taeho-dev
export KLOVER_API_TOKEN_FILE="$PWD/.local-secrets/mail-api-token"
export KLOVER_API_BASE_URL="http://127.0.0.1:8000"
corepack pnpm --filter desktop dev
```

3. 받은편지함 상단 'AI 설정' → Claude 키를 비밀번호 칸에 입력한다(채팅에 올리지 않음).
   Anthropic Console에서 사용할 수 있는 모델 ID를 확인해 입력한다. API 잔액은 Claude 구독과 별도다.
4. 외부 전송·API 비용 안내를 확인하고 허용을 선택한다. 기능별 기본 AI를 고른 뒤 '설정 저장'.
5. 'Claude 연결 검사'는 메일 없는 소량 요청이다. 로컬 검사도 확인한다.
6. 첫 검사는 합성 테스트 메일로 답장, 자연어 검색, 첫 주 보고서를 각각 실행한다.
   두 제공자 선택·실패 후 편집본 보존·앱 재실행 후 기본값 유지도 확인한다.
   실제 메일 사용은 자신이 외부 전송해도 되는 자료로 진행한다.
7. 오류가 나면 오류 문구만 전달한다. 키·.env·메일 본문은 채팅에 올리지 않는다.

## 검증 결과

- 서버 전체 pytest: 분리 PostgreSQL·pgvector 포함 **575 통과, skip 0**.
- 추가 변경 관련 서버 검사: **119 통과**(전체 검사 전에 실행, 중복 합산하지 않음).
- 서버 Ruff check/format: **178개 파일 통과**.
- 데스크톱 전체 Vitest: **182 통과**. 마지막 기간 대기 UI 제거 후 해당 화면 검사도 통과.
- 데스크톱 lint·typecheck·생산 빌드: 통과.
- Chromium 합성 화면 통합: **3 통과**(AI 설정 저장/연결 표시, 최초 초안 선택, 첫날 보고서).
  이는 합성 IPC를 사용한 앱 화면 검사이며 실제 Claude 연결 성공을 뜻하지 않는다.
- 실제 `run_mail_api.main()` 조립을 외부 호출 없이 검사: 세 수동 기능은 같은 요청 선택 통로,
  자동 분석 로더는 AI_PROVIDER가 Claude인 환경에서도 Ollama, 임베딩 bge-m3 유지 확인.
- OpenAPI/TS 공유 타입 재생성, git diff --check, 새 설정·키 파일 Git 제외 확인: 통과.

합성 자동 검사와 맥북 실기를 구분한다.
실제 Claude API·Gmail·Ollama·macOS Electron 창: 이번 환경에서는 미실행. 자동 검사는 합성 입력과
분리 PostgreSQL만 사용하며 사용자 DB에는 접근하지 않는다.

## 후속 범위

의미 검색 어댑터 연결·검색의 미지원 조건, 관련 메일/F1 요청사항의 F2 입력 연결, 메일 발송,
실제 Calendar·OS 알림 등은 이번 단위에서 확대하지 않는다. 초기 데모 전체 성능 목표도 별도 실측이 필요하다.
