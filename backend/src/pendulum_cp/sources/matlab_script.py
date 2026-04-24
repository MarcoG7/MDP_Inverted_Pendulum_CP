from pathlib import Path
from math import pi
import asyncio

from pendulum_cp.sources.base import DataSource
from pendulum_cp.sources.engine_manager import engine_manager
from pendulum_cp.models.schemas import TelemetryData

def _get_matlab_dir() -> Path:
    import sys
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS) / "simulations" / "matlab"
    return Path(__file__).resolve().parents[4] / "simulations" / "matlab"

MATLAB_DIR = _get_matlab_dir()


class MATLABScriptSource(DataSource):
  def __init__(self, ctrl_method: str = ""):
    self._running = False
    self._eng = None
    self._t: float = 0.0    # Current simulation time
    self._y: list[float] = [-3.0, 0, pi + 0.1, 0.0]  # Initial values from the matlab file we are simulating
    self._dt: float = 0.05  # Time step per get_data(), this matches the push loop rate

  def _setup(self) -> None:
    self._eng = engine_manager.get_engine()
    self._eng.addpath(str(MATLAB_DIR), nargout=0)
    print("[MATLAB Script] Engine ready.", flush=True)

  async def start(self, on_progress=None) -> None:
    # Only connect and reset state on a fresh start; preserve _t/_y on resume.
    if self._eng is None:
      print("[MATLAB Script] Starting...", flush=True)
      await asyncio.to_thread(self._setup)
      self._t = 0.0
      self._y = [-3.0, 0, pi + 0.1, 0.0]
    else:
      print("[MATLAB Script] Resuming...", flush=True)
    self._running = True
    print("[MATLAB Script] Running.", flush=True)

  async def stop(self) -> None:
    self._running = False
    print("[MATLAB Script] Stopped.", flush=True)

  async def reset(self) -> None:
    # Engine is shared — do not quit it, just release the reference.
    self._running = False
    self._eng = None
    self._t = 0.0
    self._y = []
    print("[MATLAB Script] Reset.", flush=True)
  
  def _step(self) -> None:
    import matlab
    t_new, y_new = self._eng.pendulum_step(
      matlab.double(self._y),
      self._t,
      self._dt,
      nargout=2,
    )
    self._t = float(t_new)
    self._y = list(y_new[0])
  
  async def get_data(self) -> TelemetryData:
    await asyncio.to_thread(self._step)
    return TelemetryData(
      timestamp=round(self._t, 3),
      position=round(self._y[0], 3),
      velocity=round(self._y[1], 3),
      angle=round(self._y[2] * 100 / pi, 3),
      angular_velocity=round(self._y[3], 3),
      data_source="src-matlab"
    )

  def is_running(self) -> bool:
    return self._running
