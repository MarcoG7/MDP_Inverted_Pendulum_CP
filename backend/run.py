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
from pathlib import Path


def _get_log_path() -> Path:
    if sys.platform == "win32":
        base = Path(os.environ.get("APPDATA", Path.home()))
    else:
        base = Path.home() / ".local" / "share"
    log_dir = base / "InvertedPendulumCP"
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir / "app.log"


def _setup_logging(log_path: Path):
    import logging
    from logging.handlers import RotatingFileHandler

    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S")
    handler = RotatingFileHandler(log_path, maxBytes=1_000_000, backupCount=1, encoding="utf-8")
    handler.setFormatter(fmt)

    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.addHandler(handler)

    # Redirect print() / sys.stderr so existing [Server] / [MATLAB] messages go to the file
    class _PrintToLog:
        def write(self, msg):
            if msg.strip():
                logging.info(msg.rstrip())
        def flush(self):
            pass
        def isatty(self):
            return False

    sys.stdout = _PrintToLog()
    sys.stderr = _PrintToLog()


def _find_matlab_root() -> str | None:
    """Find the MATLAB installation root directory."""
    import shutil

    # 1. Explicit env var — user-settable for non-standard installs
    if os.environ.get("MATLAB_ROOT"):
        root = os.environ["MATLAB_ROOT"]
        if os.path.isdir(root):
            return root

    # 2. Derive from the matlab executable on PATH
    matlab_exe = shutil.which("matlab")
    if matlab_exe:
        # .../bin/matlab  ->  root is two levels up
        root = os.path.dirname(os.path.dirname(os.path.realpath(matlab_exe)))
        if os.path.isdir(root):
            return root

    # 3. Scan common installation prefixes (latest release first)
    search_roots = [
        "/usr/local/MATLAB",
        "/opt/MATLAB",
        os.path.expanduser("~/MATLAB"),
        r"C:\Program Files\MATLAB",
    ]
    for base in search_roots:
        if os.path.isdir(base):
            for entry in sorted(os.listdir(base), reverse=True):
                candidate = os.path.join(base, entry)
                if os.path.isdir(os.path.join(candidate, "bin")):
                    return candidate

    return None


def _inject_matlab_path():
    """Set up the MATLAB Engine for Python without requiring a pip install.

    PyInstaller cannot bundle the matlab package — its native components
    reference absolute paths inside the MATLAB installation. Instead we:
      1. Find the user's MATLAB root at runtime
      2. Inject MATLAB's own Python engine dist into sys.path
      3. Generate _arch.txt dynamically so it points to the correct paths
         on this machine, eliminating the need for 'pip install matlabengine'
    """
    import platform
    import stat

    matlab_root = _find_matlab_root()
    if not matlab_root:
        print(
            "[run.py] WARNING: MATLAB not found. "
            "Install MATLAB or set the MATLAB_ROOT environment variable.",
            flush=True,
        )
        return

    print(f"[run.py] MATLAB root: {matlab_root}", flush=True)

    # Determine platform architecture string used by MATLAB
    system = platform.system()
    machine = platform.machine()
    if system == "Linux" and machine == "x86_64":
        arch = "glnxa64"
    elif system == "Windows" and machine == "AMD64":
        arch = "win64"
    elif system == "Darwin" and machine == "arm64":
        arch = "maca64"
    elif system == "Darwin":
        arch = "maci64"
    else:
        arch = "glnxa64"

    matlab_engine_dist = os.path.join(matlab_root, "extern", "engines", "python", "dist")

    # Copy MATLAB's pure Python files to a user-writable location and generate
    # _arch.txt there. The native .so/.dll libs are NOT copied — _arch.txt
    # points back to them inside the MATLAB installation.
    if sys.platform == "win32":
        cache_base = Path(os.environ.get("APPDATA", Path.home()))
    else:
        cache_base = Path.home() / ".local" / "share"
    engine_cache = cache_base / "InvertedPendulumCP" / "matlab_engine"

    import shutil as _shutil
    src = Path(matlab_engine_dist) / "matlab"
    dst = engine_cache / "matlab"

    # Re-copy whenever the MATLAB version changes (detected by mtime difference)
    src_mtime = src.stat().st_mtime if src.exists() else 0
    stamp = engine_cache / ".matlab_mtime"
    cached_mtime = float(stamp.read_text()) if stamp.exists() else 0

    if src_mtime != cached_mtime:
        if engine_cache.exists():
            _shutil.rmtree(engine_cache)
        # Copy only Python files — skip native binaries
        _shutil.copytree(src, dst, ignore=_shutil.ignore_patterns("*.so", "*.dll", "*.pyd"))
        stamp.write_text(str(src_mtime))

    # Generate _arch.txt pointing to the native libs in the real MATLAB install
    arch_txt = dst / "engine" / "_arch.txt"
    arch_content = "\n".join([
        arch,
        os.path.join(matlab_root, "bin", arch),
        os.path.join(matlab_engine_dist, "matlab", "engine", arch),
        os.path.join(matlab_root, "extern", "bin", arch),
    ]) + "\n"
    arch_txt.write_text(arch_content)

    cache_str = str(engine_cache)
    if cache_str not in sys.path:
        sys.path.insert(0, cache_str)

    # On Windows with Python 3.8+, PATH is no longer searched for DLLs loaded
    # by extension modules. Register MATLAB's bin directory explicitly so that
    # matlabmultidimarrayforpython.pyd can find its runtime dependencies.
    if sys.platform == "win32" and hasattr(os, "add_dll_directory"):
        for dll_dir in [
            os.path.join(matlab_root, "bin", arch),
            os.path.join(matlab_engine_dist, "matlab", "engine", arch),
            os.path.join(matlab_root, "extern", "bin", arch),
        ]:
            if os.path.isdir(dll_dir):
                os.add_dll_directory(dll_dir)

    print(f"[run.py] MATLAB engine configured ({arch})", flush=True)


def _check_port(port: int) -> bool:
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

    log_path = _get_log_path()
    # Set up logging BEFORE any print() — on Windows windowed builds sys.stdout is None
    _setup_logging(log_path)

    try:
        print(f"[run.py] Log file: {log_path}", flush=True)
        print("[run.py] Starting Inverted Pendulum CP...", flush=True)

        _inject_matlab_path()

        if _check_port(8000):
            print(
                "[run.py] ERROR: Port 8000 is already in use. "
                "Another instance may still be running.",
                flush=True,
            )
            sys.exit(1)

        from pendulum_cp.main import app

        static_dir = get_static_dir()
        if os.path.isdir(static_dir):
            mount_frontend(app, static_dir)
            threading.Timer(1.5, open_browser).start()
        else:
            print("[run.py] WARNING: static/ not found — frontend will not be served.", flush=True)

        uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")
    except Exception:
        import logging
        import traceback
        logging.error("[run.py] Fatal startup error:\n%s", traceback.format_exc())
