import { ComponentFixture, TestBed } from '@angular/core/testing';
import { signal, NO_ERRORS_SCHEMA } from '@angular/core';
import { vi, describe, it, expect, beforeEach, afterEach } from 'vitest';
import { Dashboard } from './dashboard';
import { ApiService } from '../../services/api.service';
import { ITelemetryData } from '../../models/telemetry-data';
import { RealtimeGraph } from '../realtime-graph/realtime-graph';

const MOCK_TELEMETRY: ITelemetryData = {
  timestamp: 5.0,
  position: 0.1,
  velocity: 0.2,
  angle: 30.0,
  angular_velocity: 1.0,
  data_source: 'src-sim',
};

describe('Dashboard', () => {
  let component: Dashboard;
  let fixture: ComponentFixture<Dashboard>;

  const telemetrySignal = signal<ITelemetryData | undefined>(undefined);

  const mockApi = {
    telemetry: telemetrySignal.asReadonly(),
    start: vi.fn().mockResolvedValue(undefined),
    stop: vi.fn().mockResolvedValue(undefined),
    reset: vi.fn().mockResolvedValue(undefined),
    disconnect: vi.fn(),
  };

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [Dashboard],
      providers: [{ provide: ApiService, useValue: mockApi }],
    })
      .overrideComponent(Dashboard, {
        remove: { imports: [RealtimeGraph] },
        add: { schemas: [NO_ERRORS_SCHEMA] },
      })
      .compileComponents();

    fixture = TestBed.createComponent(Dashboard);
    component = fixture.componentInstance;
    fixture.detectChanges();
    await fixture.whenStable();
  });

  afterEach(() => {
    telemetrySignal.set(undefined);
    vi.clearAllMocks();
    TestBed.resetTestingModule();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('elapsedTime starts at 0', () => {
    expect(component.elapsedTime()).toBe(0);
  });

  it('elapsedTime updates when telemetry arrives', () => {
    telemetrySignal.set(MOCK_TELEMETRY);
    fixture.detectChanges();
    expect(component.elapsedTime()).toBe(5.0);
  });

  it('start() calls api.start with correct params', () => {
    component.start({ data_source: 'src-sim', ctrl_method: 'default' });
    expect(mockApi.start).toHaveBeenCalledWith('src-sim', 'default');
  });

  it('stop() calls api.stop', () => {
    component.stop();
    expect(mockApi.stop).toHaveBeenCalled();
  });

  it('reset() calls api.reset and clears elapsedTime', () => {
    telemetrySignal.set(MOCK_TELEMETRY);
    fixture.detectChanges();

    component.reset();

    expect(mockApi.reset).toHaveBeenCalled();
    expect(component.elapsedTime()).toBe(0);
  });

  it('formatTime formats seconds correctly', () => {
    expect(component.formatTime(0)).toBe('00:00.000');
    expect(component.formatTime(61.5)).toBe('01:01.500');
    expect(component.formatTime(3599.999)).toBe('59:59.999');
  });
});
