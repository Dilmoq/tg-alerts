# tg-alerts — tiny Telegram alerting service

![CI](https://github.com/Dilmoq/tg-alerts/actions/workflows/ci.yml/badge.svg)
![Python](https://img.shields.io/badge/python-3.11%20%7C%203.12%20%7C%203.13-blue.svg?logo=python&logoColor=white)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![pytest](https://img.shields.io/badge/tests-24%20passed-brightgreen.svg?logo=pytest&logoColor=white)

Zero-dependency Telegram notification service: send messages from scripts or pair it
with [servermon](https://github.com/Dilmoq/servermon) to get firing/recovery alerts
for CPU/RAM/disk on your server — right in your pocket.

```
🔥 [srv1] CPU usage 95% > 90%
✅ [srv1] resolved: CPU usage 95% > 90%
```

## What it does

- `send` — arbitrary message from CLI or stdin (pipes into any script/CRON)
- `test` — verify token/chat credentials work
- `discover` — detect your `chat_id` automatically from messages you send to the bot
- `watch` — loop that runs a check command and notify **only on transitions**
  (fires once when something breaks, and once when it recovers — no spam)

Only the Python standard library is used: Telegram API is called via `urllib`.

## Install

```bash
pip install tg-alerts    # or: pipx install tg-alerts
```

From source: `git clone https://github.com/Dilmoq/tg-alerts && pip install ./tg-alerts`

## Setup in 2 minutes

1. **Create a bot**: in Telegram open `@BotFather` → `/newbot` → copy the token
2. **Message your bot once** (open the chat, press Start, send `hi`)
3. **Detect your chat_id**:
   ```bash
   export TG_ALERTS_TOKEN="123456:ABC..."
   tg-alerts discover      # prints {"chat_id": "123456789", ...}
   export TG_ALERTS_CHAT_ID="123456789"
   ```
4. **Verify**: `tg-alerts test` — you should get the message

Credentials live in env vars or `~/.config/tg-alerts/config.toml`:

```toml
[telegram]
token = "123456:ABC..."
chat_id = "123456789"
```

## Pair with servermon

```bash
tg-alerts watch --interval 60              # loop: servermon check -> Telegram
```

Deploy as a systemd service:

```bash
sudo cp examples/*.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now tg-alerts.service
```

## Messages straight from your shell

```bash
tg-alerts send "backup finished ✅"
df -h / | tg-alerts send --plain
echo "deploy done" | tg-alerts send
```

## How it works

- `client.py` — stdlib-only Telegram API client: HTML escaping, 4096-char chunking,
  retry with backoff on network errors, **no retry** on 401/403/404 (fail fast)
- `watchdog.py` — runs the check command, parses `ALERT:`-prefixed stderr lines,
  diffs against previously-firing state, renders fire/recovery messages
- `state.py` — a tiny JSON state file tracks what's currently firing
- transitions-only messaging keeps your Telegram quiet

## Design constraints

- **Zero dependencies** beyond Python stdlib — installs anywhere in seconds,
  runs in a few MB of RAM
- Credentials are read from environment or a config file; **never hardcoded**
- Tests never touch the network (mocked URL layer)

## License

MIT — see [LICENSE](LICENSE).
