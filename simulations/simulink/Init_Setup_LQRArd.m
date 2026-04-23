clear all
clc
r = 0.006;
M_c = 0.8145;

l = 0.15;
g = 9.81;
b= 0.00007892;
L = 0.046;
Rm = 12.5;
kb = 0.031;
kt = 0.031;
c = 0.63;
m = 0.12;
M = 0.8155;
Er = 2*m*g*l+0.0199;
I = 1/12*m*(0.3)^2;
n= 3;
AA = I*(M+m) + M*m*(l^2);
aa = (((m*l)^2)*g)/AA;
bb = ((I +m*(l^2))/AA)*(c + (kb*kt)/(Rm*(r^2)));
cc  = (b*m*l)/AA;
dd  = (m*g*l*(M+m))/AA;
ee  = ((m*l)/AA)*(c + (kb*kt)/(Rm*(r^2)));
ff  = ((M+m)*b)/AA;
mm = ((I +m*(l^2))*kt)/(AA*Rm*r);
nn = (m*l*kt)/(AA*Rm*r);
A  =  [0 0 1 0; 0 0 0 1; 0 aa -bb -cc; 0 dd -ee -ff];
B = [0;0; mm; nn]; 
Q = diag([1200 1500 10000 1000]);
R  = 0.035;
KK = lqr(A,B,Q,R);
p1 = [i*2.8; -i*2.8; i*1.5; -i*1.5]; % oscillatory
p2 =[-8+i*2; -8-i*2; -7+i*2; -7-i*2 ]; % underdamped
p3 =[-8; -10; -4.5; -5.8];  % stable. 
p4 =[-20; -15.5; -45.5; -4.8];  % Fast or Aggressive.
k = place(A,B,p3);