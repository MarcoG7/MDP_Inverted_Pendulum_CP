export type DataSource = 'src-sim' | 'src-matlab' | 'src-simulink';
export type ControlMethod = 'default' | 'PID' | 'LQR'; // ...

export interface IStartParams {
  data_source: DataSource;
  ctrl_method: ControlMethod;
}
