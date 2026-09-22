"""Single-command launcher for backend and frontend (NFR-L1).

Run it with uv, which resolves and installs the Python dependencies on
first use (D-10):

    uv run run.py

Order of work matters here. Python dependencies are imported before
anything is announced, so a cold interpreter is absorbed at launch
instead of surfacing as a slow first request (A-1). Readiness is then
reported only once both servers answer, rather than guessed at with a
sleep.
"""

import os
import shutil
import signal
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).parent.resolve()
BACKEND = ROOT / "backend"
FRONTEND = ROOT / "frontend"

sys.path.insert(0, str(BACKEND))

READY_TIMEOUT = 30.0


def ensure_frontend_dependencies(npm: str) -> None:
    """Install node modules on first run.

    This is the only step that needs the network, and it happens at
    setup rather than during a demo (NFR-D2).
    """
    if (FRONTEND / "node_modules").is_dir():
        return
    print("[setup] installing frontend dependencies, first run only...")
    result = subprocess.run([npm, "install"], cwd=FRONTEND)
    if result.returncode != 0:
        sys.exit("[setup] npm install failed")


def wait_for(url: str, timeout: float) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=1) as response:
                if response.status == 200:
                    return True
        except (urllib.error.URLError, OSError):
            time.sleep(0.2)
    return False


def stop_process_tree(process: subprocess.Popen) -> None:
    """Terminate a child and its descendants.

    npm spawns Vite as a grandchild, so terminating npm alone leaves the
    dev server holding its port and the next launch fails.
    """
    if process.poll() is not None:
        return
    if os.name == "nt":
        subprocess.run(
            ["taskkill", "/F", "/T", "/PID", str(process.pid)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    else:
        process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()


def main() -> None:
    # Line buffering, so progress and the readiness banner appear as they
    # happen even when output is piped to a file or a terminal multiplexer.
    sys.stdout.reconfigure(line_buffering=True)

    npm = shutil.which("npm")
    if npm is None:
        sys.exit("[setup] npm not found on PATH; install Node.js 20 or newer")

    ensure_frontend_dependencies(npm)

    # Imports first, readiness afterwards (A-1).
    print("[backend] loading...")
    started = time.monotonic()
    import uvicorn

    from app.config import BACKEND_HOST, BACKEND_PORT, FRONTEND_PORT
    from app.main import app

    print(f"[backend] loaded in {time.monotonic() - started:.2f}s")

    config = uvicorn.Config(
        app=app,
        host=BACKEND_HOST,
        port=BACKEND_PORT,
        log_level="warning",
    )
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()

    frontend = subprocess.Popen(
        [npm, "run", "dev", "--", "--port", str(FRONTEND_PORT), "--strictPort"],
        cwd=FRONTEND,
    )

    backend_url = f"http://{BACKEND_HOST}:{BACKEND_PORT}"
    frontend_url = f"http://localhost:{FRONTEND_PORT}"

    try:
        if not wait_for(f"{backend_url}/api/health", READY_TIMEOUT):
            raise RuntimeError("backend did not become ready")
        if not wait_for(frontend_url, READY_TIMEOUT):
            raise RuntimeError("frontend did not become ready")

        print()
        print(f"  Systems V1 ready at {frontend_url}")
        print(f"  API at {backend_url}/api")
        print("  Ctrl+C to stop")
        print()

        while frontend.poll() is None and thread.is_alive():
            time.sleep(0.5)
    except KeyboardInterrupt:
        pass
    except RuntimeError as error:
        print(f"[launch] {error}", file=sys.stderr)
    finally:
        server.should_exit = True
        stop_process_tree(frontend)
        thread.join(timeout=5)
        print("[launch] stopped")


if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal.default_int_handler)
    main()
