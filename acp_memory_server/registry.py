from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any

import httpx

from acp_memory_server.config import cache_dir

log = logging.getLogger(__name__)

REGISTRY_CACHE_FILE = "registry.json"
REGISTRY_META_FILE = "registry.meta.json"


def _cache_paths() -> tuple[Path, Path]:
    return cache_dir() / REGISTRY_CACHE_FILE, cache_dir() / REGISTRY_META_FILE


async def fetch_registry(url: str, ttl_seconds: int) -> dict[str, Any]:
    """Fetch the ACP registry. Use the cached copy if it's fresh, fall back to it on network errors."""
    cache_file, meta_file = _cache_paths()

    if cache_file.exists() and meta_file.exists():
        try:
            meta = json.loads(meta_file.read_text())
            if int(time.time()) - int(meta.get("fetched_at", 0)) < ttl_seconds:
                return json.loads(cache_file.read_text())
        except (json.JSONDecodeError, OSError) as e:
            log.warning("Stale registry cache unreadable, refetching: %s", e)

    try:
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            payload = resp.json()
    except (httpx.HTTPError, json.JSONDecodeError) as e:
        log.warning("Registry fetch failed (%s); falling back to cache if available", e)
        if cache_file.exists():
            return json.loads(cache_file.read_text())
        raise

    cache_dir().mkdir(parents=True, exist_ok=True)
    cache_file.write_text(json.dumps(payload, indent=2))
    meta_file.write_text(json.dumps({"fetched_at": int(time.time()), "url": url}))
    return payload


def parse_registry(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Return the agents array. The schema may be `{ "agents": [...] }` directly,
    or a richer wrapper. We're permissive."""
    if isinstance(payload, dict) and "agents" in payload:
        return list(payload["agents"])
    if isinstance(payload, list):
        return list(payload)
    return []
