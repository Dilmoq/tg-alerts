"""Configuration: credentials resolve from TOML file or environment variables."""

import dataclasses
import os
import pathlib
import tomllib

ENV_TOKEN = "TG_ALERTS_TOKEN"
ENV_CHAT = "TG_ALERTS_CHAT_ID"

DEFAULT_PATHS: tuple[pathlib.Path, ...] = (
    pathlib.Path.home() / ".config" / "tg-alerts" / "config.toml",
    pathlib.Path.cwd() / "tg-alerts.toml",
)

_HOWTO = (
    "Set TG_ALERTS_TOKEN / TG_ALERTS_CHAT_ID or create "
    "~/.config/tg-alerts/config.toml:\n"
    '  [telegram]\n  token = "12345:ABC"      # from @BotFather\n'
    '  chat_id = "123456789"   # via tg-alerts discover'
)


class ConfigError(Exception):
    """Raised when credentials are missing or malformed."""


@dataclasses.dataclass(frozen=True)
class Config:
    token: str
    chat_id: str
    state_path: pathlib.Path = pathlib.Path.home() / ".local" / "state" / "tg-alerts" / "state.json"

    def validate(self) -> list[str]:
        errors: list[str] = []
        if not self.token or ":" not in self.token:
            errors.append("token looks invalid (expected '<id>:<secret>' from BotFather)")
        if not self.chat_id:
            errors.append("chat_id is empty")
        return errors


def load(explicit: pathlib.Path | None = None) -> Config:
    """Build a Config: TOML file first, environment variables override."""
    token = ""
    chat = ""
    state_path = Config.state_path

    paths = (explicit,) if explicit else DEFAULT_PATHS
    for path in paths:
        if path is not None and path.is_file():
            raw = tomllib.loads(path.read_text(encoding="utf-8"))
            tg = raw.get("telegram", {})
            token = str(tg.get("token", ""))
            chat = str(tg.get("chat_id", ""))
            sp = raw.get("state_path")
            if sp:
                state_path = pathlib.Path(str(sp)).expanduser()
            break

    token = os.environ.get(ENV_TOKEN, token)
    chat = os.environ.get(ENV_CHAT, chat)

    config = Config(token=token, chat_id=chat, state_path=state_path)
    errors = config.validate()
    if errors:
        raise ConfigError("Missing credentials: " + "; ".join(errors) + "\n" + _HOWTO)
    return config
