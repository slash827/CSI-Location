function trajectory = generate_zigzag_trajectory(start_pos, end_pos, n_samples, varargin)
% GENERATE_ZIGZAG_TRAJECTORY Generate zigzag path
%
% Inputs:
%   start_pos  - [x, y] starting position (meters)
%   end_pos    - [x, y] ending position (meters)
%   n_samples  - Number of position samples
%   varargin   - Optional: 'amplitude' (meters), 'frequency' (cycles)
%
% Output:
%   trajectory - [n_samples x 2] array of [x, y] positions

    p = inputParser;
    addParameter(p, 'amplitude', 5, @isnumeric);
    addParameter(p, 'frequency', 3, @isnumeric);
    parse(p, varargin{:});
    
    % Base linear trajectory
    t = linspace(0, 1, n_samples);
    trajectory = zeros(n_samples, 2);
    
    % Direction vector
    direction = end_pos - start_pos;
    direction_norm = direction / norm(direction);
    perpendicular = [-direction_norm(2), direction_norm(1)];
    
    % Add zigzag pattern perpendicular to direction
    zigzag = p.Results.amplitude * sin(2*pi*p.Results.frequency*t);
    
    trajectory(:, 1) = start_pos(1) + t * direction(1) + zigzag * perpendicular(1);
    trajectory(:, 2) = start_pos(2) + t * direction(2) + zigzag * perpendicular(2);
end
