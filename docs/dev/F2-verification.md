# F2 구현·검증 보고

## 결과

작업 브랜치는 `feat/F2-profile-draft`, 최초 기준 커밋은 `0f68ad1`이다.
사용자 승인 후 F1/F3가 포함된 최신 `origin/develop` `9244454`를 가져와 아래 검사를 다시 실행했다.
기존 로컬 `work` 브랜치와 모든 기존 파일을 보존했다. 변경은 F2 전용 새 파일뿐이다.
이 문서는 검사 시점의 구현 범위를 기록하며 커밋·PR·develop 병합의 최종 상태는 GitHub PR을 따른다.
사용자는 이 분리 구현물의 커밋·Push·PR과 문제없는 경우 develop 병합을 승인했다.
공통 연결 패치는 미적용 상태로 포함하며 main 병합은 승인 범위 밖이다.

| 요청 범위 | 상태 | 실제 확인한 내용 |
| --- | --- | --- |
| 기본 정보·문체·인사·마무리·서명·보고 양식 | 기능 단위 완료 | 분리 PostgreSQL에서 저장·재조회·검증·사용자 격리·버전 충돌, S09 취소 |
| 미리보기·초안 계약·프로필·방향·근거 | 부분 완료 | 포트·기본 준비 부족·합성 응답·근거/메일 ID 검증. 실제 AI 없음 |
| 세 가지 수정·사용자 편집 보존 | 기능 단위 완료, 실제 AI 대기 | 현재 본문 전달·실패/늦은 응답/충돌에서 보존·임시 저장 재열기 |
| 학습 동의·끄기·기록 삭제 | 경계 완료 | 동의 없으면 활성화 거부·미사용·사용자별 삭제·제외 표현 차단 |
| S09/S06 전용 화면 | 합성 검사 완료 | 저장·취소·방향·밑줄·미리보기·오류·임시 저장·보고 순서·두 화면 크기 |
| F4 계약·F0 연결 지점 | 준비 완료 | report_profile 읽기 포트·export·전달 문서·미적용 패치 |

## 실행한 검사

| 검사 | 결과 |
| --- | --- |
| 서버 전체 pytest, 실제 테스트 PostgreSQL+pgvector 사용 | **299 통과, 실패·건너뜀 0** (F1/F2/F3·기존 기능 포함, F2 관련 50개) |
| 서버 ruff check / format --check | 통과, 106개 Python 파일 형식 확인 |
| Desktop Vitest | **39 통과** (F2 화면 20개와 기존 첫 실행·F3 검사 포함) |
| Desktop typecheck / lint | 통과 |
| 기존 Electron·renderer 프로덕션 빌드 | 통과. 실제 Electron 앱 실행 검사는 아님 |
| F2 합성 검사 앱 별도 프로덕션 빌드 | 통과 |
| Chromium Playwright | **7 통과** |
| 적용 전 패치 5개 `git apply --check` | 통과. 실제 적용하지 않음 |
| 기존 추적 파일·스테이징 변경 검사 | `git diff --exit-code HEAD`, `git diff --cached --exit-code` 모두 통과 |

브라우저 검사는 1440×900과 1280×720에서 저장·취소·편집·실패 보존·보내기 비활성을 확인했다.
1440에서는 저장 버튼까지 본문 스크롤 없이 보이고, 1280에서는 본문만 스크롤한다.
별도 검사로 참고 메일 창의 열기/Escape 닫기, 보고 섹션의 끌기/키보드 이동을 확인했다.
현재 앱의 StrictMode에서도 최초 초안을 중복 생성하지 않는지 단위 검사했다.
초기 1280 레이아웃 검사 실패는 수정했으며 위 결과는 수정 후 재검사 결과다.

최초 DB 검사는 이 작업의 `klover-f2-test-pg`, 승인 후 재검사는 별도의 pgvector 컨테이너
`klover-f2-merge-pg`와 고유 임시 스키마만 사용했다. 기존 환경·볼륨·파일을 삭제하지 않는다.
미적용 마이그레이션의 upgrade/downgrade 본문도 이 테스트 스키마에서만 실행했다.
기존 합성 메일 유지·모델 일치를 확인했으며 운영 Alembic 이력을 적용하지 않았다.
기존 인증된 `MailQueryRepository`를 사용한 F2 생성 검사에서 다른 사용자·같은 사용자의
다른 계정·사용 시작 전·보낸 메일 ID는 모두 접근을 거부했다.

## 실행하지 않은 것과 이유

- **실제 AI 생성·수정·미리보기·품질·지연·스트리밍:** 공통 제공자가 없어 입출력 포트와 합성 대역만 검사했다.
  운영 기본값은 503 ai_unavailable이며 가짜 초안을 반환하지 않는다.
- **실제 Gmail 외부 AI 전송·발송:** 요청에서 제외했다. 실제 Gmail 내용·키·토큰을 읽거나 외부 AI로 보내지 않았다.
- **관련 과거 메일 검색·F1 요청사항 분석 연결:** F1/F3 모듈은 있지만 F2에 아직 연결하지 않아 unavailable로 표시한다. 현재 인증된 읽기는 받은편지함만 허용한다.
- **실제 문체 학습:** Klover 발송 기록·수집·학습 작업자가 없어 완료 건수를 만들지 않는다.
- **일반 앱/서버 통합·운영 DB 마이그레이션:** 승인 전 패치 상태다. 공통 등록·라우터·main/preload는 수정하지 않았다.
- **F0 공통 메뉴 이동·S05 연결·Windows/macOS 실기기·F4 실제 보고서 적용:** 현재 분리된 기능 검사 범위를 넘는 연결이 필요하다.
  F2 내부 나가기·취소·자동 임시 저장과 F4용 저장 계약까지만 검사했다.
- **게시·병합 승인:** 사용자는 분리 구현물 게시와 develop 병합을 승인했다. main 병합·공통 연결 패치 적용은 포함하지 않는다.

## 확인 방법

[구현 안내](F2-profile-draft.md)의 명령으로 테스트와 합성 화면을 연다.
[전달 문서](F2-handoff.md)에 F0/F4에 그대로 보낼 문장과 F1 후속 계약을 정리했다.
[적용 전 패치](../../patches/F2/README.md)는 공통 파일 변경을 검토할 때만 사용한다.
스크린샷은 `apps/desktop/artifacts/f2/S09-1440.png`, `S09-1280.png`, `S06-1440.png`,
`S06-1280.png`다. 모두 합성 응답 화면이며 Git에는 포함하지 않는 검사 산출물이다.

## 변경 파일

아래 파일은 모두 새 파일이다. 기존 계정·키·메일·수신 코드, F0/F4 코드, 공통 잠금 파일은 보존했다.

- `apps/server/app/schemas/profile_draft.py`: 입력·출력·검증 계약.
- `apps/server/app/db/f2_models.py`, `db/repositories/profile_draft.py`: 전용 모델·사용자 격리·저장 충돌·문체 삭제·F4 읽기.
- `apps/server/app/services/profile_draft.py`: 문맥·근거·프로필 적용·생성/수정·편집 보존.
- `apps/server/app/api/profile_draft.py`: 기존 인증을 재사용하는 전용 router와 개인 응답 처리.
- `apps/server/app/ai/f2_port.py`, `ai/f2_shared_adapter.py`, `ai/prompts/draft.md`, `ai/prompts/style_extract.md`: F1 공통 계약을 재사용하는 어댑터·업무 포트·프롬프트·학습 경계.
- `apps/server/app/cli/export_f2_openapi.py`: 공통 앱을 수정하지 않는 검토용 계약 내보내기.
- `apps/server/tests/test_profile_draft.py`, `test_profile_draft_boundaries.py`, `test_f2_pending_migration.py`, `test_f2_shared_adapter.py`: 서버·분리 DB·기존 메일 조회·미적용 마이그레이션·F1 공통 계약 검사.
- `apps/desktop/src/renderer/features/profile-draft/`: S09/S06·컨트롤·밑줄·참고 메일·라우트 export·전용 생성 타입·화면 단위 검사.
- `apps/desktop/tests/f2-harness/`, `tests/f2-browser/`, `f2.vite.config.ts`, `f2.playwright.config.ts`: 운영과 분리한 합성 화면·브라우저 검사.
- `patches/F2/`: DB·서버·공통 테스트·화면·생성 타입·문서의 미적용 연결안과 설명.
- `scripts/f2/prepare_integration_patches.py`: 공통 파일을 쓰지 않는 패치 생성기.
- `docs/dev/F2-profile-draft.md`, `F2-handoff.md`, `F2-verification.md`: 구현 계약·확인 방법·전달·검증 결과.

현재 승인에 따라 분리 구현물을 게시하며 develop에 병합한다. 공통 연결 패치는 그대로 남긴다.
F0 작업과 충돌하는 main/preload·메일함 변경이나 실제 AI/발송은 포함하지 않는다.
