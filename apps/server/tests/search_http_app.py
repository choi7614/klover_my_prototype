"""별도 테스트 DB/합성 포트로만 띄우는 F3 HTTP 프로세스. 운영 진입점이 아니다."""

import os

from fastapi import FastAPI
from search_support import TODAY, SyntheticAnswerer, SyntheticParser
from sqlalchemy import create_engine

from app.api.errors import register_error_handlers
from app.api.mail_read import MailAPIContext
from app.api.search import register_search_api
from app.db.repositories.search import SQLSearchRepository
from app.db.repositories.search_recent import SQLRecentSearchRepository
from app.schemas.mail_api import LocalSession
from app.schemas.search import SearchScope
from app.services.search import SearchService


def create_test_app():
    # 명시적 테스트 설정 없이는 시작하지 않는다. .env/실제 Google 설정은 읽지 않는다.
    engine = create_engine(os.environ["F3_SYNTHETIC_DATABASE_URL"], hide_parameters=True)
    scope = SearchScope.model_validate_json(os.environ["F3_SYNTHETIC_SCOPE"])

    class Identity:
        def session(self):
            return LocalSession(**scope.model_dump(), email="synthetic@example.invalid")

    application = FastAPI()
    register_error_handlers(application)
    register_search_api(application)
    application.state.mail_api = MailAPIContext(os.environ["F3_SYNTHETIC_TOKEN"], Identity())
    application.state.search_service = SearchService(
        SQLSearchRepository(engine),
        SQLRecentSearchRepository(engine),
        parser=SyntheticParser(),
        answerer=SyntheticAnswerer(),
        clock=lambda: TODAY,
    )
    return application
