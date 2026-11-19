# 실제 Gmail의 새 받은 메일 저장·조회

연결된 테스트 Gmail의 **받은편지함(INBOX)** 메일을 명령 실행 시 한 번 수신한다.
기존 계정의 `sync_started_at` 이후만 저장한다. F0 화면·앱용 메일 API·주기적 자동 수신·
AI·발송·보관/삭제 동기화는 후속 범위다. 이전 로그인은 사용자 맥북에서 성공 확인했고,
이번 새 수신·토큰 갱신의 실제 Google 확인은 아직 진행 전이다.

## 맥북에서 실행

이 단위가 develop에 병합된 뒤 Docker Desktop을 켠다. 서버 터미널은 Control+C로 종료하거나
새 터미널을 연다. 기존 `.env`·`.local-secrets`·계정·키·DB 볼륨을 그대로 사용한다.
새 JSON·키·계정·볼륨 생성과 추가 의존성·마이그레이션은 필요하지 않다.

```bash
cd ~/Projects/klover-taeho-dev
git status --short --branch
git pull --ff-only origin develop
docker compose --env-file .env -f infra/docker-compose.yml up -d --wait
uv run --locked --directory apps/server python -m app.cli.gmail_mail sync
uv run --locked --directory apps/server python -m app.cli.gmail_mail list --limit 20
```

변경 파일이 있으면 코드 받기 전에 기존 작업부터 확인한다. sync 성공 결과는
`status`, `saved`, `skipped`, `mode`, `token_refreshed`다. list는 조회 개수와 내부 ID·수신 시각·
분석 상태만 보여준다. `pending`은 AI 분석 전이라는 뜻이다. list는 Google에 접속하지 않는다.
제목·본문·주소·토큰은 로그나 터미널에 출력하지 않는다. 실제 내용의 화면 조회는 F0 후속 단위다.

## 실제 계정 확인 순서

1. sync·list를 한 번 실행해 기준 상태를 확인한다.
2. 다른 계정에서 연결한 테스트 Gmail로 새 메일을 보내고 받은편지함 도착을 확인한다.
3. sync·list를 다시 실행해 `saved` 증가와 새 ID·수신 시각을 확인한다.
4. 같은 상태에서 다시 sync하면 `saved: 0`이고 기존 ID가 유지돼야 한다.
5. access 토큰이 만료된 후 갱신 시 `token_refreshed: true`를 확인한다. 검사를 위해 토큰·
   암호문을 수동 편집하지 않는다. 자동 검사에서는 만료 상태를 합성해 확인한다.

refresh 토큰 자체가 만료·취소되면 기존 키를 보존하고 [Google 연결 안내](google-connection.md)로
재동의한다. 설정 생성 명령을 반복하지 않는다. 결과 숫자·일반 오류만 공유하고 실제 메일·토큰은
채팅에 보내지 않는다. 최초 연결 이후 이미 받은 메일도 첫 sync 때 저장될 수 있다.

## 저장·복구 방식과 제한

- 첫 수신은 Unix 초 기반 after 검색과 INBOX 필터로 후보 ID를 얻는다. 초 경계 누락을 막기 위해
  1초 앞부터 검색한 뒤 internalDate 메타데이터로 정확한 시작 시점을 비교한다.
  시작 전 후보의 제목·본문은 요청하지 않고, 저장소에서도 경계를 다시 확인한다.
- 이후 history.list의 messageAdded·labelAdded를 따라간다. 이력 만료(404)는 기존 시작 시점
  이후 받은편지함을 다시 조회한다. 계정 시작 시점을 현재 시간으로 바꾸지 않는다.
- 배치 시작에 얻은 history ID를 처리 후 저장한다. 수신 중 추가된 변경은 다음 실행에서 다시
  포함될 수 있으나 중복을 제거한다. 중간 실패는 새 메일 배치·커서를 함께 되돌린다.
- 같은 계정의 수신을 행 잠금으로 직렬화한다. 재수신은 기존 ID·본문을 덮어쓰지 않는다.
- 만료 60초 전 또는 동기화 전 프로필 확인의 401 응답 시 한 번 갱신한다. 응답에 refresh 토큰이 없으면 기존 것을
  보존하고 새 값이 있으면 암호화한다. 갱신 결과를 후속 프로필·메일 요청보다 먼저 확정해,
  후속 실패 때 회전된 refresh 토큰을 잃지 않도록 트랜잭션을 분리한다.
  장시간 수신 도중 만료·오류는 배치를 되돌려 알린다. 다시 실행하면 토큰 상태부터 확인한다.
- MIME text/plain을 우선 저장하고 HTML만 있으면 텍스트로 바꿔 script/style을 제외한다.
  첨부 API를 호출하지 않고 첨부 파트·HTML 원문은 저장하지 않는다. 인용·서명 제거는 후속 범위다.
- 처음 저장할 때의 읽음 상태를 반영한다. 기존 메일 읽음·보관·삭제 상태를 갱신하거나 Gmail 원본을
  변경하지 않는다. 이미 받은편지함 밖에 있는 새 메일은 이번 범위에서 수집하지 않는다.
- 실행당 100페이지/10,000개 후보, JSON 8MiB, 본문 4MiB, MIME 200파트/깊이 30으로 제한한다.
  반복 페이지·형식 오류·상한 초과는 실패로 알리고 커서를 넘기지 않는다. 지원하지 않는 메일을
  조용히 버리지 않는다. 장시간 대량 수신의 배치 재개·자동 재시도는 후속 범위다.
- 로컬 운영자 한 명의 테스트 계정 전용이며 다중 사용자 서버 인증을 대신하지 않는다.

## 검사와 구현 기준

자동 검사는 합성 Google 응답과 별도 실제 PostgreSQL을 사용한다. 실제 메일이나 토큰을 fixture·
로그에 넣지 않는다. 이전 Google 로그인 확인과 이번 실제 수신 성공은 구분해 보고한다.
일반 서버 OpenAPI·공유 타입·F0 화면은 변경하지 않았다.

Google의 [동기화 안내](https://developers.google.com/workspace/gmail/api/guides/sync),
[검색 시간대 안내](https://developers.google.com/workspace/gmail/api/guides/filtering),
[오프라인 갱신](https://developers.google.com/identity/protocols/oauth2/web-server#offline)을 기준으로 한다.
