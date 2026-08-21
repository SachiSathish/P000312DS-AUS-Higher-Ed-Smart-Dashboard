# use some sensible default shell settings
SHELL := /bin/bash
.ONESHELL:
.SILENT:
.DEFAULT_GOAL := run

RED = '\033[1;31m'
CYAN = '\033[0;36m'
NC = '\033[0m'


export
API_PORT ?= 80
DB_USERNAME ?= dashboard
DB_PASSWORD ?= dashboard
DB_NAME ?= dashboard
DB_PORT ?= 5432

##@ Main targets
build: build_api ## Build the pipeline
run: run_api
api_bash: 
	docker compose exec api bash

api_cmd:
	docker compose exec api printenv DB_USERNAME

stop: 
	docker compose down


migration_setup:
	docker compose exec --workdir /models api alembic init migrations

migration_revision:
	@read -p "Revision name: " REV_NAME; \
	docker compose exec --workdir /models api alembic revision --autogenerate -m "$$REV_NAME"

migration_head:
	docker compose exec api -w /models upgrade head

.PHONY: build_api
build_api:
	echo -e $(CYAN)Building Python API$(NC)
	docker compose build

.PHONY: run_api
run_api:
	echo -e $(CYAN)Starting Python API$(NC)
	docker compose up