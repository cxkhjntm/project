"""Tests for token limit configuration in Settings."""

from app.config import Settings


class TestTokenLimitSettings:
    """Test token limit configuration fields."""

    def test_settings_has_max_tokens_per_turn(self):
        settings = Settings()
        assert hasattr(settings, "max_tokens_per_turn")
        assert isinstance(settings.max_tokens_per_turn, int)

    def test_settings_has_max_total_tokens(self):
        settings = Settings()
        assert hasattr(settings, "max_total_tokens")
        assert isinstance(settings.max_total_tokens, int)

    def test_max_tokens_per_turn_default_value(self):
        settings = Settings()
        assert settings.max_tokens_per_turn == 4096

    def test_max_total_tokens_default_value(self):
        settings = Settings()
        assert settings.max_total_tokens == 50000

    def test_max_tokens_per_turn_less_than_max_total_tokens(self):
        settings = Settings()
        assert settings.max_tokens_per_turn <= settings.max_total_tokens

    def test_token_limits_positive(self):
        settings = Settings()
        assert settings.max_tokens_per_turn > 0
        assert settings.max_total_tokens > 0

    def test_custom_token_limits(self):
        settings = Settings(max_tokens_per_turn=2048, max_total_tokens=100000)
        assert settings.max_tokens_per_turn == 2048
        assert settings.max_total_tokens == 100000
