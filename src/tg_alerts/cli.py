"""Command-line interface for tg-alerts.

Commands:
    send      send an arbitrary message (arguments or stdin pipe)
    test      verify credentials by sending a test message
    discover  detect your chat_id from recent messages to the bot
    watch     loop: run the check command, notify on firing/recovery

Credentials come from TG_ALERTS_TOKEN / TG_ALERTS_CHAT_ID or TOML config.
"""

from __future__ import annotations

import argparse
import json
import socket
import sys
import time

from . import __version__
from .client import TelegramError, TgClient, escape_html
from .config import ConfigError, load
from .watchdog import cycle

DEFAULT_CHECK = ["servermon", "check"]


def _build_client():
    """Return (config, client) or exit(2) with a helpful message."""
    try:
        config = load()
    except ConfigError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc
    return config, TgClient(config.token)


def cmd_send(args: argparse.Namespace) -> int:
    config, client = _build_client()
    if args.text:
        text = " ".join(str(t) for t in args.text)
    elif not sys.stdin.isatty():
        text = sys.stdin.read().strip()
    else:
        print("error: no message given (pass as arguments or pipe into stdin)", file=sys.stderr)
        return 2
    if not text:
        print("error: empty message", file=sys.stderr)
        return 2
    body = text if args.plain else escape_html(text)
    client.send_message(config.chat_id, body)
    return 0


def cmd_test() -> int:
    config, client = _build_client()
    host = escape_html(socket.gethostname())
    try:
        client.send_message(config.chat_id, f"✅ <b>tg-alerts</b> works on <b>{host}</b>")
    except TelegramError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print("Test message sent successfully.")
    return 0


def cmd_discover() -> int:
    _, client = _build_client()
    try:
        updates = client.get_updates()
    except TelegramError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    chats: dict[int, dict] = {}
    for update in updates:
        msg = update.get("message") or update.get("edited_message")
        if not msg:
            continue
        chat = msg.get("chat", {})
        chats[chat.get("id", 0)] = chat
    if not chats:
        print(
            "No messages found yet. Open your bot in Telegram and send it any text "
            "(press Start, tap a button or just write 'hi'), then run discover again.",
            file=sys.stderr,
        )
        return 1
    chat = chats[max(chats)]
    print(
        json.dumps(
            {
                "chat_id": chat.get("id"),
                "first_name": chat.get("first_name"),
                "username": chat.get("username"),
            },
            ensure_ascii=False,
        )
    )
    return 0


def cmd_watch(args: argparse.Namespace) -> int:
    config, client = _build_client()
    host = escape_html(socket.gethostname())
    command = args.command or DEFAULT_CHECK
    print(f"watching: {' '.join(command)} every {args.interval}s -> chat {config.chat_id}")
    try:
        while True:
            messages, _firing = cycle(command, host, config.state_path)
            for message in messages:
                try:
                    client.send_message(config.chat_id, message)
                except TelegramError as exc:
                    print(f"send failed: {exc}", file=sys.stderr)
            time.sleep(max(args.interval, 1))
    except KeyboardInterrupt:
        print("\nStopped.")
        return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="tg-alerts",
        description="Tiny Telegram alerting service with firing/recovery transitions.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    p_send = sub.add_parser("send", help="send a message (arguments or stdin)")
    p_send.add_argument("--plain", action="store_true", help="disable HTML parsing")
    p_send.add_argument("text", nargs="*")
    p_send.set_defaults(func=cmd_send)

    p_test = sub.add_parser("test", help="send a test message")
    p_test.set_defaults(func=lambda _a: cmd_test())

    p_disc = sub.add_parser("discover", help="detect chat_id from recent messages")
    p_disc.set_defaults(func=lambda _a: cmd_discover())

    p_watch = sub.add_parser("watch", help="loop: check + notify on transitions")
    p_watch.add_argument("--interval", type=int, default=60, metavar="SEC")
    p_watch.add_argument("command", nargs="*", help="check command (default: servermon check)")
    p_watch.set_defaults(func=cmd_watch)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args) or 0)


if __name__ == "__main__":
    raise SystemExit(main())
