import { ITelemetryData } from './telemetry-data';
import { IGraphConfig } from './graph-config';
import { IStartParams } from './start-params';

describe('ITelemetryData', () => {
  it('should accept a valid telemetry object', () => {
    const data: ITelemetryData = {
      timestamp: 1.0,
      position: 0.5,
      velocity: 0.1,
      angle: 5.0,
      angular_velocity: 0.2,
      data_source: 'src-sim',
    };
    expect(data.data_source).toBe('src-sim');
    expect(data.timestamp).toBe(1.0);
  });
});

describe('IStartParams', () => {
  it('should accept valid source and method', () => {
    const params: IStartParams = { data_source: 'src-sim', ctrl_method: 'default' };
    expect(params.data_source).toBe('src-sim');
    expect(params.ctrl_method).toBe('default');
  });
});

describe('IGraphConfig', () => {
  it('should accept config with optional fields omitted', () => {
    const config: IGraphConfig = {
      title: 'Angle',
      yAxisLabel: 'θ (degrees)',
      lineColor: '#432143',
    };
    expect(config.yMin).toBeUndefined();
    expect(config.windowSeconds).toBeUndefined();
  });
});
