import { DestroyRef, inject, Injectable, signal } from '@angular/core';
import { ITelemetryData } from '../models/telemetry-data';
import { ISystemStatus, LoadingStage } from '../models/system-status';
import { ISimulationParams } from '../models/simulation-params';
import { DataSource, ControlMethod } from '../models/start-params';

const BASE_URL = 'http://localhost:8000';
const WS_URL = 'ws://localhost:8000/ws/data';

@Injectable({ providedIn: 'root' })
export class ApiService {
  private readonly destroyRef = inject(DestroyRef);

  private ws: WebSocket | null = null;

  private readonly telemetrySignal = signal<ITelemetryData | undefined>(undefined);
  readonly telemetry = this.telemetrySignal.asReadonly();

  private readonly loadingStageSignal = signal<LoadingStage>(null);
  readonly loadingStage = this.loadingStageSignal.asReadonly();

  private readonly loadingMessageSignal = signal<string>('');
  readonly loadingMessage = this.loadingMessageSignal.asReadonly();

  private readonly engineReadySignal = signal<boolean>(true);
  readonly engineReady = this.engineReadySignal.asReadonly();

  private readonly simulationReadySignal = signal<boolean>(false);
  readonly simulationReady = this.simulationReadySignal.asReadonly();

  // CSV buffering - flushed in chunks to avoid large string concatenations
  private buffer: ITelemetryData[] = [];
  private chunks: string[] = [];
  private readonly FLUSH_THRESHOLD = 500;

  constructor() {
    this.destroyRef.onDestroy(() => this.disconnect());
    // Connect eagerly so the backend's initial status push (engine_ready, etc.)
    // is received as soon as the app loads, not only when Start is clicked.
    void this.connect();
  }

  connect(): Promise<void> {
    if (this.ws?.readyState === WebSocket.OPEN) {
      return Promise.resolve();
    }

    // If already connecting, wait for it rather than opening a second socket.
    if (this.ws?.readyState === WebSocket.CONNECTING) {
      return new Promise<void>((resolve, reject) => {
        this.ws!.addEventListener('open', () => resolve(), { once: true });
        this.ws!.addEventListener('error', () => reject(new Error('WebSocket connection failed')), { once: true });
      });
    }

    return new Promise<void>((resolve, reject) => {
      this.ws = new WebSocket(WS_URL);

      this.ws.onopen = () => resolve();

      this.ws.onmessage = (event) => {
        const msg = JSON.parse(event.data);

        if (msg.type === 'status') {
          const status = msg as ISystemStatus;
          this.loadingStageSignal.set(status.loading_stage);
          this.loadingMessageSignal.set(status.loading_message);
          this.engineReadySignal.set(status.engine_ready);
          this.simulationReadySignal.set(status.simulation_ready);
        } else {
          // type === 'telemetry'
          const data = msg as ITelemetryData;
          this.telemetrySignal.set(data);
          this.buffer.push(data);
          if (this.buffer.length >= this.FLUSH_THRESHOLD) this.flush();
        }
      };

      this.ws.onclose = () => {
        this.ws = null;
      };

      this.ws.onerror = () => {
        this.ws?.close();
        reject(new Error('WebSocket connection failed'));
      };
    });
  }

  disconnect(): void {
    this.ws?.close();
    this.ws = null;
  }

  async start(data_source: DataSource, ctrl_method: ControlMethod): Promise<void> {
    await this.connect();
    await fetch(`${BASE_URL}/start`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ data_source: data_source, ctrl_method: ctrl_method }),
    });
  }

  async recompile(params: ISimulationParams): Promise<void> {
    await fetch(`${BASE_URL}/simulate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(params),
    });
  }

  async stop(): Promise<void> {
    await fetch(`${BASE_URL}/stop`, { method: 'POST' });
  }

  async reset(): Promise<void> {
    this.loadingStageSignal.set(null);
    this.loadingMessageSignal.set('');
    await fetch(`${BASE_URL}/reset`, { method: 'POST' });
    this.buffer = [];
    this.chunks = [];
  }

  getExportData(): string {
    this.flush();
    return this.chunks.join('');
  }

  private flush(): void {
    const rows = this.buffer
      .map(
        (d) =>
          `${d.timestamp},${d.position},${d.velocity},${d.angle},${d.angular_velocity},${d.data_source}\n`,
      )
      .join('');
    this.chunks.push(rows);
    this.buffer = [];
  }
}
