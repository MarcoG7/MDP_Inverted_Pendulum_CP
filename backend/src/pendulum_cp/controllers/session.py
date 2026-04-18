import asyncio
import os
from fastapi import WebSocket

from pendulum_cp.models.schemas import SimulationParams, SystemStatus
from pendulum_cp.sources.base import DataSource
from pendulum_cp.sources.simulation import SimulationSource
from pendulum_cp.sources.matlab_script import MATLABScriptSource
from pendulum_cp.sources.simulink import SimulinkSource
from pendulum_cp.sources.engine_manager import engine_manager
from pendulum_cp.sources.simulink_runner import simulink_runner

PUSH_INTERVAL = 0.05  # seconds = 20 Hz

SOURCE_MAP: dict[str, type[DataSource]] = {
  "src-sim": SimulationSource,
  "src-matlab": MATLABScriptSource,
  "src-simulink": SimulinkSource,
}


class SessionManager:
  '''Manages the active data source, WebSocket connection, and push loop.'''

  def __init__(self):
    self._data_source: DataSource | None = None
    self._data_source_key: str = ""
    self._ctrl_method: str = ""
    self._ws: WebSocket | None = None
    self._task: asyncio.Task | None = None
    self._loading_stage: str | None = None
    self._loading_message: str = ""
    self._shutdown_task: asyncio.Task | None = None

  # ------------------------------------------------------------------
  # Start / Stop / Reset
  # ------------------------------------------------------------------

  async def start(self, data_source_key: str, ctrl_method: str) -> str:
    '''Kick off the data source as a background task and return immediately.'''
    if self._loading_stage is not None:
      print("[Session] Start ignored — already loading.", flush=True)
      return "Already loading"
    if self._data_source and self._data_source.is_running():
      print("[Session] Start ignored — already running.", flush=True)
      return "Already running"

    source_cls = SOURCE_MAP.get(data_source_key)
    if source_cls is None:
      print(f"[Session] Unknown source '{data_source_key}'.", flush=True)
      return f"Unknown source '{data_source_key}'"

    print(f"[Session] Starting — source={data_source_key}, ctrl={ctrl_method or 'default'}", flush=True)
    self._data_source = source_cls()
    self._data_source_key = data_source_key
    self._ctrl_method = ctrl_method
    asyncio.create_task(self._start_source())
    return "Starting"

  async def _start_source(self) -> None:
    try:
      await self._data_source.start(on_progress=self._on_progress)
    except Exception as e:
      print(f"[Session] Source startup error: {e}", flush=True)
      await self._clear_loading()
      return
    print("[Session] Source ready — streaming started.", flush=True)
    await self._clear_loading()
    self._start_push_loop()

  async def stop(self) -> str:
    print("[Session] Stop requested.", flush=True)
    if self._data_source:
      await self._data_source.stop()
    self._cancel_push_loop()
    return "Stopped"

  async def reset(self) -> str:
    print("[Session] Reset requested.", flush=True)
    if self._data_source:
      await self._data_source.reset()
    self._cancel_push_loop()
    self._data_source = None
    self._data_source_key = ""
    self._ctrl_method = ""
    self._loading_stage = None
    self._loading_message = ""
    return "Reset"

  # ------------------------------------------------------------------
  # Recompile
  # ------------------------------------------------------------------

  async def recompile(self, params: SimulationParams) -> str:
    '''Rerun the Simulink simulation with new params in the background.'''
    if simulink_runner.is_compiling:
      print("[Session] Recompile ignored — already compiling.", flush=True)
      return "Already compiling"
    print(f"[Session] Recompile requested with params: {params}", flush=True)
    asyncio.create_task(self._run_recompile(params))
    return "Recompiling"

  async def _run_recompile(self, params: SimulationParams) -> None:
    loop = asyncio.get_running_loop()
    try:
      await asyncio.to_thread(simulink_runner.run_blocking, params, loop, self._on_progress)
    except Exception as e:
      print(f"[Session] Recompile error: {e}", flush=True)
    await self._clear_loading()

  # ------------------------------------------------------------------
  # Status
  # ------------------------------------------------------------------

  def get_status(self) -> SystemStatus:
    return SystemStatus(
      is_running=self._data_source.is_running() if self._data_source else False,
      data_source=self._data_source_key,
      ctrl_method=self._ctrl_method,
      loading_stage=self._loading_stage,
      loading_message=self._loading_message,
      engine_ready=engine_manager.is_ready,
      simulation_ready=simulink_runner.has_results,
    )

  # ------------------------------------------------------------------
  # WebSocket
  # ------------------------------------------------------------------

  async def set_websocket(self, ws: WebSocket) -> None:
    print("[Session] Client connected.", flush=True)
    if self._shutdown_task and not self._shutdown_task.done():
      self._shutdown_task.cancel()
      self._shutdown_task = None
    self._ws = ws
    await self._push_status()
    if not engine_manager.is_ready:
      asyncio.create_task(self._wait_for_engine())
    elif not simulink_runner.has_results:
      asyncio.create_task(self._wait_for_simulation())
    self._start_push_loop()

  async def _wait_for_engine(self) -> None:
    await asyncio.to_thread(engine_manager._event.wait)
    await self._push_status()
    if not simulink_runner.has_results:
      asyncio.create_task(self._wait_for_simulation())

  async def _wait_for_simulation(self) -> None:
    await asyncio.to_thread(simulink_runner._results_event.wait)
    await self._push_status()

  def clear_websocket(self) -> None:
    print("[Session] Client disconnected.", flush=True)
    self._ws = None
    self._cancel_push_loop()
    self._shutdown_task = asyncio.create_task(self._auto_shutdown())

  async def _auto_shutdown(self) -> None:
    await asyncio.sleep(10)
    print("[Session] No reconnection after 10s — shutting down.", flush=True)
    os._exit(0)

  # ------------------------------------------------------------------
  # Loading stage helpers
  # ------------------------------------------------------------------

  async def _on_progress(self, stage: str, message: str) -> None:
    self._loading_stage = stage
    self._loading_message = message
    await self._push_status()

  async def _clear_loading(self) -> None:
    self._loading_stage = None
    self._loading_message = ""
    await self._push_status()

  async def _push_status(self) -> None:
    if not self._ws:
      return
    try:
      await self._ws.send_json(self.get_status().model_dump())
    except Exception:
      pass

  # ------------------------------------------------------------------
  # Push loop
  # ------------------------------------------------------------------

  def _start_push_loop(self) -> None:
    if self._task and not self._task.done():
      return
    if not (self._data_source and self._data_source.is_running() and self._ws):
      return
    self._task = asyncio.create_task(self._push_loop())

  def _cancel_push_loop(self) -> None:
    if self._task and not self._task.done():
      self._task.cancel()
      self._task = None

  async def _push_loop(self) -> None:
    try:
      while self._data_source and self._data_source.is_running() and self._ws:
        data = await self._data_source.get_data()
        payload = {"type": "telemetry", **data.model_dump()}
        await self._ws.send_json(payload)
        await asyncio.sleep(PUSH_INTERVAL)
    except Exception as e:
      print(f"[Session] Push loop error: {e}", flush=True)
