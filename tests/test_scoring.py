from datetime import date

from repair_quest.scoring import (
    COMPLETER_XP,
    CONTRIBUTOR_XP,
    SOLVER_XP,
    award_for,
    impact_summary,
    streak_length,
    streak_multiplier,
)


def test_streak_multiplier_bands() -> None:
    assert streak_multiplier(1) == 1.0
    assert streak_multiplier(3) == 1.1
    assert streak_multiplier(7) == 1.25
    assert streak_multiplier(14) == 1.5


def test_streak_resets_after_a_missed_day() -> None:
    today = date(2026, 8, 29)
    assert streak_length(["2026-08-29", "2026-08-28"], today) == 2
    assert streak_length(["2026-08-29", "2026-08-27"], today) == 1


def test_xp_awards_use_the_active_streak() -> None:
    days = ["2026-08-29", "2026-08-28", "2026-08-27"]
    assert award_for(CONTRIBUTOR_XP, days, date(2026, 8, 29)) == (22, 3, 1.1)
    assert award_for(COMPLETER_XP, days, date(2026, 8, 29)) == (55, 3, 1.1)
    assert award_for(SOLVER_XP, days, date(2026, 8, 29)) == (110, 3, 1.1)


def test_impact_summary_counts_completed_rescues_only() -> None:
    rescues = [
        {"status": "Completed", "estimated_waste_kg": 1.25, "outcome": "Repair"},
        {
            "status": "Completed",
            "estimated_waste_kg": 2,
            "outcome": "Recycle / dispose responsibly",
        },
        {"status": "Open", "estimated_waste_kg": 50, "outcome": None},
    ]
    assert impact_summary(rescues) == {
        "items_rescued": 1,
        "waste_avoided_kg": 1.2,
        "purchases_avoided": 1,
        "responsible_exits": 1,
    }
