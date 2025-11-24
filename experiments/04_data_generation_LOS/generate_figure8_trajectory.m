function trajectory = generate_figure8_trajectory(center, size, n_samples)
% GENERATE_FIGURE8_TRAJECTORY Generate figure-8 path
%
% Inputs:
%   center     - [x, y] center position (meters)
%   size       - Size of figure-8 (meters)
%   n_samples  - Number of position samples
%
% Output:
%   trajectory - [n_samples x 2] array of [x, y] positions

    t = linspace(0, 2*pi, n_samples);
    
    % Lemniscate curve (figure-8)
    trajectory = zeros(n_samples, 2);
    trajectory(:, 1) = center(1) + size * sin(t);
    trajectory(:, 2) = center(2) + size * sin(t) .* cos(t);
end
