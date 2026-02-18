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
make install            # uv pip install -e ".[dev]"

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
│   ├── paging_handler.py         # Overhead paging logic
│   └── feature_initializer.py    # Dynamic feature loading
├── sip/              # SIP protocol implementation
│   ├── server.py     # SIP server (Twisted-based)
│   ├── message.py    # SIP message parser
│   └── sdp.py        # SDP negotiation
├── rtp/              # RTP media handling
│   ├── handler.py    # RTP relay
│   ├── jitter_buffer.py
│   ├── rfc2833.py    # DTMF event handling (RFC 2833)
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

tests/                # Python test suite (238 files)
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
- Tests are relaxed on linting rules: `F401`, `F811`, `ARG`, `PLR`, `PT`, `B011`, `PLC0415`, `N806`, `N803` are ignored

## CI/CD

GitHub Actions workflows in `.github/workflows/`:

| Workflow | Purpose |
|----------|---------|
| `tests.yml` | pytest + coverage + PostgreSQL integration tests |
| `code-quality.yml` | ruff format check, ruff lint, mypy, bandit, pip-audit |
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
- **Models**: `Base` (declarative base), `Extension`, `Voicemail`, `CallRecord`, `RegisteredPhone`

## Pre-commit Hooks

Configured in `.pre-commit-config.yaml`:

1. **pre-commit-hooks** (v6.0.0) — trailing whitespace, EOF, YAML/JSON/TOML/XML checks, merge conflicts, debug statements, private key detection, LF line endings, test naming, no-commit-to-main
2. **ruff** (v0.15.1) — lint with `--fix` + format
3. **mypy** (v1.19.1) — type checking (excludes tests, skipped in CI)
4. **bandit** (1.9.3) — security scanning (excludes tests)
5. **yamllint** (v1.38.0) — YAML linting (excludes config files)
6. **markdownlint-cli2** (v0.21.0) — Markdown linting
7. **shellcheck** (v0.11.0.1) — shell script linting

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
- `PLR2004` — magic value in comparison
- `PLR0911` — too many return statements
- `PLW0603` — global statement (existing pattern)
- `ARG001/002` — unused arguments (common in callbacks/handlers)
- `B008` — function calls in default args (Flask patterns)
- `RET504` — unnecessary assignment before return
- `SIM108` — ternary operator (readability preference)
- `PTH123` — `open()` vs `Path.open()` (acceptable pattern)
- `ISC001` — single-line implicit string concat (conflicts with formatter)
- `ERA001` — commented-out code (documentation/examples that should stay)
- `RUF001` — ambiguous Unicode characters (intentional in logs)

Per-file overrides:
- `__init__.py`: `F401` ignored (re-exports)
- `tests/*`: Relaxed rules (`F401`, `F811`, `ARG`, `PLR`, `PT`, `B011`, `PLC0415`, `N806`, `N803`)
- `pbx/api/rest_api.py`: All rules ignored (deprecated file)
- `pbx/features/*`, `pbx/core/*`, `pbx/api/routes/*`, `pbx/api/app.py`, `pbx/api/server.py`, `pbx/api/utils.py`, `pbx/api/license_api.py`, `pbx/api/opensource_integration_api.py`, `pbx/rtp/handler.py`, `pbx/main.py`, `pbx/utils/*`, `pbx/integrations/*`: `PLC0415` ignored (lazy imports intentional)
- `scripts/*`: `PLC0415`, `PLW1510`, `PT028` ignored

## Known Technical Debt

### Security

| Item | File(s) | Description |
|------|---------|-------------|
| CSP unsafe-inline | `pbx/api/app.py` | CSP still uses `unsafe-inline` for `script-src` and `style-src`. Removing this requires nonce-based CSP, which is a larger refactoring effort. CORS origin restriction and `connect-src` tightening are complete. |

### Backend

| Item | File(s) | Description |
|------|---------|-------------|
| SELECT * in BI queries | `pbx/features/bi_integration.py`, `data_residency_controls.py`, `speech_analytics.py` | A few `SELECT *` queries remain for BI/data warehouse tables (`call_detail_records`, `call_queue_stats`, `qos_metrics`, `call_summaries`, `data_residency_records`) whose schemas are not defined in the codebase. These are acceptable for generic data export use cases. |

### Database

| Item | File(s) | Description |
|------|---------|-------------|
| Single Alembic migration | `alembic/versions/` | Only `001_initial_schema.py` exists. Migration discipline documentation has been added to the file. Feature modules use runtime `CREATE TABLE IF NOT EXISTS` via `pbx/utils/migrations.py`. Future core table changes must use Alembic. |

## Deployment

- **Ubuntu setup**: `scripts/setup_ubuntu.py` (automated wizard)
- **Production deploy**: `scripts/deploy_production_pilot.sh`
- **Reverse proxy**: `scripts/setup_reverse_proxy.sh` (Nginx) or Apache variant
- **SSL certs**: `scripts/generate_ssl_cert.py`
- **Kubernetes**: manifests in `kubernetes/`
- **Terraform**: IaC in `terraform/`
- **Monitoring**: Grafana dashboards in `grafana/`
