from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

from outlast.models import (
    Contribution,
    ContributionType,
    Difficulty,
    Rescue,
    RescueAction,
    RescueOutcome,
    RescueStatus,
)

PLAYERS = ["Alex", "Maya", "Noah", "Priya", "Sam"]
DEMO_ASSET_DIR = Path(__file__).parents[1] / "static" / "demo"


def _activity_date(days_ago: int = 0) -> str:
    return (date.today() - timedelta(days=days_ago)).isoformat()


def _contribution(player: str, message: str, days_ago: int = 0) -> Contribution:
    return Contribution(
        player=player,
        message=message,
        contribution_type=ContributionType.SUGGESTION,
        created_at=_activity_date(days_ago),
        xp_awarded=20,
    )


def seeded_rescues() -> list[dict]:
    rescues = [
        Rescue(
            id="fan-001",
            title="Where Did This Desk Fan’s Spin Go?",
            item_name="Desk fan",
            description="It stopped spinning yesterday and may have a loose cable.",
            owner="Maya",
            action=RescueAction.REPAIR,
            difficulty=Difficulty.EASY,
            estimated_waste_kg=1.5,
            next_step="Check the plug, cable, and power switch before opening it.",
            contributions=[
                _contribution(
                    "Noah",
                    "Try a different socket, then check whether the blades turn freely.",
                )
            ],
        ),
        Rescue(
            id="chair-002",
            title="One Loose Leg, One Solid Chair",
            item_name="Wooden chair",
            description="The frame is sound, but one leg keeps loosening.",
            owner="Priya",
            action=RescueAction.REPAIR,
            difficulty=Difficulty.MEDIUM,
            estimated_waste_kg=6.2,
            next_step="Inspect the loose joint and check whether wood glue and a clamp will help.",
            status=RescueStatus.COMPLETED,
            outcome=RescueOutcome.REPAIR,
            completed_by="Priya",
            completion_xp_award=55,
            completion_streak_multiplier=1.1,
            contributions=[
                _contribution(
                    "Alex",
                    "Remove the leg, clean the old glue from the joint, then clamp it square.",
                    4,
                ),
                _contribution(
                    "Sam",
                    "Check that the corner block is still secure before applying fresh glue.",
                    3,
                ),
            ],
            solvers=["Alex", "Sam"],
            solver_xp_awards={"Alex": 100, "Sam": 100},
            solver_streak_multipliers={"Alex": 1.0, "Sam": 1.0},
        ),
        Rescue(
            id="lamp-003",
            title="Why Does This Study Lamp Flicker?",
            item_name="LED study lamp",
            description="The light flickers after a few minutes even though the plug is secure.",
            owner="Noah",
            action=RescueAction.REPAIR,
            difficulty=Difficulty.EASY,
            estimated_waste_kg=0.8,
            next_step="Unplug it and inspect the cable and power adapter for visible damage.",
            contributions=[
                _contribution(
                    "Priya",
                    "Try the adapter in another compatible lamp before replacing the whole unit.",
                    1,
                ),
                _contribution(
                    "Maya",
                    "The frayed cable near the base should be assessed before the lamp "
                    "is used again.",
                ),
            ],
        ),
        Rescue(
            id="keyboard-004",
            title="Keys Worth Bringing Back",
            item_name="Mechanical keyboard",
            description="Several keys no longer register, but the rest of the keyboard works.",
            owner="Sam",
            action=RescueAction.REPAIR,
            difficulty=Difficulty.MEDIUM,
            estimated_waste_kg=0.9,
            next_step="Unplug it and test whether the affected keycaps or switches are sticking.",
            contributions=[
                _contribution(
                    "Maya",
                    "A switch puller makes it easier to test one affected switch at a time.",
                    2,
                )
            ],
            status=RescueStatus.COMPLETED,
            outcome=RescueOutcome.REPAIR,
            completed_by="Sam",
            completion_xp_award=50,
            completion_streak_multiplier=1.0,
            solvers=["Maya"],
            solver_xp_awards={"Maya": 110},
            solver_streak_multipliers={"Maya": 1.1},
        ),
        Rescue(
            id="kettle-005",
            title="The Case of the Silent Kettle",
            item_name="Electric kettle",
            description="No indicator light; base looks intact.",
            owner="Alex",
            action=RescueAction.REPAIR,
            difficulty=Difficulty.MEDIUM,
            estimated_waste_kg=1.1,
            next_step="Try another outlet and inspect the detachable base for debris.",
            contributions=[
                _contribution(
                    "Sam",
                    "Clean and dry the contacts on the detachable base before testing "
                    "it once more.",
                    1,
                )
            ],
        ),
        Rescue(
            id="shelf-006",
            title="Can This Bookshelf Stand Steady?",
            item_name="Small bookshelf",
            description="One shelf bracket is loose and the unit wobbles when books are added.",
            owner="Maya",
            action=RescueAction.REPAIR,
            difficulty=Difficulty.EASY,
            estimated_waste_kg=12.0,
            next_step="Empty it and inspect the loose bracket and fasteners before tightening.",
            contributions=[
                _contribution(
                    "Alex",
                    "Replace the stripped fastener and secure the back panel before "
                    "loading it again.",
                    6,
                ),
                _contribution(
                    "Noah",
                    "Check that the unit is square before tightening the new bracket.",
                    5,
                ),
            ],
            status=RescueStatus.COMPLETED,
            outcome=RescueOutcome.REPAIR,
            completed_by="Maya",
            completion_xp_award=55,
            completion_streak_multiplier=1.1,
            solvers=["Alex"],
            solver_xp_awards={"Alex": 110},
            solver_streak_multipliers={"Alex": 1.1},
        ),
        Rescue(
            id="headphones-007",
            title="Can Both Sides Play Again?",
            item_name="Wired headphones",
            description="Audio cuts out on the left when the cable bends.",
            owner="Priya",
            action=RescueAction.REPAIR,
            difficulty=Difficulty.HARD,
            estimated_waste_kg=0.3,
            next_step="Test the cable position to locate the likely break.",
            contributions=[
                _contribution(
                    "Maya",
                    "If the cut is near the plug, a repair shop may be able to replace "
                    "just the cable.",
                    8,
                )
            ],
            status=RescueStatus.COMPLETED,
            outcome=RescueOutcome.RECYCLE_DISPOSE,
            completed_by="Priya",
            completion_xp_award=50,
            completion_streak_multiplier=1.0,
            disposal_location="ALBA e-waste collection point",
        ),
        Rescue(
            id="toaster-008",
            title="A Safer Look at This Toaster",
            item_name="Two-slice toaster",
            description="Heating element is broken; casing and lever are usable.",
            owner="Noah",
            action=RescueAction.REPAIR,
            difficulty=Difficulty.HARD,
            estimated_waste_kg=1.4,
            next_step=(
                "Keep it unplugged and check its manual or a repair service before replacement."
            ),
            contributions=[
                _contribution(
                    "Priya",
                    "Do not open the toaster; the heating element should be assessed "
                    "by a repair shop.",
                    2,
                )
            ],
        ),
    ]
    image_paths = {
        "fan-001": DEMO_ASSET_DIR / "desk-fan.jpg",
        "chair-002": DEMO_ASSET_DIR / "wooden-chair.jpg",
        "lamp-003": DEMO_ASSET_DIR / "study-lamp.jpg",
        "keyboard-004": DEMO_ASSET_DIR / "mechanical-keyboard.jpg",
    }
    result = [rescue.model_dump(mode="json") for rescue in rescues]
    for rescue in result:
        if image_path := image_paths.get(rescue["id"]):
            rescue["image_url"] = str(image_path)
    return result


def seeded_player_stats() -> dict[str, dict[str, int | list[str]]]:
    today = date.today()
    return {
        "Maya": {
            "xp": 390,
            "activity_dates": [(today - timedelta(days=day)).isoformat() for day in range(3)],
        },
        "Noah": {
            "xp": 330,
            "activity_dates": [(today - timedelta(days=day)).isoformat() for day in range(7)],
        },
        "Priya": {
            "xp": 310,
            "activity_dates": [(today - timedelta(days=day)).isoformat() for day in range(2)],
        },
        "Sam": {
            "xp": 280,
            "activity_dates": [(today - timedelta(days=day)).isoformat() for day in range(2)],
        },
        "Alex": {
            "xp": 420,
            "activity_dates": [(today - timedelta(days=day)).isoformat() for day in range(4)],
        },
    }
