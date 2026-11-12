# 개발 환경 준비

> 최종 수정: 2026-10-16 | 코드 폴더(`apps/`)가 만들어지면 실제 명령으로 갱신한다.

## 필요한 도구

| 도구 | 버전 | 용도 |
| --- | --- | --- |
| Git | 최신 | 저장소 |
| Node.js | 22 LTS | 데스크톱 앱 |
| pnpm | 9 이상 | JS 패키지 관리 (모노레포 workspace) |
| Python | 3.12 | 서버 |
| uv | 최신 | Python 패키지·가상환경 관리 |
| Docker Desktop | 최신 | Postgres+pgvector, Redis |
| Claude Code | 최신 | 바이브 코딩 |

개발은 macOS·Windows 어디서나 가능하다. 단 **트레이·토스트 알림·시작 프로그램은 Windows PC에서 최종 확인**한다.

## 지금 실행 가능한 F4 첫 단위

Python 3.12 이상과 uv로 실행한다. DB·Gmail·AI 키 없이 **지정한 가짜 메일만**
읽어서 보고 입력을 준비한다. HTTP API나 완성된 보고서를 제공하는 명령은 아니다.

```bash
cd apps/server
uv sync --locked
uv run python -m app.cli.weekly_report_input \
  --fixture ../../fixtures/mails/F4-weekly-report.json \
  --user-id demo-hong --start 2026-10-05 --end 2026-10-09
uv run pytest
uv run ruff check .
uv run ruff format --check .
```

출력은 업무 그룹별 `mail_ids`·메일 정보, 제외 목록, `scope`다. 예제의 범위는
전체 12건 = 묶인 9건 + 제외 3건, 업무 6개다. 기간 밖 2건과 다른 사용자 1건은
조회되지 않는다. 아래 전체 앱 실행 절차는 아직 구현되지 않은 설계 기준이다.

## 처음 한 번

```bash
git clone <저장소 주소> klover && cd klover
cp .env.example .env              # API 키 등 채우기 (.env는 커밋 금지)
docker compose -f infra/docker-compose.yml up -d
pnpm install                      # 앱 의존성
cd apps/server && uv sync         # 서버 의존성
uv run alembic upgrade head       # DB 테이블 생성
```

## 매일 실행

```bash
# 터미널 1 — 서버
cd apps/server && uv run fastapi dev app/main.py

# 터미널 2 — 작업자 (수신·분석 파이프라인)
cd apps/server && uv run arq workers.main.WorkerSettings

# 터미널 3 — 데스크톱 앱
pnpm --filter desktop dev
```

## 메일 소스 선택

`.env`의 `MAIL_SOURCE`로 바꾼다.

- `fixture` (기본): `fixtures/mails/`의 가짜 메일을 시간차로 '도착'시킨다. Gmail 계정 없이 전체 흐름 개발 가능.
- `gmail`: 테스트 Gmail 계정 연결. Google Cloud 프로젝트의 OAuth 클라이언트가 필요하고, 계정을 **테스트 사용자**로 등록해야 한다(검수 전 앱 제한).

## 환경 변수 (.env.example)

| 이름 | 설명 |
| --- | --- |
| `DATABASE_URL` | Postgres 접속 주소 |
| `REDIS_URL` | Redis 접속 주소 |
| `MAIL_SOURCE` | `fixture` / `gmail` |
| `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` | Gmail·Calendar OAuth |
| `LLM_PROVIDER`, `LLM_API_KEY`, `LLM_MODEL` | LLM 설정 |
| `EMBEDDING_PROVIDER`, `EMBEDDING_MODEL` | 임베딩 설정 |
| `TOKEN_ENCRYPTION_KEY` | OAuth 토큰 암호화 키 |

API 키는 팀 비밀 저장소에서 공유한다. 채팅·문서·코드에 붙여 넣지 않는다.
