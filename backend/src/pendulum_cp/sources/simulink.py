import asyncio
from math import pi

from pendulum_cp.sources.base import DataSource, ProgressCallback
from pendulum_cp.sources.simulink_runner import simulink_runner
from pendulum_cp.models.schemas import TelemetryData


class SimulinkSource(DataSource):
  '''Replays precompiled Simulink results in real-time.

  The actual MATLAB execution lives in SimulinkRunner. This source copies
  the stored results on start() and replays them frame-by-frame at 20 Hz.
  If the runner hasn't finished compiling yet, start() waits for it.
  '''

  def __init__(self, ctrl_method: str = ""):
    self._running = False
    self._time: list[float] = []
    self._x: list[float] = []
    self._xd: list[float] = []
    self._theta: list[float] = []
    self._thetad: list[float] = []
    self._frame: int = 0

  async def start(self, on_progress: ProgressCallback = None) -> None:
    if not simulink_runner.has_results:
      print("[Simulink] Waiting for precompilation to finish...", flush=True)
      if on_progress:
        await on_progress("running_simulation", "Running Simulink model...")
      await asyncio.to_thread(simulink_runner._results_event.wait)

    time, x, xd, theta, thetad = simulink_runner.get_results()
    self._time   = list(time)
    self._x      = list(x)
    self._xd     = list(xd)
    self._theta  = list(theta)
    self._thetad = list(thetad)
    self._frame  = 0
    self._running = True
    print(f"[Simulink] Replay started — {len(self._time)} frames.", flush=True)

  async def stop(self) -> None:
    self._running = False
    print("[Simulink] Stopped.", flush=True)

  async def reset(self) -> None:
    self._running = False
    self._frame = 0
    self._time = []
    self._x = []
    self._xd = []
    self._theta = []
    self._thetad = []
    print("[Simulink] Reset.", flush=True)

  async def get_data(self) -> TelemetryData:
    data = TelemetryData(
      timestamp=round(self._time[self._frame], 3),
      position=round(self._x[self._frame], 3),
      velocity=round(self._xd[self._frame], 3),
      angle=round(self._theta[self._frame] * 180 / pi, 3),
      angular_velocity=round(self._thetad[self._frame], 3),
      data_source="src-simulink",
    )
    self._frame += 1
    if self._frame >= len(self._time):
      self._running = False
    return data

  def is_running(self) -> bool:
    return self._running
