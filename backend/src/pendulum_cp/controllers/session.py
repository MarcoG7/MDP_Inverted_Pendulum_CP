import asyncio
from fastapi import WebSocket

from pendulum_cp.models.schemas import SystemStatus
from pendulum_cp.sources.base import DataSource
from pendulum_cp.sources.simulation import SimulationSource
from pendulum_cp.sources.matlab_script import MATLABScriptSource
from pendulum_cp.sources.simulink import SimulinkSource

PUSH_INTERVAL = 0.05  # seconds = 20 Hz

SOURCE_MAP: dict[str, type[DataSource]] = {
  "src-sim": SimulationSource,
  "src-matlab": MATLABScriptSource,
  "src-simulink": SimulinkSource,
}


class SessionManager:
  '''Manages the active data source, WebSocket connection, and push loop.'''

  def __init__(self):
    self._data_source: DataSource | None = None   # Active data source
    self._data_source_key: str = ""
    self._ctrl_method: str = ""                   # Selected control method
    self._ws: WebSocket | None = None             # Active WebSocket connection
    self._task: asyncio.Task | None = None        # Background push loop task

  async def start(self, data_source_key: str, ctrl_method: str) -> str:
    '''Insantiate the data source and begin pushing data.
    
    Args:
      data_source_key: Key mapping to SOURCE_MAP
      ctrl_method: Control method selected
    '''
    if self._data_source and self._data_source.is_running():
      return "Already running"
    
    data_source = SOURCE_MAP.get(data_source_key)
    if data_source is None:
      return f"Unknown source '{data_source_key}'"
    
    self._data_source = data_source(ctrl_method=ctrl_method)
    self._data_source_key = data_source_key
    self._ctrl_method = ctrl_method
    await self._data_source.start()
    self._start_push_loop()
    return "Started"
  
  async def stop(self) -> str:
    '''Stop the active data source. Push loop exits on the next iteration.'''
    if self._data_source:
      await self._data_source.stop()
    self._cancel_push_loop()
    return "Stopped"

  async def reset(self) -> str:
    '''Reset the active data source and stop data push.'''
    if self._data_source:
      await self._data_source.reset()
    self._cancel_push_loop()
    self._data_source = None
    self._data_source_key = ""
    self._ctrl_method = ""
    return "Reset"

  def get_status(self) -> SystemStatus:
    '''Return the current system state.'''
    return SystemStatus(
      is_running=self._data_source.is_running() if self._data_source else False,
      data_source=self._data_source_key,
      ctrl_method=self._ctrl_method,
    )

  def set_websocket(self, ws: WebSocket) -> None:
    '''Register the frontend WebSocket connection and start the loop if the source is already running.'''
    self._ws = ws
    self._start_push_loop()

  def clear_websocket(self) -> None:
    '''Stop the push loop when the WebSocket disconnects.'''
    self._ws = None
    self._cancel_push_loop()

  def _start_push_loop(self) -> None:
    '''Start async task that pushes data over the WebSocket.'''
    if self._task and not self._task.done():
      return  # Already running
    if not (self._data_source and self._data_source.is_running() and self._ws):
      return
    self._task = asyncio.create_task(self._push_loop())

  def _cancel_push_loop(self) -> None:
    '''Cancel the push loop task if it's running.'''
    if self._task and not self._task.done():
      self._task.cancel()
      self._task = None
    
  async def _push_loop(self) -> None:
    '''Main data streaming loop.
    
    Runs as a background asyncio task. Every ~50ms (20Hz), fetches telemetry
    data from the active data source, and sends it as JSON over the WebSocket.
    Exits silently on disconnection or cancellation.
    '''
    try:
      while self._data_source and self._data_source.is_running() and self._ws:
        data = await self._data_source.get_data()
        await self._ws.send_json(data.model_dump())
        await asyncio.sleep(PUSH_INTERVAL)
    except Exception as e:
      print(f"Push loop error: {e}")
