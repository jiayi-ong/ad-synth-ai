"""Unit tests for Settings configuration."""
import pytest


@pytest.mark.unit
def test_default_image_gen_provider(monkeypatch):
    monkeypatch.delenv("IMAGE_GEN_PROVIDER", raising=False)
    from backend.core.config import Settings
    s = Settings(_env_file=None)
    assert s.image_gen_provider == "mock"


@pytest.mark.unit
def test_default_database_url_is_sqlite():
    from backend.core.config import Settings
    s = Settings(_env_file=None)
    assert "sqlite" in s.database_url


@pytest.mark.unit
def test_default_log_level_is_info():
    from backend.core.config import Settings
    s = Settings(_env_file=None)
    assert s.log_level == "INFO"


@pytest.mark.unit
def test_default_log_to_file_is_true():
    from backend.core.config import Settings
    s = Settings(_env_file=None)
    assert s.log_to_file is True


@pytest.mark.unit
def test_default_log_dir():
    from backend.core.config import Settings
    s = Settings(_env_file=None)
    assert s.log_dir == "logs"


@pytest.mark.unit
def test_default_vertexai_is_false():
    from backend.core.config import Settings
    s = Settings(_env_file=None)
    assert s.google_genai_use_vertexai is False


@pytest.mark.unit
def test_image_gen_provider_accepts_all_values(monkeypatch):
    from backend.core.config import Settings
    for provider in ("mock", "vertexai", "gemini", "shortapi"):
        s = Settings(_env_file=None, image_gen_provider=provider)
        assert s.image_gen_provider == provider


@pytest.mark.unit
def test_image_gen_provider_rejects_invalid():
    from pydantic import ValidationError
    from backend.core.config import Settings
    with pytest.raises(ValidationError):
        Settings(_env_file=None, image_gen_provider="unknown_provider")


@pytest.mark.unit
def test_log_format_accepts_json_and_text():
    from backend.core.config import Settings
    for fmt in ("json", "text"):
        s = Settings(_env_file=None, log_format=fmt)
        assert s.log_format == fmt


@pytest.mark.unit
def test_missing_env_file_does_not_crash(monkeypatch):
    monkeypatch.delenv("IMAGE_GEN_PROVIDER", raising=False)
    from backend.core.config import Settings
    s = Settings(_env_file="/nonexistent/.env")
    assert s is not None
    assert s.image_gen_provider == "mock"
