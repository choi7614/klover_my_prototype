"""명시적 pending 실행. 제공자를 주입하며 일반 앱·Gmail 수신에 자동 등록하지 않는다."""

from app.ai.interfaces import ProvidersNotConfigured, TextEmbedding, TextGeneration
from app.db.repositories.mail_analysis import AnalysisRepository
from app.pipeline.analyze import AnalysisFailed, analyze
from app.pipeline.embed import EmbeddingFailed, embed_mail
from app.schemas.mail_analysis import AnalysisModel, AnalysisOutcome

DEFAULT_TIMEOUT = 20.0


def call_timeout(provider) -> float:
    """제공자가 알려 준 시간 제한(재시도 포함)을 쓴다. 로컬 모델은 20초보다 느릴 수 있다."""
    value = getattr(provider, "call_timeout", None)
    if isinstance(value, int | float) and not isinstance(value, bool) and 0 < value <= 7200:
        return float(value)
    return DEFAULT_TIMEOUT


class BatchResult(AnalysisModel):
    outcomes: tuple[AnalysisOutcome, ...]

    @property
    def done(self):
        return sum(outcome.status == "done" for outcome in self.outcomes)

    @property
    def failed(self):
        return sum(outcome.status == "failed" for outcome in self.outcomes)


async def process_pending(
    repository: AnalysisRepository,
    llm: TextGeneration | None,
    embeddings: TextEmbedding | None,
    *,
    limit: int = 20,
    allow_gmail: bool = False,
    mail_id: str | None = None,
    reanalyze: bool = False,
) -> BatchResult:
    if type(limit) is not int or not 1 <= limit <= 100:
        raise ValueError("실행 개수는 1~100이어야 합니다")
    if llm is None or embeddings is None:
        raise ProvidersNotConfigured("AI·임베딩 제공자를 먼저 연결해야 합니다")
    if any(provider.identity.mode == "test" for provider in (llm, embeddings)) and not (
        repository.allow_test_providers
    ):
        raise ProvidersNotConfigured("기본 실행에서는 테스트 제공자를 사용하지 않습니다")
    outcomes = []
    for _ in range(limit):
        with repository.claim(
            allow_gmail=allow_gmail, mail_id=mail_id, reanalyze=reanalyze
        ) as work:
            if work is None:
                break
            attempts = 0
            try:
                result, attempts = await analyze(
                    work.mail, llm, work.examples(), timeout=call_timeout(llm)
                )
                chunks = await embed_mail(
                    work.mail.body_text,
                    result.summary,
                    embeddings,
                    timeout=call_timeout(embeddings),
                )
            except AnalysisFailed as error:
                work.save_failure(error.code, error.attempts)
                outcome = AnalysisOutcome(
                    mail_id=work.mail.mail_id,
                    status="failed",
                    failure_code=error.code,
                    attempts=error.attempts,
                )
            except EmbeddingFailed:
                work.save_failure("embedding_error", attempts)
                outcome = AnalysisOutcome(
                    mail_id=work.mail.mail_id,
                    status="failed",
                    failure_code="embedding_error",
                    attempts=attempts,
                )
            else:
                work.save_success(
                    result,
                    chunks,
                    llm=llm.identity,
                    embedding=embeddings.identity,
                    dimensions=embeddings.dimensions,
                    attempts=attempts,
                )
                outcome = AnalysisOutcome(
                    mail_id=work.mail.mail_id, status="done", attempts=attempts
                )
        # 여기까지 트랜잭션이 확정된 뒤에만 완료를 반환한다. 이벤트 전송은 별도 연결 사항이다.
        outcomes.append(outcome)
        if mail_id is not None:
            break
    return BatchResult(outcomes=tuple(outcomes))
