"""
Standalone entry point used by PyInstaller.

In development, run the FastAPI backend and Angular dev server separately.
This file is only used when building the packaged app.
"""
import sys
import os
import threading
import webbrowser
import socket


def _inject_matlab_path():
    """Find the real MATLAB Python engine and add it to sys.path.

    The matlab package cannot be bundled by PyInstaller because its native
    components reference the MATLAB installation directory at absolute paths.
    We locate the MATLAB installation at runtime and inject its Python engine.
    """
    candidates = []

    # 1. Explicit env var (user or sysadmin can set this)
    if os.environ.get("MATLAB_ROOT"):
        candidates.append(os.environ["MATLAB_ROOT"])

    # 2. Derive from the `matlab` executable on PATH
    import shutil
    matlab_exe = shutil.which("matlab")
    if matlab_exe:
        # matlab -> .../bin/matlab  =>  root is two levels up
        candidates.append(os.path.dirname(os.path.dirname(matlab_exe)))

    # 3. Common installation prefixes (Linux / Windows)
    search_roots = [
        "/usr/local/MATLAB",
        "/opt/MATLAB",
        os.path.expanduser("~/MATLAB"),
        r"C:\Program Files\MATLAB",
    ]
    for root in search_roots:
        if os.path.isdir(root):
            for entry in sorted(os.listdir(root), reverse=True):  # latest release first
                candidates.append(os.path.join(root, entry))

    for matlab_root in candidates:
        engine_path = os.path.join(matlab_root, "extern", "engines", "python", "dist")
        if os.path.isdir(engine_path):
            if engine_path not in sys.path:
                sys.path.insert(0, engine_path)
            print(f"[run.py] MATLAB engine path: {engine_path}", flush=True)
            return

    print("[run.py] WARNING: MATLAB installation not found. Simulations will not work.", flush=True)


def _check_port(port: int) -> bool:
    """Return True if the port is already in use."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(("127.0.0.1", port)) == 0


def get_static_dir() -> str:
    if getattr(sys, "frozen", False):
        base = sys._MEIPASS
    else:
        base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, "static")


def mount_frontend(app, static_dir: str):
    from fastapi.staticfiles import StaticFiles
    from fastapi.responses import FileResponse
    from fastapi import Request

    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_spa(request: Request, full_path: str):
        file_path = os.path.join(static_dir, full_path)
        if os.path.isfile(file_path):
            return FileResponse(file_path)
        return FileResponse(os.path.join(static_dir, "index.html"))

    app.mount("/", StaticFiles(directory=static_dir, html=True), name="frontend")


def open_browser():
    webbrowser.open("http://localhost:8000")


if __name__ == "__main__":
    import uvicorn

    _inject_matlab_path()

    if _check_port(8000):
        print("[run.py] ERROR: Port 8000 is already in use.", flush=True)
        print("[run.py] Another instance may still be running. Close it and try again.", flush=True)
        input("Press Enter to exit...")
        sys.exit(1)

    from pendulum_cp.main import app

    static_dir = get_static_dir()
    if os.path.isdir(static_dir):
        mount_frontend(app, static_dir)
        threading.Timer(1.5, open_browser).start()
    else:
        print("[run.py] WARNING: static/ not found — frontend will not be served.")
        print("[run.py] Build Angular first: cd frontend/pendulum-cp-ui && ng build")

    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="warning")
