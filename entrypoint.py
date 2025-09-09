#!/usr/bin/env python3
import os, shutil, sys

def ensure_symlink(src: str, dst: str) -> None:
    if os.path.islink(dst) or os.path.exists(dst):
        try:
            if os.path.islink(dst) or os.path.isfile(dst):
                os.remove(dst)
            else:
                shutil.rmtree(dst)
        except FileNotFoundError:
            pass
    os.makedirs(src, exist_ok=True)
    os.symlink(src, dst)

def main() -> None:
    port = int(os.environ.get("PORT", "8080"))
    # Forcer les migrations (variables vides = migrations ON selon ton code)
    os.environ.setdefault("EMERGENCE_FAST_BOOT", "")
    os.environ.setdefault("EMERGENCE_SKIP_MIGRATIONS", "")

    src_dir = "/tmp/emergence/db"
    dst_dir = "/app/src/backend/data/db"
    ensure_symlink(src_dir, dst_dir)
    print(f"[entrypoint] DB ready at {src_dir} (→ {dst_dir})", flush=True)

    # Remplace le process par uvicorn (signaux Cloud Run OK)
    os.execv(sys.executable, [
        sys.executable, "-m", "uvicorn",
        "--app-dir", "src", "backend.main:app",
        "--host", "0.0.0.0", "--port", str(port)
    ])

if __name__ == "__main__":
    main()
