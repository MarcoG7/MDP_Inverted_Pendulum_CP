from pydantic import BaseModel
from typing import Optional


class TelemetryData(BaseModel):
  '''Data streamed over the WebSocket.'''
  timestamp: float          
  position: float           # cart position: x
  velocity: float           # cart velocity: x'
  angle: float              # pendulum angle: θ
  angular_velocity: float   # pendulum angular velocity: θ'
  data_source: str          # active data source ("src-sim" | "src-matlab" | "src-ip")


class SystemStatus(BaseModel):
  '''Overall system state returned by GET /status.'''
  is_running: bool
  data_source: str = ""     # "src-sim" | "src-matlab" | "src-ip"
  control_method: str = ""  # "ctrl-1" | "ctrl-2" | ...
  uptime: float = 0.0


class CommandResponse(BaseModel):
  '''Response body for POST commands'''
  status: str
  message: Optional[str] = None
