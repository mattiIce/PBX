# Modernization Follow-Up Items

Items identified during the Python 3.13+ modernization sweep that are too large
for this PR and should be addressed in separate follow-up PRs.

---

## ~~1. Migrate `datetime.now()` to timezone-aware~~ DONE

Completed: All ~329 occurrences of `datetime.now()` migrated to
`datetime.now(timezone.utc)` and 4 `datetime.fromtimestamp()` calls updated
with `tz=timezone.utc` across 88 files.

---

## ~~2. Narrow broad `except Exception` blocks~~ DONE

Completed: Broad `except Exception` blocks narrowed to specific exception types
across the entire codebase. Remaining `except Exception` blocks are intentionally
kept at top-level entry points (signal handlers, main loops, route-level catch-alls).

---

## ~~3. Bump GitHub Actions to latest versions~~ DONE

Completed:
- `docker/setup-buildx-action` @v3 → @v4
- `8398a7/action-slack` @v3 → @v4
- `gitleaks/gitleaks-action` @v2 → @v3
- `aquasecurity/trivy-action` @0.34.0 was already latest

---

## 1. Gradual `os.path` to `pathlib.Path` migration

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

## ~~5. Resolve Python version strategy~~ DONE

Completed: Aligned all environments to Python 3.13 (Dockerfile, devcontainer,
and CI workflows).

---

## ~~6. Deduplicate test dependencies in pyproject.toml~~ DONE

Completed: `dev` group now includes `pbx[test]` instead of duplicating pytest
dependencies.
