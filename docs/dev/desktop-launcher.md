# 더블클릭으로 Klover 실행하기

최초 설치·Google 연결·모델 다운로드를 마친 사용자를 위한 실행 도구입니다.
설치는 [setup.md](setup.md) 한 곳을 기준으로 진행하세요. 설치용 exe/dmg는 아직 없습니다.

## 실행·종료

1. Docker Desktop을 켜고 준비 완료를 기다립니다.
2. 저장소 폴더에서 아래 파일을 더블클릭합니다. 파일만 다른 곳으로 옮기지 말고 바로가기를 만드세요.

| OS | 파일 |
| --- | --- |
| macOS | `Klover-Start.command` |
| Windows | `Klover-Start.cmd` |

3. 진행 창을 열어둡니다. DB → Ollama/모델 → 서버/계정 확인 → 앱 순서로 시작합니다.
4. 앱을 종료하면 이번 실행에서 만든 앱·서버·Ollama를 정리합니다. 이미 켜져 있던 Ollama와 DB/Docker는 유지합니다.
5. 중단할 때는 진행 창에서 Control+C를 누릅니다. 창 강제 닫기·프로세스 강제 종료 시 정리는 보장되지 않습니다.

macOS 실행 권한이 사라졌으면 최초 한 번 저장소 폴더에서 `chmod +x Klover-Start.command`를 실행합니다.
OS 보안 설정을 전체 해제하지 말고 파일 출처를 확인하세요. Windows에서는 네이티브 Windows에서 설치한
`.venv`와 `node_modules`를 사용합니다. macOS/WSL 설치 폴더를 복사하지 마세요.

## 자동으로 하는 것과 하지 않는 것

- 기존 설정·키·토큰을 사용합니다. 사용자에게 키 내용을 보여주거나 로그 파일에 기록하지 않습니다.
- Docker 엔진이 준비되면 기존 Compose 설정으로 DB를 켭니다. 이미 실행 중인 서비스는 재사용합니다.
- Ollama가 꺼져 있고 명령을 찾을 수 있으면 실행합니다. 생성·임베딩 모델의 설치 여부를 확인합니다.
- 명령을 직접 입력할 필요 없이 서버와 Electron 개발 앱을 시작합니다. 진행 창은 표시됩니다.
- 프로그램 설치·모델 다운로드·Google 최초 동의·DB 마이그레이션은 자동 수행하지 않습니다.
- 기존 서버가 8000 포트를 사용하면 안내 후 중단합니다. 다른 프로그램을 임의 종료하지 않습니다.
- DB·메일·키 초기화, Claude 연결 검사·유료 AI 요청은 실행하지 않습니다.

앱의 기존 자동 분석 동작은 그대로입니다. 앱 시작/새로고침에 따른 분석은 설정된 로컬 AI를 사용합니다.

## 준비 상태만 확인하기

서비스를 시작하지 않고 기존 DB 버전과 Ollama 모델 목록을 확인합니다. Docker·DB·Ollama가 이미 켜져 있어야 합니다.

macOS 터미널:

```bash
./Klover-Start.command --check
```

Windows PowerShell:

```powershell
.\Klover-Start.cmd --check
```

이 검사는 실제 Gmail 수신·AI 생성·Calendar 등록 성공을 뜻하지 않습니다.
OS 잠금 파일 `.local-run/launcher.lock`만 만들 수 있습니다. 비밀 설정 폴더를 새로 만들지는 않습니다.

## 문제가 생기면

| 안내 | 확인할 것 |
| --- | --- |
| 최초 설치/도구/Electron 없음 | 해당 OS에서 setup의 의존성과 Electron 다운로드 완료 |
| Docker 준비 안 됨 | Docker Desktop을 켜고 엔진 준비 완료까지 기다림 |
| DB 연결/버전 확인 필요 | 백업 후 setup의 업데이트·명시적 마이그레이션 |
| Ollama/모델 확인 필요 | Ollama 실행, `.env`의 모델 이름과 `ollama list` 비교. 기존 모델 차원은 보존 |
| 8000 포트 사용 중 | 기존 Klover 서버를 해당 창에서 종료. 다른 프로그램이면 원인 확인 |
| 실행 도구 이미 열림 | 먼저 연 진행 창/앱 확인. 잠금은 프로세스 종료 시 OS가 해제 |

오류를 전달할 때는 단계·OS·일반 오류 문구만 보내세요. `.env`·키·토큰·메일·전체 로그는 보내지 마세요.

## 확인 수준

Linux/macOS/Windows CI에서 합성 프로세스·가짜 HTTP·해당 OS 시작 파일 검사를 통과했습니다.
실제 Finder/탐색기→Docker/Ollama→Electron→Google의
새 설치 전체 흐름은 각 OS에서 따로 확인해야 합니다.

기존 맥 사용자에게 앱 사용 확인 보고가 있으나, 이 더블클릭 도구의 실기 성공 보고는 아직 없습니다.
추가 검사·한계는 [이번 검증 기록](colleague-setup-verification.md)을 참고하세요.
