from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from src.pendulum_cp.controllers.session import SessionManager
from src.pendulum_cp.models.schemas import CommandResponse, SystemStatus


app = FastAPI(title="MDP - Inverted Pendulum CP API")

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
  '''Return teh current system state.'''
  return session.get_status()


@app.websocket("/ws/data")
async def data_ws(ws: WebSocket):
  '''Real-time telemetry stream.
  
  The frontend connects here on startup. The SessionManager push
  loop sends JSON telemetry at 20Hz once a source is running.
  '''
  await ws.accept()
  session.set_websocket(ws)
  try:
    while True:
      await ws.receive_text()
  except WebSocketDisconnect:
    session.clear_websocket()
