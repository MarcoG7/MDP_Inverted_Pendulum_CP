import sys
import pytest
from unittest.mock import MagicMock, patch


@pytest.fixture
def mock_engine():
  """Inject a fake matlab.engine into sys.modules for the duration of the test."""
  eng = MagicMock()
  eng.addpath.return_value = None
  eng.pendulum_step.return_value = (0.05, [[0.1, 0.2, 3.14, 0.0]])

  mock_matlab = MagicMock()
  mock_matlab.engine.connect_matlab.return_value = eng
  mock_matlab.double = lambda x: x  # pass-through

  with patch.dict(sys.modules, {"matlab": mock_matlab, "matlab.engine": mock_matlab.engine}):
    yield eng


@pytest.fixture
def source(mock_engine):
  from pendulum_cp.sources.matlab_script import MATLABScriptSource
  return MATLABScriptSource()


def test_initial_state_not_running(source):
  assert not source.is_running()
  assert source._eng is None


async def test_start_sets_running(source, mock_engine):
  await source.start()
  assert source.is_running()


async def test_stop_clears_running(source, mock_engine):
  await source.start()
  await source.stop()
  assert not source.is_running()


async def test_reset_disconnects_engine(source, mock_engine):
  await source.start()
  await source.reset()
  assert source._eng is None
  assert not source.is_running()
  mock_engine.quit.assert_called_once()


async def test_get_data_returns_telemetry(source, mock_engine):
  await source.start()
  data = await source.get_data()
  assert data.data_source == "src-matlab"
  assert data.timestamp == 0.05
  assert isinstance(data.angle, float)


async def test_get_data_updates_internal_state(source, mock_engine):
  await source.start()
  await source.get_data()
  assert source._t == 0.05
  assert source._y == [0.1, 0.2, 3.14, 0.0]
