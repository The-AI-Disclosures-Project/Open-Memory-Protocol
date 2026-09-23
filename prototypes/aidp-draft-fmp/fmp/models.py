"""Model string resolution, including OpenRouter (same convention as the Packer harness)."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"


def load_env() -> None:
    """Load environment from ./.env, the prototype's .env, prototypes/.env, then the repo root.

    Values already set in the process win; a more local .env wins over a more shared one.
    """
    from dotenv import load_dotenv

    here = Path(__file__).resolve()
    load_dotenv(Path.cwd() / ".env")
    load_dotenv(here.parents[1] / ".env")  # this prototype's folder
    load_dotenv(here.parents[2] / ".env")  # prototypes/.env (shared)
    load_dotenv(here.parents[3] / ".env")  # repo root .env, if present


def resolve_model(spec: Any, **kwargs: Any) -> Any:
    if not isinstance(spec, str):
        return spec
    if spec.startswith("openrouter:"):
        load_env()
        from langchain_openai import ChatOpenAI

        api_key = os.environ.get("OPENROUTER_API_KEY")
        if not api_key:
            raise RuntimeError(
                "OPENROUTER_API_KEY is not set (export it, or put it in prototypes/.env; see prototypes/.env.example)"
            )
        return ChatOpenAI(
            model=spec.removeprefix("openrouter:"),
            base_url=OPENROUTER_BASE_URL,
            api_key=api_key,
            **kwargs,
        )
    from langchain.chat_models import init_chat_model

    return init_chat_model(spec, **kwargs)
