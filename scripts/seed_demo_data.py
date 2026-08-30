from __future__ import annotations

import argparse
import os
import tomllib
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from uuid import NAMESPACE_URL, uuid5

from outlast.seed import seeded_player_stats, seeded_rescues
from supabase import create_client

PROJECT_ROOT = Path(__file__).parents[1]
SECRETS_PATH = PROJECT_ROOT / ".streamlit" / "secrets.toml"


def _demo_uuid(label: str) -> str:
    return str(uuid5(NAMESPACE_URL, f"outlast-demo:{label}"))


def _credentials() -> tuple[str, str]:
    secrets: dict[str, Any] = {}
    if SECRETS_PATH.is_file():
        with SECRETS_PATH.open("rb") as secrets_file:
            secrets = tomllib.load(secrets_file)
    url = os.getenv("SUPABASE_URL") or str(secrets.get("SUPABASE_URL", ""))
    key = os.getenv("SUPABASE_KEY") or str(secrets.get("SUPABASE_KEY", ""))
    if not url or not key:
        raise RuntimeError("Set SUPABASE_URL and SUPABASE_KEY before applying demo data.")
    return url, key


def _player_rows() -> list[dict[str, Any]]:
    stats = seeded_player_stats()
    return [
        {"display_name": name, "xp": values["xp"]}
        for name, values in stats.items()
    ]


def _rescue_row(
    rescue: dict[str, Any],
    player_ids: dict[str, str],
    position: int,
    image_path: str | None,
) -> dict[str, Any]:
    created_at = datetime.now(UTC) - timedelta(days=position + 1)
    remote_outcome = rescue["outcome"]
    if remote_outcome == "Recycle / dispose responsibly":
        remote_outcome = None
    completed = rescue["status"] == "Completed" and remote_outcome is not None
    return {
        "id": _demo_uuid(rescue["id"]),
        "owner_id": player_ids[rescue["owner"]],
        "title": rescue["title"],
        "item_name": rescue["item_name"],
        "description": rescue["description"],
        "recommended_action": rescue["action"],
        "difficulty": rescue["difficulty"],
        "estimated_waste_kg": rescue["estimated_waste_kg"],
        "suggested_next_step": rescue["next_step"],
        "image_path": image_path,
        "status": "Completed" if completed else "Open",
        "outcome": remote_outcome,
        "completed_by_id": player_ids[rescue["completed_by"]]
        if completed
        else None,
        "completion_xp_awarded": rescue["completion_xp_award"] if completed else 0,
        "completion_streak_multiplier": (
            rescue["completion_streak_multiplier"] if completed else None
        ),
        "disposal_location": rescue["disposal_location"] if completed else None,
        "disposal_evidence_xp_awarded": (
            rescue["disposal_evidence_xp_award"] if completed else 0
        ),
        "created_at": created_at.isoformat(),
        "completed_at": (created_at + timedelta(days=1)).isoformat() if completed else None,
    }


def seed_remote_demo() -> None:
    url, key = _credentials()
    client = create_client(url, key)
    client.table("players").upsert(_player_rows(), on_conflict="display_name").execute()
    players = client.table("players").select("id, display_name").execute().data
    player_ids = {row["display_name"]: row["id"] for row in players}

    missing_players = set(seeded_player_stats()) - set(player_ids)
    if missing_players:
        raise RuntimeError(f"Could not prepare demo players: {sorted(missing_players)}")

    rescues = seeded_rescues()
    rescue_rows = []
    for position, rescue in enumerate(rescues):
        remote_id = _demo_uuid(rescue["id"])
        remote_image_path = None
        if local_image_path := rescue.get("image_url"):
            remote_image_path = f"{remote_id}/demo-before.jpg"
            try:
                client.storage.from_("rescue-images").upload(
                    remote_image_path,
                    Path(local_image_path).read_bytes(),
                    {"content-type": "image/jpeg", "upsert": "false"},
                )
            except Exception as error:
                message = str(error).lower()
                if "duplicate" not in message and "already exists" not in message:
                    raise
        rescue_rows.append(
            _rescue_row(rescue, player_ids, position, remote_image_path)
        )
    client.table("rescues").upsert(rescue_rows, on_conflict="id").execute()

    existing_contributions = {
        row["id"]
        for row in client.table("rescue_contributions").select("id").execute().data
    }
    contribution_rows = []
    solver_rows = []
    for rescue in rescues:
        remote_rescue_id = _demo_uuid(rescue["id"])
        for index, contribution in enumerate(rescue["contributions"]):
            contribution_id = _demo_uuid(
                f"{rescue['id']}:contribution:{contribution['player']}:{index}"
            )
            if contribution_id not in existing_contributions:
                contribution_rows.append(
                    {
                        "id": contribution_id,
                        "rescue_id": remote_rescue_id,
                        "player_id": player_ids[contribution["player"]],
                        "contribution_type": contribution["contribution_type"],
                        "message": contribution["message"],
                        "xp_awarded": contribution["xp_awarded"],
                        "streak_multiplier": 1.0,
                        "created_at": contribution["created_at"],
                    }
                )
        for solver in rescue["solvers"]:
            solver_rows.append(
                {
                    "rescue_id": remote_rescue_id,
                    "player_id": player_ids[solver],
                    "xp_awarded": rescue["solver_xp_awards"][solver],
                    "streak_multiplier": rescue["solver_streak_multipliers"][solver],
                }
            )
    if contribution_rows:
        client.table("rescue_contributions").insert(contribution_rows).execute()
    if solver_rows:
        client.table("rescue_solvers").upsert(
            solver_rows, on_conflict="rescue_id,player_id"
        ).execute()

    existing_activity = {
        (row["player_id"], str(row["activity_date"]))
        for row in client.table("player_activity_days")
        .select("player_id, activity_date")
        .execute()
        .data
    }
    activity_rows = [
        {"player_id": player_ids[player], "activity_date": activity_date}
        for player, stats in seeded_player_stats().items()
        for activity_date in stats["activity_dates"]
        if (player_ids[player], activity_date) not in existing_activity
    ]
    if activity_rows:
        client.table("player_activity_days").insert(activity_rows).execute()

    print(
        f"Seeded {len(rescues)} demo listings, {len(contribution_rows)} new contributions, "
        f"and {len(solver_rows)} solver records."
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed deterministic Outlast demo data.")
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Write the deterministic demo records to the configured Supabase project.",
    )
    args = parser.parse_args()
    if not args.apply:
        print(
            f"Dry run: {len(seeded_rescues())} listings and "
            f"{len(seeded_player_stats())} players are ready. Pass --apply to write them."
        )
        return
    seed_remote_demo()


if __name__ == "__main__":
    main()
