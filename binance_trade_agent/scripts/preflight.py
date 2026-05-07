"""Deployment preflight checks for Docker/VPS services.

The checks intentionally fail fast on unsafe production defaults. They do not
validate credentials against Binance; they only validate that the service is not
starting with placeholder secrets or an ambiguous live-trading configuration.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path


PLACEHOLDER_FRAGMENTS = (
    "CHANGE_ME",
    "changeme",
    "replace_with",
    "your_",
    "example",
    "password",
)


def _load_env_file(path: str | None) -> None:
    if not path:
        return

    env_path = Path(path)
    if not env_path.exists():
        raise SystemExit(f"Preflight failed: env file not found: {env_path}")

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


def _as_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.lower() in {"true", "1", "yes", "on"}


def _looks_placeholder(value: str | None) -> bool:
    if not value:
        return True
    lowered = value.lower()
    return any(fragment.lower() in lowered for fragment in PLACEHOLDER_FRAGMENTS)


def _require_secret(errors: list[str], name: str, *, min_length: int = 16) -> None:
    value = os.getenv(name)
    if _looks_placeholder(value):
        errors.append(f"{name} must be set to a real secret, not a placeholder/default")
        return
    if len(value or "") < min_length:
        errors.append(f"{name} must be at least {min_length} characters")


def _check_database(errors: list[str]) -> None:
    database_url = os.getenv("DATABASE_URL", "")
    if not database_url.startswith("postgresql"):
        errors.append("DATABASE_URL must point at PostgreSQL for VPS deployment")
    _require_secret(errors, "POSTGRES_PASSWORD", min_length=16)


def _check_api_auth(errors: list[str]) -> None:
    auth_required = _as_bool("API_AUTH_REQUIRED", default=True)
    if not auth_required:
        errors.append("API_AUTH_REQUIRED must remain true for VPS deployment")
    _require_secret(errors, "API_AUTH_TOKEN", min_length=24)


def _check_dashboard(errors: list[str]) -> None:
    if not _as_bool("DASHBOARD_AUTH_ENABLED", default=True):
        errors.append("DASHBOARD_AUTH_ENABLED must remain true for VPS deployment")
    _require_secret(errors, "DASHBOARD_PASSWORD", min_length=16)


def _check_trading(errors: list[str]) -> None:
    demo_mode = _as_bool("DEMO_MODE", default=False)
    testnet = _as_bool("BINANCE_TESTNET", default=True)

    if not demo_mode:
        _require_secret(errors, "BINANCE_API_KEY", min_length=8)
        _require_secret(errors, "BINANCE_API_SECRET", min_length=16)

    if not testnet and not _as_bool("ALLOW_LIVE_TRADING", default=False):
        errors.append("Live Binance trading requires ALLOW_LIVE_TRADING=true")

    if not testnet and _as_bool("TESTNET_AGGRESSIVE_MODE", default=False):
        errors.append("TESTNET_AGGRESSIVE_MODE must be false for live trading")

    if not testnet and "testnet" in os.getenv("BINANCE_API_URL", "").lower():
        errors.append("BINANCE_API_URL still points at testnet while BINANCE_TESTNET=false")

    interval = int(os.getenv("TRADING_INTERVAL_SECONDS", "120"))
    if interval < 60:
        errors.append("TRADING_INTERVAL_SECONDS must be at least 60")

    symbols = [symbol.strip() for symbol in os.getenv("TRADING_SYMBOLS", "").split(",")]
    if not any(symbols):
        errors.append("TRADING_SYMBOLS must include at least one symbol")


def run_preflight(service: str) -> list[str]:
    errors: list[str] = []

    _check_database(errors)

    if service in {"api", "dashboard"}:
        _check_api_auth(errors)

    if service == "dashboard":
        _check_dashboard(errors)

    if service == "trading-agent":
        _check_trading(errors)

    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate VPS deployment environment")
    parser.add_argument(
        "--service",
        choices=("api", "dashboard", "trading-agent"),
        required=True,
        help="Service being started",
    )
    parser.add_argument("--env-file", help="Optional dotenv file to load before validation")
    args = parser.parse_args(argv)

    _load_env_file(args.env_file)
    errors = run_preflight(args.service)

    if errors:
        print(f"[PREFLIGHT] {args.service} failed deployment checks:", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        return 1

    print(f"[PREFLIGHT] {args.service} deployment checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
