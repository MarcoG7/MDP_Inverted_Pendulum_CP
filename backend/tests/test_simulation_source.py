import asyncio
import pytest

from src.pendulum_cp.sources.simulation import SimulationSource


@pytest.fixture
def source():
  return SimulationSource()

def test_initial_state_is_not_running(source):
  assert not source.is_running()


async def test_start_sets_running(source):
  await source.start()
  assert source.is_running()


async def test_stop_clears_running(source):
  await source.start()
  await source.stop()
  assert not source.is_running()


async def test_reset_clears_running_and_time(source):
  await source.start()
  await source.reset()
  assert not source.is_running()
  assert source._elapsed_at_pause == 0.0


async def test_get_data_returns_telemetry(source):
  await source.start()
  data = await source.get_data()
  assert data.data_source == "src-sim"
  assert isinstance(data.timestamp, float)
  assert isinstance(data.angle, float)


async def test_stop_preserves_elapsed_time(source):
  await source.start()
  await asyncio.sleep(0.05)
  await source.stop()
  assert source._elapsed_at_pause > 0.0


async def test_resume_continues_from_pause(source):
  await source.start()
  await asyncio.sleep(0.05)
  await source.stop()
  paused_elapsed = source._elapsed_at_pause

  await source.start()
  await asyncio.sleep(0.05)
  data = await source.get_data()

  assert data.timestamp >= paused_elapsed
