import pytest
from src.pendulum_cp.models.schemas import TelemetryData, SystemStatus, CommandResponse


def test_telemetry_data_valid():
  data = TelemetryData(
    timestamp=1.0,
    position=0.5,
    velocity=0.1,
    angle=5.0,
    angular_velocity=0.2,
    data_source="src-test"
  )
  assert data.timestamp == 1.0
  assert data.data_source == "src-test"

def test_telemetry_data_rejects_missing_field():
  with pytest.raises(Exception):
    TelemetryData(timestamp=1.0)  # All other fields are missing

def test_system_status_defaults():
  status = SystemStatus(is_running=False)
  assert status.data_source == ""
  assert status.uptime == 0.0

def test_command_response_no_message():
  resp = CommandResponse(status="ok")
  assert resp.message is None

def test_command_response_with_message():
  resp = CommandResponse(status="ok", message="Started")
  assert resp.message == "Started"
