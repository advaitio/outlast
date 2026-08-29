from __future__ import annotations

import base64
import json
import os
from pathlib import Path
from typing import Any

from openai import OpenAI

from repair_quest.models import Difficulty, DisposalGuidance, PrePostGuidance, RescueAnalysis

SYSTEM_PROMPT = """You create safe, encouraging repair requests for a community repair game.
Assess the user's description and the image together when an image is provided. Choose exactly
one pre-post guidance value:
- Worth a repair attempt: the item appears worth one safe repair attempt.
- Pass it on instead: the item appears safe and usable already, so it does not need repair.
- Repair may not be safe: visible or described damage makes a community repair attempt unsafe
  or clearly impractical.
Never suggest passing on an unsafe, burnt, leaking, swollen, contaminated, or structurally
dangerous item. When evidence is limited, be explicit in the reason and prefer a safe inspection
or professional assessment over a confident diagnosis. Do not provide detailed electrical or
hazardous repair instructions. Give only one safe first step appropriate to the guidance. Always
generate a repair-request title because the owner may still choose to post. Estimate waste
conservatively. Keep every text field concise and suitable for the app."""

SINGAPORE_EWASTE_URL = (
    "https://www.nea.gov.sg/our-services/waste-management/3r-programmes-and-resources/"
    "e-waste-management/where-to-recycle-e-waste"
)
DISPOSAL_SYSTEM_PROMPT = """You provide concise, safety-first, owner-only disposal guidance
for Singapore.
Use only these general routes: NEA/ALBA e-waste collection for electronics and batteries,
retailer take-back or Town Council bulky-item services for large appliances, or the official
NEA recycling guide for general household items. Do not invent collection locations, rules,
or hazardous handling instructions. For batteries, say not to use general or blue recycling
bins and to tape exposed terminals or wires before recycling. Keep the advice practical and
avoid claiming the item is recyclable when uncertain."""


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
) -> RescueAnalysis:
    """Generate a structured rescue with OpenAI, or a deterministic demo fallback."""
    if not ai_available():
        return fallback_analysis(description)

    content: list[dict[str, Any]] = [{"type": "input_text", "text": description}]
    if image_bytes:
        content.append(
            {
                "type": "input_image",
                "image_url": _data_url(image_bytes, mime_type),
                "detail": "high",
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
                "name": "rescue_analysis",
                "strict": True,
                "schema": RescueAnalysis.model_json_schema(),
            }
        },
        store=False,
    )
    return RescueAnalysis.model_validate(json.loads(response.output_text))


def disposal_guidance(
    item_name: str,
    description: str,
    image_bytes: bytes | None = None,
    mime_type: str = "image/jpeg",
) -> DisposalGuidance:
    """Create Singapore-specific disposal guidance, with a safe offline fallback."""
    if not ai_available():
        return fallback_disposal_guidance(item_name, description)

    content: list[dict[str, Any]] = [
        {"type": "input_text", "text": f"Item: {item_name}\nDescription: {description}"}
    ]
    if image_bytes:
        content.append(
            {
                "type": "input_image",
                "image_url": _data_url(image_bytes, mime_type),
                "detail": "low",
            }
        )
    response = OpenAI(api_key=_secret("OPENAI_API_KEY")).responses.create(
        model=_secret("OPENAI_MODEL", "gpt-5.6-luna"),
        instructions=DISPOSAL_SYSTEM_PROMPT,
        input=[{"role": "user", "content": content}],
        reasoning={"effort": "low"},
        text={
            "format": {
                "type": "json_schema",
                "name": "singapore_disposal_guidance",
                "strict": True,
                "schema": DisposalGuidance.model_json_schema(),
            }
        },
        store=False,
    )
    guidance = DisposalGuidance.model_validate(json.loads(response.output_text))
    return guidance.model_copy(update={"official_resource_url": SINGAPORE_EWASTE_URL})


def fallback_analysis(description: str) -> RescueAnalysis:
    """Keep the demo usable without credentials or network access."""
    text = description.lower()
    unsafe_words = (
        "burnt",
        "burned",
        "swollen",
        "leaking battery",
        "exposed wire",
        "beyond repair",
        "structural crack",
    )
    working_words = ("works", "working", "unused", "no longer need", "too small")
    if any(word in text for word in unsafe_words):
        guidance = PrePostGuidance.RESPONSIBLE_EXIT
        reason = "The description indicates damage that may make a repair attempt unsafe."
        step = "Stop using the item and check the appropriate responsible disposal route."
    elif any(word in text for word in working_words):
        guidance = PrePostGuidance.PASS_ON
        reason = "The item appears usable already, so it may not need a repair request."
        step = "Confirm it works safely, clean it, and describe its condition honestly."
    else:
        guidance = PrePostGuidance.POST_REPAIR
        reason = "The description suggests a simple fault may be worth checking before replacement."
        step = "Check the power source, visible connections, and user manual first."

    words = [word.strip(".,!?()[]") for word in description.split() if len(word) > 2]
    item_name = " ".join(words[:3]).title() if words else "Household item"
    return RescueAnalysis(
        item_name=item_name,
        pre_post_guidance=guidance,
        reason=reason,
        difficulty=Difficulty.EASY,
        rescue_title=f"Give this {item_name.lower()} a second chance",
        suggested_next_step=step,
        estimated_waste_kg=1.0,
    )


def fallback_disposal_guidance(item_name: str, description: str) -> DisposalGuidance:
    """Safe, deterministic Singapore guidance when the OpenAI key is unavailable."""
    text = f"{item_name} {description}".lower()
    battery_words = ("battery", "lithium", "power bank", "rechargeable")
    electronic_words = (
        "fan", "lamp", "kettle", "toaster", "keyboard", "headphone", "charger", "cable",
        "computer", "phone", "electronic", "electric",
    )
    if any(word in text for word in battery_words):
        return DisposalGuidance(
            category="Battery or battery-powered item",
            recommendation="Use an NEA/ALBA battery or e-waste collection point in Singapore.",
            preparation_steps=[
                "Remove the battery if it can be done safely.",
                "Tape exposed battery terminals or wires.",
                "Seal a leaking battery in a leak-proof bag or container.",
            ],
            safety_note="Do not put batteries in general waste or blue recycling bins.",
            official_resource_url=SINGAPORE_EWASTE_URL,
        )
    if any(word in text for word in electronic_words):
        return DisposalGuidance(
            category="Electronic waste",
            recommendation=(
                "Take this item to a Singapore e-waste collection programme or an accepted "
                "collection point."
            ),
            preparation_steps=[
                "Unplug the item and remove detachable batteries if safe.",
                "Remove personal data from any storage device.",
                "Bring cables and accessories only if the collection point accepts them.",
            ],
            safety_note="Do not place electrical or electronic equipment in a blue recycling bin.",
            official_resource_url=SINGAPORE_EWASTE_URL,
        )
    return DisposalGuidance(
        category="Household item",
        recommendation=(
            "Check the official Singapore recycling guidance or your Town Council for the "
            "appropriate route."
        ),
        preparation_steps=[
            "Clean and empty the item before handing it over.",
            "Separate batteries, electronics, or sharp parts for their proper collection route.",
        ],
        safety_note="When unsure, do not place mixed-material items in a blue recycling bin.",
        official_resource_url="https://www.nea.gov.sg/our-services/waste-management/3r-programmes-and-resources/recycling",
    )


def load_example_image(path: str | Path) -> bytes:
    """Small helper kept separate for future seeded demo assets."""
    return Path(path).read_bytes()
