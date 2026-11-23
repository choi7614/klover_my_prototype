> 과거 기록: 2026-11-24 문서 정리 전 `f498d27`의 `docs/dev/mail-read-api.md`. 개인 경로·이전 실행 명령은 당시 기록이며 **현재 설치에 사용하지 않는다**. 현재 절차는 [setup.md](../../setup.md)를 따른다. 원문 출처와 표기는 보존했다.

# 맥북에서 실제 메일을 보는 연결 순서

이번 서버 단위는 기존 Gmail 연결·암호화 키·계정·메일·수신 명령을 보존하고,
앱이 읽을 인증·계정·받은편지함 목록·일반 텍스트 본문 API를 추가한다.
DB 변경이나 마이그레이션은 없다. Windows 앱 목표를 유지하면서 맥북 개발 실행을 먼저 확인한다.

## 확인 수준

| 항목 | 상태 |
| --- | --- |
| 실제 Google 로그인·계정 연결 | 사용자가 맥북에서 성공 확인 |
| 실제 새 Gmail 1건 저장·조회·중복 방지 | 사용자가 맥북 CLI에서 확인 |
| 접근 토큰 갱신 | 합성 Google 응답 자동 검사 통과, 실제 Google 갱신 미확인 |
| 새 인증·계정·목록·본문 API | 실제 PostgreSQL·HTTP 서버·Node fetch로 합성 메일 검사 |
| 새 API의 실제 Gmail 본문 조회 | 사용자 맥북의 check_mail_api에서 listed 1·detail ok 성공 보고 |
| F0 앱의 메일 목록·본문 표시 | 별도 F0 연결 후 사용자 확인 필요 |

## 1. 서버 코드가 develop에 병합된 뒤 준비

이 문서가 로컬 작업 브랜치에만 있을 때는 아직 맥북에서 새 명령을 실행하지 않는다.
병합 완료 안내를 받은 다음 Docker Desktop을 켠다. 기존 서버가 실행 중인 터미널에서는
**Control+C**로 멈춰 `%` 프롬프트가 나온 후 입력한다. 또는 새 터미널을 연다.

```bash
cd ~/Projects/klover-taeho-dev
git status --short --branch
```

`develop`이며 변경 파일이 없는 경우에만 계속한다. 다른 브랜치나 변경 파일이 있으면
전환·초기화하지 말고 그 상태를 먼저 확인한다.

```bash
git pull --ff-only origin develop
docker compose --env-file .env -f infra/docker-compose.yml up -d --wait
uv run --locked --directory apps/server python -m app.cli.prepare_mail_api
uv run --locked --directory apps/server python -m app.cli.run_mail_api
```

준비 명령은 `.local-secrets/mail-api-token`만 처음 생성한다(권한 600).
이미 있으면 검증하고 보존한다. 기존 `token.key`·Google JSON·`.env`를 다시 만들지 않는다.
비밀 값은 출력하지 않으므로 복사하거나 채팅에 올릴 필요가 없다.
API는 `127.0.0.1:8000`에서 실행된다. 마지막 명령 뒤에는 이 터미널을 켜둔다.
엔터를 눌러도 새 명령 프롬프트가 나오지 않는 것은 서버 실행 중이기 때문이다.

8000 포트가 사용 중이면 이전 health/Google 연결 서버를 해당 터미널에서 Control+C로 멈춘다.
다른 프로그램이 쓰는 포트는 임의로 종료하지 않는다. 필요하면 전용 서버와 검사 명령에
같은 `--port 8010`을 붙이고 아래 앱 주소도 8010으로 맞춘다.

## 2. 실제 계정·목록·본문 API 확인

**새 터미널**을 열어 실행한다.

```bash
cd ~/Projects/klover-taeho-dev
uv run --locked --directory apps/server python -m app.cli.check_mail_api
```

저장된 메일이 한 건이면 다음과 같은 결과다. 실제 계정 주소·본문·키는 출력하지 않는다.

```json
{"status":"ok","session":"ok","listed":1,"detail":"ok","has_next_page":false}
```

`detail: ok`는 API로 첫 메일 본문까지 읽고 형식을 확인했다는 뜻이다.
`listed: 0`, `detail: empty`라면 연결은 됐지만 조회할 받은 메일이 없는 상태다.
이미 저장한 메일을 지우거나 연결 시작 시점을 재설정하지 않는다.
이 결과를 확인한 뒤 [F0 연결 요청](../../F0-mail-api-handoff.md)의 문장을 F0 채팅에 보낸다.

## 3. F0 연결이 develop에 병합된 뒤 앱 실행

검토·묶음 승인 후 F0 브랜치에서 먼저 앱을 확인할 때는
[F0 메일함 실행 안내](../../F0-mailbox-run.md)를 따른다. 아래 명령은 develop 병합 후의 순서다.

**이 단계는 F0 구현·검사가 끝나고 병합된 다음에 실행한다.** 현재 서버만으로는
기존 F0 첫 화면에 메일 목록이 생기지 않는다. F0 채팅은 아래 환경 변수 계약을 구현한다.

앱용 새 터미널에서 변경 파일이 없는 develop인지 다시 확인하고 최신 코드를 받는다.

```bash
cd ~/Projects/klover-taeho-dev
git status --short --branch
git pull --ff-only origin develop
corepack pnpm install --frozen-lockfile
export KLOVER_API_TOKEN_FILE="$PWD/.local-secrets/mail-api-token"
export KLOVER_API_BASE_URL="http://127.0.0.1:8000"
corepack pnpm --filter desktop dev
```

두 환경 변수에는 **파일 경로와 로컬 주소만** 지정한다. 토큰 값을 직접 입력하지 않는다.
DB·조회 API 터미널은 계속 켜둔다. Electron 앱 창에서 다음을 확인한다.

1. 이미 연결한 Gmail 계정 주소가 표시된다.
2. 사용 시작 이후 받은 실제 메일이 목록에 표시된다.
3. 메일을 클릭하면 제목·발신자·수신 시각·일반 텍스트 본문이 표시된다.
4. 앱을 다시 열어도 기존 연결과 메일이 남는다.

이는 맥북에서 개발용 앱 창을 실행하는 과정이다. 설치용 `.app`·DMG 배포와
Windows 설치 파일·트레이·자동 실행 검증은 별도다. 첫 실행 5단계 전체·AI 기능은
아직 완료로 표시하지 않는다.

## 4. 새 메일을 추가로 확인할 때

수신은 아직 주기 실행이 아니므로 테스트 계정에 새 메일을 보낸 뒤 별도 터미널에서:

```bash
cd ~/Projects/klover-taeho-dev
uv run --locked --directory apps/server python -m app.cli.gmail_mail sync
```

2026-11-19부터 앱의 새로고침은 `POST /mails/sync`로 같은 수신을 실행한 뒤 목록을 다시 읽는다
(F0 공통 패치 01·02 적용 후). 위 명령은 터미널에서 직접 확인할 때 계속 쓸 수 있다.
과거 메일 수집·발송·보관·삭제·읽음 변경은 이번 범위 밖이다.

## 개발자용 계약과 검사

정확한 응답은 [API 목록](../../../architecture/api.md)과 실제 OpenAPI·생성 TS를 따른다.
모든 Origin 헤더를 거부하므로 renderer에서 직접 호출하지 않는다.
main에서 로컬 토큰을 읽고 Node fetch로 요청하며 IPC로 필요한 데이터만 전달한다.
전체 Bearer 인증은 한 명의 로컬 운영자용이며 공용 서버·다중 사용자 인증이 아니다.

서버 디렉터리에서 `uv run --locked pytest`, `uv run --locked ruff check .`,
`uv run --locked ruff format --check .`를 실행한다. PostgreSQL 검사는
[별도 테스트 DB](local-database-before.md#개발자용-실제-postgresql-검사)를 명시한다.
루트에서 `corepack pnpm gen:api-types`,
`corepack pnpm --filter @klover/api-types typecheck`,
`corepack pnpm --filter desktop typecheck`를 실행한다.
자동 검사는 모두 합성 계정·메일을 사용한다.
