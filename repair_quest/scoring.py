from __future__ import annotations

from datetime import date, timedelta

CONTRIBUTOR_XP = 20
SOLVER_XP = 100


def streak_length(activity_dates: list[str], today: date | None = None) -> int:
    """Return the active consecutive-day streak, including today when active."""
    today = today or date.today()
    active_days = {date.fromisoformat(day) for day in activity_dates}
    length = 0
    day = today
    while day in active_days:
        length += 1
        day -= timedelta(days=1)
    return length


def streak_multiplier(streak: int) -> float:
    if streak >= 14:
        return 1.5
    if streak >= 7:
        return 1.25
    if streak >= 3:
        return 1.1
    return 1.0


def award_for(
    base_xp: int, activity_dates: list[str], today: date | None = None
) -> tuple[int, int, float]:
    """Calculate one XP award after the activity day has been recorded."""
    streak = streak_length(activity_dates, today)
    multiplier = streak_multiplier(streak)
    return round(base_xp * multiplier), streak, multiplier


def impact_summary(rescues: list[dict]) -> dict[str, float | int]:
    completed = [rescue for rescue in rescues if rescue.get("status") == "Completed"]
    return {
        "items_rescued": len(completed),
        "waste_avoided_kg": round(
            sum(float(rescue.get("estimated_waste_kg", 0)) for rescue in completed), 1
        ),
        "purchases_avoided": sum(
            1 for rescue in completed if rescue.get("outcome") in {"Repair", "Rehome"}
        ),
    }
