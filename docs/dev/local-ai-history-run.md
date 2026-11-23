# 로컬 AI 정책·과거 메일 가져오기 — 맥북 확인

기준 develop `5e2b7a7` · 작업 `integrate/local-ai-mail-history` · 커밋/Push/PR 생성 전 사용자 승인 대기.
실제 Gmail·유료 Claude에는 개발 중 접근하지 않는다. 아래는 승인·병합 후 사용자 PC에서 진행하는 절차다.

## 기존 사용자 업데이트

1. 서버·앱 터미널에서 Control+C로 종료한다. 기존 `.env`·`.local-secrets`와 Docker DB를 함께 백업한다.
   기존 키·볼륨을 지우거나 비밀번호를 다시 생성하지 않는다. DB 백업은 setup.md의 기존 절차를 따른다.
2. 아래를 프로젝트 루트에서 실행한다. `git status`에 변경 파일이 있으면 업데이트 전에 보존 방법을 확인한다.

```bash
cd ~/Projects/klover-taeho-dev
git status --short --branch
git switch develop
git pull --ff-only origin develop
docker compose --env-file .env -f infra/docker-compose.yml up -d --wait
uv sync --locked --directory apps/server
uv run --locked --directory apps/server alembic upgrade head
uv run --locked --directory apps/server alembic current
uv run --locked --directory apps/server python -m app.cli.check_database
uv run --locked --directory apps/server python -m app.cli.run_mail_api
```

DB 이력은 `0008_history (head)`, 확인은 `database: ok, schema: current`여야 한다.
0008은 기존 메일 표시 false와 작업 표를 추가한다. 계정 시작 시점·수신 커서·암호화 키·메일은 보존한다.
이전 앱 버전과 섞어 실행하거나 테스트 목적으로 사용자 DB를 downgrade하지 않는다.

새 터미널에서:

```bash
cd ~/Projects/klover-taeho-dev
corepack pnpm install --frozen-lockfile
export KLOVER_API_TOKEN_FILE="$PWD/.local-secrets/mail-api-token"
export KLOVER_API_BASE_URL="http://127.0.0.1:8000"
corepack pnpm --filter desktop dev
```

## AI 정책 확인

1. AI 설정에서 로컬 전용을 저장한다. 세 기능 기본값에 Claude가 남아 있어도 실제 호출은 로컬이다.
   Claude 선택과 연결 검사는 차단되며 기존 키는 보존한다. 프로필 미리보기는 어느 모드에서도 로컬이다.
2. 선택적 Claude를 쓰려면 로컬 전용을 끄고 외부 전송·자료 종류·요금을 확인해 허용을 저장한다.
   기본 선택은 로컬로 두고 필요한 요청에서 Claude를 선택할 수 있다. 키는 앱 비밀번호 입력에만 넣는다.
3. Claude 제공자 연결/키/한도/모델 오류·시간 초과 시 로컬 1회 전환한다. 안전 거절·사용자 취소·미동의는
   전환하지 않는다. 형식·근거 검증 오류는 기존 보정/오류 처리를 따르며 제공자 전환 사유가 아니다. 결과에 실제 처리 AI와 이유가 나온다. 둘 다 실패하면 기존 편집본을 보존한다.
   각 제공자 호출 상한은 Claude 45초·로컬 65초이며 기존 전체 상한(초안/보고 120초, 검색 각 단계 120초)을 유지한다.
4. 연결 검사는 Claude 자체 성공만 성공으로 표시하며 로컬로 대신 성공시키지 않는다.
   연결 검사는 실제 소량 과금이 발생할 수 있으므로 사용자가 별도로 실행한다.

## 과거 메일 확인

1. 받은편지함 상단 '과거 메일 가져오기'로 이동한다. 필요한 한국 날짜 범위를 고른다(양끝 날짜 포함).
2. 현재 Gmail 받은편지함(INBOX)만 가져온다. 최대 366일·작업당 10,000건. 사전 정확한 건수는 제공하지 않으며,
   실제 조회 중 범위 상한에 도달하면 부분 저장을 보존하고 실패로 알린다. 이 경우 기간을 줄여 새 작업을 만든다.
3. '선택 기간 가져오기'의 범위 안내를 확인해야 시작한다. 진행 중에도 일반 메일함/새로고침은 사용할 수 있다.
4. '중단'은 현재 네트워크 요청 후 반영한다. 저장된 메일은 남고 그 메일의 로컬 분석은 계속될 수 있다. 재개하면 메일별 체크포인트를 이어간다.
   서버를 다시 켜면 중단 상태로 복구된다. Gmail 페이지 만료는 처음부터 재조회하며 중복 저장하지 않는다.
5. 조회/저장/중복·제외 건수를 확인한다. 메일함에서 과거 본문을 열고, 로컬 분석 완료 후 검색과 해당 기간 보고서를 확인한다.
   수집·분석 때문에 Claude를 자동 호출하지 않는다. 일반 수신 시작 시점·커서는 바꾸지 않는다.

새 사용자의 도구 설치·Google 연결·Ollama 설정은 [setup.md](setup.md)를 먼저 따른다.

## 검증 구분

자동 검사 결과는 작업 완료 보고에 기록한다. 실제 사용자 DB·Google·Claude·Ollama는 개발 검증에서 사용하지 않는다.
Electron smoke 검사 코드는 최신 IPC allowlist·인증·키 누출·화면 격리 검사를 유지한다.
Linux 환경에 그래픽 실행 환경/실행 파일이 없으면 실제 Electron 검사는 미실행이며 브라우저 합성과 구분한다.
