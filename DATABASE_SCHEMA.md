# Database Schema Documentation

## Overview

This document provides a comprehensive overview of the PostgreSQL database schema for the Binance Trading Agent application. The database uses PostgreSQL 16.11 and consists of 4 main tables for tracking trading operations, positions, and service health.

**Database Name**: `binance_trading`  
**Database User**: `trading_user`  
**Database Type**: PostgreSQL 16.11 (Alpine)

---

## Tables Summary

| Table Name | Primary Key | Record Count | Purpose |
|------------|-------------|--------------|---------|
| `trades` | `trade_id` | 4 | Historical record of all executed trades |
| `positions` | `symbol` | 2 | Current open positions per trading symbol |
| `heartbeat` | `service_name` | 0 | Service health monitoring and status tracking |
| `alembic_version` | N/A | 1 | Database migration version control |

---

## Table Schemas

### 1. `trades` Table

**Purpose**: Stores a complete historical record of all executed trades on Binance. This table is append-only and provides an audit trail of trading activity, including profit/loss calculations.

**Primary Key**: `trade_id`

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `trade_id` | VARCHAR | NOT NULL | Unique identifier for the trade (PK) |
| `symbol` | VARCHAR | NOT NULL | Trading pair symbol (e.g., BTCUSDT, ETHUSDT) |
| `side` | VARCHAR | NOT NULL | Trade direction: BUY or SELL |
| `quantity` | DOUBLE PRECISION | NOT NULL | Amount of asset traded |
| `price` | DOUBLE PRECISION | NOT NULL | Execution price per unit |
| `fee` | DOUBLE PRECISION | NOT NULL | Trading fee charged by exchange |
| `timestamp` | TIMESTAMP | NOT NULL | When the trade was executed (UTC) |
| `order_id` | VARCHAR | NULL | Exchange order ID (unique constraint) |
| `correlation_id` | VARCHAR | NULL | Links related trades (e.g., entry/exit pairs) |
| `pnl` | DOUBLE PRECISION | NULL | Realized profit/loss for this trade |

**Indexes**:
- `trades_pkey` (PRIMARY KEY): `trade_id`
- `ix_trades_symbol`: Fast lookups by trading symbol
- `ix_trades_timestamp`: Time-based queries and sorting
- `ix_trades_symbol_timestamp`: Combined symbol + time queries
- `ix_trades_correlation_id`: Linking related trades
- `uq_trades_order_id` (UNIQUE): Ensures no duplicate order IDs

**Sample Data**:
```
symbol  | side | quantity | price |         timestamp
--------+------+----------+-------+----------------------------
BTCUSDT | BUY  |     0.01 | 50000 | 2025-12-23 05:53:20
BTCUSDT | BUY  |        1 |     1 | 2025-12-23 05:53:01
ETHUSDT | BUY  |    0.003 |  0.02 | 2025-12-19 18:09:55
ETHUSDT | BUY  |      0.2 |   100 | 2025-12-19 17:54:08
```

**Current Record Count**: 4 trades

---

### 2. `positions` Table

**Purpose**: Maintains the current state of open positions for each trading symbol. This table is updated on every trade execution and provides real-time portfolio tracking.

**Primary Key**: `symbol` (one position per trading pair)

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `symbol` | VARCHAR | NOT NULL | Trading pair symbol (PK) |
| `side` | VARCHAR | NOT NULL | Position direction: LONG or SHORT |
| `quantity` | DOUBLE PRECISION | NOT NULL | Current position size (amount of asset held) |
| `average_price` | DOUBLE PRECISION | NOT NULL | Average entry price (cost basis) |
| `current_price` | DOUBLE PRECISION | NOT NULL | Last known market price |
| `unrealized_pnl` | DOUBLE PRECISION | NOT NULL | Current profit/loss (mark-to-market) |
| `realized_pnl` | DOUBLE PRECISION | NOT NULL | Cumulative realized P&L for this symbol |
| `timestamp` | TIMESTAMP | NOT NULL | Last update time (UTC) |

**Indexes**:
- `positions_pkey` (PRIMARY KEY): `symbol`
- `ix_positions_symbol`: Fast symbol lookups

**Business Logic**:
- Each symbol can have only ONE active position (enforced by PK)
- `unrealized_pnl` is calculated as: `(current_price - average_price) * quantity`
- `realized_pnl` accumulates from closed trades
- Position is removed when fully closed (quantity = 0)

**Current Record Count**: 2 active positions

---

### 3. `heartbeat` Table

**Purpose**: Monitors health and liveness of microservices in the trading system. Each service updates its heartbeat periodically to indicate it's running properly.

**Primary Key**: `service_name`

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `service_name` | VARCHAR | NOT NULL | N/A | Service identifier (PK): api, dashboard, trading-agent |
| `last_update` | TIMESTAMP | NOT NULL | N/A | Last heartbeat update time (UTC) |
| `status` | VARCHAR | NOT NULL | 'healthy' | Service health status: healthy, degraded, unhealthy |
| `details` | JSON | NULL | N/A | Additional metadata (version, errors, metrics) |

**Indexes**:
- `heartbeat_pkey` (PRIMARY KEY): `service_name`
- `ix_heartbeat_last_update`: Find stale services
- `ix_heartbeat_status`: Query by health status

**Health Monitoring**:
- Services update every 30-60 seconds
- A service is considered stale if `last_update` > 60 seconds ago
- `details` field stores JSON with service-specific diagnostics

**Example Monitoring Query**:
```sql
-- Find unhealthy services
SELECT service_name, last_update, status, details
FROM heartbeat
WHERE last_update < NOW() - INTERVAL '60 seconds'
  OR status != 'healthy';
```

**Current Record Count**: 0 (no heartbeats yet - services may not be running)

---

### 4. `alembic_version` Table

**Purpose**: Tracks the current database schema migration version. Used by Alembic for managing schema changes.

**Structure**:
```sql
version_num VARCHAR(32) NOT NULL PRIMARY KEY
```

**Current Version**: Check with:
```sql
SELECT version_num FROM alembic_version;
```

---

## Database Relationships

```
┌─────────────┐
│   trades    │ (Historical audit log)
│             │
│ trade_id PK │
│ symbol      │────┐
│ side        │    │
│ quantity    │    │ Aggregated/calculated
│ price       │    │ to update positions
│ pnl         │    │
│ timestamp   │    │
└─────────────┘    │
                   │
                   ▼
              ┌─────────────┐
              │ positions   │ (Current portfolio state)
              │             │
              │ symbol PK   │
              │ side        │
              │ quantity    │
              │ avg_price   │
              │ current_pnl │
              └─────────────┘

┌─────────────┐
│ heartbeat   │ (Service monitoring)
│             │
│ service_name│ (Independent - tracks service health)
│ last_update │
│ status      │
└─────────────┘
```

**Notes**:
- No foreign key constraints between `trades` and `positions` (intentional for flexibility)
- `positions` is derived/calculated from `trades` table
- `heartbeat` is completely independent - used for monitoring only

---

## Connection Information

### From Host Machine (Windows)
```
Host: localhost
Port: 5432
Database: binance_trading
Username: trading_user
Password: (check .env file for POSTGRES_PASSWORD)
```

### From Docker Containers
```
Host: postgres
Port: 5432
Database: binance_trading
Username: trading_user
Password: (from environment variable)
```

### Connection URL Format
```
postgresql+psycopg2://trading_user:PASSWORD@HOST:5432/binance_trading
```

---

## Common Queries

### Portfolio Summary
```sql
SELECT 
    symbol,
    side,
    quantity,
    average_price,
    current_price,
    unrealized_pnl,
    realized_pnl,
    ROUND((unrealized_pnl / (quantity * average_price) * 100)::numeric, 2) as pnl_percent
FROM positions
ORDER BY unrealized_pnl DESC;
```

### Recent Trade Activity
```sql
SELECT 
    symbol,
    side,
    quantity,
    price,
    fee,
    pnl,
    timestamp
FROM trades
ORDER BY timestamp DESC
LIMIT 20;
```

### Trading Performance by Symbol
```sql
SELECT 
    symbol,
    COUNT(*) as trade_count,
    SUM(CASE WHEN side = 'BUY' THEN quantity ELSE 0 END) as total_bought,
    SUM(CASE WHEN side = 'SELL' THEN quantity ELSE 0 END) as total_sold,
    SUM(COALESCE(pnl, 0)) as total_pnl,
    AVG(fee) as avg_fee
FROM trades
GROUP BY symbol
ORDER BY total_pnl DESC;
```

### Service Health Check
```sql
SELECT 
    service_name,
    last_update,
    status,
    EXTRACT(EPOCH FROM (NOW() - last_update)) as seconds_since_update,
    details
FROM heartbeat
ORDER BY last_update DESC;
```

### Daily Trade Volume
```sql
SELECT 
    DATE(timestamp) as trade_date,
    symbol,
    COUNT(*) as trade_count,
    SUM(quantity * price) as total_volume,
    SUM(fee) as total_fees
FROM trades
GROUP BY DATE(timestamp), symbol
ORDER BY trade_date DESC, total_volume DESC;
```

---

## Database Maintenance

### Backup Database
```bash
docker-compose exec postgres pg_dump -U trading_user binance_trading > backup_$(date +%Y%m%d).sql
```

### Restore Database
```bash
docker-compose exec -T postgres psql -U trading_user binance_trading < backup_20251230.sql
```

### Check Database Size
```sql
SELECT 
    pg_size_pretty(pg_database_size('binance_trading')) as database_size,
    pg_size_pretty(pg_total_relation_size('trades')) as trades_size,
    pg_size_pretty(pg_total_relation_size('positions')) as positions_size;
```

### Vacuum and Analyze
```sql
VACUUM ANALYZE trades;
VACUUM ANALYZE positions;
VACUUM ANALYZE heartbeat;
```

---

## Migration History

Database migrations are managed by Alembic. Migration files are located in:
```
migrations/versions/
```

### Check Current Migration Version
```sql
SELECT version_num FROM alembic_version;
```

### Run Pending Migrations
```bash
docker-compose exec migrate alembic upgrade head
```

### View Migration History
```bash
docker-compose exec migrate alembic history
```

---

## Performance Considerations

### Index Strategy
- **`trades` table**: Heavy read operations for historical analysis
  - Indexed on `symbol`, `timestamp`, and `symbol+timestamp` for fast filtering
  - Unique index on `order_id` prevents duplicate trades
  
- **`positions` table**: Frequent updates, occasional reads
  - Primary key on `symbol` provides instant lookups
  - Small table size (one row per symbol) - no additional indexes needed

- **`heartbeat` table**: Frequent writes, periodic reads
  - Indexed on `last_update` and `status` for monitoring queries

### Connection Pooling
Default pool settings (configured in `.env`):
```
DB_POOL_SIZE=5              # Connections per service
DB_MAX_OVERFLOW=10          # Additional overflow connections
DB_POOL_TIMEOUT=30          # Seconds to wait for connection
```

### Recommendations
- For high-frequency trading: Increase `DB_POOL_SIZE` to 10-20
- Archive old `trades` records to separate table after 90 days
- Monitor `pg_stat_activity` for long-running queries
- Enable query logging for slow queries (> 1000ms)

---

## Data Retention Policy

| Table | Retention | Archival Strategy |
|-------|-----------|-------------------|
| `trades` | Indefinite | Archive to cold storage after 90 days |
| `positions` | Current only | No archival needed (derived state) |
| `heartbeat` | 24 hours | Delete records older than 24h |
| `alembic_version` | Indefinite | Never delete |

---

## Security Notes

1. **Never commit `.env` file** - Contains database credentials
2. **Use Docker secrets** in production instead of environment variables
3. **Rotate passwords** regularly (at least every 90 days)
4. **Restrict network access** - PostgreSQL port 5432 should not be exposed to public internet
5. **Enable SSL/TLS** for production connections
6. **Use read-only users** for dashboard/reporting services

---

## Troubleshooting

### Connection Issues
```bash
# Test connection from host
docker-compose exec postgres psql -U trading_user -d binance_trading -c "SELECT 1"

# Check if PostgreSQL is running
docker-compose ps postgres

# View PostgreSQL logs
docker-compose logs postgres
```

### Schema Issues
```bash
# Verify tables exist
docker-compose exec postgres psql -U trading_user -d binance_trading -c "\dt"

# Check current migration version
docker-compose exec migrate alembic current
```

### Performance Issues
```sql
-- Check for locks
SELECT * FROM pg_locks WHERE NOT granted;

-- View active connections
SELECT * FROM pg_stat_activity WHERE state = 'active';

-- Check table bloat
SELECT schemaname, tablename, 
       pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

---

## References

- **Migration Guide**: [MIGRATION_COMPLETE.md](MIGRATION_COMPLETE.md)
- **Deployment Guide**: [PRODUCTION_DEPLOYMENT.md](PRODUCTION_DEPLOYMENT.md)
- **Architecture**: [docs/DESIGN_LOG.md](docs/DESIGN_LOG.md)
- **Alembic Documentation**: https://alembic.sqlalchemy.org/
- **PostgreSQL 16 Docs**: https://www.postgresql.org/docs/16/

---

*Last Updated: December 30, 2025*  
*Database Version: PostgreSQL 16.11*  
*Schema Version: Check `alembic_version` table*
