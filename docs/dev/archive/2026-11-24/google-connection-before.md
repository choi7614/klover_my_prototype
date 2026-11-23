> 과거 기록: 2026-11-24 문서 정리 전 `f498d27`의 `docs/dev/google-connection.md`. 개인 경로·이전 실행 명령은 당시 기록이며 **현재 설치에 사용하지 않는다**. 현재 절차는 [setup.md](../../setup.md)를 따른다. 원문 출처와 표기는 보존했다.

# 맥북에서 테스트 Gmail 계정 연결하기

이 단위는 Google 로그인 → Gmail 읽기 권한 동의 → 연결된 계정 확인 → 서버의 암호화 토큰 저장이다.
메일 본문·목록을 수집하거나 보내지 않는다. Calendar 권한도 요청하지 않는다.
F0 앱의 연결 버튼·앱용 인증·메일 API는 후속 단위다. 토큰 갱신은 새 수신 명령에서 처리한다.

## 현재 확인 상태

사용자 맥북에서는 기존 서버 `/health`와 DB `schema: current`까지 확인했다.
Google 프로젝트 표시 이름은 `KLOVER TAEHO DEV`이며 테스트 사용자와 웹 OAuth 클라이언트는
사용자가 등록했고 이 연결 코드의 **연결 확인 완료** 화면을 맥북에서 확인했다.
새 메일의 수신·갱신은 [메일 수신 안내](../../gmail-mail-sync.md)에서 별도로 확인한다.
자동 검사는 합성 Google 응답과 실제 별도 PostgreSQL을 사용한다. 자동 검사 통과를
실제 Gmail 연결 성공으로 보고하지 않는다.

## Google 쪽 준비

- 프로젝트에서 Gmail API 활성화. 외부·테스트 상태에서 연결용 Gmail을 테스트 사용자로 등록.
- OAuth 클라이언트 유형: 웹 애플리케이션.
- 승인된 리디렉션 URI: `http://localhost:8000/auth/google/callback`.
- Google 인증 플랫폼의 **데이터 액세스 → 범위 추가 또는 삭제**에서
  `https://www.googleapis.com/auth/gmail.readonly`를 추가하고 저장한다. Calendar 쓰기·메일 발송
  범위는 추가하지 않는다. 같은 클라이언트에서 이전에 다른 범위를 허용했다면 이번 연결은
  범위 불일치로 거절될 수 있으므로 기존 동의를 확인한다.
- JSON은 맥북에 다운로드해 두고 채팅·Git·공유 드라이브에 올리지 않는다.
- Calendar API를 활성화했어도 이번 연결에서는 Calendar 권한을 요구하지 않는다.

## 새 코드 받기와 DB 갱신

이 문서가 포함된 PR의 develop 병합 후 실행한다. Docker Desktop을 켠다.
기존 서버 터미널은 Control+C로 종료하고 `%` 입력 줄이 나오는 것을 확인한다.

```bash
cd ~/Projects/klover-taeho-dev
git status --short --branch
git pull --ff-only origin develop
uv sync --locked --directory apps/server
docker compose --env-file .env -f infra/docker-compose.yml up -d --wait
uv run --locked --directory apps/server alembic upgrade head
uv run --locked --directory apps/server python -m app.cli.check_database
```

`git status`에 변경 파일이 있으면 기존 작업부터 확인한다. DB는 기존 사용자·메일을 유지하고
암호문 저장용 `google_credentials` 테이블만 추가한다. 테이블을 삭제하거나 새 볼륨으로 바꾸지 않는다.

## 비밀 정보를 채팅에 보내지 않고 설정하기

저장소 루트에서 다음 명령을 실행한다.

```bash
uv run --locked --directory apps/server python -m app.cli.configure_google
```

첫 질문에는 다운로드한 JSON의 전체 경로를 입력한다. 예를 들어 Finder의 다운로드 폴더에서
파일을 선택하고 Option+Command+C로 경로를 복사해 붙여 넣는다. 경로 양옆에 따옴표를 붙이지 않는다.
둘째 질문에는 테스트 사용자로 등록한 연결용 Gmail 주소를 입력한다. 값은 맥북에서만 사용한다.
JSON 내용·클라이언트 비밀키·암호화 키를 터미널 출력으로 요청하지 않는다.

설정 명령은 `.local-secrets/`에 필요한 JSON·연결 계정 설정·무작위 `token.key`를 보관한다.
폴더는 권한 700, 파일은 600으로 생성하고 Git에서 제외한다. 기존 폴더가 있으면 덮어쓰지 않는다.
DB 비밀번호가 있는 기존 `.env`도 바꾸지 않는다. 입력받은 JSON의 임의 URL은 사용하지 않고,
Google의 고정 인증·토큰·Gmail 프로필 주소만 호출한다.

`token.key`를 잃으면 저장된 토큰을 복호화할 수 없으므로 키와 DB를 함께 안전하게 보관한다.
설정 명령을 반복해서 키를 재생성하거나 폴더를 지우지 않는다. 계정을 바꾸는 것은 별도 작업이다.

## Google 로그인과 계정 확인

```bash
uv run --locked --directory apps/server python -m app.cli.run_google_connection
```

이 터미널은 서버 실행용이므로 켜 두고, 브라우저에서 아래 주소를 연다.

`http://localhost:8000/auth/google`

1. **Google 계정 연결** 버튼을 누른다.
2. 설정 때 입력한 개발·테스트용 Gmail 계정을 선택한다.
3. Google 화면에서 요청하는 Gmail 읽기 권한을 확인하고 동의한다. 거부하면 저장하지 않는다.
4. Klover 화면에 **연결 확인 완료: 선택한 계정 주소**가 표시되는지 확인한다.

복귀 후 서버는 Google의 `users/me/profile`로 메일 계정 주소를 확인한다. 설정한 주소와 다르면
DB에 저장하지 않는다. 필요한 읽기 권한이나 오프라인 접근용 갱신 토큰이 없으면 오류로 알린다.
처음 연결은 계정과 사용 시작 시점을 저장한다. 같은 계정 재연결은 계정 ID·시작 시점·기존 메일을
유지하고 토큰만 갱신한다. 새 응답에 갱신 토큰이 없으면 기존 토큰을 같은 키로 복호화해 보존한다.

브라우저 결과에는 계정 주소만 표시한다. 토큰·인증 코드는 표시하지 않는다.
결과 화면 주소의 쿼리나 Google JSON을 공유하지 말고 성공 여부와 일반 오류 문구만 알려준다.
Google의 외부·테스트 앱 정책에 따라 갱신 토큰이 약 7일 뒤 만료될 수 있다. 새 수신 명령은
access 토큰을 갱신하며, refresh 토큰 자체가 만료되면 이 연결 절차로 다시 동의한다.

연결 취소·만료·권한 거부·다른 계정 선택 시 처음 주소에서 다시 시작한다. DB 오류는 DB 실행·
마이그레이션을 확인한다. 8000 포트 사용 중 오류는 이전 서버를 Control+C로 종료한 뒤 다시 실행한다.
이 단위는 고정 복귀 주소를 사용하므로 포트만 임의로 바꾸지 않는다.

## 개발 범위와 보호 장치

- 별도 로컬 연결 서버로만 실행한다. 기존 `app.main:app`은 `/health`와 기존 OpenAPI 그대로다.
  로컬 HTML 경로는 앱의 JSON 업무 계약이 아니므로 기존 TS 타입에 추가하지 않는다.
- 연결 서버는 `127.0.0.1:8000`에만 바인딩하고 단일 프로세스를 사용한다. 원격 공유 서버용이 아니다.
  `localhost:8000` 호스트와 루프백 접속만 허용하고 프록시 헤더를 신뢰하지 않는다.
- 연결 시작은 같은 출처의 폼·브라우저 쿠키를 확인한다. state는 브라우저에 묶인 10분·일회용이며
  PKCE S256을 함께 사용한다. 서버 재시작 시 진행 중 로그인은 처음부터 다시 해야 한다.
- 브라우저 쿠키는 HttpOnly·SameSite=Lax, 응답은 no-store·프레임 금지다.
  비밀 값이 없는 연결 시작 폼은 `Referrer-Policy: same-origin`으로 정상 POST의 Origin을
  유지하고, 폼 이동에는 자신의 출처와 고정 `https://accounts.google.com`만 허용한다.
  콜백 결과와 Google으로의 303 응답은 `no-referrer`를 유지한다. Origin 누락·null·외부 출처는
  허용하지 않으며 기존 폼 토큰·state·PKCE 검증도 그대로다.
- 전용 실행 명령은 접근 로그를 끄고 외부 응답·비밀 값을 오류 문구에 포함하지 않는다.
- access/refresh 토큰·권한·만료 시각은 하나의 Fernet 인증 암호문으로 저장한다. 키는 DB에 저장하지 않는다.
- 고정 로컬 운영자 `local-development`의 Gmail 한 계정만 연결한다. 연결이 기존 다른 계정을
  덮어쓰지 않도록 막는다. 앱용 로그인·다중 사용자 인증을 구현한 것으로 간주하지 않는다.

## 검사

`apps/server`에서 `uv run --locked pytest`, `uv run --locked ruff check .`,
`uv run --locked ruff format --check .`를 실행한다. 실제 PostgreSQL 검사는 기존 DB 안내처럼
명시적 `KLOVER_TEST_DATABASE_URL`을 지정한다. 자동 검사는 Google 요청을 가로채 합성 응답을
제공하며 외부 계정에 접속하지 않는다. 실제 계정에서 확인할 항목은 위 로그인 단계다.
