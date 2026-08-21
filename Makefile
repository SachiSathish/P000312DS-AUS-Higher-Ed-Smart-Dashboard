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
stop: docker compose down

.PHONY: build_api
build_api:
	echo -e $(CYAN)Building Python API$(NC)
	docker compose build

.PHONY: run_api
run_api:
	echo -e $(CYAN)Starting Python API$(NC)
	docker compose up