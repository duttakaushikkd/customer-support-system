from __future__ import annotations

import json
import logging
import math
from typing import Any

from openai import OpenAI

from app.config import settings

logger = logging.getLogger(__name__)

_client: OpenAI | None = None


def _client_or_none() -> OpenAI | None:
    global _client
    if settings.mock_llm or not settings.openai_api_key or settings.openai_api_key.startswith("sk-replace"):
        return None
    if _client is None:
        _client = OpenAI(api_key=settings.openai_api_key, base_url=settings.openai_base_url)
    return _client


def complete_json(prompt: str, *, flagship: bool = False, fallback: dict[str, Any] | None = None) -> dict[str, Any]:
    client = _client_or_none()
    if client is None:
        return fallback or {}
    model = settings.model_flagship if flagship else settings.model_mini
    try:
        resp = client.chat.completions.create(
            model=model,
            temperature=0.2,
            response_format={"type": "json_object"},
            messages=[
                {
                    "role": "system",
                    "content": "You are a customer-support agent. Reply with a single JSON object only.",
                },
                {"role": "user", "content": prompt},
            ],
        )
        content = resp.choices[0].message.content or "{}"
        return json.loads(content)
    except Exception:
        logger.exception("LLM JSON completion failed; using fallback")
        return fallback or {}


def embed(texts: list[str]) -> list[list[float]]:
    client = _client_or_none()
    if client is None:
        return [_hash_embed(t) for t in texts]
    try:
        resp = client.embeddings.create(model=settings.model_embedding, input=texts)
        return [item.embedding for item in resp.data]
    except Exception:
        logger.exception("Embedding API failed; using hash embeddings")
        return [_hash_embed(t) for t in texts]


def _hash_embed(text: str, dim: int = 64) -> list[float]:
    vec = [0.0] * dim
    tokens = text.lower().split()
    for tok in tokens:
        h = hash(tok)
        vec[h % dim] += 1.0
        vec[(h // dim) % dim] += 0.5
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / norm for v in vec]
