"""Model resolution, including OpenRouter (OpenAI-compatible) as a first-class provider.

LangChain's `init_chat_model` understands strings like "anthropic:claude-sonnet-4-6" and
"openai:gpt-5". OpenRouter is not a built-in provider, so "openrouter:<model>" is handled
here by pointing `ChatOpenAI` at OpenRouter's OpenAI-compatible endpoint.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
DEFAULT_MODEL = "openrouter:nvidia/nemotron-3-nano-30b-a3b"


def load_env() -> None:
    """Load environment from the prototype's own ./.env, then the shared prototypes/.env.

    Values already set in the process win; a local .env wins over the shared one.
    """
    from dotenv import load_dotenv

    here = Path(__file__).resolve()
    load_dotenv(Path.cwd() / ".env")
    load_dotenv(here.parents[1] / ".env")  # this prototype's folder
    load_dotenv(here.parents[2] / ".env")  # prototypes/.env (shared)


def resolve_model(spec: Any, **kwargs: Any) -> Any:
    """Turn a model string into a chat model; pass model instances through untouched."""
    if not isinstance(spec, str):
        return spec
    if spec.startswith("openrouter:"):
        load_env()
        from langchain_openai import ChatOpenAI

        api_key = os.environ.get("OPENROUTER_API_KEY")
        if not api_key:
            raise RuntimeError(
                "OPENROUTER_API_KEY is not set. Export it, or put it in prototypes/.env "
                f"(see prototypes/.env.example), to use {spec!r}."
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
