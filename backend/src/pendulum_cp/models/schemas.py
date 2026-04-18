from pydantic import BaseModel
from typing import Optional


class TelemetryData(BaseModel):
  '''Data streamed over the WebSocket.'''
  timestamp: float
  position: float           # cart position: x
  velocity: float           # cart velocity: x'
  angle: float              # pendulum angle: θ
  angular_velocity: float   # pendulum angular velocity: θ'
  data_source: str          # active data source


class SimulationParams(BaseModel):
  '''Editable physical parameters for the Simulink model.'''
  cart_mass: float = 0.5178          # M_c — kg
  pendulum_mass: float = 0.12        # m   — kg
  pendulum_length: float = 0.15      # l   — m (pivot to CoG)
  cart_friction: float = 0.63        # c   — N/m/s
  pendulum_damping: float = 0.00007892  # b — N·m·rad⁻¹·s⁻¹
  stop_time: float = 10.0            # simulation duration — s


class SystemStatus(BaseModel):
  '''Overall system state returned by GET /status or pushed via WebSocket.'''
  type: str = "status"
  is_running: bool
  data_source: str = ""
  ctrl_method: str = ""
  uptime: float = 0.0
  loading_stage: Optional[str] = None   # "running_simulation" | "loading_data" | None
  loading_message: str = ""
  engine_ready: bool = True
  simulation_ready: bool = False   # True once the runner has precompiled results


class CommandResponse(BaseModel):
  '''Response body for POST commands'''
  status: str
  message: Optional[str] = None
