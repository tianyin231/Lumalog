#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FRONTEND_PORT="${FRONTEND_PORT:-7012}"
BACKEND_PORT="${BACKEND_PORT:-7014}"
VENV_DIR="$ROOT_DIR/Mi-Fitness-Sync-main/.venv"
BACKEND_PY="$VENV_DIR/bin/python"
export NPM_CONFIG_CACHE="${NPM_CONFIG_CACHE:-$ROOT_DIR/.npm-cache}"

select_python() {
  if [ -n "${PYTHON_BIN:-}" ]; then
    echo "$PYTHON_BIN"
    return
  fi

  for candidate in python3.13 python3.12 python3; do
    if command -v "$candidate" >/dev/null 2>&1 && "$candidate" - <<'PY'
import sys
raise SystemExit(0 if sys.version_info >= (3, 12) else 1)
PY
    then
      echo "$candidate"
      return
    fi
  done
}

run_with_sudo() {
  if [ "$(id -u)" -eq 0 ]; then
    "$@"
  else
    sudo "$@"
  fi
}

install_python() {
  echo "Python 3.12 or newer was not found. Trying to install Python 3.12..."

  if command -v apt-get >/dev/null 2>&1; then
    run_with_sudo apt-get update
    run_with_sudo apt-get install -y python3.12 python3.12-venv python3.12-dev
    return
  fi

  if command -v dnf >/dev/null 2>&1; then
    run_with_sudo dnf install -y python3.12 python3.12-devel
    return
  fi

  if command -v yum >/dev/null 2>&1; then
    run_with_sudo yum install -y python3.12 python3.12-devel
    return
  fi

  if command -v brew >/dev/null 2>&1; then
    brew install python@3.12
    return
  fi

  echo "No supported package manager was found."
  echo "Install Python 3.12+ manually or run with:"
  echo "  PYTHON_BIN=/path/to/python3.12 ./start.sh"
  exit 1
}

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

PYTHON_BIN="$(select_python)"

if [ -z "$PYTHON_BIN" ]; then
  install_python
  PYTHON_BIN="$(select_python)"

  if [ -z "$PYTHON_BIN" ]; then
    echo "Python 3.12 installation finished, but no compatible Python command was found."
    echo "Run with:"
    echo "  PYTHON_BIN=/path/to/python3.12 ./start.sh"
    exit 1
  fi
fi

if [ ! -d "$ROOT_DIR/frontend/node_modules" ]; then
  echo "[1/5] Installing frontend dependencies..."
  (cd "$ROOT_DIR/frontend" && npm install)
else
  echo "[1/5] Frontend dependencies OK"
fi

if [ ! -x "$BACKEND_PY" ]; then
  echo "[2/5] Creating backend virtual environment..."
  require_command "$PYTHON_BIN"
  check_python_version "$PYTHON_BIN"
  "$PYTHON_BIN" -m venv "$VENV_DIR"
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
