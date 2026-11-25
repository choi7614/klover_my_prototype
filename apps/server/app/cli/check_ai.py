"""AI 제공자 설정·연결 확인. 메일 내용·키를 쓰거나 출력하지 않는다.

    python -m app.cli.check_ai          # 설정만 확인(네트워크 호출 없음)
    python -m app.cli.check_ai --ping   # 짧은 합성 문장으로 실제 호출 1회씩 확인

--ping은 Claude 설정이면 아주 적은 토큰 비용이 생긴다. 메일 내용은 보내지 않는다.
"""

import argparse
import asyncio
import json

from app.ai.config import environment_values
from app.ai.interfaces import (
    EmbeddingRequest,
    GenerationRequest,
    ProviderCallError,
    ProvidersNotConfigured,
)
from app.ai.runtime import is_external, load_embedding, load_generation
from app.pipeline.embed import validate_vectors

PING_SCHEMA = {
    "type": "object",
    "properties": {"ok": {"type": "boolean"}},
    "required": ["ok"],
    "additionalProperties": False,
}


async def _ping(generation, embedding) -> dict:
    result = {}
    try:
        raw = await asyncio.wait_for(
            generation.generate(
                GenerationRequest(
                    purpose="analysis",
                    system_prompt='연결 확인용 요청입니다. {"ok": true}만 JSON으로 답하세요.',
                    user_prompt="연결 확인",
                    response_schema=PING_SCHEMA,
                )
            ),
            generation.call_timeout,
        )
        result["generation"] = "ok" if json.loads(raw) == {"ok": True} else "invalid_json"
    except ProviderCallError as error:
        result["generation"] = error.code
        result["generation_hint"] = str(error)
    except (ValueError, TypeError):
        result["generation"] = "invalid_json"
        result["generation_hint"] = (
            "모델이 JSON 형식을 지키지 않았어요. OLLAMA_FORMAT 설정을 확인하세요"
        )
    except TimeoutError:
        result["generation"] = "timeout"
    try:
        vectors = await asyncio.wait_for(
            embedding.embed(EmbeddingRequest(texts=("연결 확인",))), embedding.call_timeout
        )
        validate_vectors(vectors, count=1, dimensions=embedding.dimensions)
        result["embedding"] = "ok"
    except ProviderCallError as error:
        result["embedding"] = error.code
        result["embedding_hint"] = str(error)
    except ValueError:
        result["embedding"] = "dimension_mismatch"
        result["embedding_hint"] = "EMBEDDING_DIMENSIONS가 모델 출력 차원과 같은지 확인하세요"
    except TimeoutError:
        result["embedding"] = "timeout"
    return result


def main(argv=None, values=None):
    parser = argparse.ArgumentParser(description="AI 제공자 설정·연결 확인")
    parser.add_argument("--ping", action="store_true", help="합성 문장으로 실제 호출 1회씩 확인")
    args = parser.parse_args(argv)
    values = environment_values() if values is None else values
    try:
        generation = load_generation(values)
        embedding = load_embedding(values)
    except ProvidersNotConfigured as error:
        print(json.dumps({"status": "not_configured", "reason": str(error)}, ensure_ascii=False))
        return 1
    output = {
        "status": "configured",
        "provider": generation.identity.provider,
        "generation_model": generation.identity.model,
        "embedding_model": embedding.identity.model,
        "embedding_dimensions": embedding.dimensions,
        "external_transfer": is_external(generation),
    }
    if args.ping:
        output.update(asyncio.run(_ping(generation, embedding)))
        ok = output.get("generation") == "ok" and output.get("embedding") == "ok"
        output["status"] = "reachable" if ok else "unreachable"
    print(json.dumps(output, ensure_ascii=False))
    return 0 if output["status"] in {"configured", "reachable"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
