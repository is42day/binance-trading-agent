#!/usr/bin/env sh
set -eu

if [ "$#" -ne 1 ]; then
  echo "Usage: $0 <backup.dump>" >&2
  exit 2
fi

BACKUP_FILE="$1"
POSTGRES_DB="${POSTGRES_DB:-binance_trading}"
POSTGRES_USER="${POSTGRES_USER:-trading_user}"

if [ ! -f "$BACKUP_FILE" ]; then
  echo "[RESTORE] Backup file not found: ${BACKUP_FILE}" >&2
  exit 1
fi

echo "[RESTORE] Restoring ${BACKUP_FILE} into ${POSTGRES_DB}"
echo "[RESTORE] This will clean existing database objects before restore."

docker compose exec -T postgres pg_restore \
  --clean \
  --if-exists \
  --no-owner \
  --no-acl \
  -U "$POSTGRES_USER" \
  -d "$POSTGRES_DB" < "$BACKUP_FILE"

echo "[RESTORE] Done"
