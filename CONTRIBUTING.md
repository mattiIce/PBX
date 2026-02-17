# Contributing to Warden VoIP

Thank you for your interest in contributing to Warden VoIP! We welcome bug reports, feature requests, documentation improvements, and code contributions from the community. Please read our [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) before participating.

## Development Environment Setup

### Prerequisites

- Python 3.13+
- Node.js 22+
- System packages:

```bash
sudo apt-get install espeak ffmpeg libopus-dev portaudio19-dev libspeex-dev
```

### Setup Steps

1. Fork and clone the repository:

```bash
git clone https://github.com/your-fork/PBX.git
cd PBX
```

2. Install Python dependencies (uses `uv pip install -e ".[dev]"`):

```bash
make install
```

3. Install frontend dependencies:

```bash
npm ci
```

4. Install pre-commit hooks:

```bash
make pre-commit-install
```

5. Verify everything works:

```bash
make check
```

## Code Style

### Python

- **Linter / Formatter**: `ruff` — run with `make lint` or `make format`
- **Line length**: 100 characters
- **Quotes**: Double quotes
- **Indentation**: 4 spaces
- **Line endings**: LF only (enforced by `.editorconfig` and pre-commit)
- **Type annotations**: Required — mypy strict mode is enabled for `api/`, `core/`, and `models/`
- **Datetimes**: Always timezone-aware — use `datetime.now(tz=UTC)`, never bare `datetime.now()`
- **File paths**: Use `pathlib.Path`, not `os.path`
- **Exceptions**: Use specific exception types, not bare `except Exception`

### TypeScript (Frontend)

- **Mode**: Strict
- **Target**: ES2024
- **Build tool**: Vite
- **Testing**: Jest with jsdom

## Testing

Run the test suites with:

```bash
make test-python    # All Python tests via pytest
make test-js        # All JavaScript tests via Jest
make test-unit      # Unit tests only: pytest -m unit
make test-integration  # Integration tests only: pytest -m integration
make test-cov       # With coverage report (80% minimum required)
```

### Pytest Markers

Tag your tests with the appropriate marker:

- `@pytest.mark.unit` — fast, isolated unit tests
- `@pytest.mark.integration` — tests that require external services or a running server
- `@pytest.mark.slow` — long-running tests

### Shared Fixtures

Use the shared fixtures from `tests/conftest.py` rather than creating ad-hoc mocks:

- `mock_config` — pre-configured YAML config object
- `mock_database` — in-memory SQLite database session
- `mock_extension` — a stubbed Extension model instance
- `mock_pbx_core` — a mocked PBXCore singleton
- `api_client` — Flask test client for API route tests
- `sip_message_factory` — factory for constructing SIP protocol messages

Frontend tests use Jest with jsdom. Place test files under `admin/tests/`.

## Pull Request Process

1. Fork the repository and create a feature branch off `main`.
2. Make your changes and ensure the full check suite passes:

```bash
make check
```

3. Push your branch and open a pull request with a descriptive title explaining the change.
4. At least one maintainer approval and all CI checks passing are required before merging.
5. PRs are merged via squash-merge to keep the commit history clean.

## Commit Conventions

Use the following format for commit messages:

```
type(scope): short description under 72 chars

Optional longer body explaining the why, not the what.
```

Valid types:

- `feat` — new feature
- `fix` — bug fix
- `docs` — documentation only
- `style` — formatting, no logic change
- `refactor` — code restructuring, no behaviour change
- `test` — adding or updating tests
- `chore` — build process, dependency updates
- `ci` — CI/CD configuration changes

Keep the first line under 72 characters.

## Reporting Bugs

Please open an issue on [GitHub Issues](https://github.com/mattiIce/PBX/issues) and include:

- A clear description of the problem
- Steps to reproduce
- Expected vs. actual behaviour
- Python/Node.js version and OS
