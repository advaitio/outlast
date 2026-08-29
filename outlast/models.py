from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class RescueAction(StrEnum):
    REPAIR = "Repair"


class RescueOutcome(StrEnum):
    REPAIR = "Repair"
    RECYCLE_DISPOSE = "Recycle / dispose responsibly"


class PrePostGuidance(StrEnum):
    POST_REPAIR = "Worth a repair attempt"
    PASS_ON = "Pass it on instead"
    RESPONSIBLE_EXIT = "Repair may not be safe"


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
    model_config = ConfigDict(extra="forbid")

    item_name: str = Field(description="Short, specific name of the item")
    pre_post_guidance: PrePostGuidance
    reason: str = Field(description="One concise reason for the pre-post guidance")
    difficulty: Difficulty
    rescue_title: str = Field(
        min_length=3,
        max_length=60,
        description="Distinctive 3-to-8-word listing title naming the specific item",
    )
    suggested_next_step: str = Field(description="One safe, simple next step")
    estimated_waste_kg: float = Field(ge=0.05, le=100)


class DisposalGuidance(BaseModel):
    """Owner-only, Singapore-specific next steps for an item that cannot be kept."""

    model_config = ConfigDict(extra="forbid")

    category: str = Field(description="Plain-language disposal category")
    recommendation: str = Field(description="Short Singapore-specific recommendation")
    preparation_steps: list[str] = Field(min_length=1, max_length=4)
    safety_note: str = Field(description="One important safety note")
    official_resource_url: str = Field(description="Relevant official Singapore resource")


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
    outcome: RescueOutcome | None = None
    completed_by: str | None = None
    completion_xp_award: int = Field(default=0, ge=0)
    completion_streak_multiplier: float | None = Field(default=None, ge=1, le=1.5)
    solvers: list[str] = Field(default_factory=list)
    solver_xp_awards: dict[str, int] = Field(default_factory=dict)
    solver_streak_multipliers: dict[str, float] = Field(default_factory=dict)
    disposal_location: str | None = None
    disposal_evidence_xp_award: int = Field(default=0, ge=0)
