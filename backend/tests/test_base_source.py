import pytest
from src.pendulum_cp.sources.base import DataSource
from src.pendulum_cp.models.schemas import TelemetryData


def test_cannot_instantiate_abstract_class():
  with pytest.raises(TypeError):
    DataSource()


def test_concrete_subclass_must_implement_all_methods():
  class PartialSource(DataSource):
    async def start(self, method: str) -> None: ...
    # missing stop, reset, get_data, and is_running
  
  with pytest.raises(TypeError):
    PartialSource()


def test_complete_subclass_can_be_instantiated():
  class MinimalSource(DataSource):
    async def start(self, method: str) -> None: ...
    async def stop(self) -> None: ...
    async def reset(self) -> None: ...
    async def get_data(self) -> TelemetryData: 
      return TelemetryData(
        timestamp=0.0, position=0.0, velocity=0.0, angle=0.0, angular_velocity=0.0, data_source="src-test"
      )
    def is_running(self) -> bool:
      return False
  
  source = MinimalSource()
  assert not source.is_running()
