% Recuperation des donnees depuis Simulink
t = x_raw.time;
x_data = squeeze(x_raw.signals.values);
theta_data = squeeze(theta_raw.signals.values);

% Animation plus fluide
fps = 30;                           % images par seconde
t_anim = t(1):1/fps:t(end);
x_anim = interp1(t, x_data, t_anim, 'pchip');
theta_anim = interp1(t, theta_data, t_anim, 'pchip');

% On remplace les donnees originales par les donnees interpolees
t = t_anim;
x_data = x_anim;
theta_data = theta_anim;

% Parametres
L = 0.3;          
cart_w = 0.16;    
cart_d = 0.12;    
cart_h = 0.04;    

% Figure 3D
figure;
clf;
hold on;
grid on;
axis equal;
view(3);

xlim([-0.6 1.4]);
ylim([-0.3 0.3]);
zlim([-0.3 0.5]);

xlabel('X');
ylabel('Y');
zlabel('Z');
title('Inverted Pendulum 3D');

% Rails
plot3([-1 2], [0.035 0.035], [0 0], 'k', 'LineWidth', 2);
plot3([-1 2], [-0.035 -0.035], [0 0], 'k', 'LineWidth', 2);

% Position initiale
xc = x_data(1);
yc = 0;
zc = cart_h/2;

xp = xc + L*sin(theta_data(1));
yp = -0.065;
zp = zc - L*cos(theta_data(1));

% Creation du chariot 3D
[V, F] = makeCartVertices(xc, yc, zc, cart_w, cart_d, cart_h);
hCart = patch('Vertices', V, 'Faces', F, ...
              'FaceColor', [0.2 0.6 0.8], ...
              'EdgeColor', 'k');

% Tige
hRod = plot3([xc xp], [yc-0.065 yp], [zc zp], 'r', 'LineWidth', 4);

% Pivot
hPivot = plot3(xc, yc-0.065, zc, 'go', 'MarkerSize', 6, 'MarkerFaceColor', 'g');

% Signal to Python that the window is fully rendered and ready
drawnow;
fid = fopen('animation_ready.flag', 'w');
fclose(fid);

% Animation en temps reel
tic;
for k = 1:length(t)

    xc = x_data(k);
    yc = 0;
    zc = cart_h/2;

    xp = xc + L*sin(theta_data(k));
    yp = -0.065;
    zp = zc - L*cos(theta_data(k));

    % Mise a jour du chariot
    [V, F] = makeCartVertices(xc, yc, zc, cart_w, cart_d, cart_h);
    set(hCart, 'Vertices', V, 'Faces', F);

    % Mise a jour de la tige
    set(hRod, 'XData', [xc xp], 'YData', [yc-0.065 yp], 'ZData', [zc zp]);

    % Mise a jour du pivot
    set(hPivot, 'XData', xc, 'YData', yc-0.065, 'ZData', zc);

    title(['Inverted Pendulum 3D   t = ', num2str(t(k), '%.2f'), ' s']);

    drawnow limitrate;

    while toc < t(k)
    end
end

% ===== Fonction pour creer un vrai bloc 3D =====
function [V, F] = makeCartVertices(xc, yc, zc, w, d, h)

    x1 = xc - w/2; x2 = xc + w/2;
    y1 = yc - d/2; y2 = yc + d/2;
    z1 = zc - h/2; z2 = zc + h/2;

    V = [
        x1 y1 z1;
        x2 y1 z1;
        x2 y2 z1;
        x1 y2 z1;
        x1 y1 z2;
        x2 y1 z2;
        x2 y2 z2;
        x1 y2 z2
    ];

    F = [
        1 2 3 4;
        5 6 7 8;
        1 2 6 5;
        2 3 7 6;
        3 4 8 7;
        4 1 5 8
    ];
end