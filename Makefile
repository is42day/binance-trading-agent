# Makefile for Binance Trading Agent (Docker workflow)

IMAGE_NAME=binance-agent
ENV_FILE=binance_trade_agent/.env
PORTS=8080:8080 8501:8501 9090:9090

build:
	docker build -t $(IMAGE_NAME) -f Dockerfile .

run:
	docker run -d --env-file $(ENV_FILE) -p 8080:8080 -p 8501:8501 -p 9090:9090 $(IMAGE_NAME)

ps:
	docker ps

ifeq ($(OS),Windows_NT)

stop:
	@powershell -NoProfile -Command "$$ids = (docker ps -q --filter ancestor=$(IMAGE_NAME)); if ($$ids) { $$ids | ForEach-Object { docker stop $_ } } else { Write-Host 'No running containers for $(IMAGE_NAME)' }"

rm:
	@powershell -NoProfile -Command "$$ids = (docker ps -a -q --filter ancestor=$(IMAGE_NAME)); if ($$ids) { $$ids | ForEach-Object { docker rm $_ } } else { Write-Host 'No containers to remove for $(IMAGE_NAME)' }"

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
	@IDS=$$(docker ps -q --filter ancestor=$(IMAGE_NAME)); \
	if [ -n "$$IDS" ]; then \
		docker stop $$IDS || true; \
	else \
		echo "No running containers for $(IMAGE_NAME)"; \
	fi

rm:
	@IDS_ALL=$$(docker ps -a -q --filter ancestor=$(IMAGE_NAME)); \
	if [ -n "$$IDS_ALL" ]; then \
		docker rm $$IDS_ALL || true; \
	else \
		echo "No containers to remove for $(IMAGE_NAME)"; \
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

# rebuild: stop rm build run
rebuild: stop rm build run

# Usage:
#   make build    # Build the Docker image
#   make run      # Run the container
#   make attach   # Attach to running container shell
#   make logs     # Show container logs
#   make stop     # Stop running container(s)
#   make rm       # Remove stopped container(s)
#   make rebuild  # Stop, remove, rebuild, and run
