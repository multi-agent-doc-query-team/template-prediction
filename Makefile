COMPOSE := docker compose
SERVICE := ai-unit-conversion-api

.PHONY: help build up down restart logs status shell clean rebuild test

help:
	@echo 'Available targets:'
	@echo '  make build    Build the Docker image'
	@echo '  make up       Build (if needed) and start in background'
	@echo '  make down     Stop and remove containers'
	@echo '  make restart  Restart the service'
	@echo '  make logs     Follow application logs'
	@echo '  make status   Show service status'
	@echo '  make shell    Open a shell inside the container'
	@echo '  make rebuild  Rebuild from scratch without cache'
	@echo '  make clean    Stop containers and remove the image'

build:
	$(COMPOSE) build

up:
	$(COMPOSE) up -d --build

down:
	$(COMPOSE) down

restart:
	$(COMPOSE) restart $(SERVICE)

logs:
	$(COMPOSE) logs -f $(SERVICE)

status:
	$(COMPOSE) ps

shell:
	$(COMPOSE) exec $(SERVICE) /bin/sh

rebuild:
	$(COMPOSE) build --no-cache
	$(COMPOSE) up -d

clean:
	$(COMPOSE) down --rmi local