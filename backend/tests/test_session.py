import asyncio
import pytest
from src.pendulum_cp.controllers.session import SessionManager


class MockWebSocket:
  """Minimal WebSocket stand-in that records sent messages."""
  def __init__(self):
    self.sent: list[dict] = []

  async def send_json(self, data: dict) -> None:
    self.sent.append(data)


@pytest.fixture
def session():
  return SessionManager()


@pytest.fixture
def ws():
  return MockWebSocket()


async def test_start_with_valid_source(session):
  result = await session.start("src-sim", "m1")
  assert result == "Started"
  assert session._data_source.is_running()
  await session.reset()


async def test_start_with_unknown_source(session):
  result = await session.start("src-unknown", "m1")
  assert "Unknown source" in result
  assert session._data_source is None


async def test_start_already_running(session):
  await session.start("src-sim", "m1")
  result = await session.start("src-sim", "m1")
  assert result == "Already running"
  await session.reset()


async def test_stop_halts_source(session):
  await session.start("src-sim", "m1")
  result = await session.stop()
  assert result == "Stopped"
  assert not session._data_source.is_running()


async def test_reset_clears_source(session):
  await session.start("src-sim", "m1")
  result = await session.reset()
  assert result == "Reset"
  assert session._data_source is None
  assert session._ctrl_method == ""


async def test_push_loop_starts_when_ws_set_after_start(session, ws):
  await session.start("src-sim", "m1")
  assert session._task is None  # no ws yet — loop should not have started
  session.set_websocket(ws)
  await asyncio.sleep(0.2)  # ~4 ticks at 20 Hz
  await session.stop()
  assert len(ws.sent) >= 3


async def test_push_loop_starts_when_source_starts_after_ws(session, ws):
  session.set_websocket(ws)
  await session.start("src-sim", "m1")
  await asyncio.sleep(0.2)
  await session.stop()
  assert len(ws.sent) >= 3


async def test_clear_websocket_cancels_push_loop(session, ws):
  session.set_websocket(ws)
  await session.start("src-sim", "m1")
  session.clear_websocket()
  assert session._ws is None
  assert session._task is None
  await session.reset()


async def test_session_stores_method_and_source_key(session):
  await session.start("src-sim", "m1")
  assert session._data_source_key == "src-sim"
  assert session._ctrl_method == "m1"
  await session.reset()

async def test_get_status_reflects_state(session):
  status = session.get_status()
  assert not status.is_running
  assert status.data_source == ""

  await session.start("src-sim", "m1")
  status = session.get_status()
  assert status.is_running
  assert status.data_source == "src-sim"
  assert status.ctrl_method == "m1"
  await session.reset()
