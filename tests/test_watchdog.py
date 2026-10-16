"""Watchdog: check command parsing and firing/recovery transitions."""

from pathlib import Path

from tg_alerts import watchdog
from tg_alerts.state import load_state, save_state, transitions


class TestRunCheck:
    def test_missing_binary(self):
        code, alerts = watchdog.run_check(["surely-missing-binary-xyz", "check"])
        assert code == 127
        assert alerts == ["servermon binary is missing (install servermon first)"]

    def test_parses_alert_lines_from_stderr(self):
        code, alerts = watchdog.run_check(
            [
                "python",
                "-c",
                "import sys; sys.stderr.write('OK: fine\\nALERT: CPU usage 90% > 80\\n')",
            ]
        )
        assert code == 0
        assert alerts == ["ALERT: CPU usage 90% > 80"]

    def test_clean_check(self):
        code, alerts = watchdog.run_check(
            ["python", "-c", "import sys; sys.stderr.write('OK: all good\\n'); sys.exit(0)"]
        )
        assert (code, alerts) == (0, [])


class TestTransitions:
    def test_firing(self):
        fired, recovered = transitions(set(), {"api down"})
        assert fired == {"api down"} and recovered == set()

    def test_recovery(self):
        fired, recovered = transitions({"api down"}, set())
        assert fired == set() and recovered == {"api down"}

    def test_steady_state(self):
        fired, recovered = transitions({"a", "b"}, {"a", "b"})
        assert fired == set() and recovered == set()


class TestStateRoundtrip:
    def test_save_then_load(self, tmp_path: Path):
        p = tmp_path / "state.json"
        save_state(p, {"disk 90%", "mem 85%"})
        assert load_state(p) == {"disk 90%", "mem 85%"}

    def test_missing_file_returns_empty(self, tmp_path: Path):
        assert load_state(tmp_path / "ghost.json") == set()


class TestCycle:
    def test_first_firing_sends_message_and_saves(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            watchdog,
            "run_check",
            lambda cmd: (1, ["ALERT: CPU usage 95% > 90%"]),
        )
        msgs, firing = watchdog.cycle(["servermon", "check"], "host1", tmp_path / "state.json")
        assert firing == {"CPU usage 95% > 90%"}
        assert len(msgs) == 1
        assert "host1" in msgs[0]
        assert "CPU usage 95%" in msgs[0]
        assert load_state(tmp_path / "state.json") == firing

    def test_recovery_message(self, tmp_path, monkeypatch):
        state = tmp_path / "state.json"
        save_state(state, {"CPU usage 95% > 90%"})
        monkeypatch.setattr(watchdog, "run_check", lambda cmd: (0, []))
        msgs, firing = watchdog.cycle(["servermon", "check"], "host1", state)
        assert firing == set()
        assert any("resolved" in m and "CPU" in m for m in msgs)

    def test_steady_state_no_messages(self, tmp_path, monkeypatch):
        state = tmp_path / "state.json"
        save_state(state, {"CPU usage 95% > 90%"})
        monkeypatch.setattr(watchdog, "run_check", lambda cmd: (1, ["ALERT: CPU usage 95% > 90%"]))
        msgs, _ = watchdog.cycle(["servermon", "check"], "host1", state)
        assert msgs == []
