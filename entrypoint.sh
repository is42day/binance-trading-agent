#!/bin/bash
# Entrypoint script for Binance Trading Agent container
# Ensures database is ready, runs migrations, then starts services

set -e

echo "[ENTRYPOINT] Starting Binance Trading Agent..."
echo "[ENTRYPOINT] Python version: $(python --version)"
echo "[ENTRYPOINT] Working directory: $(pwd)"

# Wait for PostgreSQL if DATABASE_URL is set
if [ -n "$DATABASE_URL" ]; then
    echo "[ENTRYPOINT] DATABASE_URL detected. Waiting for PostgreSQL..."
    
    # Extract host from DATABASE_URL (format: postgresql+psycopg2://user:pass@host:port/db)
    # Simple extraction: take everything between @ and first :
    DB_HOST=$(echo "$DATABASE_URL" | sed -n 's/.*@\([^:]*\).*/\1/p')
    DB_PORT=${DB_PORT:-5432}
    
    if [ -z "$DB_HOST" ]; then
        echo "[ENTRYPOINT] WARNING: Could not extract DB_HOST from DATABASE_URL"
    else
        echo "[ENTRYPOINT] Waiting for $DB_HOST:$DB_PORT..."
        
        # Wait up to 60 seconds for PostgreSQL to be ready
        COUNTER=0
        MAX_ATTEMPTS=60
        while ! nc -z "$DB_HOST" "$DB_PORT" 2>/dev/null; do
            COUNTER=$((COUNTER + 1))
            if [ $COUNTER -ge $MAX_ATTEMPTS ]; then
                echo "[ENTRYPOINT] ERROR: PostgreSQL not ready after $MAX_ATTEMPTS attempts"
                exit 1
            fi
            echo "[ENTRYPOINT] PostgreSQL not ready. Waiting... ($COUNTER/$MAX_ATTEMPTS)"
            sleep 1
        done
        
        echo "[ENTRYPOINT] PostgreSQL is ready at $DB_HOST:$DB_PORT"
    fi
    
    # Run migrations
    echo "[ENTRYPOINT] Running Alembic migrations..."
    alembic upgrade head
    
    if [ $? -eq 0 ]; then
        echo "[ENTRYPOINT] Migrations completed successfully"
    else
        echo "[ENTRYPOINT] ERROR: Migrations failed"
        exit 1
    fi
else
    echo "[ENTRYPOINT] DATABASE_URL not set. Using SQLite (local development mode)"
    echo "[ENTRYPOINT] Skipping PostgreSQL wait and migrations"
fi

# Start supervisord with the provided configuration
echo "[ENTRYPOINT] Starting supervisord..."
exec supervisord -c /app/supervisord.conf
