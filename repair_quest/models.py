from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class RescueAction(StrEnum):
    REPAIR = "Repair"
    REHOME = "Rehome"
    SALVAGE = "Salvage"


class Difficulty(StrEnum):
    EASY = "Easy"
    MEDIUM = "Medium"
    HARD = "Hard"


class QuestAnalysis(BaseModel):
    item_name: str = Field(description="Short, specific name of the item")
    recommended_action: RescueAction
    reason: str = Field(description="One concise reason this action keeps the item in circulation")
    difficulty: Difficulty
    quest_title: str = Field(description="Short, upbeat rescue quest title")
    suggested_next_step: str = Field(description="One safe, simple next step")
    estimated_waste_kg: float = Field(ge=0.05, le=100)


class Quest(BaseModel):
    id: str
    title: str
    item_name: str
    description: str
    owner: str
    team: str = "COM3"
    action: RescueAction
    difficulty: Difficulty
    estimated_waste_kg: float
    next_step: str
    status: str = "Open"
    helper: str | None = None
    teammates: list[str] = Field(default_factory=list)
    offers: list[str] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)
    outcome: RescueAction | None = None
    points_awarded: int = 0
