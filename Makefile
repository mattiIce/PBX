# =============================================================================
# Makefile for PBX System Development
# =============================================================================

SHELL := /bin/bash
.DEFAULT_GOAL := help

# Project paths
SRC_DIR := pbx
TEST_DIR := tests

# Python interpreter
PYTHON := python3
PIP := uv pip

# Docker settings
DOCKER_COMPOSE := docker compose
DOCKER_IMAGE := pbx-system
CONTAINER_NAME := pbx-server

# Coverage settings
COV_REPORT := htmlcov
COV_MIN := 80

# Colors
COLOR_RESET := \033[0m
COLOR_BOLD := \033[1m
COLOR_GREEN := \033[32m
COLOR_YELLOW := \033[33m
COLOR_BLUE := \033[34m

# =============================================================================
# Help
# =============================================================================

.PHONY: help
help: ## Display this help message
	@echo -e "$(COLOR_BOLD)PBX System - Development Makefile$(COLOR_RESET)"
	@echo ""
	@grep -E '^[a-zA-Z0-9_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  $(COLOR_GREEN)%-25s$(COLOR_RESET) %s\n", $$1, $$2}'
	@echo ""

# =============================================================================
# Setup & Installation
# =============================================================================

.PHONY: install
install: ## Install package in development mode with dev dependencies
	@echo -e "$(COLOR_BOLD)Installing PBX System in development mode...$(COLOR_RESET)"
	uv pip install -e ".[dev]"
	@echo -e "$(COLOR_GREEN)Done.$(COLOR_RESET)"

.PHONY: install-prod
install-prod: ## Install production dependencies only
	@echo -e "$(COLOR_BOLD)Installing production dependencies...$(COLOR_RESET)"
	uv pip install -e .
	@echo -e "$(COLOR_GREEN)Done.$(COLOR_RESET)"

.PHONY: install-constraints
install-constraints: ## Install with constraints.txt for reproducible builds
	@echo -e "$(COLOR_BOLD)Installing with constraints...$(COLOR_RESET)"
	uv pip install -e . -c constraints.txt
	@echo -e "$(COLOR_GREEN)Done.$(COLOR_RESET)"

# =============================================================================
# Code Quality (Ruff + mypy)
# =============================================================================

.PHONY: lint
lint: ## Run Ruff linter and mypy type checker
	@echo -e "$(COLOR_BOLD)Running Ruff linter...$(COLOR_RESET)"
	$(PYTHON) -m ruff check $(SRC_DIR) $(TEST_DIR)
	@echo -e "$(COLOR_BOLD)Running mypy...$(COLOR_RESET)"
	$(PYTHON) -m mypy $(SRC_DIR)
	@echo -e "$(COLOR_GREEN)All checks passed.$(COLOR_RESET)"

.PHONY: lint-fix
lint-fix: ## Auto-fix linting issues with Ruff
	@echo -e "$(COLOR_BOLD)Auto-fixing with Ruff...$(COLOR_RESET)"
	$(PYTHON) -m ruff check --fix $(SRC_DIR) $(TEST_DIR)
	@echo -e "$(COLOR_GREEN)Done.$(COLOR_RESET)"

.PHONY: mypy
mypy: ## Run mypy type checking
	@echo -e "$(COLOR_BOLD)Running mypy...$(COLOR_RESET)"
	$(PYTHON) -m mypy $(SRC_DIR)

# =============================================================================
# Formatting (Ruff formatter)
# =============================================================================

.PHONY: format
format: ## Auto-format code with Ruff
	@echo -e "$(COLOR_BOLD)Formatting with Ruff...$(COLOR_RESET)"
	$(PYTHON) -m ruff format $(SRC_DIR) $(TEST_DIR)
	$(PYTHON) -m ruff check --fix --select I $(SRC_DIR) $(TEST_DIR)
	@echo -e "$(COLOR_GREEN)Done.$(COLOR_RESET)"

.PHONY: format-check
format-check: ## Check formatting without making changes
	@echo -e "$(COLOR_BOLD)Checking code formatting...$(COLOR_RESET)"
	$(PYTHON) -m ruff format --check $(SRC_DIR) $(TEST_DIR)
	$(PYTHON) -m ruff check --select I $(SRC_DIR) $(TEST_DIR)
	@echo -e "$(COLOR_GREEN)Formatting check passed.$(COLOR_RESET)"

# =============================================================================
# Testing
# =============================================================================

.PHONY: test
test: test-python test-js ## Run all tests (Python and JavaScript)

.PHONY: test-python
test-python: ## Run Python tests with pytest
	@echo -e "$(COLOR_BOLD)Running Python tests...$(COLOR_RESET)"
	$(PYTHON) -m pytest $(TEST_DIR) -v

.PHONY: test-js
test-js: ## Run JavaScript tests with Jest
	@echo -e "$(COLOR_BOLD)Running JavaScript tests...$(COLOR_RESET)"
	npm test

.PHONY: test-js-watch
test-js-watch: ## Run JavaScript tests in watch mode
	npm run test:watch

.PHONY: test-js-cov
test-js-cov: ## Run JavaScript tests with coverage
	npm run test:coverage

.PHONY: test-unit
test-unit: ## Run unit tests only
	$(PYTHON) -m pytest $(TEST_DIR) -v -m unit

.PHONY: test-integration
test-integration: ## Run integration tests only
	$(PYTHON) -m pytest $(TEST_DIR) -v -m integration

.PHONY: test-cov
test-cov: ## Run tests with coverage report
	$(PYTHON) -m pytest $(TEST_DIR) --cov=$(SRC_DIR) --cov-report=term-missing --cov-report=html

.PHONY: test-cov-html
test-cov-html: ## Generate HTML coverage report
	$(PYTHON) -m pytest $(TEST_DIR) --cov=$(SRC_DIR) --cov-report=html
	@echo -e "$(COLOR_GREEN)Coverage report: $(COV_REPORT)/index.html$(COLOR_RESET)"

# =============================================================================
# Docker
# =============================================================================

.PHONY: docker-build
docker-build: ## Build Docker image
	$(DOCKER_COMPOSE) build

.PHONY: docker-up
docker-up: ## Start services with docker compose
	$(DOCKER_COMPOSE) up -d
	@$(DOCKER_COMPOSE) ps

.PHONY: docker-down
docker-down: ## Stop services
	$(DOCKER_COMPOSE) down

.PHONY: docker-logs
docker-logs: ## View service logs
	$(DOCKER_COMPOSE) logs -f

.PHONY: docker-shell
docker-shell: ## Open shell in PBX container
	$(DOCKER_COMPOSE) exec pbx /bin/bash

.PHONY: docker-clean
docker-clean: ## Clean up Docker resources
	$(DOCKER_COMPOSE) down -v --remove-orphans
	docker system prune -f

# =============================================================================
# Cleanup
# =============================================================================

.PHONY: clean
clean: ## Remove build artifacts, __pycache__, .pyc files
	find . -type f -name '*.pyc' -delete
	find . -type d -name '__pycache__' -delete
	find . -type d -name '*.egg-info' -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name '.eggs' -exec rm -rf {} + 2>/dev/null || true
	rm -rf build/ dist/ .eggs/

.PHONY: clean-all
clean-all: clean ## Deep clean including .venv, .pytest_cache, etc.
	rm -rf .venv/ venv/ env/
	rm -rf .pytest_cache/ .mypy_cache/ .ruff_cache/ .tox/
	rm -rf $(COV_REPORT)/ .coverage
	rm -rf logs/ recordings/ voicemail/ cdr/

# =============================================================================
# Development
# =============================================================================

.PHONY: dev
dev: ## Start backend and frontend concurrently for local development
	trap 'kill 0' EXIT; FLASK_DEBUG=1 $(PYTHON) main.py & npm run dev & wait

.PHONY: dev-backend
dev-backend: ## Run backend only with Flask debug mode
	FLASK_DEBUG=1 $(PYTHON) main.py

.PHONY: dev-frontend
dev-frontend: ## Run frontend dev server only
	npm run dev

# =============================================================================
# Dependency Management
# =============================================================================

.PHONY: lock
lock: ## Generate requirements.lock from pyproject.toml
	uv pip compile pyproject.toml -o requirements.lock

.PHONY: sync
sync: ## Install dependencies from requirements.lock
	uv pip sync requirements.lock

# =============================================================================
# Utilities
# =============================================================================

.PHONY: run
run: ## Run the PBX server locally
	$(PYTHON) main.py

.PHONY: pre-commit-install
pre-commit-install: ## Install pre-commit hooks
	$(PYTHON) -m pre_commit install

.PHONY: pre-commit-run
pre-commit-run: ## Run pre-commit on all files
	$(PYTHON) -m pre_commit run --all-files

.PHONY: check
check: format-check lint test ## Run all checks (format, lint, test)
