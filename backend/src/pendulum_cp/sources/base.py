from abc import ABC, abstractmethod
from typing import Callable, Coroutine, Any, Optional
from src.pendulum_cp.models.schemas import TelemetryData

# Async callback: (stage: str, message: str) -> None
ProgressCallback = Optional[Callable[[str, str], Coroutine[Any, Any, None]]]


class DataSource(ABC):
  '''Abstract base class for all pendulum data sources.

  Implemented by all data sources (Simulation, MATLAB, Simulink, Physical hardware...)
  '''

  @abstractmethod
  async def start(self, on_progress: ProgressCallback = None) -> None:
    '''Begin producing telemetry data.

    Args:
      on_progress: Optional async callback invoked with (stage, message) at
                   key loading milestones. Ignored by fast-starting sources.
    '''
    ...
  
  @abstractmethod
  async def stop(self) -> None:
    '''Pause data production. State is preserved until user resumes.'''
    ...
  
  @abstractmethod
  async def reset(self) -> None:
    '''Stop and clear all internal state.'''
    ...

  @abstractmethod
  async def get_data(self) -> TelemetryData:
    '''Return the latest telemetry snapshot.'''
    ...

  @abstractmethod
  def is_running(self) -> bool:
    '''Return True if the source is actively producing data.'''
    ...
