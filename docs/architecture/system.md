# 시스템 구조

> 최종 수정: 2026-11-18 | 그림: `docs/design/mockups/arch-01-system.png`

## 구현 진행 (2026-11-18)

공통 FastAPI 서버는 `GET /health`로 HTTP 프로세스 응답을 확인하는 첫 단위다.
F0 첫 화면과 F4 보고 입력 준비 서비스·CLI는 보존한다. PostgreSQL 연결·마이그레이션과
사용자·계정·받은 메일의 최소 저장소는 별도 명령으로 실행·검사한다.
메일 API·Gmail·AI·WebSocket과 앱의 실제 연결은 아직 없다. 아래 구조와 데이터 흐름은 완성 목표이며,
현재 실행 범위는 [개발 환경 준비](../dev/setup.md)와 [API 목록](api.md)을 따른다.

## 한눈에 보기

메일 계정 접근, AI 분석, 저장은 모두 **서버**가 맡고, **데스크톱 앱**은 서버가 만든 결과를 보여 주고 사용자의 승인을 받는다. 앱은 서버 API만 호출하며 메일 계정에 직접 접근하지 않는다.

```
[메일 소스]                [서버 (FastAPI)]                                      [데스크톱 앱 (Electron)]
Gmail (1단계) ─┐   메일 커넥터 (소스별 어댑터)                                  받은편지함·AI 분류
사외 웹메일 ───┼─▶      ↓                                                       자연어 검색
사내 메일 ─────┘   수신 감지·동기화 큐 (Redis + arq)                             답장 초안
                         ↓                                                       주간 보고
                   분석 파이프라인: F1 분류·메타데이터·임베딩 / F5 AI 스캔 ──푸시──▶ AI 제안 알림 (Windows 토스트)
                         ↓ 저장            ↘ 호출: AI 모델 (LLM, 임베딩)          프로필 설정
                   PostgreSQL: 메타데이터 · 벡터(pgvector) · 사용자 프로필         트레이 상주
                         ↓ 조회
                   서비스 API: 검색(F3) · 답장 초안(F2) · 주간 보고(F4) · 프로필(F2) ◀──API──▶
                         │
Google Calendar ◀────────┘ (사용자 승인 시 일정 등록, F5)
```

## 데이터 흐름

1. 새 메일 도착 → 커넥터가 감지 → 분석 파이프라인
2. 분석 결과 → 메타데이터·벡터로 저장
3. 일정 등 제안 → 앱에 푸시 알림(WebSocket → Windows 토스트) → 사용자 승인 시 캘린더 등록

## 구성 요소와 기술

| 구성 요소 | 기술 | 위치 |
| --- | --- | --- |
| 데스크톱 앱 | Electron + electron-vite + React + TypeScript, Tailwind + shadcn/ui, TanStack Query + Zustand | `apps/desktop` |
| 서버 API | Python 3.12 + FastAPI, uv | `apps/server/app/api` |
| 메일 커넥터 | 공통 인터페이스 + Gmail 구현 + fixture(가짜 메일) 구현 | `apps/server/app/connectors` |
| 수신 큐·작업 | Redis + arq | `apps/server/workers` |
| 분석 파이프라인 | ingest → preprocess → analyze(F1) → scan(F5) → embed | `apps/server/app/pipeline` |
| 저장소 | PostgreSQL 16 + pgvector, SQLAlchemy, Alembic | `apps/server/app/db` |
| AI 모델 호출부 | LLM·임베딩 인터페이스 + 외부 API 구현, 프롬프트는 MD 파일 | `apps/server/app/ai` |
| 실시간 푸시 | WebSocket | `apps/server/app/api/ws.py` |
| 타입 공유 | 서버 OpenAPI → TypeScript 타입 자동 생성 (openapi-typescript) | `packages/api-types` |
| 로컬 실행 | Docker Compose (Postgres+pgvector, Redis) | `infra/` |

## 설계 원칙 (3단계 사내 구축 대비)

- **메일 커넥터 분리**: 메일 소스가 바뀌는 부분은 `connectors/`에만 둔다. 파이프라인·저장소·화면은 소스와 무관하게 동작한다.
- **모델 호출부 분리**: LLM·임베딩은 반드시 `ai/`의 인터페이스로 호출한다. 다른 폴더에서 외부 API SDK를 직접 import하지 않는다.
- **저장소 분리**: DB 접근은 `db/repositories/`로만 한다. Vector DB를 별도 제품으로 바꿔도 리포지토리만 바꾸면 되게 한다.

## 데모 단계 단순화

| 항목 | 데모 | 나중에 |
| --- | --- | --- |
| Gmail 수신 감지 | 30초 폴링 (Gmail history API) | Gmail 푸시 알림 (Cloud Pub/Sub) |
| Vector DB | PostgreSQL pgvector | 필요 시 전용 Vector DB |
| 키워드 검색 | pg_trgm 부분 일치 | 한국어 형태소 분석 검색 |
| 서버 위치 | 개발자 PC 또는 공용 개발 서버 1대 | 사내 인프라 |
| 앱 배포 | electron-builder 설치 파일 공유 | 자동 업데이트, 코드 서명 |
| 오프라인 캐시 | 없음 | 확인 포인트 |
