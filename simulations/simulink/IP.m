clear all;
clc;
%r = 0.006;
M_c = 0.5178;     %mass of the cart
l = 0.15;         % en m distance from the pivot to the rod's center of gravity (pendulum 3m by constraints)
g = 9.81;         % gravitational constant
b = 0.00007892;   %N.m/rad/sec
% L = 0.046;
% Rm = 12.5;
% kb = 1.031;
% kt = 1.031;
c = 0.63;  %N/m/sec
m = 0.12;  %mass of the pendulum rod
I = (1/12)*(m*(2*l)^2);  %kg.m^2
% M = 0.136;
Er = 2*m*g*l;
n = 3;

% State-space representation
alpha = I*(M_c+m)+M_c*m*l^2;
A = [0 0 1 0; 0 0 0 1; 0 (m^2*l^2*g/alpha) (-c*(I+m*l^2)/alpha) -b*m*l/alpha; 0 ((M_c+m)*m*g*l/alpha) (-c*m*l/alpha) (-(M_c+m)*b/alpha)];
B = [0; 0; (I +m*(l^2))/(alpha); (m*l)/(alpha)];
C = [1 0 0 0; 0 1 0 0; 0 0 1 0; 0 0 0 1];
D = 0;
sys_c = ss(A,B,C,D);

% LQR design
Q = [5000 0 0 0; 0 1000 0 0; 0 0 0 0; 0 0 0 0];
R = 0.008;
KK = lqr(A,B,Q,R);

% Discretised system
Ts = 0.005;  %5ms
sys_d = c2d(sys_c,Ts,'zoh');

Ad = sys_d.A;
Bd = sys_d.B;
Cd = sys_d.C;
Dd = sys_d.D;
Kd = dlqr(Ad,Bd,Q,R);
