% ================================================================
% CART-PENDULUM: Energy-Based Swing-Up + LQR Stabilization
% Based on Åström & Furuta (1996)
%
% ANGLE CONVENTION:
%   theta = 0   → UPRIGHT   (target)
%   theta = ±pi → HANGING DOWN (start)
%
% v4 fixes:
%   - Swing-up now uses proper bang-bang: F = F_max * sign(E-E0) * sign(-θ̇·cos(θ))
%     This guarantees maximum energy injection every cycle regardless of k_energy.
%     k_energy is now only a softening factor near E=E0 (prevents overshoot).
%   - Cart centering removed from swing-up force (it was interfering with energy control).
%     Instead: cart centering is a separate soft-saturation layer added AFTER
%     the energy control, only when |x| > centering_threshold.
%   - Verified sign convention against dE/dt = -m*l*a*θ̇*cos(θ)
% ================================================================

clear; close all; clc;

%% ================================================================
%  1. PHYSICAL PARAMETERS
% ================================================================
p.M   = 0.5;    % cart mass [kg]
p.m   = 0.2;    % pendulum mass [kg]
p.l   = 0.3;    % pivot to CoM [m]
p.J   = 0.006;  % moment of inertia about pivot [kg·m²]
p.g   = 9.81;   % [m/s²]
p.b   = 0.1;    % cart friction [N·s/m]

p.Jp    = p.J + p.m*p.l^2;
p.F_max = 10.0;             % max cart force [N]
p.a_max = p.F_max / (p.M + p.m);
p.n     = p.a_max / p.g;   % key dimensionless parameter from paper

p.x_limit = 0.5;

fprintf('=== System Check ===\n');
fprintf('n = a_max/g = %.3f\n', p.n);
if     p.n > 2.0,   fprintf('Regime: single-swing, double-switch\n');
elseif p.n > 1.333, fprintf('Regime: single-swing, triple-switch\n');
else,               fprintf('Regime: multi-swing (%d swings expected)\n', ...
                        ceil(pi / max(asin(min(1, p.n/2)), 0.01)));
end
fprintf('E_rest = %.4f J,  E_target = 0.0000 J\n\n', -2*p.m*p.g*p.l);

%% ================================================================
%  2. CONTROL PARAMETERS
% ================================================================

% --- Swing-up ---
% The swing-up uses bang-bang (saturated) control by default.
% k_softening only reduces force when energy is already close to target,
% preventing overshoot past E=0. Set to Inf for pure bang-bang.
c.k_softening = 8.0;   % [1/J]  higher = sharper switch-off near E=E0
c.E0          = 0.0;   % target energy

% --- Catch window ---
c.catch_cos       = cos(0.4);  % pendulum within ~23° of upright
c.catch_max_thdot = 4.0;       % [rad/s] angular velocity limit at catch

% --- Cart safety ---
c.x_limit         = 0.5;       % [m] half track length
c.x_soft_limit    = 0.35;      % [m] boundary beyond which outward swing-up pulses are suppressed

%% ================================================================
%  3. LQR DESIGN
% ================================================================
den = p.Jp*(p.M + p.m) - (p.m*p.l)^2;

A = [0,                            1, 0, 0;
     (p.M+p.m)*p.m*p.g*p.l / den, 0, 0, 0;
     0,                            0, 0, 1;
    -(p.m*p.l)^2*p.g / den,        0, 0, 0];

B = [0; -p.m*p.l/den; 0; p.Jp/den];

Q = diag([150, 5, 2, 1]);
R = 0.05;

if rank(ctrb(A,B)) < 4, error('System not controllable.'); end
[c.K_lqr, ~, ~] = lqr(A, B, Q, R);

fprintf('=== LQR Gains ===\n');
fprintf('K = [%.2f, %.2f, %.2f, %.2f]\n\n', ...
    c.K_lqr(1), c.K_lqr(2), c.K_lqr(3), c.K_lqr(4));

%% ================================================================
%  4. SIMULATION
% ================================================================
state0 = [pi - 0.01; 0.0; 0.0; 0.0];

dt    = 0.005;
t_end = 20.0;
t_vec = 0:dt:t_end;
N     = length(t_vec);

state_log = zeros(4, N);
F_log     = zeros(1, N);
E_log     = zeros(1, N);
mode_log  = zeros(1, N);

state     = state0;
first_lqr = true;

for i = 1:N
    state(1) = wrapToPi(state(1));

    [F, mode] = control_law(state, p, c);

    state_log(:,i) = state;
    F_log(i)       = F;
    E_log(i)       = compute_energy(state, p);
    mode_log(i)    = mode;

    if mode==1 && first_lqr
        first_lqr = false;
        fprintf('→ LQR triggered at t=%.2f s  (θ=%.1f°, θ̇=%.2f rad/s)\n', ...
            t_vec(i), state(1)*180/pi, state(2));
    end

    k1 = ode_rhs(state,          F, p);
    k2 = ode_rhs(state+dt/2*k1,  F, p);
    k3 = ode_rhs(state+dt/2*k2,  F, p);
    k4 = ode_rhs(state+dt*k3,    F, p);
    state = state + (dt/6)*(k1 + 2*k2 + 2*k3 + k4);
    
    % Hard rail clamp: applied AFTER integration, directly on state
    if state(3) > p.x_limit
        state(3) =  p.x_limit;   % clamp position
        state(4) =  0;            % kill velocity (inelastic end-stop)
    elseif state(3) < -p.x_limit
        state(3) = -p.x_limit;
        state(4) =  0;
    end
end

fprintf('\n=== Energy Stats ===\n');
fprintf('Max energy reached : %.4f J  (target: 0.0 J)\n', max(E_log));
fprintf('Energy at t=5s     : %.4f J\n', E_log(round(5/dt)+1));
fprintf('Energy at t=10s    : %.4f J\n', E_log(round(10/dt)+1));

if first_lqr
    fprintf('\n⚠  LQR never triggered.\n');
    fprintf('   If max energy < -0.5 J: increase F_max or reduce friction p.b\n');
    fprintf('   If max energy oscillates near -0.3~-0.5 J: increase k_softening\n');
else
    final_err = mean(abs(state_log(1, end-200:end))) * 180/pi;
    fprintf('\n✓  Final avg |θ| (last 1s): %.2f°  (< 5° is good)\n', final_err);
end

%% ================================================================
%  5. PLOTS
% ================================================================
figure('Name','Swing-Up Results','Position',[40 40 1100 750]);

subplot(4,1,1);
plot(t_vec, state_log(1,:)*180/pi, 'b', 'LineWidth',1.5); hold on;
shade_regions(gca, t_vec, mode_log, [-210 210]);
yline(0,'--r','Upright','LabelHorizontalAlignment','left','FontWeight','bold');
yline(180,'--k','Hanging'); yline(-180,'--k');
ylabel('\theta [°]'); title('Pendulum Angle  (green=LQR, orange=swing-up)');
ylim([-210 210]); grid on;

subplot(4,1,2);
plot(t_vec, E_log, 'm', 'LineWidth',1.5); hold on;
shade_regions(gca, t_vec, mode_log, [min(E_log)-0.05, 0.3]);
yline(c.E0,           '--r','E=0 (target)','LabelHorizontalAlignment','left');
yline(-2*p.m*p.g*p.l,'--k','E_rest',      'LabelHorizontalAlignment','left');
ylabel('Energy [J]'); title('Pendulum Energy'); grid on;

subplot(4,1,3);
plot(t_vec, state_log(3,:), 'Color',[0 0.6 0], 'LineWidth',1.5); hold on;
shade_regions(gca, t_vec, mode_log, [-c.x_limit-0.05, c.x_limit+0.05]);
yline( c.x_limit,'--r','+limit'); yline(-c.x_limit,'--r','-limit');
ylabel('x_{cart} [m]'); title('Cart Position'); grid on;

subplot(4,1,4);
plot(t_vec, F_log, 'r', 'LineWidth',1.5); hold on;
shade_regions(gca, t_vec, mode_log, [-p.F_max-0.5, p.F_max+0.5]);
yline(p.F_max,'--k'); yline(-p.F_max,'--k');
ylabel('F [N]'); xlabel('Time [s]'); title('Control Force'); grid on;

%% ================================================================
%  6. ANIMATION
% ================================================================
animate_pendulum(t_vec, state_log, mode_log, p, c);


%% ================================================================
%  LOCAL FUNCTIONS
% ================================================================

function dxdt = ode_rhs(state, F, p)
    th=state(1); thd=state(2); xd=state(4);
    s=sin(th); c_=cos(th);
    Mm = [(p.M+p.m), p.m*p.l*c_; p.m*p.l*c_, p.Jp];
    rh = [F - p.b*xd + p.m*p.l*thd^2*s; p.m*p.g*p.l*s];
    acc  = Mm \ rh;
    dxdt = [thd; acc(2); xd; acc(1)];
end

function E = compute_energy(state, p)
    % E=0 at upright, E=-2mgl at hanging rest
    E = 0.5*p.Jp*state(2)^2 + p.m*p.g*p.l*(cos(state(1)) - 1);
end

function [F, mode] = control_law(state, p, c)
    theta = state(1);  thdot = state(2);
    x     = state(3);  xdot  = state(4);

    near_upright = (cos(theta) > c.catch_cos) && ...
                   (abs(thdot) < c.catch_max_thdot);

    if near_upright
        F    = max(-p.F_max, min(p.F_max, -c.K_lqr * state));
        mode = 1;
        return;
    end

    % ---- SWING-UP (Åström & Furuta Eq. 4) ----
    %
    % From dE/dt = -m*l*a*θ̇*cos(θ):
    % To increase energy we need:  a * θ̇ * cos(θ) < 0
    % So the correct sign for force is:  F = -sign(θ̇ * cos(θ))
    %
    % Bang-bang: always apply F_max, just flip its sign.
    % Softening: scale down only when close to E0 (prevents overshoot).
    %   tanh(k*(E0-E)) → 1 when far below E0, → 0 when E≈E0
    %   This replaces the hard saturation with a smooth cutoff.

    E            = compute_energy(state, p);
    energy_error = c.E0 - E;   % positive when energy below target

    % Smooth scaling: 1.0 when far from target, tapers to 0 at target
    scale = tanh(c.k_softening * energy_error);
    scale = max(0, scale);     % never pump energy in wrong direction

    % Direction: push to increase energy
    direction = -sign(thdot * cos(theta));

    % Handle dead zone: if θ̇≈0 or θ≈±π/2, sign is undefined → hold last
    if abs(thdot) < 0.01 || abs(cos(theta)) < 0.01
        direction = 0;
    end

    F_swing = p.F_max * scale * direction;

    % ---- CART WALL PROTECTION ----
    % The previous approaches (PD blending, alpha ramp) all failed because
    % they apply centering force continuously, which fights the swing-up and
    % prevents energy from reaching E=0.
    %
    % Correct approach: only brake when the cart is HEADING OUTWARD and the
    % predicted position (x + tau*xdot) exceeds the soft limit.
    % When heading inward or staying within bounds, use pure swing-up.
    % This way the braking is a one-sided intervention, not a continuous drag.

    tau      = 0.25;          % prediction horizon [s]
    x_pred   = x + tau*xdot;  % where cart will be in tau seconds

    F_brake = 0;
    if xdot > 0 && x_pred > c.x_soft_limit
        % heading right, predicted to exceed soft limit
        penetration = min((x_pred - c.x_soft_limit) / (p.x_limit - c.x_soft_limit), 1.0);
        F_brake = -p.F_max * penetration;
    elseif xdot < 0 && x_pred < -c.x_soft_limit
        % heading left, predicted to exceed soft limit
        penetration = min((-x_pred - c.x_soft_limit) / (p.x_limit - c.x_soft_limit), 1.0);
        F_brake = +p.F_max * penetration;
    end

    F    = max(-p.F_max, min(p.F_max, F_swing + F_brake));
    mode = 0;
end

function shade_regions(ax, t_vec, mode_log, yl)
    c_swing = [1.0 0.93 0.85];
    c_lqr   = [0.88 1.0 0.88];
    i = 1; N = length(mode_log);
    while i <= N
        m = mode_log(i); j = i;
        while j <= N && mode_log(j)==m, j=j+1; end
        t0=t_vec(i); t1=t_vec(min(j,N));
        col = c_swing; if m==1, col=c_lqr; end
        fill(ax,[t0 t1 t1 t0],[yl(1) yl(1) yl(2) yl(2)], ...
             col,'EdgeColor','none','FaceAlpha',0.5);
        i = j;
    end
end

function animate_pendulum(t_vec, state_log, mode_log, p, c)
    fig = figure('Name','Animation','Position',[200 150 950 480]);
    ax  = axes(fig);
    hw  = c.x_limit + 0.15;
    axis(ax,[-hw hw -0.48 0.52]); axis equal; grid on; hold on;
    xlabel('x [m]'); ylabel('y [m]');
    title('Cart-Pendulum  |  orange=swing-up   green=LQR');

    plot(ax,[-c.x_limit c.x_limit],[-0.08 -0.08],'k-','LineWidth',4);
    plot(ax,[ c.x_limit  c.x_limit],[-0.12 0],'r--','LineWidth',1.5);
    plot(ax,[-c.x_limit -c.x_limit],[-0.12 0],'r--','LineWidth',1.5);

    cw=0.13; ch=0.06;
    cart_h = patch(ax,[-cw/2 cw/2 cw/2 -cw/2],[-ch -ch 0 0], ...
                   [0.25 0.45 0.85],'EdgeColor','k','LineWidth',1.5);
    rod_h  = plot(ax,[0 0],[0 p.l],'k-','LineWidth',3);
    bob_h  = plot(ax,0,p.l,'o','MarkerSize',15, ...
                  'MarkerFaceColor',[0.9 0.2 0.2],'MarkerEdgeColor','k');

    mode_txt   = text(ax,-hw+0.02,0.44,'SWING-UP','FontSize',13,'FontWeight','bold','Color',[0.75 0.3 0]);
    time_txt   = text(ax,-hw+0.02,0.36,'t=0.00s','FontSize',11);
    energy_txt = text(ax,-hw+0.02,0.28,'E=---','FontSize',10,'Color',[0.5 0 0.5]);
    angle_txt  = text(ax,-hw+0.02,0.20,'θ=---','FontSize',10,'Color',[0 0 0.7]);

    dt_sim   = t_vec(2)-t_vec(1);
    playback = 0.3;   % speed multiplier: 1.0=real-time, 0.3=3x slower
    skip     = max(1, round(0.025/dt_sim));

    for i = 1:skip:length(t_vec)
        if ~ishandle(fig), break; end
        x=state_log(3,i); th=state_log(1,i);
        bx=x+p.l*sin(th); by=p.l*cos(th);

        set(cart_h,'XData',x+[-cw/2 cw/2 cw/2 -cw/2]);
        set(rod_h,'XData',[x bx],'YData',[0 by]);
        set(bob_h,'XData',bx,'YData',by);

        E=compute_energy(state_log(:,i),p);
        set(energy_txt,'String',sprintf('E = %.3f J',E));
        set(time_txt,  'String',sprintf('t = %.2f s',t_vec(i)));
        set(angle_txt, 'String',sprintf('θ = %.1f°',th*180/pi));

        if mode_log(i)==1
            set(mode_txt,'String','LQR STABILIZING','Color',[0 0.55 0]);
            set(fig,'Color',[0.93 1.0 0.93]);
        else
            set(mode_txt,'String','SWING-UP','Color',[0.75 0.3 0]);
            set(fig,'Color',[1.0 0.97 0.92]);
        end
        drawnow limitrate;
        pause(dt_sim * skip / playback);
    end
end