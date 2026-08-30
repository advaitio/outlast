from __future__ import annotations

import tomllib
from pathlib import Path


def _relative_luminance(hex_color: str) -> float:
    channels = [int(hex_color[index : index + 2], 16) / 255 for index in (1, 3, 5)]
    linear = [
        channel / 12.92
        if channel <= 0.04045
        else ((channel + 0.055) / 1.055) ** 2.4
        for channel in channels
    ]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def _contrast_ratio(first: str, second: str) -> float:
    lighter, darker = sorted(
        (_relative_luminance(first), _relative_luminance(second)), reverse=True
    )
    return (lighter + 0.05) / (darker + 0.05)


def test_theme_text_and_primary_actions_meet_wcag_aa() -> None:
    config_path = Path(__file__).parents[1] / ".streamlit" / "config.toml"
    with config_path.open("rb") as config_file:
        theme = tomllib.load(config_file)["theme"]

    assert _contrast_ratio(theme["textColor"], theme["backgroundColor"]) >= 4.5
    assert _contrast_ratio(theme["primaryColor"], "#FFFFFF") >= 4.5
