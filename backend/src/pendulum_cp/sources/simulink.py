from pathlib import Path
from math import pi
import asyncio
import numpy as np

from pendulum_cp.sources.base import DataSource
from pendulum_cp.models.schemas import TelemetryData


SIMULINK_DIR = Path(__file__).resolve().parents[4] / "simulations" / "simulink"
MODEL_NAME = "nonlinear_model_IP"
SETUP_SCRIPT = "IP"


class SimulinkSource(DataSource):
  '''Runs the Simulink model once and replays the results in real-time
  
  start() blocks while MATLAB executes the full simulation, then loads all 
  signal data into memory. get_data() replays the frames sequentially. When
  all frames are exhausted, is_running() returns False and the push loop 
  stops automatically.
  '''

  def __init__(self, ctrl_method: str = ""):
    self._running = False
    self._eng = None
    self._time: list[float] = []
    self._x: list[float] = []
    self._xd: list[float] = []
    self._theta: list[float] = []
    self._thetad: list[float] = []
    self._frame: int = 0
  
  def _run_simulation(self) -> None:
    import matlab.engine
    self._eng = matlab.engine.start_matlab()
    self._eng.addpath(str(SIMULINK_DIR), nargout=0)
    self._eng.cd(str(SIMULINK_DIR), nargout=0)

    # Run the setup script
    self._eng.run(SETUP_SCRIPT, nargout=0)

    # Run the Simulink model with tighter solver tolerance to resolve algebraic loops
    self._eng.eval(f"sim('{MODEL_NAME}');", nargout=0)

    # Extract data from the workspace
    self._eng.eval("extracted = x.time;", nargout=0)
    time = np.array(self._eng.workspace['extracted']).flatten()

    self._eng.eval("extracted = x.signals.values;", nargout=0)
    x = np.array(self._eng.workspace['extracted']).flatten()

    self._eng.eval("extracted = xd.signals.values;", nargout=0)
    xd = np.array(self._eng.workspace['extracted']).flatten()

    self._eng.eval("extracted = theta.signals.values;", nargout=0)
    theta = np.array(self._eng.workspace['extracted']).flatten()

    self._eng.eval("extracted = thetad.signals.values;", nargout=0)
    thetad = np.array(self._eng.workspace['extracted']).flatten()

    # Downsample to TARGET_DT so replay runs at real-time speed.
    # The solver may run at a much finer timestep (e.g. 1 kHz), but the
    # push loop only fires at 20 Hz — keeping every raw frame would make
    # 1 s of simulation take ~50 s of wall time.
    TARGET_DT = 0.05  # must match PUSH_INTERVAL in session.py
    target_times = np.arange(time[0], time[-1], TARGET_DT)
    indices = np.searchsorted(time, target_times)
    indices = np.unique(np.clip(indices, 0, len(time) - 1))

    self._time = time[indices].tolist()
    self._x = x[indices].tolist()
    self._xd = xd[indices].tolist()
    self._theta = theta[indices].tolist()
    self._thetad = thetad[indices].tolist()

  async def start(self) -> None:
    self._frame = 0
    await asyncio.to_thread(self._run_simulation)
    self._running = True

  async def stop(self) -> None:
    self._running = False
  
  async def reset(self) -> None:
    self._running = False
    self._frame = 0
    self._time = []
    self._x = []
    self._xd = []
    self._theta = []
    self._thetad = []
    if self._eng:
      await asyncio.to_thread(self._eng.quit)
      self._eng = None
    
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
