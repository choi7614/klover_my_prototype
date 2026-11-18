"""원문은 보존하고 본문 단락·요약의 벡터만 준비한다."""

import asyncio
import math
import struct
from collections.abc import Sequence
from dataclasses import dataclass

from app.ai.interfaces import EmbeddingRequest, TextEmbedding


@dataclass(frozen=True, repr=False)
class EmbeddedChunk:
    kind: str
    seq: int
    text: str
    vector: tuple[float, ...]


class EmbeddingFailed(Exception):
    pass


def body_chunks(body: str, size: int = 1200) -> tuple[str, ...]:
    if size < 1:
        raise ValueError("청크 크기는 양수여야 합니다")
    return tuple(
        paragraph[offset : offset + size]
        for part in body.split("\n\n")
        if (paragraph := part.strip())
        for offset in range(0, len(paragraph), size)
    )


def validate_vectors(vectors: Sequence, *, count: int, dimensions: int):
    if type(dimensions) is not int or not 1 <= dimensions <= 4096 or len(vectors) != count:
        raise ValueError("벡터 개수·차원이 맞지 않습니다")
    checked = []
    for vector in vectors:
        if len(vector) != dimensions or any(
            type(value) not in (float, int) or not math.isfinite(value) for value in vector
        ):
            raise ValueError("벡터의 값·차원이 올바르지 않습니다")
        try:
            rounded = tuple(struct.unpack("!f", struct.pack("!f", value))[0] for value in vector)
        except (OverflowError, struct.error):
            raise ValueError("벡터 값이 저장 가능한 범위를 벗어납니다") from None
        if not any(rounded):
            raise ValueError("0벡터는 검색에 사용할 수 없습니다")
        checked.append(rounded)
    return tuple(checked)


async def embed_mail(body: str, summary: str, provider: TextEmbedding, *, timeout: float = 20):
    chunks = body_chunks(body)
    texts = (*chunks, summary)
    try:
        raw = await asyncio.wait_for(provider.embed(EmbeddingRequest(texts=texts)), timeout)
        vectors = validate_vectors(raw, count=len(texts), dimensions=provider.dimensions)
    except Exception:
        raise EmbeddingFailed("embedding_error") from None
    return tuple(
        EmbeddedChunk(
            "body" if seq < len(chunks) else "summary",
            seq if seq < len(chunks) else 0,
            text,
            vector,
        )
        for seq, (text, vector) in enumerate(zip(texts, vectors, strict=True))
    )
