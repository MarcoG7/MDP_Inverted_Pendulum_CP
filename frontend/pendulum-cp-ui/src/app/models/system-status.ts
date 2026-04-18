export type LoadingStage =
  | 'starting_engine'
  | 'running_simulation'
  | 'loading_data'
  | null;

export interface ISystemStatus {
  type: 'status';
  is_running: boolean;
  data_source: string;
  ctrl_method: string;
  loading_stage: LoadingStage;
  loading_message: string;
  engine_ready: boolean;
  simulation_ready: boolean;
}
