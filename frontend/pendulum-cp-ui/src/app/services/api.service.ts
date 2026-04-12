import { DestroyRef, inject, Injectable, signal } from '@angular/core';
import { ITelemetryData } from '../models/telemetry-data';
import { DataSource, ControlMethod } from '../models/start-params';

const BASE_URL = 'http://localhost:8000';
const WS_URL = 'ws://localhost:8000/ws/data';

@Injectable({ providedIn: 'root' })
export class ApiService {
  private readonly destroyRef = inject(DestroyRef);

  private ws: WebSocket | null = null;

  private readonly telemetrySignal = signal<ITelemetryData | undefined>(undefined);
  readonly telemetry = this.telemetrySignal.asReadonly();

  // CSV buffering - flushed in chunks to avoid large string concatenations
  private buffer: ITelemetryData[] = [];
  private chunks: string[] = [];
  private readonly FLUSH_THRESHOLD = 500;

  constructor() {
    this.destroyRef.onDestroy(() => this.disconnect());
  }

  connect(): Promise<void> {
    if (this.ws?.readyState === WebSocket.OPEN) {
      return Promise.resolve();
    }

    return new Promise((resolve, reject) => {
      this.ws = new WebSocket(WS_URL);

      this.ws.onopen = () => resolve();

      this.ws.onmessage = (event) => {
        const data: ITelemetryData = JSON.parse(event.data);
        this.telemetrySignal.set(data);
        this.buffer.push(data);
        if (this.buffer.length >= this.FLUSH_THRESHOLD) this.flush();
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

  async stop(): Promise<void> {
    await fetch(`${BASE_URL}/stop`, { method: 'POST' });
  }

  async reset(): Promise<void> {
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
          `${d.timestamp},${d.position},${d.velocity},${d.angle},${d.angular_velocity},${d.data_source}`,
      )
      .join('');
    this.chunks.push(rows);
    this.buffer = [];
  }
}
