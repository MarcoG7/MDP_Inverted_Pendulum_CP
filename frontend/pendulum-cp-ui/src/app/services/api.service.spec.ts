import { TestBed } from '@angular/core/testing';
import { vi, describe, it, expect, beforeEach, afterEach } from 'vitest';
import { ApiService } from './api.service';
import { ITelemetryData } from '../models/telemetry-data';

const MOCK_TELEMETRY: ITelemetryData = {
  timestamp: 1.0,
  position: 0.1,
  velocity: 0.2,
  angle: 5.0,
  angular_velocity: 0.1,
  data_source: 'src-sim',
};

class MockWebSocket {
  static OPEN = 1;
  readyState = MockWebSocket.OPEN;

  onopen: (() => void) | null = null;
  onmessage: ((event: MessageEvent) => void) | null = null;
  onclose: (() => void) | null = null;
  onerror: (() => void) | null = null;

  constructor(public url: string) {
    setTimeout(() => this.onopen?.(), 0);
  }

  close() {
    this.onclose?.();
  }

  simulateMessage(data: object): void {
    this.onmessage?.(new MessageEvent('message', { data: JSON.stringify(data) }));
  }
}

describe('ApiService', () => {
  let service: ApiService;

  beforeEach(() => {
    vi.stubGlobal('WebSocket', MockWebSocket);
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true }));
    TestBed.configureTestingModule({});
    service = TestBed.inject(ApiService);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    TestBed.resetTestingModule();
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });

  it('telemetry signal is undefined before any data arrives', () => {
    expect(service.telemetry()).toBeUndefined();
  });

  it('connect() opens a WebSocket', async () => {
    await service.connect();
    expect(service['ws']).toBeTruthy();
  });

  it('connect() called twice reuses the same socket', async () => {
    await service.connect();
    const first = service['ws'];
    await service.connect();
    expect(service['ws']).toBe(first);
  });

  it('disconnect() closes and nulls the socket', async () => {
    await service.connect();
    service.disconnect();
    expect(service['ws']).toBeNull();
  });

  it('start() connects then calls /start', async () => {
    await service.start('src-sim', 'default');
    expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining('/start'),
      expect.objectContaining({ method: 'POST' }),
    );
  });

  it('stop() calls /stop', async () => {
    await service.stop();
    expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining('/stop'),
      expect.objectContaining({ method: 'POST' }),
    );
  });

  it('reset() calls /reset and clears the buffer', async () => {
    await service.reset();
    expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining('/reset'),
      expect.objectContaining({ method: 'POST' }),
    );
    expect(service.getExportData()).toBe('');
  });

  it('incoming message updates the telemetry signal', async () => {
    await service.connect();
    (service['ws'] as unknown as MockWebSocket).simulateMessage(MOCK_TELEMETRY);
    expect(service.telemetry()?.angle).toBe(5.0);
  });

  it('getExportData() returns CSV rows after receiving data', async () => {
    await service.connect();
    (service['ws'] as unknown as MockWebSocket).simulateMessage(MOCK_TELEMETRY);
    const csv = service.getExportData();
    expect(csv).toContain('1,0.1,0.2,5,0.1,src-sim');
  });
});
