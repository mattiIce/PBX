# Contributing to PBX System

Thank you for your interest in contributing to the PBX System! This document provides guidelines and instructions for contributing to the project.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Making Changes](#making-changes)
- [Coding Standards](#coding-standards)
- [Testing](#testing)
- [Submitting Changes](#submitting-changes)
- [Reporting Bugs](#reporting-bugs)
- [Feature Requests](#feature-requests)

## Code of Conduct

By participating in this project, you agree to abide by our [Code of Conduct](CODE_OF_CONDUCT.md). Please read it before contributing.

## Getting Started

1. Fork the repository on GitHub
2. Clone your fork locally:
   ```bash
   git clone https://github.com/YOUR_USERNAME/PBX.git
   cd PBX
   ```
3. Add the upstream repository:
   ```bash
   git remote add upstream https://github.com/mattiIce/PBX.git
   ```

## Development Setup

### Prerequisites

- Python 3.12 or higher (Python 3.12.3 recommended)
- PostgreSQL (optional, but recommended for full functionality)
- System dependencies (espeak, ffmpeg, libopus-dev, portaudio19-dev)

### Install Dependencies

1. Install system dependencies (Ubuntu/Debian):
   ```bash
   sudo apt-get update
   sudo apt-get install -y espeak ffmpeg libopus-dev portaudio19-dev libspeex-dev
   ```

2. Create a virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   pip install -r requirements-dev.txt
   ```

4. Install pre-commit hooks:
   ```bash
   pre-commit install
   ```

### Configuration

1. Copy the example environment file:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` with your configuration settings

3. Copy the example configuration:
   ```bash
   cp config.yml your_config.yml
   ```

## Making Changes

### Branch Naming

Use descriptive branch names following this pattern:
- `feature/description` - For new features
- `bugfix/description` - For bug fixes
- `hotfix/description` - For urgent production fixes
- `docs/description` - For documentation changes
- `refactor/description` - For code refactoring

### Commit Messages

Follow these guidelines for commit messages:
- Use the present tense ("Add feature" not "Added feature")
- Use the imperative mood ("Move cursor to..." not "Moves cursor to...")
- Limit the first line to 72 characters or less
- Reference issues and pull requests liberally after the first line
- Consider starting the commit message with an applicable emoji:
  - ✨ `:sparkles:` - New feature
  - 🐛 `:bug:` - Bug fix
  - 📝 `:memo:` - Documentation
  - 🎨 `:art:` - Code style/formatting
  - ♻️ `:recycle:` - Refactoring
  - ✅ `:white_check_mark:` - Tests
  - 🔒 `:lock:` - Security
  - ⬆️ `:arrow_up:` - Dependencies upgrade
  - 🚀 `:rocket:` - Performance

## Coding Standards

### Python Style Guide

We follow PEP 8 with some modifications:
- Line length: 100 characters
- Use type hints where possible
- Write docstrings for all public functions, classes, and modules

### Code Quality Tools

We use several tools to maintain code quality:

- **Black**: Code formatting
  ```bash
  black pbx/ tests/
  ```

- **isort**: Import sorting
  ```bash
  isort pbx/ tests/
  ```

- **flake8**: Linting
  ```bash
  flake8 pbx/ tests/
  ```

- **pylint**: Static analysis
  ```bash
  pylint pbx/
  ```

- **mypy**: Type checking
  ```bash
  mypy pbx/
  ```

### Running All Quality Checks

Use the Makefile for convenience:
```bash
make lint        # Run all linters
make format      # Format code with black and isort
make typecheck   # Run type checking
```

Or run pre-commit on all files:
```bash
pre-commit run --all-files
```

## Testing

### Running Tests

Run the test suite:
```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_basic.py

# Run with coverage
pytest --cov=pbx --cov-report=html

# Run tests matching a pattern
pytest -k "test_sip"
```

### Writing Tests

- Place tests in the `tests/` directory
- Name test files as `test_*.py`
- Name test functions as `test_*`
- Use descriptive test names that explain what is being tested
- Include both positive and negative test cases
- Mock external dependencies
- Aim for high code coverage (target: >80%)

### Test Structure

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

## Submitting Changes

### Pull Request Process

1. Update your fork with the latest upstream changes:
   ```bash
   git fetch upstream
   git rebase upstream/main
   ```

2. Run all tests and quality checks:
   ```bash
   make test
   make lint
   ```

3. Push your changes to your fork:
   ```bash
   git push origin feature/your-feature
   ```

4. Create a Pull Request on GitHub with:
   - A clear title describing the change
   - A detailed description of what changed and why
   - References to related issues (e.g., "Fixes #123")
   - Screenshots (if applicable)
   - Test results

5. Wait for review and address any feedback

### PR Review Checklist

Before submitting, ensure:
- [ ] Code follows the style guide
- [ ] All tests pass
- [ ] New code has tests
- [ ] Documentation is updated
- [ ] Commit messages are clear
- [ ] No unnecessary files are included
- [ ] Pre-commit hooks pass

## Reporting Bugs

### Before Submitting a Bug Report

- Check the existing issues to avoid duplicates
- Try to reproduce the bug with the latest version
- Collect relevant information (logs, configuration, environment)

### Bug Report Template

```markdown
**Describe the bug**
A clear and concise description of what the bug is.

**To Reproduce**
Steps to reproduce the behavior:
1. Configure '...'
2. Run command '...'
3. See error

**Expected behavior**
A clear description of what you expected to happen.

**Environment:**
- OS: [e.g., Ubuntu 22.04]
- Python version: [e.g., 3.12 or 3.13]
- PBX System version: [e.g., 1.0.0]

**Logs**
Relevant log output or error messages.

**Additional context**
Any other context about the problem.
```

## Feature Requests

We welcome feature requests! Please:
- Use the GitHub issue tracker
- Provide a clear use case
- Explain why the feature would be valuable
- Consider whether it fits the project's scope
- Be open to discussion and feedback

### Feature Request Template

```markdown
**Is your feature request related to a problem?**
A clear description of the problem. Ex. I'm always frustrated when [...]

**Describe the solution you'd like**
A clear description of what you want to happen.

**Describe alternatives you've considered**
Other solutions or features you've considered.

**Additional context**
Any other context, screenshots, or examples.
```

## Questions?

If you have questions about contributing, feel free to:
- Open a GitHub issue with the "question" label
- Check existing documentation in the `docs/` directory
- Review the README.md file

## License

By contributing to PBX System, you agree that your contributions will be licensed under the same license as the project (MIT License).

Thank you for contributing to PBX System! 🎉
