"""Telegram Bot API client over urllib (no third-party dependencies)."""

from __future__ import annotations

import json
import time
import typing
from urllib import error as urlerror
from urllib import request as urlrequest

API_BASE = "https://api.telegram.org"
MAX_MESSAGE = 4096  # Telegram text message limit


class TelegramError(RuntimeError):
    """Telegram API call failed after retries."""


def escape_html(text: str) -> str:
    """Escape text for Telegram HTML parse mode."""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def chunk(text: str, size: int = MAX_MESSAGE) -> list[str]:
    """Split text into pieces under the Telegram size limit."""
    if len(text) <= size:
        return [text]
    parts: list[str] = []
    while text:
        if len(text) <= size:
            parts.append(text)
            break
        cut = text.rfind("\n", 0, size)
        if cut <= 0:
            cut = size
        parts.append(text[:cut])
        text = text[cut:].lstrip("\n")
    return parts


class TgClient:
    """Minimal synchronous client: sendMessage + getUpdates."""

    def __init__(self, token: str, timeout: float = 10.0):
        self._base = f"{API_BASE}/bot{token}"
        self._timeout = timeout

    def _call(self, method: str, payload: dict) -> typing.Any:
        data = json.dumps(payload).encode("utf-8")
        req = urlrequest.Request(
            f"{self._base}/{method}",
            data=data,
            headers={"Content-Type": "application/json"},
        )
        last_exc: Exception | None = None
        for attempt in range(3):
            try:
                with urlrequest.urlopen(req, timeout=self._timeout) as resp:
                    body = json.loads(resp.read().decode("utf-8"))
                    if body.get("ok"):
                        return body.get("result", True)
                    last_exc = TelegramError(
                        f"{method}: {body.get('description', 'unknown error')}"
                    )
            except urlerror.HTTPError as exc:
                detail = exc.read().decode("utf-8", "replace")[:200]
                last_exc = TelegramError(f"{method}: HTTP {exc.code}: {detail}")
                if exc.code in (400, 401, 403, 404):
                    raise last_exc from exc  # permanent — do not retry
            except (urlerror.URLError, TimeoutError, OSError) as exc:
                last_exc = TelegramError(f"{method}: network error: {exc}")
            if attempt < 2:
                time.sleep(2**attempt)
        raise last_exc or TelegramError(f"{method}: failed")

    def send_message(self, chat_id: str, text: str) -> None:
        """Send HTML text; splits long texts automatically."""
        for part in chunk(text):
            self._call(
                "sendMessage",
                {
                    "chat_id": chat_id,
                    "text": part,
                    "parse_mode": "HTML",
                    "disable_web_page_preview": True,
                },
            )

    def get_updates(self) -> list[dict]:
        """Return pending updates (drives `tg-alerts discover`)."""
        offset = 0
        result: list[dict] = []
        while True:
            batch = self._call("getUpdates", {"offset": offset, "timeout": 0, "limit": 100})
            if not batch:
                break
            result.extend(batch)
            ids = [u["update_id"] for u in batch]
            offset = max(ids) + 1
            if len(batch) < 100:
                break
        return result
