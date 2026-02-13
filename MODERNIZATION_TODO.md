# Modernization Follow-Up Items

All items identified during the Python 3.13+ modernization sweep have been
completed.

---

## ~~1. Migrate `datetime.now()` to timezone-aware~~ DONE

Completed: All ~329 occurrences of `datetime.now()` migrated to
`datetime.now(timezone.utc)` and 4 `datetime.fromtimestamp()` calls updated
with `tz=timezone.utc` across 88 files.

---

## ~~2. Narrow broad `except Exception` blocks~~ DONE

Completed: ~695 broad `except Exception` blocks narrowed to specific exception
types across the entire codebase. Remaining `except Exception` blocks are
intentionally kept at top-level entry points (signal handlers, main loops,
route-level catch-alls).

---

## ~~3. Bump GitHub Actions to latest versions~~ DONE

Completed:
- `docker/setup-buildx-action` @v3 → @v4
- `8398a7/action-slack` @v3 → @v4
- `gitleaks/gitleaks-action` @v2 → @v3
- `aquasecurity/trivy-action` @0.34.0 was already latest

---

## ~~4. Migrate `os.path` to `pathlib.Path`~~ DONE

Completed: ~322 `os.path.*` calls migrated to `pathlib.Path` equivalents across
103 files. Only 1 intentional `os.path` reference remains (mock patch string in
test).

---

## ~~5. Resolve Python version strategy~~ DONE

Completed: Aligned all environments to Python 3.13 (Dockerfile, devcontainer,
and CI workflows).

---

## ~~6. Deduplicate test dependencies in pyproject.toml~~ DONE

Completed: `dev` group now includes `pbx[test]` instead of duplicating pytest
dependencies.
