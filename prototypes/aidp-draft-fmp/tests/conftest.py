from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from fmp.client import FederatedMemory, ServerConfig
from fmp.server import create_app
from fmp.store import SQLiteStore


def make_server(name: str, **kw):
    store = SQLiteStore(":memory:")
    app = create_app(store, name=name, description=f"{name} memory", **kw)
    return store, app, TestClient(app)


@pytest.fixture
def personal():
    return make_server("personal")


@pytest.fixture
def work():
    return make_server("work", disabled={"delete"})


@pytest.fixture
def federation(personal, work):
    _, _, pc = personal
    _, _, wc = work
    return FederatedMemory(
        [
            ServerConfig(name="personal", url="http://personal", http=pc),
            ServerConfig(name="work", url="http://work", http=wc, send_transcripts=False),
        ]
    )
