from __future__ import annotations

from datetime import date
from uuid import uuid4

import streamlit as st

from outlast import db
from outlast.models import (
    ContributionType,
    DisposalGuidance,
    RescueAction,
    RescueAnalysis,
    RescueOutcome,
    RescueStatus,
)
from outlast.scoring import COMPLETER_XP, CONTRIBUTOR_XP, SOLVER_XP, award_for
from outlast.seed import PLAYERS, seeded_player_stats, seeded_rescues


def initialise_state() -> None:
    remote = None
    persistence_error = None
    if db.available():
        try:
            remote = db.load_data()
        except db.PersistenceError as error:
            persistence_error = str(error)
    defaults = {
        "rescues": remote[0] if remote is not None else seeded_rescues(),
        "player_stats": remote[1] if remote is not None else seeded_player_stats(),
        "current_player": PLAYERS[0],
        "analysis": None,
        "analysis_description": "",
        "analysis_image_bytes": None,
        "analysis_image_mime": None,
        "flash": None,
        "persistence_error": persistence_error,
    }
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)
    if st.session_state.analysis:
        try:
            RescueAnalysis.model_validate(st.session_state.analysis)
        except ValueError:
            st.session_state.analysis = None
            st.session_state.analysis_description = ""
            st.session_state.analysis_image_bytes = None
            st.session_state.analysis_image_mime = None


def refresh_from_database() -> None:
    """Replace this session's view with the latest durable Supabase data."""
    remote = db.load_data()
    if remote is None:
        return
    st.session_state.rescues, st.session_state.player_stats = remote
    st.session_state.persistence_error = None


def repairs_helped_by(rescues: list[dict], player: str) -> list[dict]:
    """Return completed repairs where the player was recognised as a solver."""
    return [
        rescue
        for rescue in rescues
        if rescue.get("status") == RescueStatus.COMPLETED.value
        and player in rescue.get("solvers", [])
    ]


def create_rescue(
    analysis: RescueAnalysis,
    description: str,
    image_bytes: bytes | None = None,
    image_mime_type: str | None = None,
) -> dict:
    rescue = {
        "id": str(uuid4()),
        "title": analysis.rescue_title,
        "item_name": analysis.item_name,
        "description": description,
        "owner": st.session_state.current_player,
        "action": RescueAction.REPAIR.value,
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
        "disposal_guidance": None,
        "image_bytes": image_bytes,
        "image_mime_type": image_mime_type,
        "after_image_bytes": None,
        "after_image_mime_type": None,
    }
    db.create_rescue(rescue)
    st.session_state.rescues.insert(0, rescue)
    return rescue


def update_rescue(rescue_id: str, **changes: object) -> None:
    for rescue in st.session_state.rescues:
        if rescue["id"] == rescue_id:
            rescue.update(changes)
            return
    raise KeyError(f"Item not found: {rescue_id}")


def delete_rescue(rescue_id: str) -> None:
    """Delete an unresolved item posted by the current prototype user."""
    rescue = next(rescue for rescue in st.session_state.rescues if rescue["id"] == rescue_id)
    if rescue["owner"] != st.session_state.current_player:
        raise PermissionError("Only the original poster can delete this item.")
    if rescue["status"] != RescueStatus.OPEN.value:
        raise ValueError("Resolved items cannot be deleted.")
    db.delete_rescue(rescue_id, rescue["owner"])
    st.session_state.rescues = [
        item for item in st.session_state.rescues if item["id"] != rescue_id
    ]


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
        raise ValueError("Resolved items cannot receive suggestions.")
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


def save_disposal_guidance(rescue_id: str, guidance: DisposalGuidance) -> None:
    rescue = next(rescue for rescue in st.session_state.rescues if rescue["id"] == rescue_id)
    if rescue["owner"] != st.session_state.current_player:
        raise PermissionError("Only the original poster can view this disposal guidance.")
    if rescue["status"] == RescueStatus.COMPLETED.value:
        raise ValueError("This item has already been resolved.")
    payload = guidance.model_dump(mode="json")
    update_rescue(rescue_id, disposal_guidance=payload)


def complete_rescue(
    rescue_id: str,
    outcome: RescueOutcome,
    solvers: list[str],
    after_image_bytes: bytes | None = None,
    after_image_mime_type: str | None = None,
) -> tuple[tuple[int, int, float], dict[str, tuple[int, int, float]]]:
    rescue = next(rescue for rescue in st.session_state.rescues if rescue["id"] == rescue_id)
    if rescue["status"] == RescueStatus.COMPLETED.value:
        raise ValueError("This item is already resolved.")
    if rescue["owner"] != st.session_state.current_player:
        raise PermissionError("Only the original poster can resolve this item.")
    selected_solvers = list(dict.fromkeys(solvers))
    if outcome == RescueOutcome.RECYCLE_DISPOSE and selected_solvers:
        raise ValueError("A responsible disposal outcome cannot award solver XP.")
    if outcome != RescueOutcome.RECYCLE_DISPOSE and not selected_solvers:
        raise ValueError("Select at least one solver.")
    if any(player not in PLAYERS for player in selected_solvers):
        raise ValueError("Select solvers from the listed community members.")
    if outcome == RescueOutcome.RECYCLE_DISPOSE and not rescue.get("disposal_guidance"):
        raise ValueError("Get disposal guidance in My items before resolving this outcome.")
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
        "after_image_bytes": after_image_bytes,
        "after_image_mime_type": after_image_mime_type,
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
