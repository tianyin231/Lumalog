#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FRONTEND_PORT="${FRONTEND_PORT:-7012}"
BACKEND_PORT="${BACKEND_PORT:-7014}"
VENV_DIR="$ROOT_DIR/Mi-Fitness-Sync-main/.venv"
BACKEND_PY="$VENV_DIR/bin/python"

cd "$ROOT_DIR"

echo "========================================"
echo "  Lumalog - macOS/Linux start script"
echo "========================================"
echo

require_command() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "$1 was not found. Please install it first."
    exit 1
  fi
}

require_command npm

check_python_version() {
  "$1" - <<'PY'
import sys
if sys.version_info < (3, 12):
    print("Python 3.12 or newer is required.")
    print("Current:", sys.version.split()[0])
    raise SystemExit(1)
PY
}

if [ ! -d "$ROOT_DIR/frontend/node_modules" ]; then
  echo "[1/5] Installing frontend dependencies..."
  (cd "$ROOT_DIR/frontend" && npm install)
else
  echo "[1/5] Frontend dependencies OK"
fi

if [ ! -x "$BACKEND_PY" ]; then
  echo "[2/5] Creating backend virtual environment..."
  require_command python3
  check_python_version python3
  python3 -m venv "$VENV_DIR"
else
  echo "[2/5] Backend virtual environment OK"
  check_python_version "$BACKEND_PY"
fi

echo "[3/5] Installing backend dependencies..."
(cd "$ROOT_DIR/backend" && "$BACKEND_PY" -m pip install -r requirements.txt)

echo "[4/5] Checking Playwright..."
"$BACKEND_PY" - <<'PY'
from pathlib import Path
from tempfile import TemporaryDirectory
from playwright.sync_api import sync_playwright

errors = []
with sync_playwright() as p:
    for channel in ("chrome", "msedge"):
        try:
            with TemporaryDirectory() as tmp:
                context = p.chromium.launch_persistent_context(tmp, channel=channel, headless=True)
                context.close()
            print(f"{channel}: ok")
            break
        except Exception as exc:
            errors.append(f"{channel}: {exc}")
    else:
        print("Chrome or Edge is required for Xiaomi two-step verification.")
        print("\n".join(errors))
        raise SystemExit(1)
PY

cleanup() {
  if [ -n "${BACKEND_PID:-}" ] && kill -0 "$BACKEND_PID" >/dev/null 2>&1; then
    kill "$BACKEND_PID" >/dev/null 2>&1 || true
  fi
  if [ -n "${FRONTEND_PID:-}" ] && kill -0 "$FRONTEND_PID" >/dev/null 2>&1; then
    kill "$FRONTEND_PID" >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT INT TERM

echo "[5/5] Starting development servers..."
echo
echo "Backend:  http://localhost:$BACKEND_PORT  API docs: http://localhost:$BACKEND_PORT/docs"
echo "Frontend: http://localhost:$FRONTEND_PORT"
echo

(
  cd "$ROOT_DIR/backend"
  FRONTEND_PORT="$FRONTEND_PORT" BACKEND_PORT="$BACKEND_PORT" \
    "$BACKEND_PY" -m uvicorn main:app --reload --reload-dir app --port "$BACKEND_PORT"
) &
BACKEND_PID=$!

(
  cd "$ROOT_DIR/frontend"
  FRONTEND_PORT="$FRONTEND_PORT" BACKEND_PORT="$BACKEND_PORT" \
    npm run dev -- --host 127.0.0.1 --port "$FRONTEND_PORT"
) &
FRONTEND_PID=$!

echo "Press Ctrl+C to stop both servers."
wait "$BACKEND_PID" "$FRONTEND_PID"
