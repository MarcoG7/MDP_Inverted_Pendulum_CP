export interface ISimulationParams {
  cart_mass: number;        // M_c — kg
  pendulum_mass: number;    // m   — kg
  pendulum_length: number;  // l   — m
  cart_friction: number;    // c   — N/m/s
  pendulum_damping: number; // b   — N·m·rad⁻¹·s⁻¹
  stop_time: number;        // simulation duration — s
}

export const DEFAULT_SIMULATION_PARAMS: ISimulationParams = {
  cart_mass: 0.5178,
  pendulum_mass: 0.12,
  pendulum_length: 0.15,
  cart_friction: 0.63,
  pendulum_damping: 0.00007892,
  stop_time: 10.0,
};
