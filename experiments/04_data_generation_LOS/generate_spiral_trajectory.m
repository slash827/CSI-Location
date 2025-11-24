function trajectory = generate_spiral_trajectory(center, n_samples, varargin)
% GENERATE_SPIRAL_TRAJECTORY Generate spiral path
%
% Inputs:
%   center     - [x, y] center position (meters)
%   n_samples  - Number of position samples
%   varargin   - Optional: 'radius_start', 'radius_end', 'revolutions'
%
% Output:
%   trajectory - [n_samples x 2] array of [x, y] positions

    p = inputParser;
    addParameter(p, 'radius_start', 5, @isnumeric);
    addParameter(p, 'radius_end', 30, @isnumeric);
    addParameter(p, 'revolutions', 3, @isnumeric);
    addParameter(p, 'direction', 'out', @(x) ismember(x, {'out', 'in'}));
    parse(p, varargin{:});
    
    % Generate spiral parameters
    theta = linspace(0, 2*pi*p.Results.revolutions, n_samples);
    
    if strcmp(p.Results.direction, 'out')
        radius = linspace(p.Results.radius_start, p.Results.radius_end, n_samples);
    else
        radius = linspace(p.Results.radius_end, p.Results.radius_start, n_samples);
    end
    
    % Generate positions
    trajectory = zeros(n_samples, 2);
    trajectory(:, 1) = center(1) + radius' .* cos(theta');
    trajectory(:, 2) = center(2) + radius' .* sin(theta');
end
