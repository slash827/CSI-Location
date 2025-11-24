function trajectory = generate_linear_trajectory(start_pos, end_pos, n_samples, varargin)
% GENERATE_LINEAR_TRAJECTORY Generate straight-line trajectory
%
% Inputs:
%   start_pos  - [x, y] starting position (meters)
%   end_pos    - [x, y] ending position (meters)
%   n_samples  - Number of position samples
%   varargin   - Optional: 'randomize', true/false
%
% Output:
%   trajectory - [n_samples x 2] array of [x, y] positions

    p = inputParser;
    addParameter(p, 'randomize', false, @islogical);
    parse(p, varargin{:});
    
    % Linear interpolation
    t = linspace(0, 1, n_samples);
    trajectory = zeros(n_samples, 2);
    trajectory(:, 1) = start_pos(1) + t * (end_pos(1) - start_pos(1));
    trajectory(:, 2) = start_pos(2) + t * (end_pos(2) - start_pos(2));
    
    % Add small random perturbations if requested
    if p.Results.randomize
        noise_std = 0.5; % 0.5 meter standard deviation
        trajectory = trajectory + noise_std * randn(size(trajectory));
    end
end


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


function trajectory = generate_random_walk(start_pos, n_samples, varargin)
% GENERATE_RANDOM_WALK Generate random walk trajectory
%
% Inputs:
%   start_pos  - [x, y] starting position (meters)
%   n_samples  - Number of position samples
%   varargin   - Optional: 'step_size' (meters), 'bounds' ([xmin xmax ymin ymax])
%
% Output:
%   trajectory - [n_samples x 2] array of [x, y] positions

    p = inputParser;
    addParameter(p, 'step_size', 2, @isnumeric);
    addParameter(p, 'bounds', [10 90 10 90], @isnumeric);
    addParameter(p, 'smoothing', 5, @isnumeric);
    parse(p, varargin{:});
    
    trajectory = zeros(n_samples, 2);
    trajectory(1, :) = start_pos;
    
    % Random walk with momentum
    velocity = [0, 0];
    momentum = 0.7; % Keep 70% of previous velocity
    
    for i = 2:n_samples
        % Random direction with momentum
        random_accel = randn(1, 2);
        velocity = momentum * velocity + (1-momentum) * random_accel;
        velocity = velocity / norm(velocity) * p.Results.step_size;
        
        % Update position
        new_pos = trajectory(i-1, :) + velocity;
        
        % Apply bounds (bounce back)
        if new_pos(1) < p.Results.bounds(1) || new_pos(1) > p.Results.bounds(2)
            velocity(1) = -velocity(1);
            new_pos(1) = max(p.Results.bounds(1), min(p.Results.bounds(2), new_pos(1)));
        end
        if new_pos(2) < p.Results.bounds(3) || new_pos(2) > p.Results.bounds(4)
            velocity(2) = -velocity(2);
            new_pos(2) = max(p.Results.bounds(3), min(p.Results.bounds(4), new_pos(2)));
        end
        
        trajectory(i, :) = new_pos;
    end
    
    % Smooth trajectory
    if p.Results.smoothing > 1
        trajectory(:, 1) = smooth(trajectory(:, 1), p.Results.smoothing);
        trajectory(:, 2) = smooth(trajectory(:, 2), p.Results.smoothing);
    end
end


function trajectory = generate_grid_trajectory(bounds, grid_spacing, n_samples)
% GENERATE_GRID_TRAJECTORY Generate systematic grid coverage
%
% Inputs:
%   bounds        - [xmin xmax ymin ymax] (meters)
%   grid_spacing  - Distance between grid points (meters)
%   n_samples     - Number of position samples
%
% Output:
%   trajectory - [n_samples x 2] array of [x, y] positions

    xmin = bounds(1); xmax = bounds(2);
    ymin = bounds(3); ymax = bounds(4);
    
    % Generate grid points
    x_points = xmin:grid_spacing:xmax;
    y_points = ymin:grid_spacing:ymax;
    
    % Snake pattern (back and forth)
    grid_path = [];
    for j = 1:length(y_points)
        if mod(j, 2) == 1
            % Left to right
            for i = 1:length(x_points)
                grid_path = [grid_path; x_points(i), y_points(j)];
            end
        else
            % Right to left
            for i = length(x_points):-1:1
                grid_path = [grid_path; x_points(i), y_points(j)];
            end
        end
    end
    
    % Interpolate to get exact n_samples
    if size(grid_path, 1) < n_samples
        % Upsample
        t_original = linspace(0, 1, size(grid_path, 1));
        t_new = linspace(0, 1, n_samples);
        trajectory(:, 1) = interp1(t_original, grid_path(:, 1), t_new);
        trajectory(:, 2) = interp1(t_original, grid_path(:, 2), t_new);
    else
        % Downsample
        indices = round(linspace(1, size(grid_path, 1), n_samples));
        trajectory = grid_path(indices, :);
    end
end


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
