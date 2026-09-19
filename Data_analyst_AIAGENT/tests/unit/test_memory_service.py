"""Unit tests for long-term session/turn memory (SQLite CRUD)."""

from services import memory_service


def test_save_turn_creates_session_and_persists_turns():
    memory_service.save_turn(
        session_id="s1", trace_id="t1", role="user", content="Show revenue by region",
        kpi_context="Revenue", dataset_fingerprint="fp1",
    )
    memory_service.save_turn(
        session_id="s1", trace_id="t1", role="assistant", content="North leads with 500.",
        kpi_context="Revenue", dataset_fingerprint="fp1",
    )

    assert memory_service.session_exists("s1")
    turns = memory_service.fetch_relevant_turns("s1")
    assert len(turns) == 2
    assert turns[0]["role"] == "user"
    assert turns[1]["role"] == "assistant"


def test_fetch_relevant_turns_filters_by_dataset_fingerprint():
    memory_service.save_turn(
        session_id="s1", trace_id="t1", role="user", content="q1", dataset_fingerprint="fp1"
    )
    memory_service.save_turn(
        session_id="s1", trace_id="t2", role="user", content="q2", dataset_fingerprint="fp2"
    )

    fp1_turns = memory_service.fetch_relevant_turns("s1", dataset_fingerprint="fp1")
    assert [t["content"] for t in fp1_turns] == ["q1"]


def test_touch_session_updates_last_seen_without_duplicating():
    memory_service.touch_session("s1")
    memory_service.touch_session("s1")
    sessions = [s for s in memory_service.list_sessions() if s["session_id"] == "s1"]
    assert len(sessions) == 1


def test_session_exists_false_for_unknown_session():
    assert memory_service.session_exists("nope") is False
    assert memory_service.fetch_relevant_turns("nope") == []
