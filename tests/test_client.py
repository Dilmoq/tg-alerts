"""Client tests with mocked Telegram API (no network)."""

import io
import json

import pytest

from tg_alerts.client import TelegramError, TgClient, chunk, escape_html


class FakeResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class TestHelpers:
    def test_escape_html(self):
        assert escape_html("<b>x</b> & ok") == "&lt;b&gt;x&lt;/b&gt; &amp; ok"

    def test_chunk_short_single(self):
        assert chunk("hello") == ["hello"]

    def test_chunk_respects_newlines(self):
        text = "part1\n" * 1000
        parts = chunk(text, size=100)
        assert all(len(p) <= 100 for p in parts)
        assert "".join(parts).replace("\n", "").startswith("part1part1")

    def test_chunk_long_no_newlines(self):
        text = "x" * 10_000
        parts = chunk(text, size=4096)
        assert sum(len(p) for p in parts) == 10_000
        assert all(len(p) <= 4096 for p in parts)


def make_urlopen(calls: list, response: dict = None, status: int = 200):
    def fake(req, timeout=None):  # noqa: ARG001
        calls.append(json.loads(req.data.decode("utf-8")))
        if status != 200:
            from urllib.error import HTTPError

            raise HTTPError(req.full_url, status, "err", None, FakeResponse(b"{}"))
        return FakeResponse(json.dumps({"ok": True, "result": response or []}).encode("utf-8"))

    return fake


class TestTgClient:
    def test_send_message_builds_payload(self, monkeypatch):
        calls: list = []
        monkeypatch.setattr("tg_alerts.client.urlrequest.urlopen", make_urlopen(calls))
        c = TgClient("1:realtoken")
        c.send_message("42", "hi <b>there</b>")
        assert calls[0]["chat_id"] == "42"
        assert calls[0]["text"] == "hi <b>there</b>"
        assert calls[0]["parse_mode"] == "HTML"

    def test_send_message_splits_long_text(self, monkeypatch):
        calls: list = []
        monkeypatch.setattr("tg_alerts.client.urlrequest.urlopen", make_urlopen(calls))
        c = TgClient("1:realtoken")
        c.send_message("42", "y" * 5000)
        assert len(calls) == 2

    def test_http_401_raises_immediately(self, monkeypatch):
        calls: list = []
        monkeypatch.setattr("tg_alerts.client.urlrequest.urlopen", make_urlopen(calls, status=401))
        with pytest.raises(TelegramError):
            TgClient("bad:token").send_message("42", "x")
        assert len(calls) == 1  # no retries on permanent errors
