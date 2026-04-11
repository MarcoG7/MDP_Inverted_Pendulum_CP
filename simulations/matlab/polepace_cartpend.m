clear all;
close all;
clc;


m = 1;
M = 5;
L = 2;
g = -10;
d = 1;

s = 1;  % pendulum up (s=1)

A = [0 1 0 0;
    0 -d/M -m*g/M 0;
    0 0 0 1;
    0 -s*d/(M*L) -s*(m+M)*g/(M*L) 0];

B = [0; 1/M; 0; s*1/(M*L)];


%%  Pole placement

% p= [-.1;-.2;-.3;-.4]
% p= [-.3;-.4;-.5;-.6]
% p= [-1;-1.1;-1.2;-1.3]
% p= [-2;-2.1;-2.2;-2.3]
p = [-3; -3.1; -3.2; -3.3];
% p= [-3.5;-3.6;-3.7-3.8]
K = place(A, B, p);

tspan = 0:.001:10;
if (s == -1)
    y0 = [0; 0; 0; 0];
    [t, y] = ode45(@(t,y)pendcart(y, m, M, L, g, d, -K*(y-[4;0;0;0])), tspan, y0);

elseif(s == 1)
    y0 = [-3; 0; pi+.1; 0];
    [t, y] = ode45(@(t,y)pendcart(y, m, M, L, g, d, -K*(y-[2;0;pi;0])), tspan, y0);
else
end

for k = 1 : 100 : length(t)
    drawpend(y(k, :), m, M, L);
end
