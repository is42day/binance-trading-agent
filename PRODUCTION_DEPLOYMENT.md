## Production Deployment Guide

This document covers deploying Binance Trading Agent in production with PostgreSQL, separate services, health checks, and monitoring.

### Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Pre-Deployment Checklist](#pre-deployment-checklist)
3. [Environment Configuration](#environment-configuration)
4. [Deployment Steps](#deployment-steps)
5. [Health Checks & Monitoring](#health-checks--monitoring)
6. [Scaling](#scaling)
7. [Troubleshooting](#troubleshooting)
8. [Secrets Management](#secrets-management)

---

## Architecture Overview

The production deployment uses a **microservices architecture** with separate containers for each component:

```
┌─────────────────────────────────────────────────────────────┐
│                      Docker Compose                         │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │  PostgreSQL  │  │    Redis     │  │  Prometheus  │      │
│  │   (16-alpine)│  │  (7.2-alpine)│  │   (latest)   │      │
│  │   Healthcheck│  │  Healthcheck │  │  Monitoring  │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│        │                │                                    │
│        └────────────────┼────────────────────┐              │
│                         │                    │              │
│  ┌──────────────┐  ┌─────────────────────────────────────┐ │
│  │   MIGRATE    │  │    TRADING SERVICES                 │ │
│  │ (one-shot)   │  │  ┌────────────────────────────────┐ │ │
│  │ • alembic    │  │  │ Trading-Agent (8081 MCP Server)│ │ │
│  │   upgrade    │  │  │ • Autonomous trading loop       │ │ │
│  │   head       │  │  │ • Heartbeat updates             │ │ │
│  │ • Exits      │  │  │ • Retry logic (transient errs)  │ │ │
│  │              │  │  └────────────────────────────────┘ │ │
│  └──────────────┘  │                                      │ │
│        │           │  ┌────────────────────────────────┐ │ │
│        │           │  │ API (8000 FastAPI)             │ │ │
│        │           │  │ • /health endpoint             │ │ │
│        │           │  │ • Portfolio data endpoints     │ │ │
│        │           │  │ • Risk status                  │ │ │
│        │           │  │ • Market prices                │ │ │
│        │           │  └────────────────────────────────┘ │ │
│        │           │                                      │ │
│        │           │  ┌────────────────────────────────┐ │ │
│        │           │  │ Dashboard (8050 Dash)          │ │ │
│        │           │  │ • Real-time UI                 │ │ │
│        │           │  │ • Trading history              │ │ │
│        │           │  │ • Log viewer                    │ │ │
│        │           │  │ • Emergency stop               │ │ │
│        │           │  └────────────────────────────────┘ │ │
│        │           │                                      │ │
│        └──────────►│ All services share:                 │ │
│                    │ • DATABASE_URL (PostgreSQL)         │ │
│                    │ • REDIS_HOST (Cache layer)          │ │
│                    │ • BINANCE_* credentials             │ │
│                    │ • LOG_LEVEL, LOG_FORMAT             │ │
│                    └────────────────────────────────────┘ │
│                                                               │
│  [Optional: Grafana (3000) + Prometheus (9090)]             │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

### Service Dependencies

```
  postgres (healthcheck)
      ↑
      └─── migrate (one-shot) ← exits after migration
            ↑
            ├─── api (depends on migrate completion)
            ├─── dashboard (depends on migrate completion)
            └─── trading-agent (depends on migrate completion)

redis (independent)
  ↑
  ├─── api
  ├─── dashboard
  └─── trading-agent
```

---

## Pre-Deployment Checklist

### System Requirements

- **Docker**: 20.10+ with Docker Compose v1.29+
- **Memory**: Minimum 2GB, recommended 4GB+
- **Disk**: 10GB+ for PostgreSQL data
- **Network**: Outbound HTTPS for Binance API
- **OS**: Linux (production), macOS/Windows with Docker Desktop (dev)

### API Credentials

- [ ] Binance API Key (testnet or live)
- [ ] Binance API Secret (testnet or live)
- [ ] Decide: testnet (safer) vs live trading

### Database

- [ ] PostgreSQL 16+ (or use Docker image: postgres:16-alpine)
- [ ] Empty database ready (Docker Compose creates automatically)
- [ ] Connection URL prepared (format: `postgresql+psycopg2://user:pass@host:5432/db`)

### Configuration Files

- [ ] `.env` file populated (copy from `.env.example`)
- [ ] `config.toml` customized (if needed)
- [ ] `docker-compose.yml` reviewed
- [ ] Volume mounts verified

---

## Environment Configuration

### .env File Setup

Copy `.env.example` to `.env` and customize:

```bash
# Binance API Configuration
BINANCE_API_KEY=your_actual_api_key
BINANCE_API_SECRET=your_actual_api_secret
BINANCE_API_URL=https://testnet.binance.vision  # or https://api.binance.com for live

# Database Configuration (PostgreSQL)
DATABASE_URL=postgresql+psycopg2://trading_user:trading_pass_CHANGE_ME@postgres:5432/binance_trading
POSTGRES_DB=binance_trading
POSTGRES_USER=trading_user
POSTGRES_PASSWORD=trading_pass_CHANGE_ME  # Change this!

# Connection Pool Settings
DB_POOL_SIZE=5                # Connections per service
DB_MAX_OVERFLOW=10            # Additional overflow connections
DB_POOL_TIMEOUT=30            # Seconds to wait for connection

# Logging Configuration
LOG_LEVEL=INFO                # DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_FORMAT=plain              # plain or json (use json in production with ELK stack)

# Optional: Monitoring
GRAFANA_PASSWORD=admin        # Change this if using monitoring profile
```

### Security Best Practices

**NEVER commit `.env` to version control:**
```bash
# .gitignore should include:
.env
.env.*.local
secrets/
```

**Use Docker secrets or external secret management for production:**
```yaml
# docker-compose.yml with secrets
version: '3.8'
services:
  postgres:
    environment:
      - POSTGRES_PASSWORD_FILE=/run/secrets/postgres_password
    secrets:
      - postgres_password

secrets:
  postgres_password:
    file: ./secrets/postgres_password.txt
```

---

## Deployment Steps

### 1. Prepare the Environment

```bash
# Clone repository
git clone https://github.com/your-org/binance-trading-agent.git
cd binance-trading-agent

# Copy and customize environment
cp .env.example .env
# Edit .env with your actual credentials

# Create logs directory
mkdir -p logs data

# Ensure correct file permissions
chmod 600 .env
```

### 2. Build Docker Image

```bash
# Build production image
docker build -t binance-trading-agent:latest .

# Verify build succeeded
docker images | grep binance-trading-agent
```

### 3. Start Services

```bash
# Start all services (including postgres)
docker-compose up -d

# Verify all services started
docker-compose ps

# Expected output:
#   NAME                 STATUS
#   binance-postgres     Up 10s (healthy)
#   binance-migrate      Exited (0)  ← One-shot, exits after migration
#   binance-api          Up 5s (healthy)
#   binance-dashboard    Up 5s (healthy)
#   binance-trading-agent Up 5s
#   binance-redis        Up 8s (healthy)
```

### 4. Verify Migrations Ran

```bash
# Check migrate service completed successfully
docker-compose logs migrate

# Expected output:
#   [MIGRATE] Running migrations...
#   [MIGRATE] INFO  [alembic.runtime.migration] Context impl PostgresqlImpl
#   [MIGRATE] INFO  [alembic.runtime.migration] Will assume transactional DDL
#   [MIGRATE] INFO  [alembic.migration] Running upgrade  -> 001_initial_orm
#   [MIGRATE] INFO  [alembic.migration] Running upgrade 001_initial_orm -> 002_add_heartbeat
#   [MIGRATE] Schema migration completed successfully

# Verify database schema exists
docker-compose exec postgres psql -U trading_user -d binance_trading -c "\dt"

# Expected output:
#   public | heartbeat | table | trading_user
#   public | positions | table | trading_user
#   public | trades    | table | trading_user
```

### 5. Verify Service Health

```bash
# API health check
curl http://localhost:8000/health

# Expected response:
# {"status":"healthy","timestamp":"2025-12-19T12:34:56","checks":{"database":"healthy","schema":"healthy"}}

# Dashboard health check
curl http://localhost:8050/

# Dashboard should load (if using curl, will show HTML)

# Trading agent logs
docker-compose logs trading-agent | head -20

# Should show trading loop starting
```

---

## Health Checks & Monitoring

### Built-in Health Checks

Each service has automatic health checks configured in docker-compose.yml:

| Service | Endpoint | Interval | Timeout | Retries |
|---------|----------|----------|---------|---------|
| postgres | `pg_isready` | 5s | 5s | 5 |
| api | `GET /health` | 10s | 5s | 3 |
| dashboard | `GET /` | 10s | 5s | 3 |
| redis | `redis-cli ping` | 5s | 3s | 5 |

### Monitoring Heartbeats

Services update a heartbeat table every N seconds:

```sql
-- Check service health status
SELECT service_name, last_update, status, details
FROM heartbeat
ORDER BY last_update DESC;

-- Find stale services (older than 60 seconds)
SELECT service_name, last_update, status
FROM heartbeat
WHERE last_update < NOW() - INTERVAL '60 seconds'
  AND status != 'unhealthy';

-- Count unhealthy services
SELECT COUNT(*) as unhealthy_count
FROM heartbeat
WHERE status = 'unhealthy';
```

### Prometheus Metrics (Optional)

Enable monitoring profile:

```bash
# Start with monitoring stack
docker-compose --profile monitoring up -d

# Access Grafana: http://localhost:3000
# Default creds: admin / admin (set GRAFANA_PASSWORD in .env)

# Prometheus scrapes metrics at http://localhost:9090
```

---

## Scaling

### Horizontal Scaling

To run multiple instances of a service:

```bash
# Scale API service to 3 instances
docker-compose up -d --scale api=3

# Docker Compose creates:
#   binance-api_1
#   binance-api_2
#   binance-api_3
#   (Use load balancer in front)

# Important: Only ONE trading-agent should run concurrently
# Multiple agents will conflict on trades
```

### Vertical Scaling

Adjust connection pooling for high load:

```bash
# In .env:
DB_POOL_SIZE=20              # Increase for more concurrent queries
DB_MAX_OVERFLOW=30           # Allow temporary overflow
DB_POOL_TIMEOUT=60           # Wait longer for connection
```

### Resource Limits

Configure Docker resource limits:

```yaml
# docker-compose.yml
services:
  postgres:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G
        reservations:
          cpus: '1'
          memory: 1G
  
  api:
    deploy:
      resources:
        limits:
          cpus: '1'
          memory: 512M
```

---

## Troubleshooting

### Service won't start

```bash
# View detailed logs
docker-compose logs -f trading-agent

# Check if port is already in use
lsof -i :8000  # Check port 8000 (API)
lsof -i :8050  # Check port 8050 (Dashboard)
lsof -i :5432  # Check port 5432 (PostgreSQL)

# Kill conflicting process
kill -9 <PID>
```

### Database migration failed

```bash
# Check migrate service logs
docker-compose logs migrate

# If migration is stuck, you may need to reset and re-run
docker-compose exec postgres psql -U trading_user -d binance_trading
# Drop tables manually if needed
# psql> DROP TABLE IF EXISTS trades, positions, heartbeat CASCADE;

# Then re-run migrations
docker-compose exec migrate alembic upgrade head
```

### API health check fails

```bash
# Check API logs
docker-compose logs api

# Test database connectivity from API container
docker-compose exec api python -c "from binance_trade_agent.core import db; session = db.get_session(); print(session.execute('SELECT 1'))"

# Verify DATABASE_URL is set
docker-compose exec api printenv | grep DATABASE_URL
```

### High memory usage

```bash
# Check container stats
docker stats

# Reduce connection pool if high
# In .env: DB_POOL_SIZE=3

# Restart services
docker-compose restart
```

### Trading agent not executing trades

```bash
# Check trading loop logs
docker-compose logs trading-agent | grep -i "trade\|error"

# Verify Binance credentials are set
docker-compose exec trading-agent printenv | grep BINANCE

# Check portfolio manager state
docker-compose exec api python -c "from binance_trade_agent.core.portfolio_manager import PortfolioManager; pm = PortfolioManager(); print(pm.get_portfolio_stats())"
```

---

## Secrets Management

### Production-Grade Secrets

For production deployments, never use .env files. Use one of:

#### Docker Secrets (Swarm Mode)

```bash
# Create secrets
echo "trading_pass_ACTUAL_PASSWORD" | docker secret create postgres_password -
echo "your-actual-api-key" | docker secret create binance_api_key -

# Reference in compose
version: '3.8'
services:
  postgres:
    environment:
      POSTGRES_PASSWORD_FILE: /run/secrets/postgres_password
    secrets:
      - postgres_password
```

#### Kubernetes Secrets

```bash
kubectl create secret generic binance-credentials \
  --from-literal=binance_api_key=YOUR_KEY \
  --from-literal=binance_api_secret=YOUR_SECRET

# Reference in deployment
env:
  - name: BINANCE_API_KEY
    valueFrom:
      secretKeyRef:
        name: binance-credentials
        key: binance_api_key
```

#### HashiCorp Vault

```bash
# Store secret
vault kv put secret/binance-trading \
  binance_api_key=YOUR_KEY \
  binance_api_secret=YOUR_SECRET

# Agent retrieves at runtime using Vault client
```

---

## Maintenance & Operations

### Database Backups

```bash
# Manual backup
docker-compose exec postgres pg_dump -U trading_user binance_trading > backup_$(date +%Y%m%d).sql

# Automated backup (cron job)
0 2 * * * docker-compose exec postgres pg_dump -U trading_user binance_trading > /backups/binance_$(date +\%Y\%m\%d).sql

# Restore from backup
docker-compose exec -T postgres psql -U trading_user binance_trading < backup_20251219.sql
```

### Log Rotation

Logs are output to stdout (12-factor app). Docker handles rotation:

```bash
# Configure Docker daemon for log rotation
# /etc/docker/daemon.json
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  }
}
```

### Monitoring Checklist

Daily:
- [ ] All services showing healthy in `docker-compose ps`
- [ ] No error logs in trading-agent
- [ ] API /health returns 200 OK
- [ ] Heartbeats updated within last 60 seconds

Weekly:
- [ ] Database size is reasonable
- [ ] Connection pool utilization reasonable
- [ ] No memory leaks (container memory stable)
- [ ] Trades executing successfully

---

## Support & References

- **Alembic Migrations**: `MIGRATION_COMPLETE.md`
- **Architecture Details**: `docs/DESIGN_LOG.md`
- **API Endpoints**: `binance_trade_agent/api/api.py`
- **Troubleshooting**: See logs at `/app/logs/`
