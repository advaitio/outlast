from __future__ import annotations

import base64
import json
import os
from pathlib import Path
from typing import Any

from openai import OpenAI

from repair_quest.models import Difficulty, QuestAnalysis, RescueAction

SYSTEM_PROMPT = """You create safe, encouraging Rescue Quests for a community reuse game.
Choose the best way to keep the item in circulation: Repair, Rehome, or Salvage.
Do not provide detailed electrical or hazardous repair instructions. Give only one safe first step.
Estimate waste conservatively. Keep every text field concise and suitable for a public
quest card."""


def _secret(name: str, default: str = "") -> str:
    """Read from Streamlit secrets when available, then the environment."""
    try:
        import streamlit as st

        value = st.secrets.get(name)
        if value:
            return str(value)
    except (FileNotFoundError, KeyError, RuntimeError):
        pass
    return os.getenv(name, default)


def ai_available() -> bool:
    return bool(_secret("OPENAI_API_KEY"))


def _data_url(image_bytes: bytes, mime_type: str) -> str:
    encoded = base64.b64encode(image_bytes).decode("ascii")
    return f"data:{mime_type};base64,{encoded}"


def analyze_item(
    description: str,
    image_bytes: bytes | None,
    mime_type: str = "image/jpeg",
) -> QuestAnalysis:
    """Generate a structured quest with OpenAI, or a deterministic demo fallback."""
    if not ai_available():
        return fallback_analysis(description)

    content: list[dict[str, Any]] = [{"type": "input_text", "text": description}]
    if image_bytes:
        content.append(
            {
                "type": "input_image",
                "image_url": _data_url(image_bytes, mime_type),
                "detail": "low",
            }
        )

    client = OpenAI(api_key=_secret("OPENAI_API_KEY"))
    response = client.responses.create(
        model=_secret("OPENAI_MODEL", "gpt-5.6-luna"),
        instructions=SYSTEM_PROMPT,
        input=[{"role": "user", "content": content}],
        reasoning={"effort": "low"},
        text={
            "format": {
                "type": "json_schema",
                "name": "quest_analysis",
                "strict": True,
                "schema": QuestAnalysis.model_json_schema(),
            }
        },
        store=False,
    )
    return QuestAnalysis.model_validate(json.loads(response.output_text))


def fallback_analysis(description: str) -> QuestAnalysis:
    """Keep the demo usable without credentials or network access."""
    text = description.lower()
    if any(word in text for word in ("works", "working", "unused", "no longer need", "too small")):
        action = RescueAction.REHOME
        reason = "It appears usable and can serve someone else without requiring a replacement."
        step = "Clean it, confirm it works, and share its condition with the community."
    elif any(word in text for word in ("shattered", "burnt", "corroded", "beyond repair")):
        action = RescueAction.SALVAGE
        reason = "Useful components may be recovered even if the whole item cannot be repaired."
        step = "Keep it powered off and identify parts that can be safely removed or recycled."
    else:
        action = RescueAction.REPAIR
        reason = "The description suggests a simple fault may be worth checking before replacement."
        step = "Check the power source, visible connections, and user manual first."

    words = [word.strip(".,!?()[]") for word in description.split() if len(word) > 2]
    item_name = " ".join(words[:3]).title() if words else "Household item"
    return QuestAnalysis(
        item_name=item_name,
        recommended_action=action,
        reason=reason,
        difficulty=Difficulty.EASY if action != RescueAction.SALVAGE else Difficulty.MEDIUM,
        quest_title=f"Give this {item_name.lower()} a second chance",
        suggested_next_step=step,
        estimated_waste_kg=1.0,
    )


def load_example_image(path: str | Path) -> bytes:
    """Small helper kept separate for future seeded demo assets."""
    return Path(path).read_bytes()
