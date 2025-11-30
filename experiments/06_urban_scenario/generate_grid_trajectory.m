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
