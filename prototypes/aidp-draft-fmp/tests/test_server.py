"""Server + client tests against the draft's endpoint list."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from fmp.client import FMPClient
from fmp.schema import (
    ALL_ENDPOINTS,
    FileUpload,
    InferenceUpload,
    MemoryType,
    Message,
    SearchRequest,
    TranscriptUpload,
)
from fmp.server import create_app
from fmp.store import ACPIndexStore


def test_info_lists_every_endpoint(personal):
    _, _, c = personal
    info = c.get("/fmp/info").json()
    assert info["fmp_version"] == "0.1" and info["name"] == "personal"
    assert set(info["capabilities"]) == set(ALL_ENDPOINTS)
    assert all(info["capabilities"].values())
    assert info["memory_types"] == ["file", "transcript", "inference"]


def test_disabled_endpoint_is_501_and_reported(work):
    _, _, c = work
    assert c.get("/fmp/info").json()["capabilities"]["delete"] is False
    r = c.post("/fmp/delete", json={"type": "inference", "id": "x"})
    assert r.status_code == 501


def test_three_memory_types_round_trip(personal):
    _, _, http = personal
    client = FMPClient("http://personal", name="personal", http=http)
    fids = client.upload_files(
        [FileUpload(name="notes.txt", content="the deploy runbook uses blue-green")]
    )
    tid = client.upload_transcript(
        TranscriptUpload(
            source="test",
            messages=[
                Message(role="user", content="how do we deploy?"),
                Message(role="assistant", content="blue-green, see the runbook"),
            ],
        )
    )
    iids = client.upload_inferences(
        [InferenceUpload(content="User deploys with blue-green", based_on=[f"transcript:{tid}#1"])]
    )
    assert len(fids) == 1 and len(iids) == 1

    hits = client.search(SearchRequest(query="blue-green"))
    assert {h.type for h in hits} == {MemoryType.file, MemoryType.transcript, MemoryType.inference}
    assert all(h.server == "personal" for h in hits)
    assert any(h.ref == f"transcript:{tid}#1" for h in hits)

    only = client.search(SearchRequest(query="blue-green", types=[MemoryType.inference]))
    assert [h.type for h in only] == [MemoryType.inference]

    ts, nxt, total = client.read_transcripts(include_messages=True)
    assert (
        total == 1
        and nxt is None
        and ts[0].message_count == 2
        and ts[0].messages[1].role == "assistant"
    )
    infs, _, _ = client.read_inferences()
    assert infs[0].content.startswith("User deploys")

    client.delete(MemoryType.inference, iids[0])
    assert client.read_inferences()[2] == 0
    assert not client.search(SearchRequest(query="blue-green", types=[MemoryType.inference]))


def test_partial_transcript_uploads_append(personal):
    _, _, http = personal
    client = FMPClient("http://personal", http=http)
    tid = client.upload_transcript(
        TranscriptUpload(
            id="s1", source="t", partial=True, messages=[Message(role="user", content="one")]
        )
    )
    client.upload_transcript(
        TranscriptUpload(
            id="s1", source="t", partial=True, messages=[Message(role="assistant", content="two")]
        )
    )
    ts, _, _ = client.read_transcripts(include_messages=True)
    assert tid == "s1" and [m.content for m in ts[0].messages] == ["one", "two"]
    # A non-partial upload of the same id replaces.
    client.upload_transcript(
        TranscriptUpload(id="s1", source="t", messages=[Message(role="user", content="fresh")])
    )
    ts, _, _ = client.read_transcripts(include_messages=True)
    assert [m.content for m in ts[0].messages] == ["fresh"]


def test_pagination(personal):
    _, _, http = personal
    client = FMPClient("http://personal", http=http)
    for i in range(5):
        client.upload_inferences([InferenceUpload(content=f"fact {i}")])
    page1, cursor, total = client.read_inferences(limit=2)
    assert total == 5 and len(page1) == 2 and cursor == "2"
    page2, cursor, _ = client.read_inferences(cursor=cursor, limit=2)
    page3, cursor, _ = client.read_inferences(cursor=cursor, limit=2)
    assert len(page2) == 2 and len(page3) == 1 and cursor is None


def test_search_punctuation_does_not_break_fts(personal):
    _, _, http = personal
    client = FMPClient("http://personal", http=http)
    client.upload_inferences([InferenceUpload(content='uses C++ and "quotes"')])
    assert client.search(SearchRequest(query='C++ "quotes" (x)'))


def test_acp_index_backend_is_read_only(tmp_path: Path):
    import re
    import sqlite3

    # The real schema from the ACP prototype, read without importing its package.
    src = (Path(__file__).resolve().parents[2] / "acp_memory_server" / "index.py").read_text()
    SCHEMA = re.search(r'SCHEMA = """(.*?)"""', src, re.DOTALL).group(1)

    db = tmp_path / "acp.sqlite"
    conn = sqlite3.connect(db)
    conn.executescript(SCHEMA)
    conn.execute(
        "INSERT INTO sessions VALUES ('claude-code','sess1','/repo','fix bug',1700000000,1700000100,2,'{}')"
    )
    conn.execute(
        "INSERT INTO turns(agent_id,session_id,turn_index,role,content_text,ts) VALUES ('claude-code','sess1',0,'user','please fix the flaky pagination test',1700000000)"
    )
    conn.execute(
        "INSERT INTO turns(agent_id,session_id,turn_index,role,content_text,ts) VALUES ('claude-code','sess1',1,'assistant','fixed the pagination cursor',1700000100)"
    )
    conn.commit()
    conn.close()

    app = create_app(ACPIndexStore(db), name="history")
    c = TestClient(app)
    caps = c.get("/fmp/info").json()["capabilities"]
    assert caps["search"] and caps["read_transcripts"]
    assert not caps["upload_transcript"] and not caps["delete"] and not caps["upload_inferences"]
    assert c.post("/fmp/upload/inferences", json=[]).status_code == 501

    hits = c.post("/fmp/search", json={"query": "pagination"}).json()["hits"]
    assert (
        len(hits) == 2
        and hits[0]["id"] == "claude-code/sess1"
        and hits[0]["ref"].startswith("transcript:claude-code/sess1#")
    )
    page = c.get("/fmp/read_transcripts", params={"include_messages": True}).json()
    assert page["total"] == 1 and page["items"][0]["messages"][1]["role"] == "assistant"
    assert page["items"][0]["metadata"]["cwd"] == "/repo"
