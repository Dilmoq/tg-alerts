"""Unit tests for configuration resolution."""

from pathlib import Path

import pytest

from tg_alerts.config import ConfigError, load


def write_cfg(tmp_path: Path, token: str = "", chat: str = "") -> Path:
    p = tmp_path / "config.toml"
    p.write_text(
        f'[telegram]\ntoken = "{token}"\nchat_id = "{chat}"\n',
        encoding="utf-8",
    )
    return p


class TestLoad:
    def test_from_toml(self, tmp_path, monkeypatch):
        monkeypatch.delenv("TG_ALERTS_TOKEN", raising=False)
        monkeypatch.delenv("TG_ALERTS_CHAT_ID", raising=False)
        p = write_cfg(tmp_path, token="123:SOMETOKEN", chat="42")
        config = load(p)
        assert config.token == "123:SOMETOKEN"
        assert config.chat_id == "42"

    def test_env_overrides_toml(self, tmp_path, monkeypatch):
        monkeypatch.setenv("TG_ALERTS_TOKEN", "999:ENVTOKEN")
        monkeypatch.setenv("TG_ALERTS_CHAT_ID", "777")
        p = write_cfg(tmp_path, token="123:SOMETOKEN", chat="42")
        config = load(p)
        assert config.token == "999:ENVTOKEN"
        assert config.chat_id == "777"

    def test_missing_credentials_raise(self, tmp_path, monkeypatch):
        monkeypatch.delenv("TG_ALERTS_TOKEN", raising=False)
        monkeypatch.delenv("TG_ALERTS_CHAT_ID", raising=False)
        p = write_cfg(tmp_path)
        with pytest.raises(ConfigError) as exc:
            load(p)
        assert "@BotFather" in str(exc.value)

    def test_missing_file_no_env_raises(self, tmp_path, monkeypatch):
        monkeypatch.delenv("TG_ALERTS_TOKEN", raising=False)
        monkeypatch.delenv("TG_ALERTS_CHAT_ID", raising=False)
        with pytest.raises(ConfigError):
            load(tmp_path / "ghost.toml")

    def test_env_only_is_enough(self, tmp_path, monkeypatch):
        monkeypatch.setenv("TG_ALERTS_TOKEN", "123:ENV")
        monkeypatch.setenv("TG_ALERTS_CHAT_ID", "1")
        config = load(tmp_path / "ghost.toml")  # file missing
        assert config.token == "123:ENV"

    def test_invalid_token_detected(self, tmp_path, monkeypatch):
        monkeypatch.delenv("TG_ALERTS_TOKEN", raising=False)
        monkeypatch.setenv("TG_ALERTS_CHAT_ID", "1")
        p = write_cfg(tmp_path, token="no-colon-right")
        with pytest.raises(ConfigError):
            load(p)
