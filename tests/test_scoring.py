from repair_quest.models import RescueAction
from repair_quest.scoring import HELP_BONUS, calculate_points, impact_summary


def test_outcome_points_and_helper_bonus() -> None:
    assert calculate_points(RescueAction.REPAIR) == 100
    assert calculate_points(RescueAction.REHOME, helper_count=2) == 80 + 2 * HELP_BONUS
    assert calculate_points(RescueAction.SALVAGE, helper_count=-1) == 60


def test_impact_summary_counts_completed_quests_only() -> None:
    quests = [
        {
            "status": "Completed",
            "estimated_waste_kg": 1.25,
            "outcome": "Repair",
            "points_awarded": 130,
        },
        {
            "status": "Completed",
            "estimated_waste_kg": 2,
            "outcome": "Salvage",
            "points_awarded": 60,
        },
        {"status": "Open", "estimated_waste_kg": 50, "points_awarded": 999},
    ]

    assert impact_summary(quests) == {
        "items_rescued": 2,
        "waste_avoided_kg": 3.2,
        "purchases_avoided": 1,
        "points": 190,
    }
