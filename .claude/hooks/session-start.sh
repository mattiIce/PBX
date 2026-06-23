#!/bin/bash
# Warden VoIP requires Python >=3.13, but the remote base image's default python3
# is 3.11 (mypy can't even parse the project's 3.12+ f-strings under 3.11, and the
# deps won't resolve). This hook builds a 3.13 venv, installs the project + dev
# extras (same as `make install`), and makes that venv the session default so
# `make lint`/`make test` (which call `python3 -m ruff|mypy|pytest`) match CI.
set -euo pipefail
[ "${CLAUDE_CODE_REMOTE:-}" != "true" ] && exit 0   # web sessions only

# Run asynchronously: emit the directive, then the harness starts the session
# while this finishes in the background (asyncTimeout caps the heavy install).
# The venv + PATH are written before the slow install, so the environment is
# usable even if dependency installation is still running or gets timed out.
echo '{"async": true, "asyncTimeout": 600000}'

cd "$CLAUDE_PROJECT_DIR"
VENV="$CLAUDE_PROJECT_DIR/.venv"

# 1. Find a Python >=3.13 interpreter (image ships 3.10-3.13; default is 3.11)
PYBIN=""
for cand in python3.13 python3.14 /usr/bin/python3.13 python3; do
  if command -v "$cand" >/dev/null 2>&1 \
     && "$cand" -c 'import sys; raise SystemExit(0 if sys.version_info[:2] >= (3,13) else 1)' 2>/dev/null; then
    PYBIN="$(command -v "$cand")"; break
  fi
done
[ -z "$PYBIN" ] && PYBIN="$(command -v python3)"   # fallback + warn

# 2. System audio libs CI installs (best-effort, never aborts startup)
if command -v apt-get >/dev/null 2>&1; then
  apt-get install -y --no-install-recommends \
    espeak ffmpeg libopus-dev portaudio19-dev libspeex-dev >/dev/null 2>&1 || true
fi

# 3. Create the 3.13 venv (idempotent)
if [ ! -x "$VENV/bin/python" ] \
   || ! "$VENV/bin/python" -c 'import sys; raise SystemExit(0 if sys.version_info[:2]>=(3,13) else 1)' 2>/dev/null; then
  rm -rf "$VENV"; "$PYBIN" -m venv "$VENV"
fi

# 4. Make the venv the session default (guarded against duplicate appends)
if ! grep -qs "WARDEN_VENV_ON_PATH" "$CLAUDE_ENV_FILE" 2>/dev/null; then
  { echo "# WARDEN_VENV_ON_PATH";
    echo "export VIRTUAL_ENV=\"$VENV\"";
    echo "export PATH=\"$VENV/bin:\$PATH\""; } >> "$CLAUDE_ENV_FILE"
fi

# 5. Install project + dev extras (mirrors `make install`); retried, best-effort
install_deps() { uv pip install --python "$VENV/bin/python" -e ".[dev]"; }
attempt=1
until install_deps; do
  [ "$attempt" -ge 3 ] && { echo "[session-start] deps install incomplete; run 'make install' when network is up"; break; }
  sleep $((2 ** attempt)); attempt=$((attempt + 1))
done
exit 0
