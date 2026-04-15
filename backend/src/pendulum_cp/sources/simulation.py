from time import time
from math import sin, cos, pi

from pendulum_cp.sources.base import DataSource
from pendulum_cp.models.schemas import TelemetryData


class SimulationSource(DataSource):
  def __init__(self, ctrl_method: str = ""):
    self._running: bool = False
    self._t0: float = 0.0
    self._elapsed_at_pause: float = 0.0
  
  async def start(self) -> None:
    '''Start (or resume) the signal generator.'''
    self._t0 = time() - self._elapsed_at_pause
    self._running = True
  
  async def stop(self) -> None:
    '''Pause the generator, preserving elapsed time for resume.'''
    self._elapsed_at_pause = time() - self._t0
    self._running = False
  
  async def reset(self) -> None:
    '''Stop and clear all time state.'''
    self._running = False
    self._t0 = 0.0
    self._elapsed_at_pause = 0.0
  
  async def get_data(self) -> TelemetryData:
    '''Return a telemetry snapshot based on elapsed time.
    
      angle             - 30 degrees amplitude sine wave
      angular_velocity  - derivative of angle
      position          - 2-unit amplitude sine, quarter-period offset
      velocity          - derivative of position, same offset
    '''

    t = time() - self._t0

    return TelemetryData(
      timestamp=round(t, 3),
      angle=round(sin(t) * 30, 3),
      angular_velocity=round(cos(t) * 30, 3),
      position=round(sin(t + pi/2) * 2, 3),
      velocity=round(cos(t + pi/2) * 2, 3),
      data_source="src-sim",
    )
  
  def is_running(self) -> bool:
    return self._running
