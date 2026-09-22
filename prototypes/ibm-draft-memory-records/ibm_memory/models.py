"""Model string resolution, including OpenRouter (same convention as the Packer harness)."""

from __future__ import annotations

import os
from typing import Any

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"


def resolve_model(spec: Any, **kwargs: Any) -> Any:
    if not isinstance(spec, str):
        return spec
    if spec.startswith("openrouter:"):
        from langchain_openai import ChatOpenAI

        api_key = os.environ.get("OPENROUTER_API_KEY")
        if not api_key:
            raise RuntimeError("OPENROUTER_API_KEY is not set (export it or put it in .env)")
        return ChatOpenAI(
            model=spec.removeprefix("openrouter:"),
            base_url=OPENROUTER_BASE_URL,
            api_key=api_key,
            **kwargs,
        )
    from langchain.chat_models import init_chat_model

    return init_chat_model(spec, **kwargs)
