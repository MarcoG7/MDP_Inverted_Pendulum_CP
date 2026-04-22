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

export interface IParamRange {
  min: number;
  max: number;
  step: number;
}

// Adjust min/max/step here to change allowed ranges for each parameter.
export const PARAM_RANGES: Record<keyof ISimulationParams, IParamRange> = {
  stop_time:         { min: 1,       max: 300,    step: 1         },
  cart_mass:         { min: 0.01,    max: 10,     step: 0.001     },
  pendulum_mass:     { min: 0.001,   max: 5,      step: 0.001     },
  pendulum_length:   { min: 0.01,    max: 2,      step: 0.001     },
  cart_friction:     { min: 0,       max: 10,     step: 0.01      },
  pendulum_damping:  { min: 0,       max: 0.01,   step: 0.0000001 },
};
