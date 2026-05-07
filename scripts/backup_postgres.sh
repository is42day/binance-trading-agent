#!/usr/bin/env sh
set -eu

BACKUP_DIR="${BACKUP_DIR:-./backups}"
TIMESTAMP="$(date -u +%Y%m%dT%H%M%SZ)"
POSTGRES_DB="${POSTGRES_DB:-binance_trading}"
POSTGRES_USER="${POSTGRES_USER:-trading_user}"
OUT_FILE="${BACKUP_DIR}/${POSTGRES_DB}_${TIMESTAMP}.dump"

mkdir -p "$BACKUP_DIR"

echo "[BACKUP] Creating PostgreSQL backup: ${OUT_FILE}"
docker compose exec -T postgres pg_dump \
  --format=custom \
  --no-owner \
  --no-acl \
  -U "$POSTGRES_USER" \
  "$POSTGRES_DB" > "$OUT_FILE"

echo "[BACKUP] Done: ${OUT_FILE}"
