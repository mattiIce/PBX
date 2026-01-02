# GitHub Copilot Coding Agent Instructions

This file provides instructions for GitHub Copilot Coding Agent when working with the Warden VoIP PBX System.

## Project Overview

Warden VoIP is a comprehensive, feature-rich Private Branch Exchange (PBX) and VoIP system built in Python. It provides full SIP protocol support, RTP media handling, advanced call features, and modern VoIP capabilities.

**Language**: Python 3.12+
**Type**: VoIP/Telephony System
**Architecture**: Event-driven SIP/RTP server with REST API and web admin interface

## Development Setup

### Prerequisites
- Python 3.12.3
- PostgreSQL (recommended for production)
- System dependencies: espeak, ffmpeg, libopus-dev, portaudio19-dev, libspeex-dev

### Installation

1. **Install system dependencies** (Ubuntu/Debian):
   ```bash
   sudo apt-get update
   sudo apt-get install -y espeak ffmpeg libopus-dev portaudio19-dev libspeex-dev
   ```

2. **Create and activate virtual environment**:
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install Python dependencies**:
   ```bash
   pip install -r requirements.txt
   pip install -r requirements-dev.txt
   ```

4. **Install pre-commit hooks**:
   ```bash
   pre-commit install
   ```

### Configuration

1. Copy the example environment file:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` with your configuration settings

3. Copy and customize the configuration:
   ```bash
   cp config.yml your_config.yml
   ```

## Building and Running

### Development Mode

Run the PBX server locally:
```bash
python main.py
```

Or using the Makefile:
```bash
make run
```

### Using Docker

Build and run with Docker Compose:
```bash
make docker-build
make docker-up
```

View logs:
```bash
make docker-logs
```

Stop services:
```bash
make docker-down
```

## Code Quality Standards

### Python Style Guide

We follow PEP 8 with these modifications:
- **Line length**: 100 characters
- **Use type hints** where possible
- **Write docstrings** for all public functions, classes, and modules
- **Follow the present tense** in commit messages ("Add feature" not "Added feature")

### Code Quality Tools

All code quality checks are automated via pre-commit hooks and can be run manually:

1. **Black** (Code formatting):
   ```bash
   make black
   # or
   black pbx/ tests/
   ```

2. **isort** (Import sorting):
   ```bash
   make isort
   # or
   isort pbx/ tests/
   ```

3. **flake8** (Linting):
   ```bash
   make flake8
   # or
   flake8 pbx/ tests/
   ```

4. **pylint** (Static analysis):
   ```bash
   make pylint
   # or
   pylint pbx/
   ```

5. **mypy** (Type checking):
   ```bash
   make mypy
   # or
   mypy pbx/
   ```

### Running All Quality Checks

Use the Makefile for convenience:
```bash
make lint        # Run all linters (pylint, flake8, mypy)
make format      # Format code with black and isort
```

Or run pre-commit on all files:
```bash
pre-commit run --all-files
```

## Testing

### Running Tests

The project uses pytest for testing with comprehensive test coverage:

```bash
# Run all tests
pytest
# or
make test

# Run specific test file
pytest tests/test_basic.py

# Run with coverage
pytest --cov=pbx --cov-report=html
# or
make test-cov

# Run tests matching a pattern
pytest -k "test_sip"

# Run unit tests only
pytest -m unit
# or
make test-unit

# Run integration tests only
pytest -m integration
# or
make test-integration
```

### Test Coverage

Coverage reports are generated in the `htmlcov/` directory:
```bash
make test-cov-html
# Open htmlcov/index.html in your browser
```

Target coverage: >80%

### Writing Tests

- Place tests in the `tests/` directory
- Name test files as `test_*.py`
- Name test functions as `test_*`
- Use descriptive test names that explain what is being tested
- Include both positive and negative test cases
- Mock external dependencies
- Use the Arrange-Act-Assert pattern:
  ```python
  def test_feature_description():
      """Test that feature does something specific."""
      # Arrange - Set up test data and conditions
      input_data = create_test_data()
      
      # Act - Execute the code being tested
      result = function_under_test(input_data)
      
      # Assert - Verify the results
      assert result == expected_output
  ```

## Project Structure

```
PBX/
├── pbx/                    # Main source code
│   ├── api/               # REST API implementation
│   ├── core/              # Core PBX functionality
│   ├── features/          # Advanced features (voicemail, auto-attendant, etc.)
│   ├── integrations/      # Third-party integrations (AD, CRM, etc.)
│   ├── rtp/               # RTP media handling
│   ├── sip/               # SIP protocol implementation
│   └── utils/             # Utility functions
├── tests/                 # Test files
├── admin/                 # Admin web interface
├── auto_attendant/        # Auto-attendant configuration
├── provisioning_templates/# Phone provisioning templates
├── config.yml            # Main configuration file
├── main.py               # Entry point
└── requirements.txt      # Python dependencies
```

## Common Development Tasks

### Adding a New Feature

1. Create a feature branch:
   ```bash
   git checkout -b feature/description
   ```

2. Implement the feature following the coding standards

3. Add tests for the new feature

4. Run quality checks:
   ```bash
   make lint
   make format
   make test
   ```

5. Commit changes with a descriptive message:
   ```bash
   git commit -m "✨ Add feature description"
   ```

### Fixing a Bug

1. Create a bugfix branch:
   ```bash
   git checkout -b bugfix/description
   ```

2. Write a failing test that reproduces the bug

3. Fix the bug

4. Ensure the test now passes

5. Run all tests to ensure no regressions:
   ```bash
   make test
   ```

6. Commit with a descriptive message:
   ```bash
   git commit -m "🐛 Fix bug description"
   ```

## Important Conventions

### Commit Message Emojis

Use these emojis to categorize commits:
- ✨ `:sparkles:` - New feature
- 🐛 `:bug:` - Bug fix
- 📝 `:memo:` - Documentation
- 🎨 `:art:` - Code style/formatting
- ♻️ `:recycle:` - Refactoring
- ✅ `:white_check_mark:` - Tests
- 🔒 `:lock:` - Security
- ⬆️ `:arrow_up:` - Dependencies upgrade
- 🚀 `:rocket:` - Performance

### Branch Naming

- `feature/description` - For new features
- `bugfix/description` - For bug fixes
- `hotfix/description` - For urgent production fixes
- `docs/description` - For documentation changes
- `refactor/description` - For code refactoring

## Documentation

Key documentation files:
- `README.md` - Project overview and quick start
- `CONTRIBUTING.md` - Detailed contribution guidelines
- `ARCHITECTURE.md` - System architecture overview
- `API_DOCUMENTATION.md` - REST API documentation
- `INSTALLATION.md` - Installation instructions
- `DEPLOYMENT_GUIDE.md` - Production deployment guide
- `TESTING_GUIDE.md` - Testing guidelines

## Configuration Files

- `.flake8` - Flake8 linting configuration
- `.pylintrc` - Pylint configuration
- `mypy.ini` - MyPy type checking configuration
- `pyproject.toml` - Project metadata and tool configurations
- `.pre-commit-config.yaml` - Pre-commit hooks configuration
- `.editorconfig` - Editor configuration for consistent coding style

## Dependencies

### Production Dependencies

See `requirements.txt` for the complete list. Key dependencies include:
- `PyYAML` - Configuration file parsing
- `cryptography` - Security and encryption
- `twisted` - Event-driven networking
- `SQLAlchemy` - Database ORM
- `flask` - Web framework for API
- `psycopg2-binary` - PostgreSQL driver

### Development Dependencies

See `requirements-dev.txt` for the complete list. Key tools include:
- `pytest` - Testing framework
- `pytest-cov` - Coverage reporting
- `pylint` - Static code analysis
- `flake8` - Code linting
- `black` - Code formatting
- `mypy` - Type checking
- `isort` - Import sorting
- `pre-commit` - Git hook management

## Best Practices

1. **Always run tests before submitting changes**
2. **Use type hints** for function arguments and return values
3. **Write docstrings** for public functions and classes
4. **Keep functions small and focused** - single responsibility principle
5. **Use meaningful variable names** - avoid single-letter variables except in loops
6. **Handle errors gracefully** - use try-except blocks appropriately
7. **Log important events** - use the logging module, not print statements
8. **Avoid hardcoding values** - use configuration files or constants
9. **Write tests first** (TDD) when fixing bugs
10. **Keep commits atomic** - one logical change per commit

## Security Considerations

- Never commit secrets or credentials to the repository
- Use environment variables for sensitive configuration
- Validate and sanitize all user inputs
- Follow secure coding practices for telephony systems
- Be aware of VoIP-specific security concerns (SIP flooding, RTP injection, etc.)

## Getting Help

- Read the documentation in the repository
- Check existing tests for examples
- Review the `CONTRIBUTING.md` file for detailed guidelines
- Look at recent pull requests for code style examples

## Cleanup

Clean up build artifacts and temporary files:
```bash
make clean       # Remove build artifacts, __pycache__, .pyc files
make clean-all   # Deep clean including .venv, .pytest_cache, etc.
```

## Additional Notes

- The PBX system is designed to run on Linux (Ubuntu 24.04 LTS recommended for production)
- The system uses UDP ports 5060 (SIP) and 10000-20000 (RTP)
- The REST API runs on port 8080 (HTTPS) by default
- Always test VoIP features with actual SIP phones or softphones when possible
- Database migrations should be handled carefully in production environments
- Voice prompts must be generated before the system can fully function (see `SETUP_GTTS_VOICES.md`)

## Troubleshooting Development Issues

Common issues and solutions:

1. **Import errors**: Ensure virtual environment is activated and dependencies are installed
2. **Test failures**: Check if all system dependencies are installed
3. **Linting errors**: Run `make format` to auto-fix formatting issues
4. **Type checking errors**: Add type hints or use `# type: ignore` with justification
5. **Pre-commit hook failures**: Fix the issues or use `git commit --no-verify` (not recommended)

---

For more detailed information, always refer to the specific documentation files listed above.
