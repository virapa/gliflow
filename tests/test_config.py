import json
import tempfile
from pathlib import Path
import pytest
from src.config.manager import ConfigManager, DEFAULT_CONFIG


@pytest.fixture
def tmp_cfg(tmp_path):
    return ConfigManager(config_dir=tmp_path)


def test_default_config_created(tmp_path):
    cfg = ConfigManager(config_dir=tmp_path)
    config_file = tmp_path / "config.json"
    assert config_file.exists()
    data = json.loads(config_file.read_text())
    assert "general" in data
    assert "provider" in data
    assert "hotkey" in data
    assert "widget" in data


def test_get_dotted_key(tmp_cfg):
    assert tmp_cfg.get("general.language") == "es"
    assert tmp_cfg.get("provider.active") == "groq"
    assert tmp_cfg.get("hotkey.double_tap_ms") == 400
    assert tmp_cfg.get("nonexistent.key", "fallback") == "fallback"


def test_set_and_persist(tmp_path):
    cfg = ConfigManager(config_dir=tmp_path)
    cfg.set("general.language", "en")
    cfg.set("provider.active", "openai")

    # Reload from disk
    cfg2 = ConfigManager(config_dir=tmp_path)
    assert cfg2.get("general.language") == "en"
    assert cfg2.get("provider.active") == "openai"


def test_merge_preserves_defaults(tmp_path):
    """Partial config on disk still gets defaults for missing keys."""
    config_file = tmp_path / "config.json"
    config_file.write_text(json.dumps({"general": {"language": "en"}}))
    cfg = ConfigManager(config_dir=tmp_path)
    assert cfg.get("general.language") == "en"
    assert cfg.get("provider.active") == "groq"  # from defaults
    assert cfg.get("hotkey.double_tap_ms") == 400  # from defaults


def test_set_nested_key(tmp_cfg):
    tmp_cfg.set("provider.groq.api_key", "test-key-123")
    assert tmp_cfg.get("provider.groq.api_key") == "test-key-123"
