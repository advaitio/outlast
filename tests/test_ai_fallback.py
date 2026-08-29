from types import SimpleNamespace

from repair_quest import ai
from repair_quest.ai import fallback_analysis, fallback_disposal_guidance
from repair_quest.models import PrePostGuidance


def test_fallback_suggests_passing_on_an_item_that_already_works() -> None:
    result = fallback_analysis("Working desk lamp that I no longer need")
    assert result.pre_post_guidance == PrePostGuidance.PASS_ON


def test_fallback_suggests_responsible_exit_for_badly_damaged_item() -> None:
    result = fallback_analysis("The toaster casing is burnt and beyond repair")
    assert result.pre_post_guidance == PrePostGuidance.RESPONSIBLE_EXIT
    assert "Stop using" in result.suggested_next_step


def test_fallback_defaults_to_repair() -> None:
    result = fallback_analysis("My desk fan stopped spinning")
    assert result.pre_post_guidance == PrePostGuidance.POST_REPAIR


def test_photo_is_sent_to_openai_and_structured_result_is_parsed(monkeypatch) -> None:
    captured = {}

    class FakeResponses:
        def create(self, **kwargs):
            captured.update(kwargs)
            return SimpleNamespace(
                output_text=(
                    '{"item_name":"Desk fan","pre_post_guidance":"Worth a repair attempt",'
                    '"reason":"A simple fault may be repairable.","difficulty":"Easy",'
                    '"rescue_title":"Rescue this desk fan",'
                    '"suggested_next_step":"Check the plug.","estimated_waste_kg":1.5}'
                )
            )

    fake_client = SimpleNamespace(responses=FakeResponses())
    monkeypatch.setattr(ai, "ai_available", lambda: True)
    monkeypatch.setattr(ai, "_secret", lambda name, default="": "test-key")
    monkeypatch.setattr(ai, "OpenAI", lambda **kwargs: fake_client)

    result = ai.analyze_item("The fan stopped spinning.", b"photo", "image/png")

    content = captured["input"][0]["content"]
    assert content[0] == {"type": "input_text", "text": "The fan stopped spinning."}
    assert content[1]["type"] == "input_image"
    assert content[1]["image_url"] == "data:image/png;base64,cGhvdG8="
    assert content[1]["detail"] == "high"
    assert result.item_name == "Desk fan"
    assert result.pre_post_guidance == PrePostGuidance.POST_REPAIR


def test_openai_schema_forbids_additional_properties() -> None:
    schema = ai.RescueAnalysis.model_json_schema()

    assert schema["additionalProperties"] is False


def test_disposal_schema_forbids_additional_properties() -> None:
    schema = ai.DisposalGuidance.model_json_schema()

    assert schema["additionalProperties"] is False


def test_disposal_fallback_gives_battery_safety_guidance() -> None:
    result = fallback_disposal_guidance("Power bank", "The lithium battery is swollen.")

    assert result.category == "Battery or battery-powered item"
    assert "Do not put batteries" in result.safety_note
