#!/bin/bash
# Codex GPT Cloud bootstrap script for Emergence V8
# Usage: bash scripts/setup-codex-cloud.sh

set -euo pipefail

echo "[codex-cloud] Starting environment bootstrap..."

REPO_DIR="/workspace/emergencev8"
if [ -d "$REPO_DIR" ]; then
  cd "$REPO_DIR"
else
  echo "[codex-cloud] Repository not found at /workspace/emergencev8; using $(pwd)"
fi

if [ ! -f "package.json" ] || [ ! -d "src" ]; then
  echo "[codex-cloud] ERROR: This script must be executed from the project root."
  exit 1
fi

PYTHON_VERSION="${PYTHON_VERSION:-3.11}"
PYTHON_BIN=""
for candidate in "python${PYTHON_VERSION}" "python${PYTHON_VERSION%.*}" python3 python; do
  if command -v "$candidate" >/dev/null 2>&1; then
    PYTHON_BIN="$candidate"
    break
  fi
done

if [ -z "$PYTHON_BIN" ]; then
  echo "[codex-cloud] ERROR: Python ${PYTHON_VERSION} was not found in PATH."
  echo "[codex-cloud] Install the requested Python version or expose it via PYTHON_BIN before rerunning."
  exit 1
fi

echo "[codex-cloud] Using Python binary: $PYTHON_BIN"
if [ ! -d ".venv" ]; then
  echo "[codex-cloud] Creating virtual environment (.venv)..."
  "$PYTHON_BIN" -m venv .venv
fi

# shellcheck disable=SC1091
source .venv/bin/activate
echo "[codex-cloud] Python virtualenv activated."

echo "[codex-cloud] Upgrading pip..."
python -m pip install --upgrade pip

if [ -f "requirements.txt" ]; then
  echo "[codex-cloud] Installing Python dependencies (requirements.txt)..."
  pip install -r requirements.txt
else
  echo "[codex-cloud] WARNING: requirements.txt not found; skipping Python dependency installation."
fi

NODE_VERSION="${NODE_VERSION:-18}"
ensure_node() {
  if command -v npm >/dev/null 2>&1 && command -v node >/dev/null 2>&1; then
    return 0
  fi

  if [ -z "${NVM_DIR:-}" ]; then
    for candidate_dir in "$HOME/.nvm" "/usr/local/share/nvm"; do
      if [ -s "$candidate_dir/nvm.sh" ]; then
        export NVM_DIR="$candidate_dir"
        break
      fi
    done
  fi

  if [ -z "${NVM_DIR:-}" ]; then
    export NVM_DIR="$HOME/.nvm"
    echo "[codex-cloud] Installing nvm into $NVM_DIR..."
    curl -fsSL https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.7/install.sh | bash >/dev/null
  fi

  if [ ! -s "$NVM_DIR/nvm.sh" ]; then
    echo "[codex-cloud] ERROR: nvm is not available at $NVM_DIR/nvm.sh."
    return 1
  fi

  # shellcheck disable=SC1090
  source "$NVM_DIR/nvm.sh"
  nvm install "${NODE_VERSION}" >/dev/null
  nvm use "${NODE_VERSION}" >/dev/null
}

echo "[codex-cloud] Ensuring Node.js ${NODE_VERSION}..."
ensure_node
echo "[codex-cloud] Node version: $(node --version)"
echo "[codex-cloud] npm version:  $(npm --version)"

if [ -f "package-lock.json" ]; then
  echo "[codex-cloud] Installing Node dependencies (npm ci)..."
  npm ci
else
  echo "[codex-cloud] WARNING: package-lock.json not found; skipping npm ci."
fi

missing=()

if [ ! -f "SYNC_STATUS.md" ]; then
  missing+=("SYNC_STATUS.md")
fi

if [ ! -f "AGENT_SYNC_CODEX.md" ]; then
  if [ -f "AGENT_SYNC.md" ]; then
    echo "[codex-cloud] WARNING: AGENT_SYNC_CODEX.md missing; legacy AGENT_SYNC.md detected."
  else
    missing+=("AGENT_SYNC_CODEX.md")
  fi
fi

if [ ! -f "docs/passation_codex.md" ]; then
  if [ -f "docs/passation.md" ]; then
    echo "[codex-cloud] WARNING: docs/passation_codex.md missing; legacy docs/passation.md detected."
  else
    missing+=("docs/passation_codex.md")
  fi
fi

if [ "${#missing[@]}" -gt 0 ]; then
  echo "[codex-cloud] ERROR: Required files are missing: ${missing[*]}"
  echo "[codex-cloud] Verify that the repository was cloned correctly."
  exit 1
fi

echo "[codex-cloud] Environment bootstrap completed successfully."
echo "[codex-cloud] Next steps:"
echo "  - Review SYNC_STATUS.md, AGENT_SYNC_CODEX.md, docs/passation_codex.md."
echo "  - Run project tests as needed (npm run build, pytest, etc.)."
