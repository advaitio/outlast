from __future__ import annotations

from datetime import date, timedelta

from outlast.models import Contribution, ContributionType, Difficulty, Rescue, RescueAction

PLAYERS = ["Alex", "Maya", "Noah", "Priya", "Sam"]


def seeded_rescues() -> list[dict]:
    today = date.today().isoformat()
    rescues = [
        Rescue(
            id="fan-001",
            title="Bring this desk fan back to life",
            item_name="Desk fan",
            description="It stopped spinning yesterday and may have a loose cable.",
            owner="Maya",
            action=RescueAction.REPAIR,
            difficulty=Difficulty.EASY,
            estimated_waste_kg=1.5,
            next_step="Check the plug, cable, and power switch before opening it.",
            contributions=[
                Contribution(
                    player="Noah",
                    message="Try a different socket first.",
                    contribution_type=ContributionType.SUGGESTION,
                    created_at=today,
                    xp_awarded=20,
                )
            ],
        ),
        Rescue(
            id="chair-002",
            title="Give a wobbly chair another semester",
            item_name="Wooden chair",
            description="The frame is sound, but one leg keeps loosening.",
            owner="Priya",
            action=RescueAction.REPAIR,
            difficulty=Difficulty.MEDIUM,
            estimated_waste_kg=6.2,
            next_step="Inspect the loose joint and check whether wood glue and a clamp will help.",
        ),
        Rescue(
            id="lamp-003",
            title="Stop this study lamp from flickering",
            item_name="LED study lamp",
            description="The light flickers after a few minutes even though the plug is secure.",
            owner="Noah",
            action=RescueAction.REPAIR,
            difficulty=Difficulty.EASY,
            estimated_waste_kg=0.8,
            next_step="Unplug it and inspect the cable and power adapter for visible damage.",
        ),
        Rescue(
            id="keyboard-004",
            title="Bring these keyboard keys back",
            item_name="Mechanical keyboard",
            description="Several keys no longer register, but the rest of the keyboard works.",
            owner="Sam",
            action=RescueAction.REPAIR,
            difficulty=Difficulty.MEDIUM,
            estimated_waste_kg=0.9,
            next_step="Unplug it and test whether the affected keycaps or switches are sticking.",
            contributions=[
                Contribution(
                    player="Maya",
                    message="A switch puller will make the reusable parts easier to remove.",
                    contribution_type=ContributionType.SUGGESTION,
                    created_at=today,
                    xp_awarded=20,
                )
            ],
        ),
        Rescue(
            id="kettle-005",
            title="Bring the silent kettle back to life",
            item_name="Electric kettle",
            description="No indicator light; base looks intact.",
            owner="Alex",
            action=RescueAction.REPAIR,
            difficulty=Difficulty.MEDIUM,
            estimated_waste_kg=1.1,
            next_step="Try another outlet and inspect the detachable base for debris.",
        ),
        Rescue(
            id="shelf-006",
            title="Stabilise this small bookshelf",
            item_name="Small bookshelf",
            description="One shelf bracket is loose and the unit wobbles when books are added.",
            owner="Maya",
            action=RescueAction.REPAIR,
            difficulty=Difficulty.EASY,
            estimated_waste_kg=12.0,
            next_step="Empty it and inspect the loose bracket and fasteners before tightening.",
        ),
        Rescue(
            id="headphones-007",
            title="Fix the one-sided headphones",
            item_name="Wired headphones",
            description="Audio cuts out on the left when the cable bends.",
            owner="Priya",
            action=RescueAction.REPAIR,
            difficulty=Difficulty.HARD,
            estimated_waste_kg=0.3,
            next_step="Test the cable position to locate the likely break.",
        ),
        Rescue(
            id="toaster-008",
            title="Give this toaster one safe repair attempt",
            item_name="Two-slice toaster",
            description="Heating element is broken; casing and lever are usable.",
            owner="Noah",
            action=RescueAction.REPAIR,
            difficulty=Difficulty.HARD,
            estimated_waste_kg=1.4,
            next_step=(
                "Keep it unplugged and check its manual or a repair service before replacement."
            ),
        ),
    ]
    return [rescue.model_dump(mode="json") for rescue in rescues]


def seeded_player_stats() -> dict[str, dict[str, int | list[str]]]:
    today = date.today()
    return {
        "Maya": {
            "xp": 240,
            "activity_dates": [(today - timedelta(days=day)).isoformat() for day in range(3)],
        },
        "Noah": {
            "xp": 210,
            "activity_dates": [(today - timedelta(days=day)).isoformat() for day in range(7)],
        },
        "Priya": {"xp": 180, "activity_dates": [today.isoformat()]},
        "Sam": {"xp": 130, "activity_dates": []},
        "Alex": {"xp": 120, "activity_dates": []},
    }
