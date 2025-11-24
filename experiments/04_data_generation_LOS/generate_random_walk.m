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
    
    % Smooth trajectory using simple moving average
    if p.Results.smoothing > 1
        window = p.Results.smoothing;
        trajectory(:, 1) = movmean(trajectory(:, 1), window);
        trajectory(:, 2) = movmean(trajectory(:, 2), window);
    end
end
