#!/bin/bash
# ---------------------------------------------------------------------------
# Warden VoIP PBX — systemd pre-start validation
# ---------------------------------------------------------------------------
# Called by ExecStartPre in pbx.service.  Validates prerequisites and runs
# Alembic database migrations when available.
#
# Exit codes:
#   0 — all checks passed (migrations ran or were skipped gracefully)
#   1 — fatal error (missing project files, no Python interpreter, etc.)
# ---------------------------------------------------------------------------

set -euo pipefail

# Resolve paths relative to this script's location
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PBX_ROOT="$(dirname "$SCRIPT_DIR")"

echo "PBX pre-start: project root = $PBX_ROOT"

# ---------- Validate project root ----------

if [ ! -f "$PBX_ROOT/main.py" ]; then
    echo "FATAL: main.py not found at $PBX_ROOT/main.py" >&2
    exit 1
fi

# ---------- Validate config.yml ----------

if [ ! -f "$PBX_ROOT/config.yml" ]; then
    echo "FATAL: config.yml not found at $PBX_ROOT/config.yml" >&2
    exit 1
fi

# Check that the configured API port is not already in use
API_PORT=$(grep -A2 '^api:' "$PBX_ROOT/config.yml" | grep 'port:' | head -1 | sed 's/.*port: *//' | tr -d '[:space:]')
if [ -n "$API_PORT" ] && command -v ss >/dev/null 2>&1; then
    if ss -tlnp 2>/dev/null | grep -q ":${API_PORT} "; then
        echo "WARNING: port $API_PORT is already in use — PBX API may fail to bind" >&2
        ss -tlnp 2>/dev/null | grep ":${API_PORT} " >&2
    else
        echo "PBX pre-start: API port $API_PORT is available"
    fi
fi

# ---------- Locate Python interpreter ----------

PYTHON=""
for venv_dir in "$PBX_ROOT/venv" "$PBX_ROOT/.venv"; do
    if [ -x "$venv_dir/bin/python3" ]; then
        PYTHON="$venv_dir/bin/python3"
        break
    fi
done
if [ -z "$PYTHON" ]; then
    PYTHON="$(command -v python3 || true)"
fi

if [ -z "$PYTHON" ] || [ ! -x "$PYTHON" ]; then
    echo "FATAL: no Python 3 interpreter found (checked venv/, .venv/, and PATH)" >&2
    exit 1
fi

echo "PBX pre-start: Python = $PYTHON"

# ---------- Check critical Python dependencies ----------

if ! "$PYTHON" -c "import yaml" 2>/dev/null; then
    echo "FATAL: PyYAML is not installed in $PYTHON" >&2
    echo "  Fix: $PYTHON -m pip install 'PyYAML>=6.0.3'" >&2
    exit 1
fi
echo "PBX pre-start: critical Python dependencies OK"

# ---------- Run Alembic migrations (if available) ----------

ALEMBIC=""
for venv_dir in "$PBX_ROOT/venv" "$PBX_ROOT/.venv"; do
    if [ -x "$venv_dir/bin/alembic" ]; then
        ALEMBIC="$venv_dir/bin/alembic"
        break
    fi
done
if [ -z "$ALEMBIC" ]; then
    ALEMBIC="$(command -v alembic || true)"
fi

ALEMBIC_INI="$PBX_ROOT/alembic.ini"

if [ -n "$ALEMBIC" ] && [ -f "$ALEMBIC_INI" ]; then
    echo "PBX pre-start: running Alembic migrations..."
    cd "$PBX_ROOT"
    "$ALEMBIC" -c "$ALEMBIC_INI" upgrade head
    echo "PBX pre-start: migrations complete"
else
    echo "PBX pre-start: skipping Alembic migrations"
    if [ -z "$ALEMBIC" ]; then
        echo "  reason: alembic binary not found (install with: uv pip install -e .)"
    fi
    if [ ! -f "$ALEMBIC_INI" ]; then
        echo "  reason: $ALEMBIC_INI not found"
    fi
fi

# ---------- Create required runtime directories ----------

for subdir in logs recordings voicemail cdr moh; do
    mkdir -p "$PBX_ROOT/$subdir"
done

echo "PBX pre-start: all checks passed"
