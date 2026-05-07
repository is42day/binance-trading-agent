# VPS Deployment Runbook

This runbook is for a single Linux VPS running the full stack with Docker Compose:
PostgreSQL, Redis, FastAPI, Dash dashboard, and the autonomous trading agent.

## 1. Server Prerequisites

- Docker Engine and Docker Compose plugin installed.
- A non-root deploy user in the `docker` group.
- Firewall open only for SSH and the dashboard port you choose.
- At least 2 vCPU, 2 GB RAM, and persistent disk space for PostgreSQL backups.

Recommended firewall posture:

```bash
sudo ufw allow OpenSSH
sudo ufw allow 8050/tcp
sudo ufw enable
```

PostgreSQL, Redis, API, and MCP are bound internally or to localhost by default.

## 2. Prepare Environment

```bash
cp .env.example .env
```

Set real values for these fields before starting:

```bash
POSTGRES_PASSWORD=...
API_AUTH_TOKEN=...
DASHBOARD_PASSWORD=...
BINANCE_API_KEY=...
BINANCE_API_SECRET=...
```

Keep testnet enabled until you have watched the dashboard through multiple full trading sessions:

```bash
BINANCE_TESTNET=true
ALLOW_LIVE_TRADING=false
BINANCE_API_URL=https://testnet.binance.vision
```

For live trading, flip all three intentionally:

```bash
BINANCE_TESTNET=false
ALLOW_LIVE_TRADING=true
BINANCE_API_URL=https://api.binance.com
```

## 3. Preflight

Run all service checks locally on the VPS:

```bash
make preflight
```

The Docker services also run the same preflight during startup and will refuse
unsafe defaults such as placeholder passwords, disabled API auth, or live trading
without `ALLOW_LIVE_TRADING=true`.

## 4. Start The Stack

```bash
docker compose up -d --build
docker compose ps
```

Open:

```text
http://<your-vps-ip>:8050
```

Use `DASHBOARD_USERNAME` and `DASHBOARD_PASSWORD` from `.env`.

## 5. Operations

Follow logs:

```bash
docker compose logs -f --tail=200 api dashboard trading-agent
```

Check health:

```bash
curl -fsS http://127.0.0.1:8000/health
curl -fsS http://127.0.0.1:8050/health
```

Emergency stop is persisted in the shared database when
`RISK_SHARED_STATE_ENABLED=true`, so API, dashboard, and trading-agent processes
read the same control flag.

## 6. Test Runs

Run a paper smoke test without real orders:

```bash
make paper-smoke
```

Run a testnet connectivity and reconciliation check:

```bash
make testnet-smoke
```

Submit one tiny testnet order only after confirming the `.env` is testnet-only:

```bash
make testnet-order
```

## 7. Backups

Create a database backup:

```bash
sh scripts/backup_postgres.sh
```

Backups are written to `./backups` by default. Move them off the VPS regularly.

Restore a backup:

```bash
sh scripts/restore_postgres.sh backups/binance_trading_YYYYMMDDTHHMMSSZ.dump
```

## 8. Updates

Before pulling new code:

```bash
sh scripts/backup_postgres.sh
docker compose down
```

After updating the repo:

```bash
make preflight
docker compose up -d --build
docker compose ps
```

## 9. Production Notes

- Keep Binance API keys restricted by IP when possible.
- Do not expose PostgreSQL or Redis to the public internet.
- Keep `TESTNET_AGGRESSIVE_MODE=false` outside short testnet-only experiments.
- Start with small `TRADING_SYMBOLS` and conservative quantities.
- Watch dashboard P&L, drawdown, trade count, and recent rejected orders before scaling.
