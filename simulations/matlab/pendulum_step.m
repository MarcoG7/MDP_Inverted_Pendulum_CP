function [t_new, y_new] = pendulum_step(y_current, t_current, dt)
% PENDULUM_STEP  Advance the inverted pendulum simulation by one timestep.
%
%   [t_new, y_new] = pendulum_step(y_current, t_current, dt)
%
%   Inputs:
%     y_current - current state vector [position; velocity; angle; angular_velocity] (4x1)
%     t_current - current simulation time (scalar)
%     dt        - time interval to advance (scalar, e.g., 0.05)
%
%   Outputs:
%     t_new - new simulation time (t_current + dt)
%     y_new - new state vector after advancing by dt (1x4 row vector)
%
%   Called by Python (MATLABSource) every 50ms via the MATLAB Engine API.
%   Uses ode45 internally for accurate integration over the interval.

    % ── System parameters (same as your simulation script) ──
    m = 1;       % pendulum mass
    M = 5;       % cart mass
    L = 2;       % pendulum length
    g = -10;     % gravity
    d = 1;       % damping

    s = 1;       % pendulum up (s=1) or down (s=-1)

    A = [0 1 0 0;
         0 -d/M -m*g/M 0;
         0 0 0 1;
         0 -s*d/(M*L) -s*(m+M)*g/(M*L) 0];

    B = [0; 1/M; 0; s*1/(M*L)];

    % ── Controller gain (pole placement) ──
    p = [-3; -3.1; -3.2; -3.3];
    K = place(A, B, p);

    % ── Reference state (setpoint) ──
    y_ref = [2; 0; pi; 0];   % adapt to your desired reference

    % ── Run ode45 for one small interval ──
    % y_current comes from Python as a 1x4 double; reshape to column vector
    y0 = reshape(y_current, [], 1);

    [~, y_out] = ode45(@(t, y) pendcart(y, m, M, L, g, d, -K*(y - y_ref)), ...
                       [t_current, t_current + dt], y0);

    % Return the final state (last row of ode45 output)
    t_new = t_current + dt;
    y_new = y_out(end, :);   % 1x4 row vector

    % ── Draw the pendulum in MATLAB figure ──
    drawpend(y_new, m, M, L);
end
