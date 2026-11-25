# Klover 설치·실행 안내

> 2026-11-25 · 동료 설치 기준 main · 준비 원본 develop `f3c09f7`(#49). 최초 설치·평소 실행·업데이트의 단일 기준 안내.

처음이면 1~6절, 설치가 끝났으면 8절, 기존 사용자 업데이트는 9절을 따릅니다.
macOS는 터미널, Windows는 PowerShell에서 진행합니다. 2~6절의 공통 명령은 두 OS에서 같고,
환경 변수와 백업처럼 문법이 다른 부분은 OS를 구분했습니다. 최초 준비 이후에는 더블클릭으로 실행합니다.

현재는 소스에서 실행하는 개발용 데모다. 앱(Electron)·서버(FastAPI)·PostgreSQL과 로컬 Ollama를
같은 컴퓨터에서 사용한다. 클라우드 이전은 보류, 사내망 적용은 장기 목표다.
[현황판](progress.md)과 [공유 준비 점검](main-sharing-verification.md)에서 구현·실환경 미검증을 구분한다.

## 1. OS와 필요한 도구

| OS | 지원 목표·확인 수준 |
| --- | --- |
| Windows 10 이상 | 제품 목표. 이번 Windows 신규 설치·Google 로그인·Electron·트레이 검증은 미실행 |
| macOS | 기존 사용자 사용 확인 보고(API 키 연결 제외). 동료의 신규 설치·실제 모델 종합 검증과 Finder 실행은 미검증 |
| Linux | GitHub Ubuntu CI·이번 분리 환경 자동 검사 대상. 실제 Google·Ollama·Claude·모든 데스크톱 동작까지 확인한 것은 아님 |

명령은 **저장소 루트**에서 실행한다. Windows에서는 `cd` 대신 `Set-Location`도 사용할 수 있다.
`export`·`$PWD`·백업 명령은 macOS 전용 예시이며 Windows 예시를 따로 제공한다.
Windows 실행 경로는 준비했지만 실제 OS/파일 ACL 확인은 남아 있다. WSL 성공과 Windows 앱 성공은 다르다.

| 도구 | 버전·준비 | 공식 설치 안내 |
| --- | --- | --- |
| Git | 최신 안정 버전 | [Git](https://git-scm.com/downloads) |
| Node.js | package.json: `^22.22.2` 또는 `>=24.15.0`. 22/24 LTS 권장 | [Node.js](https://nodejs.org/en/download) |
| pnpm | **10.34.9**, 루트 packageManager에 고정. Corepack이 없으면 별도 설치 | [pnpm·Corepack](https://pnpm.io/installation) |
| Python | **3.12 권장**, pyproject는 3.12 이상. 다른 버전 전체는 미검증 | [Python](https://www.python.org/downloads/) |
| uv | 잠금 파일을 지원하는 최신 안정 버전 | [uv](https://docs.astral.sh/uv/getting-started/installation/) |
| Docker | Desktop(macOS/Windows) 또는 Engine+Compose v2(Linux), 데몬 실행 필요 | [Docker](https://docs.docker.com/get-started/get-docker/) |
| Ollama | 로컬 생성·임베딩용. 저장소에 버전 미고정, 이번 실제 모델 실행 미검증 | [Ollama](https://ollama.com/download) |
| Google | 본인의 테스트 Gmail·Cloud 프로젝트·웹 OAuth 클라이언트 | [Cloud Console](https://console.cloud.google.com/) |
| Claude API | 선택 사항. 키·사용 가능한 모델 ID·API 잔액 | [Anthropic Console](https://console.anthropic.com/) |

설치 후 새 터미널에서 `git --version`, `node --version`, `corepack pnpm --version`,
`uv --version`, `docker compose version`, `docker info`를 확인한다. Python은 uv가 준비할 수 있다. Corepack이 없는 Node 배포판이라면
pnpm 공식 안내로 정확한 버전을 설치한다. Codex·Claude Code는 앱 실행에 필요하지 않다.
모델은 메모리·디스크를 많이 쓰므로 모델 카드의 요구 사항을 확인한다. 최소 RAM·속도·정확도를 보장하지 않는다.

## 2. 새 사용자 — 저장소와 의존성

동료용 공유 버전은 **main**을 지정한다. 공개 저장소의 읽기에는 초대가 필요하지 않다.
비공개 저장소로 바뀌면 소유자에게 접근 권한을 받고 GitHub 인증을 준비한다. 본인이 선택한 부모 폴더에서 실행한다.

```bash
git clone --branch main --single-branch https://github.com/choi7614/klover_my_prototype.git
cd klover_my_prototype
git status --short --branch
git log -1 --oneline
uv sync --locked --python 3.12 --directory apps/server
corepack pnpm install --frozen-lockfile
```

이후 별도 안내가 없으면 **저장소 루트**에서 실행한다. 특정 개인의 폴더나 이미 만든 토큰은 필요하지 않다.
잠금 파일은 바꾸지 않는다. Node 버전 오류는 버전을 맞추고 새 터미널에서 재시도한다.
이미 사용 중이면 새 설치를 반복하지 말고 [업데이트](#9-기존-사용자--업데이트)를 따른다.
`git log -1 --oneline` 결과는 문의할 때 쓸 코드 버전이다.

Electron 실행 파일 다운로드가 누락된 경우 먼저 네트워크·프록시 설정을 확인하고 다음을 한 번 실행한다.

```bash
corepack pnpm --filter desktop exec node node_modules/electron/install.js
```

새 `.env`·키를 다시 만들거나 의존성/DB를 삭제하는 복구 절차가 아니다.

## 3. 새 사용자 — DB 설정·실행·마이그레이션

Docker를 켠 뒤 실행한다.

```bash
uv run --locked --directory apps/server python -m app.cli.init_local_db
docker compose --env-file .env -f infra/docker-compose.yml up -d --wait
uv run --locked --directory apps/server alembic upgrade head
uv run --locked --directory apps/server alembic current
uv run --locked --directory apps/server python -m app.cli.check_database
```

`init_local_db`는 `.env`가 없을 때만 무작위 DB 비밀번호를 만든다. **.env.example을 그대로 복사하지 않는다.**
예시 비밀번호 `replace-with-local-random-password`는 서버가 거절한다. 이미 있는 `.env`는 보존하므로
잘못된 예시가 자동으로 고쳐지지도 않는다. 잘못 복사했고 DB를 아직 만들지 않았다면 로컬 편집기로
고유한 무작위 비밀번호를 설정한다. 기존 DB는 비밀번호만 바꿔도 갱신되지 않으므로 삭제·재생성하지 않는다.

정상 결과: `0009_f5_calendar (head)`, `{"database":"ok","schema":"current"}`.
DB 이미지 `pgvector/pgvector:pg16`, DB 이름·사용자 `klover`, 기본 호스트 포트 `5432`다.
데이터는 기본 Compose 프로젝트 기준 `klover_postgres_data` 볼륨에 남는다.
포트가 겹치면 **새 DB 실행 전** `.env`의 `POSTGRES_PORT`를 빈 포트로 바꾼다.
`DATABASE_URL` 환경 변수가 있으면 위 설정보다 우선한다. 기존 셸 설정을 확인하되 값을 공유하지 않는다.
기존 설치의 Compose 프로젝트명·볼륨을 임의로 바꾸면 기존 DB가 빈 DB처럼 보일 수 있다.

Redis·arq·별도 작업자는 현재 실행하지 않는다. 서버는 테이블을 자동 생성하지 않는다.
`/health` 성공은 프로세스 응답일 뿐 DB·Gmail·AI 준비 완료가 아니다.

## 4. 새 사용자 — Google 프로젝트·OAuth JSON·로그인

1. 본인의 Google Cloud 프로젝트를 만들거나 선택하고 **Gmail API**를 활성화한다.
2. Google Auth Platform의 브랜딩·대상 사용자 설정을 완료한다. 외부 앱의 테스트 상태에서는
   연결할 Gmail을 **테스트 사용자**로 등록한다. 프로젝트 이름은 본인이 정한다.
3. 데이터 액세스에서 `https://www.googleapis.com/auth/gmail.readonly` 범위를 등록한다.
   최초 메일 연결에는 Calendar 권한이 필요하지 않다. Calendar는 앱 설정에서 별도로 동의한다.
4. OAuth 클라이언트를 **웹 애플리케이션**으로 만들고 리디렉션 URI를 정확히
   `http://localhost:8000/auth/google/callback`으로 등록한다. 데스크톱 유형 JSON은 사용하지 않는다.
5. JSON을 내려받아 본인 컴퓨터의 비공개 위치에 보관한다. Git·채팅·공유 문서에 올리지 않는다.
6. 아래 설정 명령의 질문에 JSON의 전체 경로(따옴표 제외), 테스트 사용자 Gmail 주소를 입력한다.
   JSON 내용·클라이언트 키를 붙여 넣는 절차가 아니다.

```bash
uv run --locked --directory apps/server python -m app.cli.configure_google
uv run --locked --directory apps/server python -m app.cli.run_google_connection
```

서버 터미널을 켜둔 채 `http://localhost:8000/auth/google`을 연다.
**Google 계정 연결 → 지정한 테스트 계정 → Gmail 읽기 동의 → 연결 확인 완료**를 확인한다.
현재 최초 설정은 CLI·브라우저 방식이다. **앱 첫 화면의 Google 연결·다음 버튼은 비활성**이다.
고정 콜백이므로 이 서버의 포트는 임의로 바꾸지 않는다. 본인의 이전 서버는 해당 터미널에서
`Ctrl+C`로 종료하며 다른 프로그램의 프로세스를 임의 종료하지 않는다.

설정은 `.local-secrets/`에 JSON·계정 설정·`token.key`를 저장하고 OAuth 토큰은 DB에 암호화 저장한다.
`configure_google`은 폴더가 있으면 덮어쓰지 않는다. 기존 사용자는 재실행하지 않는다.
성공 후 **Google 연결 서버를 Ctrl+C로 종료**한다. 앱용 서버가 같은 포트를 사용한다.
재동의는 기존 JSON·키를 유지한 채 `run_google_connection`만 다시 실행한다. 같은 계정 재연결은
메일·시작 시점·ID를 보존한다. 다른 계정으로 바꾸는 도구는 아직 없다.
외부·테스트 앱의 갱신 토큰 만료 정책은 [Google 오프라인 동의](https://developers.google.com/identity/protocols/oauth2/web-server#offline)를 확인한다.
인증 URL의 쿼리·코드·Google 응답·실제 계정·메일을 오류 보고에 첨부하지 않는다.

## 5. 새 사용자 — 기본 로컬 AI

Ollama 공식 앱을 설치해 로컬 서비스를 켠다. 이미 실행 중이라면 중복 실행하지 않는다.
서비스가 꺼져 있다면 별도 터미널에서 `ollama serve`를 실행해 켜둔다.
다른 터미널에서 생성 모델·임베딩 모델을 받는다. 생성 모델은 **예시**이며 기기에 맞게 선택한다.

```bash
ollama pull qwen3:14b
ollama pull bge-m3
ollama list
```

기존 DB 비밀번호를 보존하며 루트 `.env`에 아래 **AI 항목만** 로컬 편집기로 추가·수정한다.
다른 모델을 받았다면 `OLLAMA_MODEL`은 `ollama list`에 나타난 정확한 태그로 바꾼다.

```dotenv
AI_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen3:14b
OLLAMA_FORMAT=schema
OLLAMA_THINK=false
OLLAMA_TIMEOUT_SECONDS=120
OLLAMA_RETRIES=1
EMBEDDING_MODEL=bge-m3
EMBEDDING_DIMENSIONS=1024
```

`OLLAMA_THINK=false`는 지원 모델용이며 미지원이면 항목을 비운다. Ollama 주소는 같은 컴퓨터의
loopback HTTP만 허용한다. 기존 데이터의 임베딩 모델·차원을 임의로 바꾸지 않는다.

```bash
uv run --locked --directory apps/server python -m app.cli.check_ai
uv run --locked --directory apps/server python -m app.cli.check_ai --ping
```

첫 명령은 설정만 읽는다. 두 번째는 **실제 선택된 제공자**에 합성 문장을 보내 생성·임베딩을 검사한다.
로컬 설정에서 `external_transfer: false`, `generation: ok`, `embedding: ok`를 확인한다.
기존 셸·.env가 Claude를 선택하면 `--ping`도 외부 요청·과금이 생기므로 로컬 선택을 먼저 확인한다.
CLI는 앱에 암호화 저장한 Claude 설정을 읽는 검사와 다르다.

## 6. 새 사용자 — 앱 API 토큰·서버·앱 실행

Google 연결 성공 후 준비한다. 기존 API 토큰은 검증·보존하며 값을 출력하지 않는다.

```bash
uv run --locked --directory apps/server python -m app.cli.prepare_mail_api
uv run --locked --directory apps/server python -m app.cli.run_mail_api
```

서버 터미널을 켜둔다. 일반 `uvicorn app.main:app`은 HTTP·스키마 점검용이며 실제 메일·AI 저장소를
조립하지 않으므로 앱용 명령으로 대신 쓰지 않는다. 전용 명령은 접근 로그를 끈다.
더블클릭 실행과 Google/Calendar 동의는 기본 8000 포트를 사용한다. 먼저 기존 서버를 종료한다.
수동 메일 서버의 포트를 변경하는 고급 사용에서는 검사·앱 주소도 동일하게 맞춰야 한다.

**수동 실행을 사용할 때만** 새 터미널에서 저장소 루트로 이동해 실행한다. 평소에는 아래 8절의 더블클릭 실행을 권장한다.

macOS/Linux:

```bash
uv run --locked --directory apps/server python -m app.cli.check_mail_api
export KLOVER_API_TOKEN_FILE="$PWD/.local-secrets/mail-api-token"
export KLOVER_API_BASE_URL="http://127.0.0.1:8000"
corepack pnpm --filter desktop dev
```

Windows PowerShell에서는 위 `export` 대신 다음을 사용한다.

```powershell
uv run --locked --directory apps/server python -m app.cli.check_mail_api
$env:KLOVER_API_TOKEN_FILE = Join-Path (Get-Location) '.local-secrets\mail-api-token'
$env:KLOVER_API_BASE_URL = 'http://127.0.0.1:8000'
corepack pnpm --filter desktop dev
```

API 확인: `status: ok`, `session: ok`, `listed`(개수), `detail: ok/empty`.
0건은 정상적인 빈 목록일 수 있다. 앱 토큰 환경 변수는 **절대 파일 경로**이며 키 내용이 아니다.
`mail-api-token`은 POSIX 권한 600인 일반 파일이어야 한다. 앱 main만 읽고 renderer에는 전달하지 않는다.
`dev:renderer`는 브라우저 미리보기로 Electron 통로가 없으므로 실제 메일 앱을 대신하지 못한다.

## 7. 첫 연결 후 확인과 선택적 Claude

1. 먼저 **AI 설정**에서 답장·검색·보고서 기본값을 모두 로컬로 두고 외부 전송 동의는 끈다.
2. **첫 연결 완료 후** 다른 계정에서 테스트 Gmail로 가짜 업무 내용의 새 메일을 보낸다.
   앱 새로고침 → 새 메일 건수·목록 → 텍스트 본문 → 분석 상태·요약·분류·제안을 확인한다.
   분석은 백그라운드라 시간이 걸린다. 같은 메일을 다시 수신해도 중복 행이 없어야 한다.
   CLI `gmail_mail sync`는 저장만 하므로 분석 확인은 앱용 서버를 켜고 앱 새로고침으로 한다.
3. **설정 → 내 프로필·문체**에서 이름·소속·인사·서명·보고 양식·보고 대상을 저장하고 재진입해 보존을 확인한다.
4. 메일의 **답장 초안 만들기**로 진입해 로컬을 고르고 **초안 만들기**를 누른다. 수정·재작성·실패 시
   편집본 보존을 확인한다. 초안의 실제 발송은 아직 없다.
5. 상단 검색창에서 테스트 메일의 간단한 주제·기간·상대를 검색해 목록·근거·답변을 확인한다.
   조직·미회신·분류·첨부 조건은 미지원이다. [F3 공통 연결](F3-memory-search-integration.md)을 포함한
   버전은 F1의 호환 벡터도 검색한다. 누락·오류 안내와 키워드 결과를 구분해 확인한다.
6. **주간 보고**에서 시작일부터 오늘까지의 첫 주 기간·프로필·보고 대상을 확인한 뒤 생성한다.
   1주를 기다릴 필요는 없지만 메일이 없거나 분석이 미완료면 자료가 없다. 대상·제외 건수·원문 근거·
   저장·재조회·편집·복사를 확인한다. Word 출력·자동 발송은 미구현이다.

7. Calendar가 필요하면 Google 프로젝트에서 Calendar API를 사용 설정하고 **설정 → 캘린더 연결**에서
   기존 Gmail과 같은 계정으로 추가 동의한다. 연결 상태를 다시 확인하고 별도 테스트 캘린더에서 승인 등록한다.
   연결만으로 일정이 등록되지 않는다. [상세 확인](settings-calendar-integration.md).
8. **설정 → 개인정보·학습 데이터**에서 저장된 프로필·동의·기록을 확인한다. 실제 수집·학습은 준비 중이다.
   삭제 버튼은 실제 기록을 지우므로 정상 사용자 데이터로 시험하지 않는다.

위는 사용자 확인 체크리스트이며 이번에 실제 Google·모델·메일로 성공 검증했다는 뜻이 아니다.
기본 수신은 사용 시작 이후의 현재 INBOX다. 과거 메일은 설정에서 기간을 골라 명시적으로 가져온다.
[기간 선택 과거 메일 가져오기](../product/features/planned-mail-history-import.md)는 **구현됐으며 실제 Gmail 검증은 남아 있다**.
시작 시각·DB를 수동 수정하거나 재연결해 우회하지 않는다.

Claude가 필요한 경우에만 앱 **AI 설정**에서 키·본인 계정에서 사용 가능한 모델 ID를 입력하고
전송 자료와 비용 안내를 읽어 최초 동의를 저장한다. 세 기본값은 로컬로 두고 해당 화면에서
**이번 요청만 Claude** 선택을 권장한다. 저장한 기본값은 이후 요청에도 적용된다.
키는 현재 서버 `.local-secrets/ai-settings.enc`에 암호화 저장하고 복호화 키는 `ai-settings.key`다.
기존 OAuth·DB 키와 다르며 앱에는 등록 여부만 반환한다. 예시 기본 모델 ID의 실제 사용 가능성을 보장하지 않는다.

| Claude 요청 | 전송될 수 있는 자료 |
| --- | --- |
| F2 초안·수정 | 선택 메일·프로필·작성 중 답장·수정 요청 |
| F3 검색·답변 | 질문·검색 조건 입력, 답변에 필요한 검색 결과 |
| F4 보고 | 대상 업무 메일·분석·프로필·보고 양식 |
| 연결 검사 | 메일 없는 합성 소량 요청. 실제 API 요금 발생 가능 |

Claude 구독과 API 요금은 별도다. 개인의 동의는 조직 보안 승인을 대신하지 않는다.
자동 프로필 미리보기는 로컬만 사용한다. 로컬 전용 모드에서는 Claude 선택·호출·연결 검사를 차단한다.
Claude 생성 실패 시 로컬로 1회 전환하고 실제 처리 AI를 표시한다. 연결 검사는 전환하지 않는다.
자세한 정책·과거 메일 가져오기·기존 사용자 업데이트는 [통합 실행 안내](local-ai-history-run.md)를 따른다.

## 8. 평소 실행·종료

최초 설치 후에는 키 생성·Google 연결·의존성 설치를 반복하지 않는다.

1. Docker Desktop을 켜고 준비 완료를 기다린다.
2. macOS는 `Klover-Start.command`, Windows는 `Klover-Start.cmd`를 더블클릭한다.
3. 진행 창을 열어둔다. 도구가 DB·Ollama 모델·계정 인증을 확인하고 서버·앱을 시작한다.
4. 앱을 종료하면 이번 실행 도구가 띄운 앱·서버·Ollama를 정리한다. 기존 DB/Docker와 기존 Ollama는 그대로 둔다.
5. 중단할 때는 진행 창의 Control+C를 사용한다. 강제 창 닫기는 정리를 보장하지 않는다.

실행 파일은 저장소 안에 두고 바탕화면에는 바로가기를 만든다. 실제 두 OS의 더블클릭 실행은 검증 대기다.
실행 권한·준비 확인·오류 해결은 [실행 도구 안내](desktop-launcher.md)를 따른다.
수동 실행이 필요하면 6절의 서버·앱 명령을 사용한다. 주기 수신은 없으므로 앱에서 새로고침한다.

DB까지 멈추려면(데이터는 보존):

```bash
docker compose --env-file .env -f infra/docker-compose.yml stop db
```

`down -v`·볼륨 삭제·DB 초기화·downgrade는 실행하지 않는다.

## 9. 기존 사용자 — 업데이트

앱·서버를 종료하고 10절에 따라 DB와 비밀 파일을 함께 백업한다.
`git status --short --branch`, `git fetch origin`으로 현재 브랜치·변경을 확인한다.
**미커밋 파일이 없고 로컬 main이 분기하지 않았을 때만** 아래를 실행한다.
기능 브랜치·기존 변경이 있으면 reset·강제 전환·덮어쓰기를 하지 말고 먼저 작업을 보존한다.

```bash
git fetch origin main:refs/remotes/origin/main
git switch main
git pull --ff-only origin main
uv sync --locked --directory apps/server
corepack pnpm install --frozen-lockfile
docker compose --env-file .env -f infra/docker-compose.yml up -d --wait
uv run --locked --directory apps/server alembic upgrade head
uv run --locked --directory apps/server alembic current
uv run --locked --directory apps/server python -m app.cli.check_database
```

기존 develop 사용자도 위 절차로 main을 선택할 수 있다. 명시적 fetch는 develop만 받던 저장소에도 main을 가져온다.
`git switch main`이나 `pull --ff-only`가 실패하면 중단하고 변경을 보존한다. reset·강제 Push로 맞추지 않는다.
개발 참여로 develop을 계속 사용할 때만 기존 브랜치를 유지하며 `git pull --ff-only origin develop`을 사용한다.
두 브랜치를 동시에 실행하지 않는다.

기존 `.env`·`.local-secrets`·DB 볼륨·Compose 프로젝트명·모델 차원을 유지한다.
비밀번호·키·계정을 다시 만들지 않는다. PR #37 자체에는 새 DB 이력이 없지만 이전 사용자는
`0009_f5_calendar`까지 필요하다. Calendar 연결은 [설정·Calendar 통합 안내](settings-calendar-integration.md)를 따른다. 재실행 후 `check_mail_api`와 7절의 합성 메일 흐름을 확인한다.
자동 검사 성공은 본인의 DB·재로그인·모델 품질 성공을 보장하지 않는다.

## 10. 데이터와 암호화 키 백업

아래 첫 예시는 macOS/Linux입니다. Windows PowerShell 예시는 뒤에 있습니다.

앱·서버의 쓰기를 멈추고 DB를 켠 상태에서, 본인이 정한 **저장소 밖의 새 비공개 백업 폴더**에 저장한다.
`BACKUP_DIR`은 먼저 실제 절대 경로로 설정한다. 아래 명령은 예시이며 이번 작업에서 운영 백업·복구는 실행하지 않는다.

```bash
# BACKUP_DIR을 본인이 만든 비공개 백업 폴더 절대 경로로 먼저 설정한다.
umask 077
test -d "$BACKUP_DIR" || exit 1
docker compose --env-file .env -f infra/docker-compose.yml exec -T db pg_dump -U klover -d klover -Fc > "$BACKUP_DIR/klover-$(date +%Y%m%d-%H%M%S).dump"
cp -p .env "$BACKUP_DIR/"
cp -Rp .local-secrets "$BACKUP_DIR/"
```

Windows PowerShell(앱·서버를 종료하고 DB가 켜진 상태):

```powershell
$backupDir = Join-Path $HOME ('Klover-backups\backup-' + (Get-Date -Format 'yyyyMMdd-HHmmss'))
New-Item -ItemType Directory -Path $backupDir -ErrorAction Stop | Out-Null
docker compose --env-file .env -f infra/docker-compose.yml exec -T db pg_dump -U klover -d klover -Fc -f /tmp/klover-backup.dump
if ($LASTEXITCODE -ne 0) { throw 'DB 백업 실패' }
docker compose --env-file .env -f infra/docker-compose.yml cp db:/tmp/klover-backup.dump "$backupDir/klover.dump"
if ($LASTEXITCODE -ne 0) { throw '백업 파일 복사 실패' }
docker compose --env-file .env -f infra/docker-compose.yml exec -T db pg_restore --list /tmp/klover-backup.dump | Out-Null
if ($LASTEXITCODE -ne 0) { throw '백업 형식 확인 실패' }
Copy-Item .env $backupDir -ErrorAction Stop
Copy-Item .local-secrets $backupDir -Recurse -ErrorAction Stop
```

Windows PowerShell 5의 바이너리 출력 변환을 피하려고 DB 컨테이너에서 덤프한 뒤 파일로 복사합니다.
백업 폴더는 본인 계정만 접근하는 비공개 위치에 보관하세요.

매번 새 백업 폴더를 쓰고 실패한 dump를 성공 백업으로 취급하지 않는다. 저장장치를 암호화하고 공유·Git 업로드하지 않는다.
DB 덤프에는 **실제 메일 본문**이 포함된다. `.local-secrets`에는 Google JSON·계정 설정·`token.key`·API 토큰,
사용한 경우 `ai-settings.key`·`ai-settings.enc`가 있다. DB만 있고 token.key를 잃으면 OAuth 복호화가 불가능하다.
AI 설정의 암호문과 키도 함께 보존한다. 코드 버전·DB 연결 포트·Compose 프로젝트명은 비밀 값 없이 기록한다.
복구는 기존 DB에 덮어쓰기 전에 별도 볼륨·포트에서 확인하는 통합 작업이다.

## 11. 오류 해결과 아직 쓸 수 없는 기능

| 증상 | 확인 순서 |
| --- | --- |
| 실행 코드·package.json이 없음 | main 브랜치·커밋 확인. 공유 버전 반영 전 초기 커밋이면 최신 main을 받기 |
| DB 비밀번호 거절 | 예시 복사 여부·기존 DB 암호·DATABASE_URL 우선 여부. DB 삭제 금지 |
| DB·schema 오류 | Docker → 포트 → migration → check_database. /health만으로 판단 금지 |
| Google 설정 생성 실패 | 웹 JSON·정확한 콜백·기존 .local-secrets 확인. 키 삭제 금지 |
| Google 접근 거부·재동의 | 본인 프로젝트 Gmail API·테스트 사용자·readonly·선택 계정·토큰 만료 확인 |
| 8000 충돌 | 본인 연결 서버를 Ctrl+C로 종료. 앱 서버 포트 변경 시 검사·앱 주소도 변경 |
| 앱 인증 실패 | 전용 run_mail_api·prepare_mail_api·절대 토큰 경로·POSIX 600 확인. 토큰 출력 금지 |
| 앱 연결 버튼 비활성 | 현재 제한. 4절 CLI·브라우저 연결 선행 |
| 새 메일 없음 | 연결 후 새 테스트 메일·INBOX·앱 새로고침. 과거 INBOX는 명시적 가져오기, 보낸편지함 수집은 없음 |
| 분석 대기·AI 오류 | Ollama 실행·정확한 태그·로컬 check_ai --ping. .env 수정 후 서버 재시작. 반복 요약 실패는 [고정 사유 진단](F1-summary-diagnostics.md)(해당 변경을 포함한 버전에서 사용) |
| 검색 조건 미지원 | 기간·상대·주제로 좁히기. 조직·미회신·분류·첨부는 미지원 |
| 의미 검색 제한 안내 | [공통 연결 포함 버전](F3-memory-search-integration.md)인지 확인. 기존 F1 임베딩의 제공자·모델 태그·차원·모드가 현재 로컬 설정과 맞아야 함. 기존 벡터를 삭제하거나 재생성하지 말고 키워드 결과와 안내를 확인 |
| 보고서 생성 불가 | 프로필·보고 대상·분석 완료 업무 메일·0008·AI. 첫 주 자체는 차단하지 않음 |
| Electron 다운로드/실행 실패 | 네트워크·프록시·지원 OS·그래픽 환경·sandbox 설치를 확인. 이번 Linux Cloud는 SUID sandbox 오류로 창 실행 미검증. 기존 파일 삭제나 sandbox 끄기를 일반 해결법으로 쓰지 않음 |
| Claude 실패 | 앱 키 등록·모델 ID·동의·API 잔액. 생성 실패 시 로컬 1회 전환. 연결 검사는 대체하지 않음 |

현재 미구현: 앱 안 Google 연결·5단계 완료, 작성·발송·보관·삭제·스팸·읽음 동기화,
주기 수신, WebSocket·OS 알림·트레이·자동 실행, F2 관련 메일 자동 검색·문체 학습 수집, Word 출력, 배포 설치 파일·자동 업데이트.
후속 개발·장기 목표는 [현황판](progress.md)·[통합 후속 작업](integration-followups.md)을 본다.
오류 보고는 단계·OS·코드 버전·일반 오류 코드·건수만 공유한다.
키·토큰·.env·Google 응답·실제 메일·인증 URL·전체 콘솔 로그는 붙여 넣지 않는다.

## 12. 개발자용 안전한 검사

CI는 서버 Ruff·pytest와 앱 lint·typecheck·단위 검사다. DB 검사는 전용 DB 변수가 없으면 skip된다.
실제 DB 검사는 **분리된 테스트 DB만** `KLOVER_TEST_DATABASE_URL`, `KLOVER_F1_TEST_DATABASE_URL`,
`KLOVER_F5_TEST_DATABASE_URL`에 지정한다. F1 DB 이름은 `_test`로 끝나야 하고 F5는 loopback의 정확한 이름 `klover_f5_test`만 허용한다. 운영 접속 주소를 넣지 않는다.

```bash
uv run --locked --directory apps/server ruff check .
uv run --locked --directory apps/server ruff format --check .
uv run --locked --directory apps/server pytest -q -rs
corepack pnpm --filter desktop lint
corepack pnpm --filter desktop typecheck
corepack pnpm --filter desktop test
corepack pnpm --filter desktop build
corepack pnpm --filter desktop exec playwright install chromium
corepack pnpm --filter desktop test:e2e
```

브라우저 검사는 합성 IPC·화면을 검사하며 실제 Gmail·AI 성공을 뜻하지 않는다.
`test:electron`·`test:mail-read`는 별도 그래픽 환경이 필요한 Electron 실행 검사다.
Playwright Electron 검사는 OS sandbox를 끄므로 OS sandbox 안전성 검증이 아니다. 두 smoke 스크립트의 IPC/새로고침 기대값은 #39에서 보완했으며 네이티브 실행 재검증은 남아 있다. 이번 환경은 Electron SUID sandbox 오류로 정상 창이 미검증이며 sandbox를 끄는 사용자 우회는 권장하지 않는다. [근거와 전달 사항](integration-followups.md)을 본다.
`pnpm gen:api-types`는 생성 파일을 쓰는 개발 명령으로 일반 설치·실행에는 필요하지 않다.
[과거 기록](archive/2026-11-24/README.md)의 개인 경로·과거 명령은 현재 실행 지시로 쓰지 않는다.

## 앱에서 기능 찾기

받은편지함의 설정은 설정 첫 화면(`/settings`)으로 이어진다.
분석 완료 메일은 본문의 메일 분류 선택으로 변경할 수 있다. 새 DB 이력은 없다.
세부 검증 기록과 확인 절차는 [분류·설정 UI](category-settings-ui.md)를 따른다.
