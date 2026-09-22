"""Model resolution, including OpenRouter (OpenAI-compatible) as a first-class provider.

LangChain's `init_chat_model` understands strings like "anthropic:claude-sonnet-4-6" and
"openai:gpt-5". OpenRouter is not a built-in provider, so "openrouter:<model>" is handled
here by pointing `ChatOpenAI` at OpenRouter's OpenAI-compatible endpoint.
"""

from __future__ import annotations

import os
from typing import Any

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
DEFAULT_MODEL = "openrouter:moonshotai/kimi-k3"


def resolve_model(spec: Any, **kwargs: Any) -> Any:
    """Turn a model string into a chat model; pass model instances through untouched."""
    if not isinstance(spec, str):
        return spec
    if spec.startswith("openrouter:"):
        from langchain_openai import ChatOpenAI

        api_key = os.environ.get("OPENROUTER_API_KEY")
        if not api_key:
            raise RuntimeError(
                "OPENROUTER_API_KEY is not set. Export it (or put it in a .env file) to use "
                f"{spec!r}."
            )
        return ChatOpenAI(
            model=spec.removeprefix("openrouter:"),
            base_url=OPENROUTER_BASE_URL,
            api_key=api_key,
            default_headers={
                "HTTP-Referer": "https://github.com/The-AI-Disclosures-Project/Open-Memory-Protocol",
                "X-Title": "OMP LangChain harness",
            },
            **kwargs,
        )
    from langchain.chat_models import init_chat_model

    return init_chat_model(spec, **kwargs)
