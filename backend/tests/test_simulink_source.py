import sys
import pytest
from unittest.mock import MagicMock, patch
from math import pi


def make_fake_signal(values: list[float]):
    """Mimics MATLAB column vector: list of single-element lists."""
    return [[v] for v in values]


@pytest.fixture
def mock_engine():
  eng = MagicMock()
  eng.addpath.return_value = None
  eng.cd.return_value = None
  eng.run.return_value = None
  eng.sim.return_value = None

  t  = [0.0, 0.005, 0.010]
  x  = [0.0, 0.01,  0.02]
  xd = [0.0, 0.1,   0.2]
  th = [pi,  pi - 0.01, pi - 0.02]
  td = [0.0, 0.05,  0.10]

  def fake_eval(expr, nargout):
    mapping = {
      "x.time": t,
      "x.signals.values": make_fake_signal(x),
      "xd.signals.values": make_fake_signal(xd),
      "theta.signals.values": make_fake_signal(th),
      "thetad.signals.values": make_fake_signal(td),
    }
    return mapping[expr]

  eng.eval.side_effect = fake_eval

  mock_matlab = MagicMock()
  mock_matlab.engine.connect_matlab.return_value = eng

  with patch.dict(sys.modules, {"matlab": mock_matlab, "matlab.engine": mock_matlab.engine}):
    yield eng


@pytest.fixture
def source(mock_engine):
  from pendulum_cp.sources.simulink import SimulinkSource
  return SimulinkSource()


def test_initial_state_not_running(source):
  assert not source.is_running()


async def test_start_sets_running(source, mock_engine):
  await source.start()
  assert source.is_running()
  assert len(source._time) == 3


async def test_get_data_returns_first_frame(source, mock_engine):
  await source.start()
  data = await source.get_data()
  assert data.data_source == "src-simulink"
  assert data.timestamp == 0.0
  assert data.position == 0.0


async def test_get_data_advances_frame(source, mock_engine):
  await source.start()
  await source.get_data()
  assert source._frame == 1


async def test_exhausted_frames_stops_source(source, mock_engine):
  await source.start()
  # consume all 3 frames
  for _ in range(3):
      await source.get_data()
  assert not source.is_running()


async def test_stop_preserves_frame(source, mock_engine):
  await source.start()
  await source.get_data()
  await source.stop()
  assert source._frame == 1


async def test_reset_clears_all_state(source, mock_engine):
  await source.start()
  await source.reset()
  assert not source.is_running()
  assert source._frame == 0
  assert source._time == []
  mock_engine.quit.assert_called_once()
