# F3 공통 통합 패치 기록

> 보관 기록 (2026-11-24, 현재 develop f498d27): 이 패치/제안은 기존 통합 PR 등에서 적용되었거나 후속 구현으로 대체됐다. **현재 설치·업데이트에 재적용하지 않는다.** 과거 기준·명령은 이력이며 현재 절차는 [setup.md](../../docs/dev/setup.md)를 따른다. 원본 패치 파일은 수정하지 않았다.

이 폴더는 승인 전 검토·검사를 마친 패치의 기록이다. 2026-11-19 사용자 승인 후
`feat/F3-search` 소스에 적용했다. 실제 사용 중인 DB에는 적용하지 않았다.
자세한 동작·검사·F0/F1/F2 연결 요청은 [F3 전달 문서](../../docs/dev/F3-search-handoff.md)에 있다.

| 파일 | 반영한 내용 |
| --- | --- |
| `01-storage.patch` | `search_runs` 추가 마이그레이션, F3 메타데이터와 기존 모델의 공동 검사 |
| `02-server-registration.patch` | F3 API 등록·로컬 실행 앱의 검색 저장소 조립·등록 경로 검사 갱신. AI 포트는 기본 미연결 |
| `03-shared-api-types.patch` | 등록된 실제 API에서 생성한 OpenAPI·TypeScript 공유 타입 |
| `baseline.json` | 시작 커밋과 보존 대상 파일의 해시 |
| `.gitattributes` | 패치 문법의 문맥 공백을 보존하는 이 폴더 한정 규칙 |

현재 부모 이력은 `0002`다. 다른 기능이 공통 DB 이력을 추가했으면 새 revision·부모와 충돌을
다시 확인한다. F1의 공통 AI·임베딩 인터페이스와 F0 화면 연결은 이 패치에 포함하지 않았다.
공통 모델 파일, 기존 인증/메일 API, 키·수신 코드·공통 잠금 파일의 변경은 필요하지 않다.

시작 기반은 `0f68ad1`이며 F1 모듈이 들어온 `4fef3fe`를 로컬 통합했다.
`baseline.json`은 적용 직전 기준이다. 기존 F0·모델·인증/수신·잠금 파일을 보존했고,
공통 앱 등록·새 마이그레이션·생성 타입과 관련 검사만 승인 범위로 수정했다.

다음은 적용 전 복사본에서 사용한 검사 명령이다. 이미 반영된 현재 소스에 재적용하지 않는다.

```bash
git apply --check integration/F3-search/01-storage.patch integration/F3-search/02-server-registration.patch integration/F3-search/03-shared-api-types.patch
```

최근 검색 DB 변경은 독립 테스트 복사본·임시 스키마에서만 검사했다. 현재 운영 DB는 변경하지
않았다. 마이그레이션의 되돌리기 검사는 합성 테스트 DB에서만 실행했다.

패치 생성기는 `scripts/f3/prepare_integration.py`다. 생성 전에 별도 서버와 Node 개발 의존성을
설치해야 한다. 생성 과정도 공통 파일을 수정하지 않는다. 이미 적용된 소스에서는 기록을
덮어쓰지 않고 중단한다. 승인 전 검사 파일은 `apps/server/tests/f3_proposal_checks.py`다.
통합 후에는 기본 서버 검사와 공유 생성 타입 검사를 실행한다.
