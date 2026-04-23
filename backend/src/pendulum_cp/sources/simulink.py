import asyncio
import bisect
import time as wallclock

from pendulum_cp.sources.base import DataSource, ProgressCallback
from pendulum_cp.sources.simulink_runner import simulink_runner
from pendulum_cp.models.schemas import TelemetryData


class SimulinkSource(DataSource):
  '''Replays precompiled Simulink results in real-time.

  Frame selection is driven by wall-clock time rather than a fixed frame
  counter, so the replay stays at 1:1 speed regardless of push-loop jitter
  or event-loop overhead.  Late pushes automatically skip ahead; early ones
  repeat the last frame.

  Theta and angular velocity are kept in the units output by the Simulink
  model (degrees and deg/s) with no additional conversion.
  '''

  def __init__(self, ctrl_method: str = ""):
    self._running = False
    self._time: list[float] = []
    self._x: list[float] = []
    self._xd: list[float] = []
    self._theta: list[float] = []
    self._thetad: list[float] = []
    self._frame: int = 0
    self._wall_start: float = 0.0
    self._sim_start: float = 0.0

  async def start(self, on_progress: ProgressCallback = None) -> None:
    if not simulink_runner.has_results:
      print("[Simulink] Waiting for precompilation to finish...", flush=True)
      if on_progress:
        await on_progress("running_simulation", "Running Simulink model...")
      await asyncio.to_thread(simulink_runner._results_event.wait)

    # Only load data on a fresh start; preserve frame position on resume.
    if not self._time:
      t, x, xd, theta, thetad = simulink_runner.get_results()
      self._time   = list(t)
      self._x      = list(x)
      self._xd     = list(xd)
      self._theta  = list(theta)
      self._thetad = list(thetad)
      self._frame  = 0

    # If animation is enabled, wait for the MATLAB window to be ready before
    # starting the graph replay so both begin at the same moment.
    if simulink_runner.params.show_animation:
      await asyncio.to_thread(simulink_runner.start_animation)

    # Anchor wall-clock to the current simulation-time position so resuming
    # after a pause continues from where it left off.
    self._wall_start = wallclock.monotonic()
    self._sim_start  = self._time[self._frame]
    self._running = True
    print(f"[Simulink] Replay started at frame {self._frame}/{len(self._time)}.", flush=True)

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
    # Map elapsed wall time to the nearest stored simulation frame.
    elapsed = wallclock.monotonic() - self._wall_start
    target  = self._sim_start + elapsed
    self._frame = min(bisect.bisect_left(self._time, target), len(self._time) - 1)

    if self._frame >= len(self._time) - 1:
      self._running = False

    return TelemetryData(
      timestamp=round(self._time[self._frame], 3),
      position=round(self._x[self._frame], 4),
      velocity=round(self._xd[self._frame], 4),
      angle=round(self._theta[self._frame], 3),          # degrees — no conversion needed
      angular_velocity=round(self._thetad[self._frame], 3),  # deg/s — no conversion needed
      data_source="src-simulink",
    )

  def is_running(self) -> bool:
    return self._running
