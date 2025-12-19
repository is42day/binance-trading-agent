# Makefile for Binance Trading Agent (Docker workflow)

IMAGE_NAME=binance-trading-agent:latest
ENV_FILE=.env
DOCKER_IMAGE=binance-trading-agent:latest

build:
	docker build -t $(DOCKER_IMAGE) . -q

start: build
	-docker rm api dashboard trading-agent -f 2>nul
	docker run -d -p 8000:8000 --env-file $(ENV_FILE) -v "$(CURDIR)/data:/app/data" --name api $(DOCKER_IMAGE) python -m binance_trade_agent.api.api
	docker run -d -p 8050:8050 --env-file $(ENV_FILE) --name dashboard $(DOCKER_IMAGE) python binance_trade_agent/dashboard/run.py
	docker run -d --env-file $(ENV_FILE) -v "$(CURDIR)/logs:/app/logs" -v "$(CURDIR)/data:/app/data" --name trading-agent $(DOCKER_IMAGE) python start_auto_trading.py --strategy combined --symbols BTCUSDT --interval 60
	@echo "✅ System started!"
	@echo "   Dashboard: http://localhost:8050"
	@echo "   API: http://localhost:8000"

run:
	docker run -d --env-file $(ENV_FILE) -p 8000:8000 -p 8050:8050 $(DOCKER_IMAGE)

ps:
	docker ps

ifeq ($(OS),Windows_NT)

stop:
	@powershell -NoProfile -Command "docker stop api dashboard trading-agent 2>$$null; Write-Host 'Stopped all services'"

rm:
	@powershell -NoProfile -Command "$$ids = (docker ps -a -q --filter ancestor=$(DOCKER_IMAGE)); if ($$ids) { $$ids | ForEach-Object { docker rm $_ } } else { Write-Host 'No containers to remove for $(DOCKER_IMAGE)' }"

attach:
	@powershell -NoProfile -Command "$$id = (docker ps -q --filter ancestor=$(IMAGE_NAME) | Select-Object -First 1); if ($$id) { docker exec -it $$id /bin/bash } else { Write-Host 'No running container found for $(IMAGE_NAME)' }"

logs:
	@powershell -NoProfile -Command "$$id = (docker ps -q --filter ancestor=$(IMAGE_NAME) | Select-Object -First 1); if ($$id) { docker logs --tail 200 $$id } else { Write-Host 'No running container for $(IMAGE_NAME)' }"

# Execute package modules inside running container (uses python -m to preserve package context)

exec-cli:
	@powershell -NoProfile -Command "$$id = (docker ps -q --filter ancestor=$(IMAGE_NAME) | Select-Object -First 1); if ($$id) { docker exec -it $$id /bin/bash -lc 'cd /app/data && /opt/venv/bin/python -m binance_trade_agent.cli' } else { Write-Host 'No running container found for $(IMAGE_NAME)' }"

exec-mcp:
	@powershell -NoProfile -Command "$$id = (docker ps -q --filter ancestor=$(IMAGE_NAME) | Select-Object -First 1); if ($$id) { docker exec -it $$id /bin/bash -lc '/opt/venv/bin/python -m binance_trade_agent.mcp_server' } else { Write-Host 'No running container found for $(IMAGE_NAME)' }"

else

stop:
	@docker stop api dashboard trading-agent 2>/dev/null || true; echo "Stopped all services"

rm:
	@IDS_ALL=$$(docker ps -a -q --filter ancestor=$(DOCKER_IMAGE)); \
	if [ -n "$$IDS_ALL" ]; then \
		docker rm $$IDS_ALL || true; \
	else \
		echo "No containers to remove for $(DOCKER_IMAGE)"; \
	fi

attach:
	@id=$$(docker ps -q --filter ancestor=$(IMAGE_NAME) | head -n 1); \
	if [ -n "$$id" ]; then \
		docker exec -it $$id /bin/bash; \
	else \
		echo "No running container found for $(IMAGE_NAME)"; \
	fi

logs:
	@id=$$(docker ps -q --filter ancestor=$(IMAGE_NAME) | head -n 1); \
	if [ -n "$$id" ]; then \
		docker logs --tail 200 $$id; \
	else \
		echo "No running container for $(IMAGE_NAME)"; \
	fi

endif

rebuild: stop rm build run

# Development & Testing Commands (run inside container)
lint:
	docker run --rm -v "$(CURDIR):/app" -w /app $(DOCKER_IMAGE) ruff check binance_trade_agent tests/

format:
	docker run --rm -v "$(CURDIR):/app" -w /app $(DOCKER_IMAGE) black . --exclude="venv|.venv|migrations"

format-check:
	docker run --rm -v "$(CURDIR):/app" -w /app $(DOCKER_IMAGE) black . --check --exclude="venv|.venv|migrations"

test:
	docker run --rm -v "$(CURDIR):/app" -w /app -e DB_PATH=/tmp/test_portfolio.db $(DOCKER_IMAGE) pytest -v

test-cov:
	docker run --rm -v "$(CURDIR):/app" -w /app -e DB_PATH=/tmp/test_portfolio.db $(DOCKER_IMAGE) pytest --cov=binance_trade_agent tests/

isort:
	docker run --rm -v "$(CURDIR):/app" -w /app $(DOCKER_IMAGE) isort binance_trade_agent tests/ --profile black

clean:
	docker system prune -f

# Database Management (PostgreSQL migration targets)
db-up:
	@echo "🚀 Starting PostgreSQL..."
	docker-compose up -d postgres
	@echo "⏳ Waiting for PostgreSQL to be healthy..."
	@timeout 30 sh -c 'until docker-compose exec -T postgres pg_isready -U trading_user -d binance_trading; do sleep 1; done' || echo "Timeout waiting for PostgreSQL"
	@echo "✅ PostgreSQL is ready"

db-down:
	@echo "🛑 Stopping PostgreSQL..."
	docker-compose stop postgres
	@echo "✅ PostgreSQL stopped"

migrate:
	@echo "🔄 Running database migrations..."
	alembic upgrade head
	@echo "✅ Migrations complete"

migrate-sqlite:
	@echo "🔄 Migrating data from SQLite to PostgreSQL..."
	@echo "⚠️  Make sure PostgreSQL is running (make db-up) and migrations are applied (make migrate)"
	python -m binance_trade_agent.scripts.migrate_sqlite_to_postgres
	@echo "✅ Migration complete"
	docker run --rm -v "$(CURDIR):/app" -w /app $(DOCKER_IMAGE) sh -c "find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true && find . -type f -name '*.pyc' -delete 2>/dev/null || true && rm -rf .pytest_cache .mypy_cache 2>/dev/null || true"

logs-api:
	docker logs -f api

logs-dashboard:
	docker logs -f dashboard

logs-trading:
	docker logs -f trading-agent

.PHONY: build start stop rm ps logs attach rebuild lint format format-check test test-cov isort clean logs-api logs-dashboard logs-trading

# Usage:
#   make build          # Build the Docker image
#   make start          # Build and start all three services (api, dashboard, trading-agent)
#   make stop           # Stop all services
#   make rm             # Remove all stopped containers
#   make ps             # List running containers
#   make logs           # Show logs from most recent container
#   make attach         # Attach to running container shell
#   make rebuild        # Stop, remove, rebuild, and start
#
#   Development:
#   make lint           # Run ruff linting
#   make format         # Format code with black
#   make format-check   # Check formatting without changes
#   make isort          # Organize imports
#   make test           # Run all tests
#   make test-cov       # Run tests with coverage report
#   make clean          # Clean up Docker resources and cache
#
#   Logs:
#   make logs-api       # Stream API logs
#   make logs-dashboard # Stream Dashboard logs
#   make logs-trading   # Stream Trading Agent logs
