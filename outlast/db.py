"""Small optional Supabase repository used by the Streamlit state layer.

The demo continues to work with local session state when Supabase secrets are
missing or the remote project is unavailable.
"""

from __future__ import annotations

from datetime import date
from typing import Any

import streamlit as st


class PersistenceError(RuntimeError):
    """Raised when a configured Supabase write cannot be completed."""


def _secret(name: str) -> str:
    try:
        value = st.secrets.get(name)
        if value:
            return str(value)
    except (FileNotFoundError, KeyError, RuntimeError):
        pass
    return ""


def available() -> bool:
    return bool(_secret("SUPABASE_URL") and _secret("SUPABASE_KEY"))


@st.cache_resource
def _client() -> Any:
    from supabase import create_client

    return create_client(_secret("SUPABASE_URL"), _secret("SUPABASE_KEY"))


def _player_id(name: str) -> str:
    row = _client().table("players").select("id").eq("display_name", name).single().execute().data
    return row["id"]


def _image_path(rescue_id: str, label: str, mime_type: str | None) -> str:
    extensions = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"}
    return f"{rescue_id}/{label}.{extensions.get(mime_type or '', 'jpg')}"


def _upload_image(
    client: Any, rescue_id: str, label: str, image_bytes: bytes | None, mime_type: str | None
) -> str | None:
    if not image_bytes:
        return None
    path = _image_path(rescue_id, label, mime_type)
    client.storage.from_("rescue-images").upload(
        path, image_bytes, {"content-type": mime_type or "image/jpeg", "upsert": "false"}
    )
    return path


def _public_image_url(client: Any, path: str | None) -> str | None:
    return client.storage.from_("rescue-images").get_public_url(path) if path else None


def load_data() -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]] | None:
    if not available():
        return None
    try:
        client = _client()
        players = client.table("players").select("id, display_name, xp").execute().data
        rescues = client.table("rescues").select("*").order("created_at", desc=True).execute().data
        contributions = (
            client.table("rescue_contributions").select("*, players(display_name)").execute().data
        )
        solvers = client.table("rescue_solvers").select("*, players(display_name)").execute().data
        activity = (
            client.table("player_activity_days").select("player_id, activity_date").execute().data
        )
        by_rescue: dict[str, list[dict[str, Any]]] = {}
        for row in contributions:
            by_rescue.setdefault(row["rescue_id"], []).append(
                {
                    "player": (row.get("players") or {}).get("display_name", "Unknown"),
                    "message": row["message"],
                    "contribution_type": row["contribution_type"],
                    "created_at": row["created_at"],
                    "xp_awarded": row["xp_awarded"],
                }
            )
        solver_by_rescue: dict[str, list[str]] = {}
        awards_by_rescue: dict[str, dict[str, int]] = {}
        multipliers_by_rescue: dict[str, dict[str, float]] = {}
        for row in solvers:
            name = (row.get("players") or {}).get("display_name", "Unknown")
            solver_by_rescue.setdefault(row["rescue_id"], []).append(name)
            awards_by_rescue.setdefault(row["rescue_id"], {})[name] = row["xp_awarded"]
            multipliers_by_rescue.setdefault(row["rescue_id"], {})[name] = float(
                row["streak_multiplier"]
            )
        names = {row["id"]: row["display_name"] for row in players}
        dates = {name: [] for name in names.values()}
        for row in activity:
            if row["player_id"] in names:
                dates[names[row["player_id"]]].append(str(row["activity_date"]))
        result = []
        for row in rescues:
            owner = next(
                (item["display_name"] for item in players if item["id"] == row["owner_id"]),
                "Unknown",
            )
            completed_by = next(
                (
                    item["display_name"]
                    for item in players
                    if item["id"] == row.get("completed_by_id")
                ),
                None,
            )
            result.append(
                {
                    "id": row["id"],
                    "title": row["title"],
                    "item_name": row["item_name"],
                    "description": row["description"],
                    "owner": owner,
                    "action": row["recommended_action"],
                    "difficulty": row["difficulty"],
                    "estimated_waste_kg": float(row["estimated_waste_kg"]),
                    "next_step": row["suggested_next_step"],
                    "status": row["status"],
                    "contributions": by_rescue.get(row["id"], []),
                    "outcome": row.get("outcome"),
                    "completed_by": completed_by,
                    "completion_xp_award": row.get("completion_xp_awarded", 0),
                    "completion_streak_multiplier": row.get("completion_streak_multiplier"),
                    "solvers": solver_by_rescue.get(row["id"], []),
                    "solver_xp_awards": awards_by_rescue.get(row["id"], {}),
                    "solver_streak_multipliers": multipliers_by_rescue.get(row["id"], {}),
                    "image_url": _public_image_url(client, row.get("image_path")),
                    "after_image_url": _public_image_url(client, row.get("after_image_path")),
                }
            )
        stats = {
            row["display_name"]: {"xp": row["xp"], "activity_dates": dates[row["display_name"]]}
            for row in players
        }
        return result, stats
    except Exception as error:
        raise PersistenceError("Could not load data from Supabase.") from error


def create_rescue(rescue: dict[str, Any]) -> bool:
    if not available():
        return False
    try:
        client = _client()
        image_path = _upload_image(
            client,
            rescue["id"],
            "before",
            rescue.get("image_bytes"),
            rescue.get("image_mime_type"),
        )
        client.table("rescues").insert(
            {
                "id": rescue["id"],
                "owner_id": _player_id(rescue["owner"]),
                "title": rescue["title"],
                "item_name": rescue["item_name"],
                "description": rescue["description"],
                "recommended_action": rescue["action"],
                "difficulty": rescue["difficulty"],
                "estimated_waste_kg": rescue["estimated_waste_kg"],
                "suggested_next_step": rescue["next_step"],
                "image_path": image_path,
            }
        ).execute()
        rescue["image_path"] = image_path
        rescue["image_url"] = _public_image_url(client, image_path)
        return True
    except Exception as error:
        raise PersistenceError("Could not save the new item to Supabase.") from error


def add_contribution(rescue_id: str, player: str, message: str, xp: int, multiplier: float) -> bool:
    if not available():
        return False
    try:
        _client().rpc(
            "add_rescue_suggestion",
            {
                "p_rescue_id": rescue_id,
                "p_player_id": _player_id(player),
                "p_message": message,
                "p_xp_awarded": xp,
                "p_streak_multiplier": multiplier,
                "p_activity_date": date.today().isoformat(),
            },
        ).execute()
        return True
    except Exception as error:
        raise PersistenceError("Could not save the suggestion to Supabase.") from error


def complete_rescue(rescue: dict[str, Any]) -> bool:
    if not available():
        return False
    try:
        client = _client()
        after_image_path = _upload_image(
            client,
            rescue["id"],
            "after",
            rescue.get("after_image_bytes"),
            rescue.get("after_image_mime_type"),
        )
        solvers = [
            {
                "player_id": _player_id(player),
                "xp_awarded": xp,
                "streak_multiplier": rescue["solver_streak_multipliers"][player],
            }
            for player, xp in rescue["solver_xp_awards"].items()
        ]
        client.rpc(
            "complete_rescue_with_awards",
            {
                "p_rescue_id": rescue["id"],
                "p_completed_by_id": _player_id(rescue["completed_by"]),
                "p_outcome": rescue["outcome"],
                "p_completion_xp_awarded": rescue["completion_xp_award"],
                "p_completion_streak_multiplier": rescue["completion_streak_multiplier"],
                "p_solvers": solvers,
                "p_activity_date": date.today().isoformat(),
                "p_after_image_path": after_image_path,
            },
        ).execute()
        rescue["after_image_path"] = after_image_path
        rescue["after_image_url"] = _public_image_url(client, after_image_path)
        return True
    except Exception as error:
        raise PersistenceError("Could not resolve the item in Supabase.") from error
