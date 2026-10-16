"""Watch cycle: run the check command, diff state, emit messages."""

from __future__ import annotations

import subprocess

from .state import load_state, save_state, transitions


def run_check(command: list[str]) -> tuple[int, list[str]]:
    """Run the check command and return (exit_code, alert_lines).

    Alert lines are lines starting with "ALERT:" on stderr.
    Missing binary -> (127, ["servermon binary is missing"]).
    """
    try:
        proc = subprocess.run(command, capture_output=True, text=True, timeout=90)
    except FileNotFoundError:
        return 127, ["servermon binary is missing (install servermon first)"]
    except subprocess.TimeoutExpired:
        return 124, ["check command timed out"]
    alerts = [line for line in proc.stderr.splitlines() if line.startswith("ALERT:")]
    return proc.returncode, alerts


def render_message(host: str, fired: set[str], recovered: set[str], code: int) -> tuple[str, str]:
    """Build (fire_message, recovery_message); either may be empty."""
    prefix = f"🔥 <b>{host}</b>"
    fire_lines = [f"{prefix}] {key}" for key in fired]
    if code in (127, 124):
        fire_lines = [f"{prefix}] monitoring issue: {key}" for key in fired]
    recover_lines = [f"✅ <b>{host}</b> resolved: {key}" for key in recovered]
    return "\n".join(fire_lines), "\n".join(recover_lines)


def cycle(command: list[str], host: str, state_path) -> tuple[list[str], set[str]]:
    """Run one watch cycle: returns (messages_to_send, current_firing) and
    persists state when it changed."""
    code, alerts = run_check(command)
    now = {a.split("ALERT: ", 1)[-1] for a in alerts}
    prev = load_state(state_path)
    fired, recovered = transitions(prev, now)
    if fired or recovered:
        save_state(state_path, now)
    fire_msg, recover_msg = render_message(host, fired, recovered, code)
    return [m for m in (fire_msg, recover_msg) if m], now
