import pytest
from httpx import AsyncClient, ASGITransport
from src.pendulum_cp.main import app, session


@pytest.fixture(autouse=True)
async def reset_session():
  '''Ensure the session is clean before and after every test.'''
  await session.reset()
  yield
  await session.reset()


@pytest.fixture
async def client():
  async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
    yield c


async def test_status_initially_not_running(client):
  response = await client.get("/status")
  assert response.status_code == 200
  assert response.json()["is_running"] is False


async def test_start_valid_source(client):
  response = await client.post("/start", json={"data_source": "src-sim", "ctrl_method": "m1"})
  assert response.status_code == 200
  assert response.json()["message"] == "Started"


async def test_start_unknown_source(client):
  response = await client.post("/start", json={"data_source": "src-unknown", "ctrl_method": "m1"})
  assert response.status_code == 200
  assert "Unknown source" in response.json()["message"]


async def test_start_then_status_is_running(client):
  await client.post("/start", json={"data_source": "src-sim", "ctrl_method": "m1"})
  response = await client.get("/status")
  data = response.json()
  assert data["is_running"] is True
  assert data["data_source"] == "src-sim"
  assert data["ctrl_method"] == "m1"


async def test_stop_after_start(client):
  await client.post("/start", json={"data_source": "src-sim", "ctrl_method": "m1"})
  response = await client.post("/stop")
  assert response.status_code == 200
  assert response.json()["message"] == "Stopped"


async def test_reset_clears_status(client):
  await client.post("/start", json={"data_source": "src-sim", "ctrl_method": "m1"})
  await client.post("/reset")
  response = await client.get("/status")
  assert response.json()["is_running"] is False


async def test_start_missing_field_returns_422(client):
  response = await client.post("/start", json={"data_source": "src-sim"})
  assert response.status_code == 422
