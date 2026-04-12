import { DataSource } from './start-params';

export interface ITelemetryData {
  timestamp: number;
  position: number; // cart position - x
  velocity: number; // cart velocity - x'
  angle: number; // pendulum angle - θ
  angular_velocity: number; // pendulum angular velocity - θ'
  data_source: DataSource; // active data source
}
