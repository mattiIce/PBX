# Modernization Follow-Up Items

Items identified during the Python 3.13+ modernization sweep that are too large
for this PR and should be addressed in separate follow-up PRs.

---

## 1. Migrate `datetime.now()` to timezone-aware (`datetime.now(timezone.utc)`)

**Priority:** High
**Scope:** ~325 occurrences across ~60 files
**Effort:** Large

The codebase has ~325 instances of `datetime.now()` without a timezone parameter,
creating naive datetimes. Since Python 3.12, timezone-naive usage is discouraged.
There are also 4 instances of `datetime.fromtimestamp()` without timezone.

### Key files

- `pbx/core/call.py` - Call start/end timestamps
- `pbx/core/pbx.py` - System timestamps
- `pbx/features/bi_integration.py` - Export timestamps (12+ occurrences)
- `pbx/features/advanced_call_features.py` - Feature timing
- `pbx/features/ai_call_routing.py` - Routing timestamps
- `pbx/features/call_blending.py` - Queue timing
- `pbx/features/call_parking.py` - Park timing
- `pbx/features/recording_retention.py` - `fromtimestamp()` without tz (3 locations)
- `scripts/import_merlin_voicemail.py` - `fromtimestamp()` without tz (1 location)
- Plus ~50 more files in `pbx/features/`, `pbx/utils/`, `pbx/integrations/`

### Approach

1. Add `from datetime import timezone` to affected files
2. Replace `datetime.now()` with `datetime.now(timezone.utc)`
3. Replace `datetime.fromtimestamp(ts)` with `datetime.fromtimestamp(ts, tz=timezone.utc)`
4. Review all datetime arithmetic to ensure both operands are timezone-aware
5. Run full test suite - naive vs aware comparison will raise `TypeError`

---

## 2. Narrow broad `except Exception` blocks

**Priority:** Medium
**Scope:** ~1030 occurrences
**Effort:** Very Large

The codebase has ~1030 broad `except Exception` blocks that mask specific errors
and make debugging harder. Each should be analyzed to catch only the exceptions
actually expected.

### Highest-impact files

- `pbx/utils/database.py` - 13+ broad catches around DB operations
- `pbx/utils/config.py` - 8+ broad catches around config parsing
- `pbx/utils/licensing.py` - 7+ broad catches
- `pbx/utils/production_health.py` - 8+ broad catches
- `pbx/utils/graceful_shutdown.py` - 6+ broad catches
- `pbx/core/pbx.py` - 10+ broad catches
- `pbx/core/voicemail_handler.py` - 8+ broad catches

### Approach

This is best done module-by-module. For each `except Exception`:
1. Identify what exceptions the `try` block can actually raise
2. Replace with specific exception types (e.g., `OSError`, `ValueError`, `KeyError`)
3. Keep `except Exception` only at top-level entry points (signal handlers, main loops)

---

## 3. Bump GitHub Actions to latest versions

**Priority:** Medium
**Scope:** 5 version bumps across 2 workflow files
**Effort:** Small

### Stale action versions

| File | Action | Current | Recommended |
|------|--------|---------|-------------|
| `production-deployment.yml:77` | `docker/setup-buildx-action` | `@v3` | `@v4` |
| `production-deployment.yml:187,221` | `8398a7/action-slack` | `@v3` | `@v4` |
| `security-scanning.yml:111` | `gitleaks/gitleaks-action` | `@v2` | `@v3` |
| `security-scanning.yml:129` | `aquasecurity/trivy-action` | `@0.34.0` | Latest stable |
| `production-deployment.yml:276` | `aquasecurity/trivy-action` | `@0.34.0` | Latest stable |

---

## 4. Gradual `os.path` to `pathlib.Path` migration

**Priority:** Low
**Scope:** ~311 occurrences
**Effort:** Very Large

The codebase has ~311 uses of `os.path` functions (`os.path.join`,
`os.path.exists`, `os.path.isfile`, etc.) that could use `pathlib.Path` for
more idiomatic modern Python.

### Approach

Do not mass-replace. Instead:
1. Use `pathlib.Path` in all new code going forward
2. Migrate module-by-module when touching files for other reasons
3. Prioritize library code (`pbx/`) over scripts and tests

---

## 5. Resolve Python version strategy (3.13 vs 3.14)

**Priority:** Low
**Scope:** 3 files
**Effort:** Small

The Dockerfile uses Python 3.14, while the devcontainer uses 3.13. Both are
within the `requires-python = ">=3.13"` range, but the inconsistency may cause
subtle differences between development and containerized deployment.

### Files

- `Dockerfile` lines 3, 32: `FROM python:3.14-slim-bookworm`
- `.devcontainer/devcontainer.json` line 3: `python:3.13`
- All CI workflows: `python-version: '3.13'`

### Decision needed

Either:
- Align everything to 3.13 (conservative), or
- Bump devcontainer and CI to 3.14 to match Dockerfile (aggressive)

---

## 6. Deduplicate test dependencies in pyproject.toml

**Priority:** Low
**Scope:** 1 file
**Effort:** Tiny

Testing dependencies (pytest, pytest-cov, pytest-asyncio, pytest-timeout,
pytest-mock) are duplicated in both the `dev` and `test` optional dependency
groups in `pyproject.toml`. This creates a maintenance burden - version updates
must be made in two places.

### Approach

Have `dev` include `test` as a dependency:
```toml
[project.optional-dependencies]
test = [
    "pytest>=9.0.2",
    "pytest-cov>=7.0.0",
    # ...
]
dev = [
    "pbx[test]",  # Include test deps
    "ruff>=0.9",
    # ...
]
```
