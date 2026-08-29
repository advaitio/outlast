from repair_quest.ai import fallback_analysis
from repair_quest.models import RescueAction


def test_fallback_recommends_rehome_for_working_item() -> None:
    result = fallback_analysis("Working desk lamp that I no longer need")
    assert result.recommended_action == RescueAction.REHOME


def test_fallback_recommends_salvage_for_badly_damaged_item() -> None:
    result = fallback_analysis("The toaster casing is burnt and beyond repair")
    assert result.recommended_action == RescueAction.SALVAGE


def test_fallback_defaults_to_repair() -> None:
    result = fallback_analysis("My desk fan stopped spinning")
    assert result.recommended_action == RescueAction.REPAIR
