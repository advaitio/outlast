from types import SimpleNamespace

from repair_quest import state
from repair_quest.models import Difficulty, QuestAnalysis, RescueAction


def test_photo_survives_create_and_completion_flow(monkeypatch) -> None:
    session = SimpleNamespace(current_player="Alex", team="COM3", quests=[])
    monkeypatch.setattr(state.st, "session_state", session)
    analysis = QuestAnalysis(
        item_name="Desk fan",
        recommended_action=RescueAction.REPAIR,
        reason="It may have a simple fault.",
        difficulty=Difficulty.EASY,
        quest_title="Rescue this desk fan",
        suggested_next_step="Check the plug.",
        estimated_waste_kg=1.5,
    )

    quest = state.create_quest(
        analysis,
        "The fan stopped spinning.",
        image_bytes=b"before-image",
        image_mime_type="image/jpeg",
    )

    assert quest["image_bytes"] == b"before-image"
    assert quest["image_mime_type"] == "image/jpeg"
    assert quest["status"] == "Open"

    points = state.complete_quest(
        quest["id"],
        RescueAction.REPAIR,
        after_image_bytes=b"after-image",
        after_image_mime_type="image/png",
    )

    assert points == 100
    assert quest["status"] == "Completed"
    assert quest["outcome"] == "Repair"
    assert quest["after_image_bytes"] == b"after-image"
    assert quest["after_image_mime_type"] == "image/png"
