from __future__ import annotations

from uuid import uuid4

import streamlit as st

from repair_quest.models import QuestAnalysis, RescueAction
from repair_quest.scoring import calculate_points
from repair_quest.seed import PLAYERS, TEAM, seeded_quests


def initialise_state() -> None:
    defaults = {
        "quests": seeded_quests(),
        "current_player": PLAYERS[0],
        "team": TEAM,
        "analysis": None,
        "analysis_description": "",
        "analysis_image_bytes": None,
        "analysis_image_mime": None,
        "flash": None,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def create_quest(
    analysis: QuestAnalysis,
    description: str,
    image_bytes: bytes | None = None,
    image_mime_type: str | None = None,
) -> dict:
    quest = {
        "id": str(uuid4())[:8],
        "title": analysis.quest_title,
        "item_name": analysis.item_name,
        "description": description,
        "owner": st.session_state.current_player,
        "team": st.session_state.team,
        "action": analysis.recommended_action.value,
        "difficulty": analysis.difficulty.value,
        "estimated_waste_kg": analysis.estimated_waste_kg,
        "next_step": analysis.suggested_next_step,
        "status": "Open",
        "helper": None,
        "teammates": [],
        "offers": [],
        "suggestions": [],
        "outcome": None,
        "points_awarded": 0,
        "image_bytes": image_bytes,
        "image_mime_type": image_mime_type,
        "after_image_bytes": None,
        "after_image_mime_type": None,
    }
    st.session_state.quests.insert(0, quest)
    return quest


def update_quest(quest_id: str, **changes: object) -> None:
    for quest in st.session_state.quests:
        if quest["id"] == quest_id:
            quest.update(changes)
            return
    raise KeyError(f"Quest not found: {quest_id}")


def complete_quest(
    quest_id: str,
    outcome: RescueAction,
    after_image_bytes: bytes | None = None,
    after_image_mime_type: str | None = None,
) -> int:
    quest = next(quest for quest in st.session_state.quests if quest["id"] == quest_id)
    helpers = {name for name in quest.get("teammates", []) if name != quest["owner"]}
    if quest.get("helper") and quest["helper"] != quest["owner"]:
        helpers.add(quest["helper"])
    points = calculate_points(outcome, len(helpers))
    update_quest(
        quest_id,
        status="Completed",
        outcome=outcome.value,
        points_awarded=points,
        after_image_bytes=after_image_bytes,
        after_image_mime_type=after_image_mime_type,
    )
    return points
