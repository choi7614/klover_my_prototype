# F2 개인정보·학습 데이터 — 검증과 인수인계

2026-11-25 · Codex · `feat/F2-privacy-data` · 기준 develop `7668d94aa5f251541d95e17c9ed238fabc52b418`.
PR #40(F2 안정화)·#41(F1 진단)의 병합 상태와 최신 develop을 확인했다.
이 단위는 미커밋·미Push이고 새 PR은 없다. 경로 `/workspace/klover_my_prototype`.
기존 초기 work 브랜치와 모든 원격 기능 브랜치를 보존했다. 동명 privacy 브랜치가 없어 fetch 후 새로 만들었다.

## 구현

- PrivacyPage: 서버에 저장된 기본 정보·직접 설정 문체·서명·보고 양식을 표시하고 용도를 안내한다.
- 저장된 학습 동의와 실제 작동 상태를 구분한다. 기존 기록이 있어도 수집/학습은 항상 준비 중으로 표시한다.
- 기존 F2Client profile/saveProfile/style/deleteStyle과 인증된 GET/PUT /profile·GET/DELETE /profile/style을 재사용한다.
- 동의 켜기/끄기는 사용자 확인 후 버전 조건으로 저장한다. 끄기는 기록을 보존한다.
- 삭제 확인에는 문체 학습 결과(건수·표현·특징)와 제외 표현 전체, 동의 끄기, 되돌릴 수 없음, 유지되는 데이터를 명시한다.
- 삭제 후 프로필과 학습 상태를 재조회한다. 삭제/저장 또는 후속 조회 실패 시 추가 변경을 막고 재조회를 제공한다.
- 기존 S09 학습 안내와 삭제 확인 문구도 현재 기능에 맞췄다.
- GET /profile/style은 동의가 꺼져도 관리용 기존 기록을 반환한다(형식 변경 없음). 초안 내부 조회는 기본 include_inactive=False로 기존 사용 차단을 유지한다.
- 실제 학습/수집·탈퇴·전체 데이터 삭제·발송·키 관리·외부 전송 동의는 새로 구현하지 않았다.

## 변경 파일

- `apps/desktop/src/renderer/features/profile-draft/privacy-page.tsx`: 기능 화면.
- 같은 폴더 `privacy-page.test.tsx`: 합성 UI 7건.
- 같은 폴더 `profile-page.tsx`: 준비 중 상태와 정확한 삭제 영향 안내.
- 같은 폴더 `index.ts`: 화면 export.
- `apps/server/app/api/profile_draft.py`, `app/db/repositories/profile_draft.py`: 관리 조회와 초안 사용 경계 분리.
- `apps/server/tests/test_profile_draft.py`: 동의 끈 기록 조회·초안 사용 차단, 삭제 후 재조회·다른 사용자/프로필/초안 보존·반복 삭제.
- `patches/F2/privacy-data/`: 미적용 공통 연결 변경안과 적용 순서.
- 이 문서 및 F2 status: 현재 상태/검사/후속 작업.

## 검사

- 분리 컨테이너 `klover-f2-privacy-test`, loopback 55434, DB `klover_f2_privacy_test`; 매 검사 UUID 스키마 생성/정리. 합성 사용자/메일/AI만 사용.
- `KLOVER_TEST_DATABASE_URL=<분리 DB> uv run --locked --directory apps/server pytest tests/test_profile_draft.py -q`: **42 통과, skip 0**.
- 앱 `vitest run`: **199 통과(30개 파일)**. 신규 UI 7건 포함. 확인 전 취소·삭제 성공/실패·후속 재조회 실패·켜기/끄기·프로필 없음·복귀 콜백 검사.
- 앱 `tsc --noEmit`, `eslint . --max-warnings=0`, `electron-vite build`: 통과.
- 변경 Python Ruff check/format, git diff --check, 세 패치 git apply --check: 통과.
- 의존성은 기존 잠금 파일로 설치했다. pnpm 환경 경로 오류 후 /tmp 저장소를 사용했으며 실행은 설치된 node_modules/.bin 도구를 사용했다. 설치 도구가 만든 pnpm-workspace 임시 문구는 제거했다. 공유 잠금 파일/설정 최종 변경 없음.
- 전체 서버 회귀·실제 Mac/Windows Electron·실제 Gmail/AI·사용자 DB는 미실행. 관련 서버 검사를 분리 DB에서 수행했으며 실제 모델을 호출할 필요가 없다. 앱 빌드는 미적용 경로 연결의 검증이 아니다.
- 삭제 코드는 StyleRecord와 프로필 동의/제외 표현만 변경한다. 토큰/Claude 키 저장소 호출은 없고 원문을 화면/로그로 요청하지 않는다. 기존 초안·다른 사용자·기본 프로필 보존은 DB 검사로 확인했다. 실제 자격 증명으로 삭제 실험하지 않았다.

## 통합 채팅에 붙여넣기

F2 개인정보·학습 데이터 구현은 feat/F2-privacy-data, 기준 develop 7668d94입니다. 현재 로컬 미커밋·미Push이며 새 PR은 없습니다. 저장 프로필/학습 동의/기존 기록·제외 표현 조회, 명시적 동의 변경, 삭제 대상·영향 확인, 삭제 후 재조회와 실패 복구를 구현했습니다. 실제 수집/학습은 준비 중으로 안내합니다. 기존 프로필/초안/메일/토큰/키 삭제는 하지 않습니다. 분리 PostgreSQL F2 42/skip 0, 앱 전체 199, Ruff·타입·lint·빌드·패치 검사 통과입니다. 공통 App/설정 진입은 patches/F2/privacy-data/01→02→03을 함께 검사/적용해야 하며 현재 실제 앱 경로 통합은 미완료입니다. main/preload·공유 타입·DB 이력 변경은 필요 없습니다. progress.md에는 이번 상태와 검사 건수를 통합 채팅에서 반영해 주세요. 커밋·Push·PR은 결과 보고 후 묶음 승인 대기이고 develop/main 병합은 이번 요청에서 금지입니다.

## 맥북 확인 절차 (통합 후, 합성 계정·분리 DB 사용)

1. 기존 작업을 보존하고 승인된 통합 결과를 받은 뒤 setup.md에 따라 분리 DB·서버·앱을 실행한다. 실제 사용자 DB에서 삭제 검사를 하지 않는다.
2. 합성 프로필에 이름·서명·보고 양식·제외 표현을 저장한다. 테스트 데이터 없이 학습 완료 상태를 만들지 않는다.
3. 설정 > 내 프로필·문체 > 개인정보·학습 데이터로 이동한다. 저장한 항목과 동의, 실제 학습 '준비 중'을 확인한다.
4. 동의 변경 확인을 취소하면 상태가 유지되는지, 확인하면 재진입 후에도 동의가 유지되는지 확인한다. 끄기는 기존 기록을 보관한다.
5. 삭제 버튼을 누르고 대상·영향·유지되는 항목을 읽는다. 취소 시 보존, 확인 시 기록/제외 표현 없음·동의 끔을 확인한다.
6. 프로필로 돌아갔다 재진입하고 같은 상태인지 확인한다. 기존 합성 프로필·초안·메일을 다시 열어 보존을 확인한다. 키/토큰 원문을 열거나 로그에 출력하지 않는다.
7. 서버 연결을 끊었을 때 오류와 다시 불러오기를 확인한다. 연결 복구 후 서버 상태로 갱신되는지 확인한다. 로그 공유는 고정 오류 코드만 사용한다.
