"""Tests for MeteoraSettings configuration.

[WHY] Validates default values, custom overrides, and base_url normalization.
[OWNERSHIP] Infrastructure layer — settings tests.
"""

from meteora.settings import MeteoraSettings


class TestMeteoraSettings:
    """MeteoraSettings tests."""

    def test_default_settings(self) -> None:
        """Default settings have correct values."""
        settings = MeteoraSettings()
        assert settings.base_url == "https://dlmm.datapi.meteora.ag"
        assert settings.timeout == 30.0
        assert settings.max_retries == 3
        assert settings.retry_delay == 1.0
        assert settings.rate_limit_rps == 30

    def test_custom_settings(self) -> None:
        """Custom values override defaults correctly."""
        settings = MeteoraSettings(timeout=60.0, max_retries=5)
        assert settings.timeout == 60.0
        assert settings.max_retries == 5
        # Non-overridden defaults remain
        assert settings.base_url == "https://dlmm.datapi.meteora.ag"
        assert settings.retry_delay == 1.0
        assert settings.rate_limit_rps == 30

    def test_base_url_no_trailing_slash(self) -> None:
        """base_url is stored without trailing slash."""
        settings_with_slash = MeteoraSettings(base_url="https://custom.api.com/")
        assert settings_with_slash.base_url == "https://custom.api.com"

        settings_without_slash = MeteoraSettings(base_url="https://custom.api.com")
        assert settings_without_slash.base_url == "https://custom.api.com"

        # Default also has no trailing slash
        settings_default = MeteoraSettings()
        assert not settings_default.base_url.endswith("/")
