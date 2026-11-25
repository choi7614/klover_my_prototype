"""F3의 F1 벡터 읽기 전용 검색. 새 벡터·인덱스·테이블을 만들지 않는다."""

import json

from sqlalchemy import Float, and_, distinct, func, select, text

from app.db.f1_models import MailAnalysisRecord as Analysis
from app.db.f1_models import MailChunkRecord as Chunk
from app.db.models import Mail
from app.db.repositories.search import _conditions, _exact_conditions, _scope_query
from app.schemas.search import RankedHit, SemanticCoverage
from app.services.search_ports import SemanticBatch


class SQLSemanticRepository:
    def __init__(self, engine, *, candidate_limit=2000, min_similarity=0.5):
        if not 1 <= candidate_limit <= 10000 or not 0 < min_similarity <= 1:
            raise ValueError("벡터 검색 상한·관련도 기준을 확인하세요")
        self.engine = engine
        self.candidate_limit, self.min_similarity = candidate_limit, min_similarity

    def search(self, *, scope, parsed, vector, identity, dimensions, limit):
        # 두 검색은 같은 메일 원본·계정·시작일·명시 조건을 사용한다.
        eligible = (
            _scope_query(scope)
            .where(*_conditions(parsed.filters), *_exact_conditions(parsed))
            .with_only_columns(Mail.mail_id)
            .subquery()
        )
        compatible = (
            select(Chunk.mail_id, Chunk.embedding, Chunk.chunk_id, Chunk.received_at, Chunk.text)
            .join(eligible, eligible.c.mail_id == Chunk.mail_id)
            .join(Mail, Mail.mail_id == Chunk.mail_id)
            .join(
                Analysis,
                and_(
                    Analysis.mail_id == Chunk.mail_id,
                    Analysis.user_id == Chunk.user_id,
                    Analysis.account_id == Chunk.account_id,
                ),
            )
            .where(
                Mail.analysis_status == "done",
                Analysis.llm_mode == identity.mode,
                Analysis.embedding_mode == identity.mode,
                Analysis.embedding_provider == identity.provider,
                Analysis.embedding_model == identity.model,
                Analysis.embedding_dimensions == dimensions,
                Chunk.user_id == scope.user_id,
                Chunk.account_id == scope.account_id,
                Chunk.embedding_provider == identity.provider,
                Chunk.embedding_model == identity.model,
                Chunk.embedding_mode == identity.mode,
                Chunk.embedding_dimensions == dimensions,
                func.public.vector_dims(Chunk.embedding) == dimensions,
                func.public.vector_norm(Chunk.embedding) > 0,
            )
        )
        # 가변 차원 열에는 현재 ANN 인덱스가 없다. 범위 내 최신 청크만 상한 안에서 검사하고
        # 누락 가능성을 응답에 알린다. MATERIALIZED로 호환 필터를 거리 연산보다 먼저 적용한다.
        candidates = (
            compatible.order_by(Chunk.received_at.desc(), Chunk.chunk_id)
            .limit(self.candidate_limit + 1)
            .cte("f3_candidates")
            .prefix_with("MATERIALIZED")
        )
        bounded = (
            select(
                candidates.c.mail_id,
                candidates.c.embedding,
                candidates.c.text,
                candidates.c.chunk_id,
            )
            .order_by(candidates.c.received_at.desc(), candidates.c.chunk_id)
            .limit(self.candidate_limit)
            .cte("f3_bounded")
            .prefix_with("MATERIALIZED")
        )
        similarity = 1 - bounded.c.embedding.op("OPERATOR(public.<=>)", return_type=Float)(
            text("CAST(:query_vector AS public.vector)")
        )
        best = select(
            bounded.c.mail_id,
            similarity.label("score"),
            bounded.c.text,
            func.row_number()
            .over(partition_by=bounded.c.mail_id, order_by=(similarity.desc(), bounded.c.chunk_id))
            .label("rank"),
        ).subquery()
        query = (
            select(best.c.mail_id, best.c.score, best.c.text)
            .where(best.c.rank == 1, best.c.score >= self.min_similarity)
            .order_by(best.c.score.desc(), best.c.mail_id)
            .limit(limit)
        )
        with self.engine.connect() as connection, connection.begin():
            connection.execute(text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY"))
            # 취소 후 동기 DB 작업이 계속 남지 않도록 DB에서도 대기 시간을 제한한다.
            connection.execute(text("SET LOCAL statement_timeout = '2000ms'"))
            eligible_count = connection.scalar(select(func.count()).select_from(eligible))
            compatible_count = connection.scalar(
                select(func.count(distinct(compatible.subquery().c.mail_id)))
            )
            scanned = connection.scalar(select(func.count()).select_from(candidates))
            rows = connection.execute(
                query, {"query_vector": json.dumps(vector, allow_nan=False)}
            ).all()
        return SemanticBatch(
            hits=tuple(
                RankedHit(
                    mail_id=row.mail_id, score=min(1, max(0, row.score)), excerpt=row.text[:1200]
                )
                for row in rows
            ),
            coverage=SemanticCoverage(
                eligible_mails=eligible_count,
                compatible_mails=compatible_count,
                scanned_chunks=min(scanned, self.candidate_limit),
                limited=scanned > self.candidate_limit,
            ),
        )
