#!/usr/bin/env bash
set -Eeuo pipefail

echo "=== [BOOT] ÉMERGENCE entrypoint ==="
echo "PWD=$(pwd)"
echo "PYTHONPATH=${PYTHONPATH:-<none>}"
echo "PORT=${PORT:-<none>}"
echo "ENV:"
env | sort

echo "=== [LS] /app ==="
ls -la /app || true
echo "=== [LS] /app/src ==="
ls -la /app/src || true
echo "=== [LS] /app/src/backend ==="
ls -la /app/src/backend || true

echo "=== [PY] Version & site-packages ==="
python -V
python - <<'PY'
import sys, os, importlib.util
print("sys.path:", sys.path)
print("CWD:", os.getcwd())
print("Check file exists:", os.path.exists("/app/src/backend/main.py"))
try:
    import backend.main as m
    print("Import backend.main: OK")
    print("Has 'app' attr:", hasattr(m, "app"))
except Exception as e:
    print("Import backend.main FAILED:", repr(e))
    raise
PY

echo "=== [FS] Prépare /tmp/data (writable) & symlink ==="
mkdir -p /tmp/data
[ -L /app/data ] || { rm -rf /app/data; ln -s /tmp/data /app/data; }
echo "stat /app/data ->"
ls -la /app | sed -n '1,200p'
echo "stat /tmp/data ->"
ls -la /tmp/data

echo "=== [RUN] Lance Uvicorn sur ${PORT:-8080} ==="
exec uvicorn backend.main:app --host 0.0.0.0 --port "${PORT:-8080}" --log-level debug
