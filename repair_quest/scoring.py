from repair_quest.models import RescueAction

OUTCOME_POINTS = {
    RescueAction.REPAIR: 100,
    RescueAction.REHOME: 80,
    RescueAction.SALVAGE: 60,
}
HELP_BONUS = 30


def calculate_points(outcome: RescueAction, helper_count: int = 0) -> int:
    """Return outcome points plus one collaboration bonus per helper."""
    return OUTCOME_POINTS[outcome] + max(0, helper_count) * HELP_BONUS


def impact_summary(quests: list[dict]) -> dict[str, float | int]:
    completed = [quest for quest in quests if quest.get("status") == "Completed"]
    return {
        "items_rescued": len(completed),
        "waste_avoided_kg": round(
            sum(float(quest.get("estimated_waste_kg", 0)) for quest in completed), 1
        ),
        "purchases_avoided": sum(
            1
            for quest in completed
            if quest.get("outcome")
            in {RescueAction.REPAIR, RescueAction.REHOME, "Repair", "Rehome"}
        ),
        "points": sum(int(quest.get("points_awarded", 0)) for quest in completed),
    }
