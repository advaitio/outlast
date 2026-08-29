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


class RescueStatus(StrEnum):
    OPEN = "Open"
    COMPLETED = "Completed"


class ContributionType(StrEnum):
    SUGGESTION = "Suggestion"


class RescueAnalysis(BaseModel):
    item_name: str = Field(description="Short, specific name of the item")
    recommended_action: RescueAction
    reason: str = Field(description="One concise reason this action keeps the item in circulation")
    difficulty: Difficulty
    rescue_title: str = Field(description="Short, upbeat rescue title")
    suggested_next_step: str = Field(description="One safe, simple next step")
    estimated_waste_kg: float = Field(ge=0.05, le=100)


class Contribution(BaseModel):
    player: str
    message: str = Field(min_length=1, max_length=280)
    contribution_type: ContributionType = ContributionType.SUGGESTION
    created_at: str
    xp_awarded: int = Field(ge=0)


class Rescue(BaseModel):
    id: str
    title: str
    item_name: str
    description: str
    owner: str
    action: RescueAction
    difficulty: Difficulty
    estimated_waste_kg: float
    next_step: str
    status: RescueStatus = RescueStatus.OPEN
    contributions: list[Contribution] = Field(default_factory=list)
    outcome: RescueAction | None = None
    completed_by: str | None = None
    completion_xp_award: int = Field(default=0, ge=0)
    completion_streak_multiplier: float | None = Field(default=None, ge=1, le=1.5)
    solvers: list[str] = Field(default_factory=list)
    solver_xp_awards: dict[str, int] = Field(default_factory=dict)
