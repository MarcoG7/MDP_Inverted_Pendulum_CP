from pathlib import Path
from dataclasses import dataclass
import asyncio
import threading
import time
import numpy as np

from pendulum_cp.sources.engine_manager import engine_manager

def _get_simulink_dir() -> Path:
    import sys
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS) / "simulations" / "simulink"
    return Path(__file__).resolve().parents[4] / "simulations" / "simulink"

SIMULINK_DIR = _get_simulink_dir()
MODEL_NAME = "IP_SwingUp_Design"
SETUP_SCRIPT = "Init_Setup_LQRArd"
ANIMATION_SCRIPT = "animation3d1"
ANIMATION_FLAG = SIMULINK_DIR / "animation_ready.flag"
TARGET_DT = 0.01  # 100 Hz — must match PUSH_INTERVAL in session.py


@dataclass
class SimulationParams:
  cart_mass: float = 0.8145        # M_c / M  — kg
  pendulum_mass: float = 0.12      # m        — kg
  pendulum_length: float = 0.15    # l        — m (pivot to CoG)
  cart_friction: float = 0.63      # c        — N/m/s
  pendulum_damping: float = 0.00007892  # b   — N·m·rad⁻¹·s⁻¹
  stop_time: float = 10.0          # simulation duration — s
  show_animation: bool = False     # run 3D animation after simulation


class SimulinkRunner:
  """Singleton that owns the Simulink simulation lifecycle.

  After the MATLAB engine is ready, call schedule_after_engine() to kick off
  an automatic precompilation with default params. SimulinkSource.start()
  then just copies the stored results instead of re-running MATLAB.

  For user-triggered recompilation call run_blocking() via asyncio.to_thread().
  """

  def __init__(self):
    self._params = SimulationParams()
    self._time: list[float] = []
    self._x: list[float] = []
    self._xd: list[float] = []
    self._theta: list[float] = []
    self._thetad: list[float] = []
    self._results_event = threading.Event()
    self._compile_lock = threading.Lock()  # serialises compilation AND animation (shared engine)
    self._animation_thread: threading.Thread | None = None

  # ------------------------------------------------------------------
  # Public API
  # ------------------------------------------------------------------

  def schedule_after_engine(self) -> None:
    """Start a daemon thread that waits for the engine then precompiles."""
    threading.Thread(
      target=self._wait_and_run,
      daemon=True,
      name="simulink-precompile",
    ).start()

  def run_blocking(
    self,
    params: SimulationParams,
    loop=None,
    on_progress=None,
  ) -> None:
    """Run the simulation with given params. Blocks until complete.

    Safe to call from asyncio.to_thread(). Uses _compile_lock to prevent
    concurrent runs. Notifies on_progress at each stage if provided.
    """
    def notify(stage: str, message: str) -> None:
      if on_progress and loop:
        asyncio.run_coroutine_threadsafe(on_progress(stage, message), loop)

    with self._compile_lock:
      self._params = params
      self._results_event.clear()
      print(f"[Simulink Runner] Starting compilation (stop_time={params.stop_time}s)...", flush=True)
      t_total = time.time()
      try:
        self._compile(params, notify)
        self._results_event.set()
      except Exception as e:
        print(f"[Simulink Runner] Compilation failed: {e}", flush=True)
        raise
      print(f"[Simulink Runner] Done. ({time.time() - t_total:.1f}s total)", flush=True)

  @property
  def has_results(self) -> bool:
    return self._results_event.is_set()

  @property
  def is_compiling(self) -> bool:
    return self._compile_lock.locked() and not self.is_animating

  @property
  def is_animating(self) -> bool:
    return self._animation_thread is not None and self._animation_thread.is_alive()

  @property
  def params(self) -> SimulationParams:
    return self._params

  def get_results(self) -> tuple[list, list, list, list, list]:
    """Return (time, x, xd, theta, thetad) — only valid after has_results."""
    return self._time, self._x, self._xd, self._theta, self._thetad

  def start_animation(self) -> None:
    """Start the 3D animation and block until the window is ready (max 30 s).

    Intended to be called via asyncio.to_thread() so it does not block the
    event loop.  The animation itself continues running in the background
    after this method returns.  The compile lock is held for the duration of
    the animation so recompiles queue up rather than racing the engine.
    Calling again while already animating is a no-op.
    """
    if not self.has_results:
      print("[Simulink Runner] Animation skipped — no results yet.", flush=True)
      return
    if self.is_animating:
      print("[Simulink Runner] Animation already running.", flush=True)
      return

    # Remove any stale flag from a previous run.
    if ANIMATION_FLAG.exists():
      ANIMATION_FLAG.unlink()

    self._animation_thread = threading.Thread(
      target=self._animate,
      daemon=True,
      name="simulink-animation",
    )
    self._animation_thread.start()

    # Block until animation3d1.m writes the flag (window rendered) or timeout.
    print("[Simulink Runner] Waiting for animation window...", flush=True)
    deadline = time.monotonic() + 30.0
    while not ANIMATION_FLAG.exists():
      if time.monotonic() > deadline:
        print("[Simulink Runner] Animation ready timeout — starting anyway.", flush=True)
        break
      if not self._animation_thread.is_alive():
        print("[Simulink Runner] Animation thread ended before ready.", flush=True)
        break
      time.sleep(0.05)

    if ANIMATION_FLAG.exists():
      ANIMATION_FLAG.unlink()
    print("[Simulink Runner] Animation window ready.", flush=True)

  # ------------------------------------------------------------------
  # Internal
  # ------------------------------------------------------------------

  def _wait_and_run(self) -> None:
    engine_manager.get_engine()   # blocks until engine is ready
    try:
      self.run_blocking(self._params)
    except Exception:
      pass  # error already printed in run_blocking

  def _animate(self) -> None:
    eng = engine_manager.get_engine()
    with self._compile_lock:
      try:
        print("[Simulink Runner] 3D animation started.", flush=True)
        eng.run(ANIMATION_SCRIPT, nargout=0)
        print("[Simulink Runner] 3D animation finished.", flush=True)
      except Exception as e:
        print(f"[Simulink Runner] Animation error: {e}", flush=True)

  def _compile(self, params: SimulationParams, notify) -> None:
    eng = engine_manager.get_engine()

    # Init_Setup_LQRArd.m starts with 'clear all', so run it first to establish a clean baseline
    eng.addpath(str(SIMULINK_DIR), nargout=0)
    eng.cd(str(SIMULINK_DIR), nargout=0)
    eng.run(SETUP_SCRIPT, nargout=0)

    # set_param requires the model to be loaded; load_system is a no-op if already open
    eng.eval(f"load_system('{MODEL_NAME}');", nargout=0)

    # Override physical params and recompute all derived quantities.
    # Mirrors the equations in Init_Setup_LQRArd.m so the Simulink model sees consistent values.
    # M (total cart mass incl. motor) and M_c (cart body) are distinct in Init_Setup_LQRArd.m
    # (0.8155 vs 0.8145). We keep M offset fixed; only M_c is user-controlled.
    M_offset = 0.8155 - 0.8145  # fixed hardware offset between total and body mass
    override = f"""
M_c = {params.cart_mass};
M   = {params.cart_mass + M_offset};
m   = {params.pendulum_mass};
l   = {params.pendulum_length};
c   = {params.cart_friction};
b   = {params.pendulum_damping};
g   = 9.81;
r = 0.006; L = 0.046; Rm = 12.5; kb = 0.031; kt = 0.031; n = 3;
Er  = 2*m*g*l + 0.0199;
I   = 1/12*m*(2*l)^2;
AA  = I*(M+m) + M*m*(l^2);
aa  = (((m*l)^2)*g)/AA;
bb  = ((I+m*(l^2))/AA)*(c + (kb*kt)/(Rm*(r^2)));
cc  = (b*m*l)/AA;
dd  = (m*g*l*(M+m))/AA;
ee  = ((m*l)/AA)*(c + (kb*kt)/(Rm*(r^2)));
ff  = ((M+m)*b)/AA;
mm  = ((I+m*(l^2))*kt)/(AA*Rm*r);
nn  = (m*l*kt)/(AA*Rm*r);
A   = [0 0 1 0; 0 0 0 1; 0 aa -bb -cc; 0 dd -ee -ff];
B   = [0; 0; mm; nn];
Q   = diag([1200 1500 10000 1000]);
R   = 0.035;
KK  = lqr(A, B, Q, R);
p3  = [-8; -10; -4.5; -5.8];
k   = place(A, B, p3);
set_param('{MODEL_NAME}', 'StopTime', '{params.stop_time}');
"""
    eng.eval(override, nargout=0)

    notify("running_simulation", "Running Simulink model...")
    print(f"[Simulink Runner] Running model '{MODEL_NAME}'...", flush=True)
    t0 = time.time()
    eng.eval(f"sim('{MODEL_NAME}');", nargout=0)
    print(f"[Simulink Runner] Simulation complete. ({time.time() - t0:.1f}s)", flush=True)

    notify("loading_data", "Loading simulation data...")
    print("[Simulink Runner] Extracting workspace data...", flush=True)

    eng.eval("extracted = x.time;", nargout=0)
    raw_time = np.array(eng.workspace['extracted']).flatten()

    eng.eval("extracted = x.signals.values;", nargout=0)
    x = np.array(eng.workspace['extracted']).flatten()

    eng.eval("extracted = xd.signals.values;", nargout=0)
    xd = np.array(eng.workspace['extracted']).flatten()

    eng.eval("extracted = theta.signals.values;", nargout=0)
    theta = np.array(eng.workspace['extracted']).flatten()

    eng.eval("extracted = thetad.signals.values;", nargout=0)
    thetad = np.array(eng.workspace['extracted']).flatten()

    # Downsample to TARGET_DT — solver runs much finer than 20 Hz push rate
    target_times = np.arange(raw_time[0], raw_time[-1], TARGET_DT)
    indices = np.searchsorted(raw_time, target_times)
    indices = np.unique(np.clip(indices, 0, len(raw_time) - 1))

    self._time  = raw_time[indices].tolist()
    self._x     = x[indices].tolist()
    self._xd    = xd[indices].tolist()
    self._theta = theta[indices].tolist()
    self._thetad = thetad[indices].tolist()

    duration = self._time[-1] - self._time[0] if self._time else 0
    print(
      f"[Simulink Runner] Data ready — {len(self._time)} frames, {duration:.1f}s.",
      flush=True,
    )


simulink_runner = SimulinkRunner()
