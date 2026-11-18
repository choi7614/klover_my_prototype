# 맥북에서 개발용 DB 준비하기

이번 단위는 PostgreSQL 연결과 사용자·메일 계정·메일의 최소 저장 구조다.
DB 파일은 맥북 Docker의 `postgres_data` 볼륨에 보관된다. 별도 클라우드는 필요 없다.
실제 Gmail 로그인·메일 수신·앱 연결은 아직 구현하지 않았다. Google OAuth JSON은
이번 명령에서 사용하지 않으며 다운로드 폴더 등 저장소 밖에 보관한다.

## 처음 한 번

Docker Desktop을 실행한다. 서버가 실행 중인 터미널은 그대로 두고 새 터미널을 연다.
아래는 저장소를 `~/Projects/klover-taeho-dev`에 받은 경우다. 이 문서가 포함된 PR이
develop에 병합된 뒤, 작업 폴더에 본인의 변경이 없는 것을 확인하고 최신 코드를 받는다.

```bash
cd ~/Projects/klover-taeho-dev
git status --short --branch
git pull --ff-only origin develop
uv sync --locked --directory apps/server
uv run --locked --directory apps/server python -m app.cli.init_local_db
```

`git status`에 `## develop...origin/develop` 외의 변경 파일이 나오면 먼저 기존 작업을 확인한다.
초기화 명령은 루트 `.env`가 없을 때만 무작위 DB 비밀번호를 만들며 기존 파일은 보존한다.
비밀번호를 채팅에 보내거나 명령에 직접 붙여 넣을 필요는 없다. `.env`는 Git에서 제외된다.

저장소 루트에서 DB를 실행한다.

```bash
docker compose --env-file .env -f infra/docker-compose.yml up -d --wait
```

첫 실행에는 DB 이미지를 내려받는다. 완료 후 아래 명령으로 테이블을 만들고 확인한다.

```bash
cd apps/server
uv run --locked alembic upgrade head
uv run --locked python -m app.cli.check_database
```

정상 결과는 `{"database":"ok","schema":"current"}`다. 메일이나 접속 비밀번호는 출력하지 않는다.
HTTP `/health`는 서버 실행 확인이며 DB 검사는 별도 명령으로 수행한다.
서버 실행 시 테이블을 자동 생성하거나 마이그레이션하지 않는다.

5432 포트가 이미 사용 중이면 `.env`의 `POSTGRES_PORT`를 비어 있는 다른 번호로 바꾼 뒤
DB 실행 명령을 다시 실행한다. 설정을 생성한 뒤 비밀번호만 바꾸면 기존 DB의 비밀번호가
자동 변경되지는 않는다. 이미 사용 중인 DB 설정을 변경해야 하면 먼저 기존 데이터를 확인한다.

## 종료와 다시 실행

저장소 루트에서 종료한다. 컨테이너를 멈춰도 볼륨의 데이터는 남는다.

```bash
docker compose --env-file .env -f infra/docker-compose.yml stop db
```

다음에 Docker Desktop을 켜고 아래 명령으로 다시 실행한다.

```bash
docker compose --env-file .env -f infra/docker-compose.yml up -d --wait
```

Docker에서 볼륨을 삭제하면 저장된 데이터도 삭제되므로 기존 데이터가 있는 볼륨은 보존한다.
이 설정은 개발용으로, DB 포트를 맥북 자신의 `127.0.0.1`에만 열어 둔다.
다른 사람에게 공유하는 서버의 배포·접근 제어·백업은 후속 범위다.

## 개발자용 실제 PostgreSQL 검사

일반 `uv run --locked pytest`는 설정·기존 HTTP·F4 검사를 실행한다. PostgreSQL 검사는
`KLOVER_TEST_DATABASE_URL`을 지정하지 않으면 이유와 함께 건너뛴다.
실제 DB 검사는 별도 테스트 DB를 명시적으로 지정한다. 검사마다 무작위 이름의 임시
스키마를 만들고 그 스키마만 제거한다. 운영 데이터로 검사하지 않는다.

검사 범위는 마이그레이션 반복·되돌림·모델 일치, 별도 연결에서의 저장 데이터 조회,
중복 수신, 사용자 분리·DB 제약, 시작 시점 경계·시간대, 트랜잭션 되돌림과 상태 확인이다.
자동 검사 메일은 모두 합성 데이터다. 사용자 Gmail의 실제 메일은 fixture나 로그로 남기지 않는다.

이번 저장소는 SQLAlchemy의 동기 Session을 사용한다. 향후 비동기 API·작업자에서 호출할 때는
동기 실행 경계(스레드풀 등)를 적용한다. 이번 단위는 HTTP 메일 API를 공개하지 않는다.
