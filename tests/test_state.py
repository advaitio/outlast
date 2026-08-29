import streamlit as st

from repair_quest.models import RescueAction
from repair_quest.seed import seeded_player_stats, seeded_rescues
from repair_quest.state import complete_rescue


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
