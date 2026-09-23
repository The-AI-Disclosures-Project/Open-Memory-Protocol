"""Model string resolution, including OpenRouter (same convention as the other prototypes)."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
DEFAULT_MODEL = "openrouter:nvidia/nemotron-3-nano-30b-a3b"


def load_env() -> None:
    """Load ./.env, this prototype's .env, prototypes/.env, then the repo root; process env wins."""
    from dotenv import load_dotenv

    here = Path(__file__).resolve()
    load_dotenv(Path.cwd() / ".env")
    load_dotenv(here.parents[1] / ".env")
    load_dotenv(here.parents[2] / ".env")
    load_dotenv(here.parents[3] / ".env")


def resolve_model(spec: Any, **kwargs: Any) -> Any:
    if not isinstance(spec, str):
        return spec
    if spec.startswith("openrouter:"):
        load_env()
        from langchain_openai import ChatOpenAI

        api_key = os.environ.get("OPENROUTER_API_KEY")
        if not api_key:
            raise RuntimeError(
                "OPENROUTER_API_KEY is not set (put it in prototypes/.env; see .env.example)"
            )
        return ChatOpenAI(
            model=spec.removeprefix("openrouter:"),
            base_url=OPENROUTER_BASE_URL,
            api_key=api_key,
            **kwargs,
        )
    from langchain.chat_models import init_chat_model

    return init_chat_model(spec, **kwargs)
