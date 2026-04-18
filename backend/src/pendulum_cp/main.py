from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from pendulum_cp.controllers.session import SessionManager
from pendulum_cp.models.schemas import CommandResponse, SimulationParams, SystemStatus


@asynccontextmanager
async def lifespan(app: FastAPI):
  '''Pre-load the MATLAB engine in the background as the server starts.

  By the time the user selects Simulink and clicks Start, the engine
  will often already be warmed up, eliminating most of the startup delay.
  Uses pendulum_cp.* (not src.pendulum_cp.*) to stay on the same module
  instance that simulink.py and session.py use.
  '''
  from pendulum_cp.sources.engine_manager import engine_manager
  from pendulum_cp.sources.simulink_runner import simulink_runner
  print("[Server] Starting up — pre-loading MATLAB engine and scheduling first compilation.", flush=True)
  engine_manager.preload()
  simulink_runner.schedule_after_engine()
  yield
  print("[Server] Shutting down.", flush=True)


app = FastAPI(title="MDP - Inverted Pendulum CP API", lifespan=lifespan)

app.add_middleware(
  CORSMiddleware,
  allow_origins=["http://localhost:4200"],
  allow_methods=["*"],
  allow_headers=["*"],
)

session = SessionManager()


class StartRequest(BaseModel):
  '''Request body for POST /start.'''
  data_source: str  # "src-sim" | "src-matlab" | ...
  ctrl_method: str  # "PID" | "LQR" | ...


@app.post("/start", response_model=CommandResponse)
async def start(req: StartRequest):
  '''Start the pendulum system with the given source and control method.'''
  message = await session.start(req.data_source, req.ctrl_method)
  return CommandResponse(status="ok", message=message)


@app.post("/stop", response_model=CommandResponse)
async def stop():
  '''Pause the active source while keeping the WebSocket open.'''
  message = await session.stop()
  return CommandResponse(status="ok", message=message)


@app.post("/reset", response_model=CommandResponse)
async def reset():
  '''Stop the source and clear all state.'''
  message = await session.reset()
  return CommandResponse(status="ok", message=message)


@app.get("/status", response_model=SystemStatus)
async def status():
  '''Return the current system state.'''
  return session.get_status()


@app.post("/simulate", response_model=CommandResponse)
async def simulate(params: SimulationParams):
  '''Recompile the Simulink model with new physical parameters.'''
  message = await session.recompile(params)
  return CommandResponse(status="ok", message=message)


@app.get("/simulate", response_model=SimulationParams)
async def get_params():
  '''Return the current simulation parameters (defaults on first run).'''
  from pendulum_cp.sources.simulink_runner import simulink_runner
  return simulink_runner.params


@app.websocket("/ws/data")
async def data_ws(ws: WebSocket):
  '''Real-time telemetry and status stream.

  The frontend connects here on startup. The SessionManager push loop sends
  JSON telemetry at 20Hz once a source is running. Loading status updates
  are also sent here with {"type": "status", ...} during startup.
  '''
  await ws.accept()
  await session.set_websocket(ws)
  try:
    while True:
      await ws.receive_text()
  except WebSocketDisconnect:
    session.clear_websocket()
