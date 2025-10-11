# Makefile for Binance Trading Agent (Docker workflow)

IMAGE_NAME=binance-agent
ENV_FILE=binance_trade_agent/.env
PORT=8080

build:
	docker build -t $(IMAGE_NAME) -f Dockerfile .

run:
	docker run -d --env-file $(ENV_FILE) -p $(PORT):8080 $(IMAGE_NAME)

ps:
	docker ps

stop:
	docker stop $$(docker ps -q --filter ancestor=$(IMAGE_NAME))

rm:
	docker rm $$(docker ps -a -q --filter ancestor=$(IMAGE_NAME))

attach:
	@powershell -Command "$$id = docker ps -q --filter ancestor=$(IMAGE_NAME) | Select-Object -First 1; if ($$id) { docker exec -it $$id /bin/bash } else { Write-Host 'No running container found.' }"

logs:
	docker logs $$(docker ps -q --filter ancestor=$(IMAGE_NAME) | head -n 1)

rebuild: stop rm build run

# Usage:
#   make build    # Build the Docker image
#   make run      # Run the container
#   make attach   # Attach to running container shell
#   make logs     # Show container logs
#   make stop     # Stop running container(s)
#   make rm       # Remove stopped container(s)
#   make rebuild  # Stop, remove, rebuild, and run
