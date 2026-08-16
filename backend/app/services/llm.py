from __future__ import annotations

import json
import logging
from typing import Any

from openai import OpenAI

from app.config import settings

logger = logging.getLogger(__name__)

_client: OpenAI | None = None


def get_client() -> OpenAI:
    global _client
    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY is required")
    if _client is None:
        _client = OpenAI(api_key=settings.openai_api_key, base_url=settings.openai_base_url)
    return _client


def complete_json(prompt: str, *, flagship: bool = False, fallback: dict[str, Any] | None = None) -> dict[str, Any]:
    del fallback  # retained on call sites; responses always come from the LLM
    model = settings.model_flagship if flagship else settings.model_mini
    resp = get_client().chat.completions.create(
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
    try:
        data = json.loads(content)
    except json.JSONDecodeError as exc:
        logger.exception("LLM returned non-JSON")
        raise RuntimeError("LLM returned non-JSON") from exc
    if not isinstance(data, dict):
        raise RuntimeError("LLM JSON was not an object")
    return data


def embed(texts: list[str]) -> list[list[float]]:
    resp = get_client().embeddings.create(model=settings.model_embedding, input=texts)
    return [item.embedding for item in resp.data]
