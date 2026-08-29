"""Small optional Supabase repository used by the Streamlit state layer.

The demo continues to work with local session state when Supabase secrets are
missing or the remote project is unavailable.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any

import streamlit as st


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


def load_data() -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]] | None:
    if not available():
        return None
    try:
        client = _client()
        players = client.table("players").select("id, display_name, xp").execute().data
        rescues = client.table("rescues").select("*").order("created_at", desc=True).execute().data
        contributions = client.table("rescue_contributions").select("*, players(display_name)").execute().data
        solvers = client.table("rescue_solvers").select("*, players(display_name)").execute().data
        activity = client.table("player_activity_days").select("player_id, activity_date").execute().data
        by_rescue: dict[str, list[dict[str, Any]]] = {}
        for row in contributions:
            by_rescue.setdefault(row["rescue_id"], []).append({
                "player": (row.get("players") or {}).get("display_name", "Unknown"),
                "message": row["message"], "contribution_type": row["contribution_type"],
                "created_at": row["created_at"], "xp_awarded": row["xp_awarded"],
            })
        solver_by_rescue: dict[str, list[str]] = {}
        awards_by_rescue: dict[str, dict[str, int]] = {}
        for row in solvers:
            name = (row.get("players") or {}).get("display_name", "Unknown")
            solver_by_rescue.setdefault(row["rescue_id"], []).append(name)
            awards_by_rescue.setdefault(row["rescue_id"], {})[name] = row["xp_awarded"]
        names = {row["id"]: row["display_name"] for row in players}
        dates = {name: [] for name in names.values()}
        for row in activity:
            if row["player_id"] in names:
                dates[names[row["player_id"]]].append(str(row["activity_date"]))
        result = []
        for row in rescues:
            owner = next((item["display_name"] for item in players if item["id"] == row["owner_id"]), "Unknown")
            completed_by = next((item["display_name"] for item in players if item["id"] == row.get("completed_by_id")), None)
            result.append({
                "id": row["id"], "title": row["title"], "item_name": row["item_name"],
                "description": row["description"], "owner": owner, "action": row["recommended_action"],
                "difficulty": row["difficulty"], "estimated_waste_kg": float(row["estimated_waste_kg"]),
                "next_step": row["suggested_next_step"], "status": row["status"],
                "contributions": by_rescue.get(row["id"], []), "outcome": row.get("outcome"),
                "completed_by": completed_by, "completion_xp_award": row.get("completion_xp_awarded", 0),
                "completion_streak_multiplier": row.get("completion_streak_multiplier"),
                "solvers": solver_by_rescue.get(row["id"], []),
                "solver_xp_awards": awards_by_rescue.get(row["id"], {}),
            })
        stats = {row["display_name"]: {"xp": row["xp"], "activity_dates": dates[row["display_name"]]} for row in players}
        return result, stats
    except Exception:
        return None


def create_rescue(rescue: dict[str, Any]) -> bool:
    if not available():
        return False
    try:
        client = _client()
        client.table("rescues").insert({
            "id": rescue["id"], "owner_id": _player_id(rescue["owner"]), "title": rescue["title"],
            "item_name": rescue["item_name"], "description": rescue["description"],
            "recommended_action": rescue["action"], "difficulty": rescue["difficulty"],
            "estimated_waste_kg": rescue["estimated_waste_kg"], "suggested_next_step": rescue["next_step"],
        }).execute()
        return True
    except Exception:
        return False


def add_contribution(rescue_id: str, player: str, message: str, xp: int, multiplier: float) -> bool:
    if not available():
        return False
    try:
        _client().table("rescue_contributions").insert({
            "rescue_id": rescue_id, "player_id": _player_id(player), "contribution_type": "Suggestion",
            "message": message, "xp_awarded": xp, "streak_multiplier": multiplier,
        }).execute()
        _client().table("players").update({"xp": _client().table("players").select("xp").eq("display_name", player).single().execute().data["xp"] + xp}).eq("display_name", player).execute()
        _client().table("player_activity_days").upsert({"player_id": _player_id(player), "activity_date": date.today().isoformat()}).execute()
        return True
    except Exception:
        return False


def complete_rescue(rescue: dict[str, Any]) -> bool:
    if not available():
        return False
    try:
        client = _client()
        client.table("rescues").update({
            "status": "Completed", "outcome": rescue["outcome"], "completed_by_id": _player_id(rescue["completed_by"]),
            "completion_xp_awarded": rescue["completion_xp_award"],
            "completion_streak_multiplier": rescue["completion_streak_multiplier"],
            "completed_at": datetime.now(timezone.utc).isoformat(),
        }).eq("id", rescue["id"]).execute()
        for player, xp in rescue["solver_xp_awards"].items():
            client.table("rescue_solvers").upsert({
                "rescue_id": rescue["id"], "player_id": _player_id(player), "xp_awarded": xp,
                "streak_multiplier": rescue["completion_streak_multiplier"],
            }).execute()
        for player, xp in [(rescue["completed_by"], rescue["completion_xp_award"]), *rescue["solver_xp_awards"].items()]:
            row = client.table("players").select("id, xp").eq("display_name", player).single().execute().data
            client.table("players").update({"xp": row["xp"] + xp}).eq("id", row["id"]).execute()
            client.table("player_activity_days").upsert({"player_id": row["id"], "activity_date": date.today().isoformat()}).execute()
        return True
    except Exception:
        return False
