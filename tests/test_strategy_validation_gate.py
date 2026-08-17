"""
Tests for the Strategy Validation Gate (Priority 4 — Tasks 4.2–4.3).

Verifies:
- Missing gate file → HOLD ("gate_missing")
- Stale gate file → HOLD ("gate_stale")
- Symbol not in gate → HOLD ("symbol_not_in_gate")
- Negative daily_eur → HOLD ("negative_daily_eur")
- Drawdown exceeded → HOLD ("drawdown_exceeded")
- Positive, fresh gate → cleared=True
- build_gate_artifact() produces correct pass/fail per symbol
"""

import json
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from binance_trade_agent.core.strategy_validation_gate import ValidationGate
from binance_trade_agent.scripts.micro_strategy_validator import build_gate_artifact

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_gate(directory: Path, symbols: dict, generated_at: str = None, ttl: int = 86400) -> Path:
    """Write a gate artifact JSON and return the path."""
    if generated_at is None:
        generated_at = datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    artifact = {
        "generated_at": generated_at,
        "ttl_seconds": ttl,
        "gate_strategy": "micro_grid",
        "max_drawdown_threshold_pct": 10.0,
        "assumptions": {},
        "symbols": symbols,
        "overall_pass": all(s.get("gate_pass") for s in symbols.values()),
    }
    gate_file = directory / "latest.json"
    gate_file.write_text(json.dumps(artifact), encoding="utf-8")
    return gate_file


@pytest.fixture()
def gate_dir():
    """Provide a temporary directory using Python's tempfile module."""
    with tempfile.TemporaryDirectory() as d:
        yield Path(d)


def _pass_entry(daily_eur=5.0, max_dd=2.0):
    return {
        "gate_pass": True,
        "gate_reason": "positive_after_fees",
        "strategy": "micro_grid",
        "daily_eur": daily_eur,
        "max_drawdown_pct": max_dd,
        "trades": 42,
        "win_rate": 0.6,
    }


def _fail_entry(reason="negative_daily_eur"):
    return {
        "gate_pass": False,
        "gate_reason": reason,
        "strategy": "micro_grid",
        "daily_eur": -1.0,
        "max_drawdown_pct": 5.0,
        "trades": 10,
        "win_rate": 0.4,
    }


# ---------------------------------------------------------------------------
# ValidationGate.check() tests
# ---------------------------------------------------------------------------


class TestValidationGateMissing:
    def test_missing_file_returns_gate_missing(self, gate_dir):
        gate = ValidationGate(str(gate_dir / "nonexistent.json"))
        result = gate.check("BTCUSDT")
        assert not result.cleared
        assert result.reason == "gate_missing"
        assert result.age_seconds is None


class TestValidationGateStale:
    def test_stale_gate_returns_gate_stale(self, gate_dir):
        # generated 2 hours ago, TTL 3600 seconds (1 hour)
        old_time = (datetime.now(tz=timezone.utc) - timedelta(hours=2)).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )
        gate_file = _write_gate(
            gate_dir,
            symbols={"BTCUSDT": _pass_entry()},
            generated_at=old_time,
            ttl=3600,
        )
        gate = ValidationGate(str(gate_file))
        result = gate.check("BTCUSDT")
        assert not result.cleared
        assert result.reason == "gate_stale"
        assert result.age_seconds is not None
        assert result.age_seconds > 3600

    def test_fresh_gate_not_stale(self, gate_dir):
        gate_file = _write_gate(gate_dir, symbols={"BTCUSDT": _pass_entry()}, ttl=86400)
        gate = ValidationGate(str(gate_file))
        result = gate.check("BTCUSDT")
        assert result.cleared


class TestValidationGateSymbolAbsent:
    def test_missing_symbol_returns_symbol_not_in_gate(self, gate_dir):
        gate_file = _write_gate(gate_dir, symbols={"ETHUSDT": _pass_entry()})
        gate = ValidationGate(str(gate_file))
        result = gate.check("BTCUSDT")
        assert not result.cleared
        assert result.reason == "symbol_not_in_gate"

    def test_present_symbol_passes(self, gate_dir):
        gate_file = _write_gate(gate_dir, symbols={"BTCUSDT": _pass_entry()})
        gate = ValidationGate(str(gate_file))
        result = gate.check("BTCUSDT")
        assert result.cleared


class TestValidationGateNegativeEUR:
    def test_negative_daily_eur_blocks(self, gate_dir):
        gate_file = _write_gate(gate_dir, symbols={"BTCUSDT": _fail_entry("negative_daily_eur")})
        gate = ValidationGate(str(gate_file))
        result = gate.check("BTCUSDT")
        assert not result.cleared
        assert result.reason == "negative_daily_eur"


class TestValidationGateDrawdown:
    def test_drawdown_exceeded_blocks(self, gate_dir):
        gate_file = _write_gate(gate_dir, symbols={"BTCUSDT": _fail_entry("drawdown_exceeded")})
        gate = ValidationGate(str(gate_file))
        result = gate.check("BTCUSDT")
        assert not result.cleared
        assert result.reason == "drawdown_exceeded"


class TestValidationGatePositive:
    def test_cleared_result_has_gate_data(self, gate_dir):
        entry = _pass_entry(daily_eur=7.5, max_dd=3.2)
        gate_file = _write_gate(gate_dir, symbols={"BTCUSDT": entry})
        gate = ValidationGate(str(gate_file))
        result = gate.check("BTCUSDT")
        assert result.cleared
        assert result.reason is None
        assert result.gate_data is not None
        assert result.gate_data["daily_eur"] == 7.5

    def test_symbol_normalised_to_upper(self, gate_dir):
        gate_file = _write_gate(gate_dir, symbols={"BTCUSDT": _pass_entry()})
        gate = ValidationGate(str(gate_file))
        result = gate.check("btcusdt")
        assert result.cleared


# ---------------------------------------------------------------------------
# build_gate_artifact() tests
# ---------------------------------------------------------------------------


class TestBuildGateArtifact:
    def _fake_validation_output(self):
        return {
            "assumptions": {
                "symbols": ["BTCUSDT", "ETHUSDT"],
                "interval": "1m",
                "days": 7,
                "capital": 2500.0,
                "fee_rate": 0.001,
                "slippage_rate": 0.0002,
            },
            "results": {
                "BTCUSDT": {
                    "micro_grid": {
                        "final": 2550.0,
                        "pnl": 50.0,
                        "daily_eur": 7.14,
                        "trades": 35,
                        "win_rate": 0.63,
                        "max_drawdown_pct": 3.2,
                        "days": 7.0,
                    }
                },
                "ETHUSDT": {
                    "micro_grid": {
                        "final": 2490.0,
                        "pnl": -10.0,
                        "daily_eur": -1.43,
                        "trades": 12,
                        "win_rate": 0.42,
                        "max_drawdown_pct": 8.1,
                        "days": 7.0,
                    }
                },
            },
        }

    def test_positive_symbol_gets_gate_pass(self):
        artifact = build_gate_artifact(self._fake_validation_output(), "micro_grid")
        assert artifact["symbols"]["BTCUSDT"]["gate_pass"] is True
        assert artifact["symbols"]["BTCUSDT"]["gate_reason"] == "positive_after_fees"

    def test_negative_eur_symbol_fails_gate(self):
        artifact = build_gate_artifact(self._fake_validation_output(), "micro_grid")
        assert artifact["symbols"]["ETHUSDT"]["gate_pass"] is False
        assert artifact["symbols"]["ETHUSDT"]["gate_reason"] == "negative_daily_eur"

    def test_overall_pass_false_when_any_symbol_fails(self):
        artifact = build_gate_artifact(self._fake_validation_output(), "micro_grid")
        assert artifact["overall_pass"] is False

    def test_overall_pass_true_when_all_symbols_pass(self):
        output = self._fake_validation_output()
        # Make ETHUSDT also positive
        output["results"]["ETHUSDT"]["micro_grid"]["daily_eur"] = 3.0
        artifact = build_gate_artifact(output, "micro_grid")
        assert artifact["overall_pass"] is True

    def test_drawdown_exceeds_threshold_fails_gate(self):
        output = self._fake_validation_output()
        output["results"]["BTCUSDT"]["micro_grid"]["max_drawdown_pct"] = 15.0
        artifact = build_gate_artifact(output, "micro_grid", max_drawdown_threshold_pct=10.0)
        assert artifact["symbols"]["BTCUSDT"]["gate_pass"] is False
        assert artifact["symbols"]["BTCUSDT"]["gate_reason"] == "drawdown_exceeded"

    def test_artifact_contains_generated_at_and_ttl(self):
        artifact = build_gate_artifact(
            self._fake_validation_output(), "micro_grid", ttl_seconds=3600
        )
        assert "generated_at" in artifact
        assert artifact["ttl_seconds"] == 3600

    def test_missing_strategy_fails_gate(self):
        output = self._fake_validation_output()
        del output["results"]["BTCUSDT"]["micro_grid"]
        artifact = build_gate_artifact(output, "micro_grid")
        assert artifact["symbols"]["BTCUSDT"]["gate_pass"] is False
        assert artifact["symbols"]["BTCUSDT"]["gate_reason"] == "strategy_missing"
