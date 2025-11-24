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
