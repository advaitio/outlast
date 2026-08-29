from __future__ import annotations

from datetime import date
from uuid import uuid4

import streamlit as st

from repair_quest import db
from repair_quest.models import ContributionType, RescueAction, RescueAnalysis, RescueStatus
from repair_quest.scoring import COMPLETER_XP, CONTRIBUTOR_XP, SOLVER_XP, award_for
from repair_quest.seed import PLAYERS, seeded_player_stats, seeded_rescues


def initialise_state() -> None:
    remote = db.load_data()
    defaults = {
        "rescues": remote[0] if remote and remote[0] else seeded_rescues(),
        "player_stats": remote[1] if remote and remote[0] else seeded_player_stats(),
        "current_player": PLAYERS[0],
        "analysis": None,
        "flash": None,
    }
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)


def create_rescue(analysis: RescueAnalysis, description: str) -> dict:
    rescue = {
        "id": str(uuid4()),
        "title": analysis.rescue_title,
        "item_name": analysis.item_name,
        "description": description,
        "owner": st.session_state.current_player,
        "action": analysis.recommended_action.value,
        "difficulty": analysis.difficulty.value,
        "estimated_waste_kg": analysis.estimated_waste_kg,
        "next_step": analysis.suggested_next_step,
        "status": RescueStatus.OPEN.value,
        "contributions": [],
        "outcome": None,
        "completed_by": None,
        "completion_xp_award": 0,
        "completion_streak_multiplier": None,
        "solvers": [],
        "solver_xp_awards": {},
        "solver_streak_multipliers": {},
    }
    db.create_rescue(rescue)
    st.session_state.rescues.insert(0, rescue)
    return rescue


def update_rescue(rescue_id: str, **changes: object) -> None:
    for rescue in st.session_state.rescues:
        if rescue["id"] == rescue_id:
            rescue.update(changes)
            return
    raise KeyError(f"Rescue not found: {rescue_id}")


def _award_preview(player: str, base_xp: int) -> tuple[int, int, float]:
    stats = st.session_state.player_stats[player]
    today = date.today().isoformat()
    activity_dates = [*stats["activity_dates"]]
    if today not in activity_dates:
        activity_dates.append(today)
    awarded, streak, multiplier = award_for(base_xp, activity_dates)
    return awarded, streak, multiplier


def _apply_award(player: str, awarded: int) -> None:
    stats = st.session_state.player_stats[player]
    today = date.today().isoformat()
    if today not in stats["activity_dates"]:
        stats["activity_dates"].append(today)
    stats["xp"] += awarded


def add_suggestion(rescue_id: str, message: str) -> tuple[int, int, float]:
    if not message.strip():
        raise ValueError("A suggestion cannot be empty.")
    rescue = next(rescue for rescue in st.session_state.rescues if rescue["id"] == rescue_id)
    if rescue["status"] == RescueStatus.COMPLETED.value:
        raise ValueError("Completed rescues cannot receive suggestions.")
    player = st.session_state.current_player
    awarded, streak, multiplier = _award_preview(player, CONTRIBUTOR_XP)
    contribution = {
        "player": player,
        "message": message.strip(),
        "contribution_type": ContributionType.SUGGESTION.value,
        "created_at": date.today().isoformat(),
        "xp_awarded": awarded,
    }
    db.add_contribution(rescue_id, player, message.strip(), awarded, multiplier)
    update_rescue(rescue_id, contributions=[*rescue["contributions"], contribution])
    _apply_award(player, awarded)
    return awarded, streak, multiplier


def complete_rescue(
    rescue_id: str, outcome: RescueAction, solvers: list[str]
) -> tuple[tuple[int, int, float], dict[str, tuple[int, int, float]]]:
    rescue = next(rescue for rescue in st.session_state.rescues if rescue["id"] == rescue_id)
    if rescue["status"] == RescueStatus.COMPLETED.value:
        raise ValueError("This rescue is already complete.")
    if rescue["owner"] != st.session_state.current_player:
        raise PermissionError("Only the original poster can complete this rescue.")
    selected_solvers = list(dict.fromkeys(solvers))
    if not selected_solvers:
        raise ValueError("Select at least one solver.")
    if any(player not in PLAYERS for player in selected_solvers):
        raise ValueError("Select solvers from the listed community members.")
    completion_award = _award_preview(rescue["owner"], COMPLETER_XP)
    solver_awards = {player: _award_preview(player, SOLVER_XP) for player in selected_solvers}
    changes = {
        "status": RescueStatus.COMPLETED.value,
        "outcome": outcome.value,
        "completed_by": rescue["owner"],
        "completion_xp_award": completion_award[0],
        "completion_streak_multiplier": completion_award[2],
        "solvers": selected_solvers,
        "solver_xp_awards": {player: award[0] for player, award in solver_awards.items()},
        "solver_streak_multipliers": {player: award[2] for player, award in solver_awards.items()},
    }
    db.complete_rescue({**rescue, **changes})
    _apply_award(rescue["owner"], completion_award[0])
    for player, award in solver_awards.items():
        _apply_award(player, award[0])
    update_rescue(
        rescue_id,
        **changes,
    )
    return completion_award, solver_awards
