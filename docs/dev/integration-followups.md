# 통합 개발 채팅 전달 사항

## 2026-11-24 구현 갱신

자동 미리보기·Electron 기대값·로컬 전용·로컬 재시도·과거 메일의 코드는 `integrate/local-ai-mail-history`에서 구현·자동 검사 완료, 커밋·Push·PR 생성 승인 대기다.
아래는 개발 전 요청 기록이며 현재 사용 절차는 [통합 실행 안내](local-ai-history-run.md)를 따른다. 실제 외부 연결·OS 전체 실행은 별도 확인이다.


## 남은 확인

- 분리 DB 포함 서버 590개·앱 185개·합성 Chromium 4개 통과. [검증 기록](verification-local-ai-history.md).
- 실제 Gmail 기간 조회·Ollama 처리 속도·Claude 과금/품질과 macOS/Windows 전체 흐름은 미검증.
- 네이티브 Electron은 실행 파일 다운로드 실패로 실행하지 못했다. sandbox·인증·화면 격리 검사는 삭제하지 않았다.
- 승인 후 PR 생성, develop 병합 별도 승인, 맥북 업데이트/실기 확인 순서. main 병합은 별도다.

<details>
<summary>PR #38 당시 개발 요청 — 이미 작업 브랜치에서 처리한 항목 포함</summary>

> 2026-11-24 · 기준 `develop f498d27`(PR #37). 이 문서는 코드 수정 요청이며 이번 문서 작업에서 구현하지 않았다.

## 1. 현재 동작에서 수정이 필요한 부분

| 우선순위 | 문제·근거 | 영향 | 권장 수정 순서·확인 |
| --- | --- | --- | --- |
| 1 | 프로필 자동 미리보기. `apps/desktop/src/renderer/features/profile-draft/profile-page.tsx:38~48`은 진입/변경 1초 후 preview 호출. `apps/server/app/ai/f2_shared_adapter.py`는 preview도 purpose=draft로 전송하며 `app/ai/selection.py:154~178`은 저장 기본값을 사용 | 답장 기본값 Claude·전송 동의가 있으면 생성 버튼 없이 합성 예시/프로필이 외부 전송·과금될 수 있음. '필요한 요청만 Claude'라는 사용 의도에 비해 자동 경로가 남음 | 미리보기는 로컬 고정 또는 명시적 생성/전송 선택으로 변경. 서버에서도 통제하고 무동의/Claude 기본값/동시 요청 검사를 추가. 수정 전 문서는 로컬 기본값 유지로 안내 |
| 2 | Electron smoke 검사 기대값이 옛 통로에 고정. `apps/desktop/scripts/smoke-electron.mjs:58`, `smoke-mail-read.mjs:52~53`은 platform/mail와 3개 조회만 예상. 현재 `src/preload/index.ts:75`는 ai/f2/search/weeklyReport/suggestions/analysis와 mail.sync도 공개. mail smoke 버튼 이름도 현재 새로고침과 다름 | 단위·브라우저 검사가 통과해도 실제 Electron 통합 검사를 최신 흐름의 증거로 사용할 수 없음. 정적 대조로 발견했으며 이번에 이 assertion까지 실제 실행한 것은 아님 | 현재 승인된 제한 IPC 목록·새로고침 의미에 맞는 합성 fixture/기대값·키 누출/인증/오류 검사를 함께 갱신. 보안 검사를 단순 삭제하지 않음. 그래픽 환경에서 다시 실행 |
| 3 | 신규 사용자 Windows/macOS 전체 설치·실제 Google/로컬 모델/앱 연결 미검증 | GitHub 안내만으로 모든 OS의 실행 성공을 보장할 수 없음. 특히 토큰 POSIX 권한과 Windows ACL 차이 확인 필요 | 문서의 신규 설치를 깨끗한 각 OS에서 수행. 합성 메일로 프로필·초안·검색·첫 주 보고·재시작/업데이트까지 확인하고 성공 범위 기록 |

## 2. 실행 환경에서 발견한 제약 (앱 기능 버그로 단정하지 않음)

- Linux Cloud에서 `pnpm install --frozen-lockfile`·빌드는 성공했지만 Electron 실행 파일 확인은
  기본 다운로드의 프록시 fetch 실패 후, 상속 프록시 사용 설정으로 다운로드한 다음 **SUID sandbox helper 설정 오류(SIGTRAP)**로 중단됐다.
- 이 환경에는 DISPLAY·xvfb-run이 없다. 정상 Electron 창·실제 앱 흐름은 미검증이다.
- 코드·패키지·OS sandbox 권한을 바꾸거나 sandbox를 끄는 우회는 하지 않았다.
  사용자 OS의 지원되는 Electron 설치/보안 환경에서 먼저 재현하고, 환경 설정 문제와 앱 문제를 나누어 처리한다.
- Corepack/pnpm의 기본 캐시 폴더 접근 오류는 작업용 /tmp 캐시 위치로 분리해 해결했다. 일반 사용자에게 이 임시 경로를 설치 필수조건으로 안내하지 않는다.

## 3. 확정된 개발 예정 — 현재는 없음

### 강제 로컬 전용 모드

앱 선택 UI뿐 아니라 서버의 요청 선택·저장 기본값·Claude 연결 검사·프로필 자동 미리보기까지 막아야 한다.
현재 `external_consent=false`와 로컬 기본값은 이 모드 전체가 아니다. 기존 Claude 키·계정·자료를 지우지 않고
정책을 적용하고, 클라이언트에서 직접 Claude 요청을 보내도 서버가 차단하는 검사를 우선한다.

### Claude 실패 시 로컬 1회 자동 재시도

F2/F3/F4의 필요한 요청에 한해 실패 종류·동일 요청 범위·검색의 두 단계/동시 요청·취소·편집 보존·결과 출처를 설계한다.
로컬로 한 번 시도하고 두 제공자 실패를 구분한다. 무한 전환·중복 저장·의도하지 않은 추가 외부 호출을 막는다.
현재 형식 보정이나 SDK의 동일 제공자 재시도와 다르다. 먼저 위 자동 미리보기/로컬 전용 경계를 정리한다.

### 기간 선택 과거 메일 가져오기

보류가 아니라 [확정 개발 예정](../product/features/planned-mail-history-import.md)이다.
현재 기본 수신은 시작 이후 INBOX로 보존한다. UI·API만 추가해서는 안 되고
`app/db/repositories/gmail_sync.py`, 메일 저장·조회, `mail_analysis.py`의 보고 입력,
`search.py`의 `Mail.received_at >= sync_started_at` 제한을 함께 설계해야 한다.
기존 계정·키·메일·커서 보존 → 범위·중복/재개 계약 → 진행/중단/재시도 → 로컬 분석 → 검색/보고 연결 순서를 권장한다.
가져오기만으로 Claude 호출하지 않는 통합 검사도 필요하다. 아직 엔드포인트·마이그레이션을 예약하지 않았다.

## 4. 그 밖의 미구현·장기 범위

- 앱 안 Google 연결/온보딩 완료, 작성·발송·보관·삭제·읽음 변경, 주기 수신.
- F3 벡터 의미 검색·미지원 필터, F2 관련 메일·실제 문체 학습, F1 분류 수정 UI·근거 강조.
- 실제 Calendar, OS 알림·트레이·S10, Word 출력·설치 파일 배포.
- 클라우드 이전은 보류. 현재 앱·서버·PostgreSQL을 유지하며 사내망 적용은 장기 목표다.

이 항목들은 문서 오류 수정과 구분한다. 이미 병합된 #18/#16/#23/#28/#30/#34/#37의 패치는
현재 브랜치에 재적용하지 않는다. 이번 작업은 문서만 작성했고 개발 착수·병합 승인이 아니다.

</details>
