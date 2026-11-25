"""F3의 로컬 질의 임베딩. F1 공통 제공자·검증을 재사용한다."""

import asyncio

from starlette.concurrency import run_in_threadpool

from app.ai.config import environment_values
from app.ai.interfaces import EmbeddingRequest, ProvidersNotConfigured
from app.ai.runtime import load_embedding
from app.pipeline.embed import validate_vectors


class LocalSemanticSearch:
    def __init__(self, repository, embedding, *, allow_test_provider=False):
        if (
            embedding.identity.mode != "live"
            and not allow_test_provider
            or not allow_test_provider
            and (
                embedding.identity.provider != "ollama"
                or getattr(embedding, "external_transfer", True) is not False
            )
        ):
            raise ProvidersNotConfigured("의미 검색에는 로컬 임베딩만 사용할 수 있습니다")
        self.repository, self.embedding = repository, embedding

    @property
    def ready(self):
        # 실제 저장 범위·모델 일치 여부는 질의마다 확인하고 coverage로 반환한다.
        return True

    async def search(self, *, scope, parsed, limit):
        # 확장어로 메타데이터를 바꾸지 않는다. 원래 주제만 한 번 임베딩한다.
        raw = await asyncio.wait_for(
            self.embedding.embed(EmbeddingRequest(texts=(parsed.topic,), purpose="query")), 10
        )
        (vector,) = validate_vectors(raw, count=1, dimensions=self.embedding.dimensions)
        return await run_in_threadpool(
            self.repository.search,
            scope=scope,
            parsed=parsed,
            vector=vector,
            identity=self.embedding.identity,
            dimensions=self.embedding.dimensions,
            limit=limit,
        )


def build_semantic_search(engine):
    from app.db.repositories.search_semantic import SQLSemanticRepository

    try:
        embedding = load_embedding({**environment_values(), "AI_PROVIDER": "ollama"})
        return LocalSemanticSearch(SQLSemanticRepository(engine), embedding)
    except ProvidersNotConfigured:
        return None
