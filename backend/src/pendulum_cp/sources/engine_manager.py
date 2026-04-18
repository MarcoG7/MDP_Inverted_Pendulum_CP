import threading
import time


class EngineManager:
  """Pre-loads and reuses a single shared MATLAB engine.

  Call preload() once at app startup to kick off a background thread that
  starts the engine. All subsequent calls to get_engine() block until the
  engine is ready, then return the shared instance — so start_matlab() is
  only ever called once for the lifetime of the server process.

  preload() is idempotent: multiple calls are safe. get_engine() also calls
  preload() implicitly, so the engine will always start even if preload() was
  never called explicitly (e.g. due to Python module import-path differences).
  """

  def __init__(self):
    self._engine = None
    self._error: Exception | None = None
    self._ready = False
    self._started = False
    self._event = threading.Event()
    self._lock = threading.Lock()

  def preload(self) -> None:
    """Start the MATLAB engine in a daemon background thread (idempotent)."""
    with self._lock:
      if self._started:
        return
      self._started = True
    thread = threading.Thread(
      target=self._load,
      daemon=True,
      name="matlab-engine-loader",
    )
    thread.start()

  def _load(self) -> None:
    print("[MATLAB Engine] Starting...", flush=True)
    t0 = time.time()
    try:
      import matlab.engine
      self._engine = matlab.engine.start_matlab()
      self._ready = True
      elapsed = time.time() - t0
      print(f"[MATLAB Engine] Ready. ({elapsed:.1f}s)", flush=True)
    except Exception as e:
      elapsed = time.time() - t0
      print(f"[MATLAB Engine] Failed to start after {elapsed:.1f}s: {e}", flush=True)
      self._error = e
    finally:
      self._event.set()

  def get_engine(self):
    """Block until the engine is ready and return the shared instance.

    Calls preload() implicitly if nobody has done so yet, so the engine
    will always start regardless of which import path was used.
    Raises the original exception if the engine failed to start.
    """
    self.preload()  # no-op if already started
    self._event.wait()
    if self._error:
      raise self._error
    return self._engine

  @property
  def is_ready(self) -> bool:
    return self._ready

  def clear_workspace(self) -> None:
    """Clear all variables from the MATLAB base workspace."""
    if self._engine:
      print("[MATLAB Engine] Clearing workspace.", flush=True)
      self._engine.eval("clear all;", nargout=0)

  def shutdown(self) -> None:
    """Quit the MATLAB engine, terminating the MATLAB process."""
    if self._engine:
      print("[MATLAB Engine] Shutting down.", flush=True)
      try:
        self._engine.quit()
      except Exception:
        pass
      self._engine = None
      self._ready = False


engine_manager = EngineManager()
