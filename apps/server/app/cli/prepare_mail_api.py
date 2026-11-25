from app.google_config import ROOT
from app.mail_api_config import MailAPIConfigurationError, prepare_api_token


def main():
    try:
        created = prepare_api_token(ROOT / ".local-secrets")
    except (OSError, MailAPIConfigurationError):
        raise SystemExit("기존 Google 설정 폴더와 API 토큰 파일을 확인하세요.") from None
    print("로컬 메일 API 설정을 생성했습니다." if created else "기존 메일 API 설정을 보존했습니다.")


if __name__ == "__main__":
    main()
