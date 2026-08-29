import pytest
import streamlit as st

from repair_quest import db
from repair_quest.models import Difficulty, RescueAction, RescueAnalysis
from repair_quest.seed import seeded_player_stats, seeded_rescues
from repair_quest.state import add_suggestion, complete_rescue, create_rescue


def test_completion_awards_xp_to_the_original_poster() -> None:
    st.session_state.clear()
    st.session_state.rescues = seeded_rescues()
    st.session_state.player_stats = seeded_player_stats()
    st.session_state.current_player = "Maya"
    initial_xp = st.session_state.player_stats["Maya"]["xp"]

    completion_award, solver_awards = complete_rescue("fan-001", RescueAction.REPAIR, ["Noah"])

    rescue = next(rescue for rescue in st.session_state.rescues if rescue["id"] == "fan-001")
    assert completion_award[0] == 55
    assert solver_awards["Noah"][0] == 125
    assert st.session_state.player_stats["Maya"]["xp"] == initial_xp + 55
    assert rescue["completed_by"] == "Maya"
    assert rescue["completion_xp_award"] == 55
    assert rescue["solver_streak_multipliers"]["Noah"] == 1.25


def test_failed_persistence_does_not_change_session_state(monkeypatch: pytest.MonkeyPatch) -> None:
    st.session_state.clear()
    st.session_state.rescues = seeded_rescues()
    st.session_state.player_stats = seeded_player_stats()
    st.session_state.current_player = "Maya"
    initial_xp = st.session_state.player_stats["Maya"]["xp"]
    initial_contributions = list(st.session_state.rescues[0]["contributions"])

    def fail_write(*_args: object, **_kwargs: object) -> bool:
        raise db.PersistenceError("Supabase is unavailable.")

    monkeypatch.setattr(db, "add_contribution", fail_write)

    with pytest.raises(db.PersistenceError, match="Supabase is unavailable"):
        add_suggestion("fan-001", "Check the cable.")

    assert st.session_state.player_stats["Maya"]["xp"] == initial_xp
    assert st.session_state.rescues[0]["contributions"] == initial_contributions


def test_photos_survive_create_and_completion_flow(monkeypatch: pytest.MonkeyPatch) -> None:
    st.session_state.clear()
    st.session_state.rescues = []
    st.session_state.player_stats = seeded_player_stats()
    st.session_state.current_player = "Alex"
    monkeypatch.setattr(db, "create_rescue", lambda _rescue: False)
    monkeypatch.setattr(db, "complete_rescue", lambda _rescue: False)
    analysis = RescueAnalysis(
        item_name="Desk fan",
        recommended_action=RescueAction.REPAIR,
        reason="It may have a simple fault.",
        difficulty=Difficulty.EASY,
        rescue_title="Rescue this desk fan",
        suggested_next_step="Check the plug.",
        estimated_waste_kg=1.5,
    )

    rescue = create_rescue(analysis, "Stopped spinning.", b"before", "image/jpeg")
    complete_rescue(rescue["id"], RescueAction.REPAIR, ["Maya"], b"after", "image/png")

    assert rescue["image_bytes"] == b"before"
    assert rescue["status"] == "Completed"
    assert rescue["after_image_bytes"] == b"after"
    assert rescue["after_image_mime_type"] == "image/png"
