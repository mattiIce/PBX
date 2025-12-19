# =============================================================================
# Makefile for PBX System Development
# =============================================================================
# This Makefile provides common development tasks for the PBX system.
# Run 'make help' or just 'make' to see all available targets.
# =============================================================================

# -----------------------------------------------------------------------------
# Variables
# -----------------------------------------------------------------------------
SHELL := /bin/bash
.DEFAULT_GOAL := help

# Project paths
SRC_DIR := pbx
TEST_DIR := tests
DOCS_DIR := docs

# Python interpreter
PYTHON := python3
PIP := $(PYTHON) -m pip

# Docker settings
DOCKER_COMPOSE := docker-compose
DOCKER_IMAGE := pbx-system
CONTAINER_NAME := pbx-server

# Coverage settings
COV_REPORT := htmlcov
COV_MIN := 80

# Colors for output
COLOR_RESET := \033[0m
COLOR_BOLD := \033[1m
COLOR_GREEN := \033[32m
COLOR_YELLOW := \033[33m
COLOR_BLUE := \033[34m

# =============================================================================
# Default Target: Help
# =============================================================================

.PHONY: help
help: ## Display this help message
	@echo -e "$(COLOR_BOLD)PBX System - Development Makefile$(COLOR_RESET)"
	@echo ""
	@echo -e "$(COLOR_BOLD)Usage:$(COLOR_RESET)"
	@echo "  make <target>"
	@echo ""
	@echo -e "$(COLOR_BOLD)Setup & Installation:$(COLOR_RESET)"
	@grep -E '^[a-zA-Z0-9_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; /^(install|install-prod|install-constraints):/ {printf "  $(COLOR_GREEN)%-25s$(COLOR_RESET) %s\n", $$1, $$2}'
	@echo ""
	@echo -e "$(COLOR_BOLD)Code Quality & Linting:$(COLOR_RESET)"
	@grep -E '^[a-zA-Z0-9_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; /^(lint|pylint|flake8|mypy):/ {printf "  $(COLOR_YELLOW)%-25s$(COLOR_RESET) %s\n", $$1, $$2}'
	@echo ""
	@echo -e "$(COLOR_BOLD)Formatting:$(COLOR_RESET)"
	@grep -E '^[a-zA-Z0-9_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; /^(format|format-check|black|isort):/ {printf "  $(COLOR_BLUE)%-25s$(COLOR_RESET) %s\n", $$1, $$2}'
	@echo ""
	@echo -e "$(COLOR_BOLD)Testing:$(COLOR_RESET)"
	@grep -E '^[a-zA-Z0-9_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; /^(test|test-unit|test-integration|test-cov|test-cov-html):/ {printf "  $(COLOR_GREEN)%-25s$(COLOR_RESET) %s\n", $$1, $$2}'
	@echo ""
	@echo -e "$(COLOR_BOLD)Docker:$(COLOR_RESET)"
	@grep -E '^[a-zA-Z0-9_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; /^docker-/ {printf "  $(COLOR_BLUE)%-25s$(COLOR_RESET) %s\n", $$1, $$2}'
	@echo ""
	@echo -e "$(COLOR_BOLD)Cleanup:$(COLOR_RESET)"
	@grep -E '^[a-zA-Z0-9_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; /^clean/ {printf "  $(COLOR_YELLOW)%-25s$(COLOR_RESET) %s\n", $$1, $$2}'
	@echo ""
	@echo -e "$(COLOR_BOLD)Utilities:$(COLOR_RESET)"
	@grep -E '^[a-zA-Z0-9_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; /^(run|pre-commit-install|pre-commit-run):/ {printf "  $(COLOR_GREEN)%-25s$(COLOR_RESET) %s\n", $$1, $$2}'
	@echo ""

# =============================================================================
# Setup & Installation
# =============================================================================

.PHONY: install
install: ## Install package in development mode with dev dependencies
	@echo -e "$(COLOR_BOLD)Installing PBX System in development mode...$(COLOR_RESET)"
	$(PIP) install --upgrade pip setuptools wheel
	$(PIP) install -e ".[dev]"
	@echo -e "$(COLOR_GREEN)✓ Installation complete!$(COLOR_RESET)"

.PHONY: install-prod
install-prod: ## Install production dependencies only
	@echo -e "$(COLOR_BOLD)Installing production dependencies...$(COLOR_RESET)"
	$(PIP) install --upgrade pip setuptools wheel
	$(PIP) install -e .
	@echo -e "$(COLOR_GREEN)✓ Production installation complete!$(COLOR_RESET)"

.PHONY: install-constraints
install-constraints: ## Install with constraints.txt for reproducible builds
	@echo -e "$(COLOR_BOLD)Installing with constraints...$(COLOR_RESET)"
	$(PIP) install --upgrade pip setuptools wheel
	$(PIP) install -e . -c constraints.txt
	@echo -e "$(COLOR_GREEN)✓ Constrained installation complete!$(COLOR_RESET)"

# =============================================================================
# Code Quality & Linting
# =============================================================================

.PHONY: lint
lint: pylint flake8 mypy ## Run all linters (pylint, flake8, mypy)
	@echo -e "$(COLOR_GREEN)✓ All linting checks passed!$(COLOR_RESET)"

.PHONY: pylint
pylint: ## Run pylint on pbx directory
	@echo -e "$(COLOR_BOLD)Running pylint...$(COLOR_RESET)"
	$(PYTHON) -m pylint $(SRC_DIR)

.PHONY: flake8
flake8: ## Run flake8 on pbx directory
	@echo -e "$(COLOR_BOLD)Running flake8...$(COLOR_RESET)"
	$(PYTHON) -m flake8 $(SRC_DIR)

.PHONY: mypy
mypy: ## Run mypy type checking
	@echo -e "$(COLOR_BOLD)Running mypy...$(COLOR_RESET)"
	$(PYTHON) -m mypy $(SRC_DIR)

# =============================================================================
# Formatting
# =============================================================================

.PHONY: format
format: black isort ## Auto-format code with black and isort
	@echo -e "$(COLOR_GREEN)✓ Code formatting complete!$(COLOR_RESET)"

.PHONY: format-check
format-check: ## Check formatting without making changes
	@echo -e "$(COLOR_BOLD)Checking code formatting...$(COLOR_RESET)"
	$(PYTHON) -m black --check --line-length 100 $(SRC_DIR) $(TEST_DIR)
	$(PYTHON) -m isort --check-only --profile black --line-length 100 $(SRC_DIR) $(TEST_DIR)
	@echo -e "$(COLOR_GREEN)✓ Formatting check passed!$(COLOR_RESET)"

.PHONY: black
black: ## Run black formatter (line-length 100 from pyproject.toml)
	@echo -e "$(COLOR_BOLD)Running black formatter...$(COLOR_RESET)"
	$(PYTHON) -m black --line-length 100 $(SRC_DIR) $(TEST_DIR)

.PHONY: isort
isort: ## Run isort for import sorting
	@echo -e "$(COLOR_BOLD)Running isort...$(COLOR_RESET)"
	$(PYTHON) -m isort --profile black --line-length 100 $(SRC_DIR) $(TEST_DIR)

# =============================================================================
# Testing
# =============================================================================

.PHONY: test
test: ## Run all tests with pytest
	@echo -e "$(COLOR_BOLD)Running all tests...$(COLOR_RESET)"
	$(PYTHON) -m pytest $(TEST_DIR) -v

.PHONY: test-unit
test-unit: ## Run unit tests only
	@echo -e "$(COLOR_BOLD)Running unit tests...$(COLOR_RESET)"
	$(PYTHON) -m pytest $(TEST_DIR) -v -m unit

.PHONY: test-integration
test-integration: ## Run integration tests only
	@echo -e "$(COLOR_BOLD)Running integration tests...$(COLOR_RESET)"
	$(PYTHON) -m pytest $(TEST_DIR) -v -m integration

.PHONY: test-cov
test-cov: ## Run tests with coverage report
	@echo -e "$(COLOR_BOLD)Running tests with coverage...$(COLOR_RESET)"
	$(PYTHON) -m pytest $(TEST_DIR) --cov=$(SRC_DIR) --cov-report=term-missing --cov-report=html

.PHONY: test-cov-html
test-cov-html: ## Generate HTML coverage report
	@echo -e "$(COLOR_BOLD)Generating HTML coverage report...$(COLOR_RESET)"
	$(PYTHON) -m pytest $(TEST_DIR) --cov=$(SRC_DIR) --cov-report=html
	@echo -e "$(COLOR_GREEN)✓ Coverage report generated in $(COV_REPORT)/index.html$(COLOR_RESET)"

# =============================================================================
# Docker
# =============================================================================

.PHONY: docker-build
docker-build: ## Build Docker image
	@echo -e "$(COLOR_BOLD)Building Docker image...$(COLOR_RESET)"
	$(DOCKER_COMPOSE) build
	@echo -e "$(COLOR_GREEN)✓ Docker image built successfully!$(COLOR_RESET)"

.PHONY: docker-up
docker-up: ## Start services with docker-compose
	@echo -e "$(COLOR_BOLD)Starting Docker services...$(COLOR_RESET)"
	$(DOCKER_COMPOSE) up -d
	@echo -e "$(COLOR_GREEN)✓ Services started!$(COLOR_RESET)"
	@$(DOCKER_COMPOSE) ps

.PHONY: docker-down
docker-down: ## Stop services
	@echo -e "$(COLOR_BOLD)Stopping Docker services...$(COLOR_RESET)"
	$(DOCKER_COMPOSE) down
	@echo -e "$(COLOR_GREEN)✓ Services stopped!$(COLOR_RESET)"

.PHONY: docker-logs
docker-logs: ## View service logs
	@echo -e "$(COLOR_BOLD)Viewing Docker logs...$(COLOR_RESET)"
	$(DOCKER_COMPOSE) logs -f

.PHONY: docker-shell
docker-shell: ## Open shell in PBX container
	@echo -e "$(COLOR_BOLD)Opening shell in $(CONTAINER_NAME)...$(COLOR_RESET)"
	$(DOCKER_COMPOSE) exec pbx /bin/bash

.PHONY: docker-clean
docker-clean: ## Clean up Docker resources
	@echo -e "$(COLOR_BOLD)Cleaning up Docker resources...$(COLOR_RESET)"
	$(DOCKER_COMPOSE) down -v --remove-orphans
	docker system prune -f
	@echo -e "$(COLOR_GREEN)✓ Docker cleanup complete!$(COLOR_RESET)"

# =============================================================================
# Cleanup
# =============================================================================

.PHONY: clean
clean: ## Remove build artifacts, __pycache__, .pyc files
	@echo -e "$(COLOR_BOLD)Cleaning build artifacts...$(COLOR_RESET)"
	find . -type f -name '*.pyc' -delete
	find . -type d -name '__pycache__' -delete
	find . -type d -name '*.egg-info' -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name '.eggs' -exec rm -rf {} + 2>/dev/null || true
	rm -rf build/ dist/ .eggs/
	@echo -e "$(COLOR_GREEN)✓ Cleanup complete!$(COLOR_RESET)"

.PHONY: clean-all
clean-all: clean ## Deep clean including .venv, .pytest_cache, etc.
	@echo -e "$(COLOR_BOLD)Performing deep clean...$(COLOR_RESET)"
	rm -rf .venv/ venv/ env/
	rm -rf .pytest_cache/ .mypy_cache/ .tox/
	rm -rf $(COV_REPORT)/ .coverage
	rm -rf logs/ recordings/ voicemail/ cdr/
	@echo -e "$(COLOR_GREEN)✓ Deep clean complete!$(COLOR_RESET)"

# =============================================================================
# Utilities
# =============================================================================

.PHONY: run
run: ## Run the PBX server locally
	@echo -e "$(COLOR_BOLD)Starting PBX server...$(COLOR_RESET)"
	$(PYTHON) main.py

.PHONY: pre-commit-install
pre-commit-install: ## Install pre-commit hooks
	@echo -e "$(COLOR_BOLD)Installing pre-commit hooks...$(COLOR_RESET)"
	$(PYTHON) -m pre_commit install
	@echo -e "$(COLOR_GREEN)✓ Pre-commit hooks installed!$(COLOR_RESET)"

.PHONY: pre-commit-run
pre-commit-run: ## Run pre-commit on all files
	@echo -e "$(COLOR_BOLD)Running pre-commit on all files...$(COLOR_RESET)"
	$(PYTHON) -m pre_commit run --all-files
