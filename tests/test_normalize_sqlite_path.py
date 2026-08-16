"""
Regression coverage for normalize_sqlite_path outside the Docker container.

Docker services hardcode DB paths like "/app/data/web_portfolio.db"
throughout the codebase (TradeExecutionAgent, AutonomousTradingLoop, etc.).
Outside the container — a bare CI runner, a local dev checkout — "/app"
doesn't exist and isn't writable; trying to create it raises PermissionError
at the filesystem root. This previously only remapped on Windows
(os.name == "nt"), so it silently broke every non-Windows environment
without a real /app, including GitHub Actions runners once CI actually
reached the test-execution step (see the PR that reached this fix).
"""

from pathlib import Path

from binance_trade_agent.core import db


def test_app_path_remapped_when_app_dir_does_not_exist(monkeypatch, tmp_path):
    monkeypatch.setattr(db.os.path, "isdir", lambda path: False)
    monkeypatch.chdir(tmp_path)

    result = db.normalize_sqlite_path("/app/data/web_portfolio.db")

    assert not result.startswith("/app")
    assert Path(result).is_relative_to(tmp_path)
    assert Path(result).parent.is_dir()


def test_app_path_left_alone_when_app_dir_exists(monkeypatch):
    monkeypatch.setattr(db.os.path, "isdir", lambda path: path == "/app")
    monkeypatch.setattr(Path, "mkdir", lambda self, **kwargs: None)

    result = db.normalize_sqlite_path("/app/data/web_portfolio.db")

    assert result == "/app/data/web_portfolio.db"


def test_relative_path_resolved_against_cwd(monkeypatch, tmp_path):
    monkeypatch.setattr(db.os.path, "isdir", lambda path: False)
    monkeypatch.chdir(tmp_path)

    result = db.normalize_sqlite_path("data/portfolio.db")

    assert Path(result) == tmp_path / "data" / "portfolio.db"
