#!/usr/bin/env bash
set -euo pipefail

REMOTE_NAME="origin"
DEFAULT_REMOTE_URL="https://github.com/DrKz36/emergencev8.git"
REMOTE_URL="$DEFAULT_REMOTE_URL"
START_SCRIPT="start"
SKIP_START=0

usage() {
  cat <<'EOF'
Usage: scripts/bootstrap.sh [options]

Options:
  --remote-name NAME   Git remote name to manage (default: origin)
  --remote-url URL     Remote URL to add or update (default: https://github.com/DrKz36/emergencev8.git)
  --start-script NAME  NPM script to launch (default: start)
  --skip-start         Configure remote only, do not run npm
  -h, --help           Show this help message
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --remote-name)
      REMOTE_NAME="$2"
      shift 2
      ;;
    --remote-url)
      REMOTE_URL="$2"
      shift 2
      ;;
    --start-script)
      START_SCRIPT="$2"
      shift 2
      ;;
    --skip-start)
      SKIP_START=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      usage
      exit 1
      ;;
  esac
done

if [[ -z "$REMOTE_URL" ]]; then
  echo "Remote URL cannot be empty. Provide --remote-url or rely on the default." >&2
  exit 1
fi

if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "This script must run from the repository root." >&2
  exit 1
fi

if git remote | grep -qx "$REMOTE_NAME"; then
  current_url=$(git remote get-url "$REMOTE_NAME")
  if [[ "$current_url" != "$REMOTE_URL" ]]; then
    git remote set-url "$REMOTE_NAME" "$REMOTE_URL"
    echo "Updated remote '$REMOTE_NAME' -> $REMOTE_URL"
  fi
else
  git remote add "$REMOTE_NAME" "$REMOTE_URL"
  echo "Added remote '$REMOTE_NAME' -> $REMOTE_URL"
fi

if [[ $SKIP_START -eq 0 ]]; then
  echo "Starting npm script '$START_SCRIPT'..."
  npm run "$START_SCRIPT"
fi
