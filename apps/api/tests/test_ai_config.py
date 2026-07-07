import pytest

from veridian_api.core.config import Settings


def test_deepinfra_resolves_base_url_and_key() -> None:
    settings = Settings(
        ai_provider="deepinfra",
        deepinfra_api_key="di-test-key",
        ai_model="deepseek-ai/DeepSeek-V3",
    )
    assert settings.resolved_ai_provider == "deepinfra"
    assert settings.resolved_ai_base_url == "https://api.deepinfra.com/v1/openai"
    assert settings.resolved_ai_api_key == "di-test-key"
    assert settings.ai_enabled is True


def test_openai_legacy_key_still_works() -> None:
    settings = Settings(ai_provider="openai", openai_api_key="sk-test")
    assert settings.resolved_ai_base_url == "https://api.openai.com/v1"
    assert settings.resolved_ai_api_key == "sk-test"


def test_ai_api_key_overrides_provider_specific_keys() -> None:
    settings = Settings(
        ai_provider="deepinfra",
        ai_api_key="shared-key",
        deepinfra_api_key="ignored",
    )
    assert settings.resolved_ai_api_key == "shared-key"


def test_custom_base_url_override() -> None:
    settings = Settings(
        ai_provider="deepinfra",
        ai_api_base_url="https://proxy.example.com/v1/openai",
        ai_api_key="key",
    )
    assert settings.resolved_ai_base_url == "https://proxy.example.com/v1/openai"
