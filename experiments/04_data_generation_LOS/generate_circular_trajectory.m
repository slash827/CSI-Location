function trajectory = generate_circular_trajectory(center, radius, n_samples, varargin)
% GENERATE_CIRCULAR_TRAJECTORY Generate circular path
%
% Inputs:
%   center     - [x, y] center position (meters)
%   radius     - Circle radius (meters)
%   n_samples  - Number of position samples
%   varargin   - Optional: 'direction' ('cw'/'ccw'), 'start_angle' (radians)
%
% Output:
%   trajectory - [n_samples x 2] array of [x, y] positions

    p = inputParser;
    addParameter(p, 'direction', 'ccw', @(x) ismember(x, {'cw', 'ccw'}));
    addParameter(p, 'start_angle', 0, @isnumeric);
    addParameter(p, 'revolutions', 1, @isnumeric);
    parse(p, varargin{:});
    
    % Generate angles
    theta = linspace(0, 2*pi*p.Results.revolutions, n_samples) + p.Results.start_angle;
    
    % Clockwise or counter-clockwise
    if strcmp(p.Results.direction, 'cw')
        theta = -theta;
    end
    
    % Generate positions
    trajectory = zeros(n_samples, 2);
    trajectory(:, 1) = center(1) + radius * cos(theta);
    trajectory(:, 2) = center(2) + radius * sin(theta);
end
