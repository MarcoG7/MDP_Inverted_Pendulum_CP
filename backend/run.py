"""
Standalone entry point used by PyInstaller.

In development, run the FastAPI backend and Angular dev server separately.
This file is only used when building the packaged app.
"""
import sys
import os
import threading
import webbrowser
import uvicorn


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
        # Serve actual files if they exist, otherwise fall back to index.html
        # for Angular's client-side routing
        file_path = os.path.join(static_dir, full_path)
        if os.path.isfile(file_path):
            return FileResponse(file_path)
        return FileResponse(os.path.join(static_dir, "index.html"))

    app.mount("/", StaticFiles(directory=static_dir, html=True), name="frontend")


def open_browser():
    webbrowser.open("http://localhost:8000")


if __name__ == "__main__":
    # Must be imported after sys.path is set up by PyInstaller
    from pendulum_cp.main import app

    static_dir = get_static_dir()
    if os.path.isdir(static_dir):
        mount_frontend(app, static_dir)
        threading.Timer(1.5, open_browser).start()
    else:
        print("[run.py] WARNING: static/ not found — frontend will not be served.")
        print("[run.py] Build Angular first: cd frontend/pendulum-cp-ui && ng build")

    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="warning")
