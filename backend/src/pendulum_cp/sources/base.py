from abc import ABC, abstractmethod
from src.pendulum_cp.models.schemas import TelemetryData


class DataSource(ABC):
  '''Abstract base class for all pendulum data sources.
  
  Implemented by all data sources (test, MATLAB, physical hardware...)
  '''

  @abstractmethod
  async def start(self, control_method: str) -> None:
    '''Begin producing telemetry data.'''
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
