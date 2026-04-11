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


async def test_start_with_valid_source(session):
  result = await session.start("src-sim", "m1")
  assert result == "Started"
  assert session._source.is_running()
  await session.reset()


async def test_start_with_unknown_source(session):
  result = await session.start("src-unknown", "m1")
  assert "Unknown source" in result
  assert session._source is None


async def test_start_already_running(session):
  await session.start("src-sim", "m1")
  result = await session.start("src-test", "m1")
  assert result == "Already running"
  await session.reset()


async def test_stop_halts_source(session):
  await session.start("src-sim", "m1")
  result = await session.stop()
  assert result == "Stopped"
  assert not session._source.is_running()


async def test_reset_clears_source(session):
  await session.start("src-sim", "m1")
  result = await session.reset()
  assert result == "Reset"
  assert session._source is None


async def test_push_loop_sends_data(session):
  ws = MockWebSocket()
  session.set_websocket(ws)
  await session.start("src-sim", "m1")
  await asyncio.sleep(0.2)  # ~4 ticks at 20 Hz
  await session.stop()
  assert len(ws.sent) >= 3


async def test_clear_websocket_cancels_push_loop(session):
  ws = MockWebSocket()
  session.set_websocket(ws)
  await session.start("src-sim", "m1")
  session.clear_websocket()
  assert session._ws is None
  assert session._task is None
  await session.reset()