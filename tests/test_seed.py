from __future__ import annotations

from pathlib import Path

from outlast.models import RescueOutcome, RescueStatus
from outlast.seed import PLAYERS, seeded_rescues


def test_demo_seed_has_activity_for_every_player() -> None:
    rescues = seeded_rescues()

    assert len(rescues) >= 8
    assert {rescue["owner"] for rescue in rescues} == set(PLAYERS)
    active_participants = {
        contribution["player"]
        for rescue in rescues
        for contribution in rescue["contributions"]
    } | {solver for rescue in rescues for solver in rescue["solvers"]}
    assert active_participants == set(PLAYERS)


def test_demo_seed_includes_open_and_resolved_stories() -> None:
    rescues = seeded_rescues()

    assert any(rescue["status"] == RescueStatus.OPEN.value for rescue in rescues)
    assert any(
        rescue["status"] == RescueStatus.COMPLETED.value
        and rescue["outcome"] == RescueOutcome.REPAIR.value
        for rescue in rescues
    )
    assert any(
        rescue["status"] == RescueStatus.COMPLETED.value
        and rescue["outcome"] == RescueOutcome.RECYCLE_DISPOSE.value
        for rescue in rescues
    )


def test_demo_listing_photos_are_local_project_assets() -> None:
    photo_paths = [
        Path(rescue["image_url"])
        for rescue in seeded_rescues()
        if rescue.get("image_url")
    ]

    assert len(photo_paths) >= 4
    assert all(path.is_file() for path in photo_paths)
