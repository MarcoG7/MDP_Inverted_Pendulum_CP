from pathlib import Path
from math import pi
import asyncio

from pendulum_cp.sources.base import DataSource
from pendulum_cp.models.schemas import TelemetryData

MATLAB_DIR = Path(__file__).resolve().parents[4] / "simulations" / "matlab"


class MATLABScriptSource(DataSource):
  def __init__(self, ctrl_method: str = ""):
    self._running = False
    self._eng = None
    self._t: float = 0.0    # Current simulation time
    self._y: list[float] = [-3.0, 00, pi + 0.1, 0.0]  # Initial values from the matlab file we are simulating
    self._dt: float = 0.05  # Time step per get_data(), this matches the push loop rate

  def _connect(self) -> None:
    import matlab.engine
    self._eng = matlab.engine.connect_matlab()
    self._eng.addpath(str(MATLAB_DIR), nargout=0)
  
  async def start(self) -> None:
    await asyncio.to_thread(self._connect)
    self._t = 0.0
    self._y = [-3.0, 00, pi + 0.1, 0.0]
    self._running = True
  
  async def stop(self) -> None:
    self._running = False
  
  async def reset(self) -> None:
    self._running = False
    self._t = 0.0
    self._y = []
    if self._eng:
      await asyncio.to_thread(self._eng.quit)
      self._eng = None
  
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
