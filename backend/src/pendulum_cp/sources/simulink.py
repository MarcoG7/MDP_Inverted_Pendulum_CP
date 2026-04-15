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
    self._eng.eval("extracted = x.time;", nargout=0);
    self._time = list(self._eng.workspace['extracted'])
    self._time = np.array(self._eng.workspace['extracted']).flatten().tolist()

    self._eng.eval("extracted = x.signals.values;", nargout=0);
    self._x = list(self._eng.workspace['extracted'])
    self._x = np.array(self._eng.workspace['extracted']).flatten().tolist()

    self._eng.eval("extracted = xd.signals.values;", nargout=0);
    self._xd = list(self._eng.workspace['extracted'])
    self._xd = np.array(self._eng.workspace['extracted']).flatten().tolist()

    self._eng.eval("extracted = theta.signals.values;", nargout=0);
    self._theta = list(self._eng.workspace['extracted'])
    self._theta = np.array(self._eng.workspace['extracted']).flatten().tolist()

    self._eng.eval("extracted = thetad.signals.values;", nargout=0);
    self._thetad = list(self._eng.workspace['extracted'])
    self._thetad = np.array(self._eng.workspace['extracted']).flatten().tolist()

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
