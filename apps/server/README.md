# Klover 서버

> 현재 구현 기준 `develop f498d27`(PR #37), 2026-11-24 확인.

**설치·DB·Google 최초 연결·AI·토큰·실행·업데이트는 [setup.md](../../docs/dev/setup.md) 한 곳을 따른다.**
신규 사용자는 DB/Google 준비를 생략하지 않는다. 앱용 서버는 `python -m app.cli.run_mail_api`다.
일반 `uvicorn app.main:app`은 HTTP·스키마 점검용으로 저장소·계정·AI를 조립하지 않는다.

## 현재 서버가 제공하는 것

- 로컬 운영자 한 명의 Gmail 읽기 연결·토큰 암호화·명시적 INBOX 수신·중복 방지·메일 조회.
- 로컬 Bearer API와 Origin 거부·loopback 경계. 앱 main만 토큰을 읽고 API에 접근한다.
- F1 자동 로컬 분석/임베딩·F5 훅, F2 프로필/초안, F3 검색/답변, F4 보고서, F5 제안/할 일, 선택 AI 설정.
- PostgreSQL 마이그레이션 0001~0007_f1. 실제 사용자의 migration 상태는 check_database로 별도 확인한다.

`/health`는 인증·DB·Google·AI 없이 프로세스 응답만 확인한다. `/docs`와 `/openapi.json`은
공개 API의 스키마이지 기능 준비 완료 표시가 아니다. 전용 서버는 접근 로그를 끈다.
오류는 고정 code/message로 반환하며 입력·키·외부 응답 상세를 노출하지 않는다.

## 제한·검사·구조

현재 Redis/arq·주기 수신·WebSocket·실제 Calendar·메일 발송·기간 선택 과거 수집은 없다.
Claude 실패 시 로컬 대체 재시도·강제 로컬 전용 모드는 개발 예정이다.
프로필 미리보기의 답장 기본 AI 호출·외부 전송 주의는 setup.md를 반드시 확인한다.
기능 테스트는 합성 Google/AI와 분리 PostgreSQL을 사용한다. 실제 서비스 품질 검사와 다르다.
검사 명령은 setup.md의 개발자용 검사, 결과는 [이번 검증](../../docs/dev/verification-2026-11-24.md)을 따른다.
공유 타입은 실제 OpenAPI에서 자동 생성하며 `packages/api-types`를 직접 수정하지 않는다.

[API](../../docs/architecture/api.md) · [데이터](../../docs/architecture/data-model.md) ·
[구조](../../docs/architecture/system.md) · [과거 서버 README](../../docs/dev/archive/2026-11-24/server-readme-before.md)
