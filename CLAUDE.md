# CLAUDE.md — Warden VoIP (PBX)

## Project Overview

Warden VoIP is a comprehensive VoIP/PBX system built from scratch in Python 3.13+. It implements the full SIP protocol stack, RTP media handling, and an extensive feature set (76 modules) without depending on Asterisk or FreeSWITCH. The project includes a modern admin web interface built with TypeScript/Vite.

## Quick Reference

| Item | Value |
|------|-------|
| Language | Python 3.13+ (backend), TypeScript (frontend) |
| Package manager | `uv pip` (Python), `npm` (frontend) |
| Build system | `hatchling` (Python), `vite` (frontend) |
| Test framework | `pytest` (Python), `jest` (frontend) |
| Linter/Formatter | `ruff` (Python), `markdownlint-cli2` (Markdown) |
| Type checker | `mypy` (strict mode) |
| Line length | 100 characters |
| Entry point | `pbx/main.py` → `pbx-server` console script |

## Common Commands

```bash
# Install dependencies (development)
make install            # pip install -e ".[dev]"

# Run all checks (format + lint + test)
make check

# Linting and formatting
make lint               # ruff check + mypy
make lint-fix           # ruff check --fix
make format             # ruff format + isort fix
make format-check       # check only, no changes

# Testing
make test               # all tests (Python + JavaScript)
make test-python        # pytest only
make test-js            # jest only
make test-unit          # pytest -m unit
make test-integration   # pytest -m integration
make test-cov           # pytest with coverage report

# Development servers
make dev                # backend + frontend concurrently
make dev-backend        # Flask debug mode only
make dev-frontend       # Vite dev server only

# Run production
make run                # python main.py

# Docker
make docker-build       # docker compose build
make docker-up          # docker compose up -d
make docker-down        # docker compose down

# Pre-commit hooks
make pre-commit-install
make pre-commit-run
```

## Architecture

### Layered Design

```
pbx/
├── api/              # REST API layer (Flask)
│   ├── routes/       # 22 route modules organized by feature
│   ├── schemas/      # Request/response validation
│   ├── app.py        # Flask app factory (create_app)
│   ├── errors.py     # Error handling
│   ├── openapi.py    # OpenAPI documentation
│   └── server.py     # API server initialization
├── core/             # Core PBX engine
│   ├── pbx.py        # PBXCore - central coordinator
│   ├── call.py       # Call state machine
│   ├── call_router.py # Routing logic
│   ├── auto_attendant_handler.py # IVR logic
│   ├── voicemail_handler.py      # Voicemail processing
│   ├── emergency_handler.py      # E911 handling
│   └── feature_initializer.py    # Dynamic feature loading
├── sip/              # SIP protocol implementation
│   ├── server.py     # SIP server (Twisted-based)
│   ├── message.py    # SIP message parser
│   └── sdp.py        # SDP negotiation
├── rtp/              # RTP media handling
│   ├── handler.py    # RTP relay
│   ├── jitter_buffer.py
│   └── rtcp_monitor.py
├── features/         # 76 feature modules (pluggable)
│   └── ...           # Each feature is a self-contained .py module
├── models/           # SQLAlchemy ORM models
├── utils/            # Cross-cutting concerns
│   ├── config.py     # YAML config management
│   ├── database.py   # DB abstraction (PostgreSQL/SQLite)
│   ├── encryption.py # FIPS 140-2 encryption
│   └── tls_support.py
└── integrations/     # Third-party integrations

admin/                # Frontend admin interface
├── js/
│   ├── pages/        # Page modules (TypeScript)
│   ├── api/client.ts # API client
│   ├── state/store.ts # State management
│   └── ui/           # UI components
├── css/              # Stylesheets
├── tests/            # Jest tests
├── vite.config.js
└── tsconfig.json

tests/                # Python test suite (126 files)
├── conftest.py       # Shared fixtures
├── integration/      # Integration tests (API, call flow, provisioning)
└── test_*.py
```

### Key Patterns

- **PBXCore** is the central coordinator/singleton that owns all subsystems
- **Feature modules** in `pbx/features/` are loaded dynamically via `FeatureInitializer`
- **Database abstraction** supports PostgreSQL (production) and SQLite (fallback)
- **Configuration** is YAML-based (`config.yml`) with `.env` file support
- **API routes** are organized by feature domain in `pbx/api/routes/`
- **Flask app** uses a factory pattern via `create_app(pbx_core)`

## Code Style and Conventions

### Python

- **Python 3.13+** required — use modern syntax (`match`, `|` union types, `pathlib.Path`)
- **Line length**: 100 characters
- **Quotes**: Double quotes
- **Indentation**: 4 spaces
- **Imports**: Sorted by ruff (isort rules), `pbx` is first-party
- **Type annotations**: Required — mypy strict mode is enabled for `api/`, `core/`, `models/`
- **Datetime**: Always use timezone-aware datetimes (UTC) — `datetime.now(tz=UTC)`, never bare `datetime.now()`
- **File paths**: Use `pathlib.Path`, not `os.path`
- **Exception handling**: Use specific exception types, not bare `except Exception`
- **Line endings**: LF only (enforced by `.editorconfig` and pre-commit)

### TypeScript (Frontend)

- **Target**: ES2024
- **Strict mode** enabled
- **Build tool**: Vite 7.3
- **Testing**: Jest with jsdom

### YAML

- 2-space indentation
- Max line length: 120

## Testing

### Running Tests

```bash
make test-python       # Run all Python tests
make test-js           # Run all JavaScript tests
make test-unit         # Only unit tests: pytest -m unit
make test-integration  # Only integration tests: pytest -m integration
make test-cov          # With coverage (80% minimum)
```

### Test Conventions

- Test files: `tests/test_*.py`
- Test classes: `Test*`
- Test functions: `test_*`
- Use markers: `@pytest.mark.unit`, `@pytest.mark.integration`, `@pytest.mark.slow`
- Fixtures are in `tests/conftest.py`: `mock_config`, `mock_database`, `mock_extension`, `mock_pbx_core`, `api_client`, `sip_message_factory`

### Writing Tests

- Use the shared fixtures from `conftest.py` rather than creating ad-hoc mocks
- API tests should use the `api_client` fixture (provides a Flask test client)
- SIP protocol tests should use `sip_message_factory` to construct messages
- Tests are relaxed on linting rules: `F401`, `F811`, `ARG`, `PLR`, `PT`, `B011` are ignored

## CI/CD

GitHub Actions workflows in `.github/workflows/`:

| Workflow | Purpose |
|----------|---------|
| `tests.yml` | pytest + coverage + PostgreSQL integration tests |
| `code-quality.yml` | ruff format check, ruff lint, mypy, bandit, safety |
| `security-scanning.yml` | Trivy, gitleaks, SAST, dependency audit |
| `production-deployment.yml` | Docker build/push, Kubernetes deploy |
| `dependency-updates.yml` | Automated dependency checks |
| `syntax-check.yml` | Python + YAML syntax validation |

System dependencies required in CI: `espeak`, `ffmpeg`, `libopus-dev`, `portaudio19-dev`, `libspeex-dev`

## Configuration

- **Primary config**: `config.yml` (YAML format, ~27KB example)
- **Environment vars**: `.env` file (see `.env.example`)
- **Trunk examples**: `config_att_sip.yml`, `config_comcast_sip.yml`
- **Docker**: `docker-compose.yml` (PostgreSQL 17 + Redis 7 + PBX)

## Database

- **ORM**: SQLAlchemy 2.0 with models in `pbx/models/`
- **Migrations**: Alembic (config in `alembic/`)
- **Production**: PostgreSQL 17
- **Development fallback**: SQLite
- **Models**: `Extension`, `Voicemail`, `CallRecord`, `RegisteredPhone`

## Pre-commit Hooks

Configured in `.pre-commit-config.yaml`:

1. **pre-commit-hooks** (v5.0.0) — trailing whitespace, EOF, YAML/JSON/TOML/XML checks, merge conflicts, debug statements, private key detection, LF line endings, test naming, no-commit-to-main
2. **ruff** (v0.9.10) — lint with `--fix` + format
3. **mypy** (v1.15.0) — type checking (excludes tests, skipped in CI)
4. **bandit** (1.9.0) — security scanning (excludes tests)
5. **yamllint** (v1.35.1) — YAML linting (excludes config files)
6. **markdownlint-cli2** (v0.17.2) — Markdown linting
7. **shellcheck** (v0.10.0.1) — shell script linting

## Key Files

| File | Purpose |
|------|---------|
| `main.py` | CLI entry point with startup checks |
| `pbx/core/pbx.py` | PBXCore central coordinator |
| `pbx/api/app.py` | Flask app factory |
| `pbx/sip/server.py` | SIP protocol server |
| `pbx/utils/config.py` | Configuration management |
| `pbx/utils/database.py` | Database abstraction layer |
| `pyproject.toml` | Build config, dependencies, ruff, mypy, pytest settings |
| `Makefile` | All development commands |
| `config.yml` | Runtime configuration |
| `docker-compose.yml` | Container orchestration |
| `Dockerfile` | Multi-stage build (python:3.14-slim-bookworm) |

## Ruff Rules Summary

Selected rule sets: `E`, `W`, `F`, `I`, `N`, `UP`, `B`, `A`, `C4`, `DTZ`, `T10`, `ISC`, `PIE`, `PT`, `RSE`, `RET`, `SIM`, `TCH`, `ARG`, `PTH`, `ERA`, `PL`, `PERF`, `FURB`, `LOG`, `RUF`

Notable ignored rules:
- `E501` — line length (formatter handles it)
- `E402` — module-level import order (needed for env loading)
- `PLR0913/0912/0915` — complexity thresholds (relaxed)
- `ARG001/002` — unused arguments (common in callbacks/handlers)
- `B008` — function calls in default args (Flask patterns)

Per-file overrides:
- `__init__.py`: `F401` ignored (re-exports)
- `tests/*`: Relaxed rules (`F401`, `F811`, `ARG`, `PLR`, `PT`, `B011`)
- `pbx/api/rest_api.py`: All rules ignored (deprecated file)

## Deployment

- **Ubuntu setup**: `scripts/setup_ubuntu.py` (automated wizard)
- **Production deploy**: `scripts/deploy_production_pilot.sh`
- **Reverse proxy**: `scripts/setup_reverse_proxy.sh` (Nginx) or Apache variant
- **SSL certs**: `scripts/generate_ssl_cert.py`
- **Kubernetes**: manifests in `kubernetes/`
- **Terraform**: IaC in `terraform/`
- **Monitoring**: Grafana dashboards in `grafana/`
