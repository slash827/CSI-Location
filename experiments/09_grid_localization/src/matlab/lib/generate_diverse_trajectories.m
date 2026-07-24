function [walk_indices, movement_times] = generate_diverse_trajectories(grid_size, n_steps, pattern_type, speed_ms, spacing_m, seed)
% GENERATE_DIVERSE_TRAJECTORIES Generate structured and realistic UE movement paths
%
%   [WALK_INDICES, MOVEMENT_TIMES] = generate_diverse_trajectories(GRID_SIZE, N_STEPS, PATTERN_TYPE, SPEED_MS, SPACING_M, SEED)
%
%   Inputs:
%     grid_size    - size of grid side (e.g., 25 for 25x25)
%     n_steps      - number of movement steps (e.g., 400 to 600)
%     pattern_type - 'billiards', 'momentum_walk', 'waypoint_tour', 'straight_transit'
%     speed_ms     - UE movement speed in m/s
%     spacing_m    - grid spacing in meters (e.g., 4.0)
%     seed         - random seed for reproducibility
%
%   Outputs:
%     walk_indices   - [n_steps + 1, 1] 1-based grid point indices
%     movement_times - [n_steps, 1] step time duration in seconds

if nargin >= 6 && ~isempty(seed)
    rng(seed);
end

n_points = grid_size * grid_size;
walk_indices = zeros(n_steps + 1, 1);
movement_times = zeros(n_steps, 1);

% Helper functions for row/col <-> index conversion
idx_from_rc = @(r, c) (r - 1) * grid_size + c;
rc_from_idx = @(idx) [ceil(idx / grid_size), mod(idx - 1, grid_size) + 1];

switch lower(pattern_type)
    case 'billiards'  % Road / Straight street navigation with boundary bounces
        % Pick random start position
        curr_r = randi(grid_size);
        curr_c = randi(grid_size);
        walk_indices(1) = idx_from_rc(curr_r, curr_c);
        
        % Initial direction vector
        dirs = [-1 -1; -1 0; -1 1; 0 -1; 0 1; 1 -1; 1 0; 1 1];
        d = dirs(randi(size(dirs, 1)), :);
        
        for step = 1:n_steps
            next_r = curr_r + d(1);
            next_c = curr_c + d(2);
            
            % Check boundary hit
            if next_r < 1 || next_r > grid_size || next_c < 1 || next_c > grid_size
                % Reflect direction
                if next_r < 1 || next_r > grid_size
                    d(1) = -d(1);
                end
                if next_c < 1 || next_c > grid_size
                    d(2) = -d(2);
                end
                next_r = curr_r + d(1);
                next_c = curr_c + d(2);
                
                % Safety clamp if in corner
                next_r = max(1, min(grid_size, next_r));
                next_c = max(1, min(grid_size, next_c));
            end
            
            is_diag = (d(1) ~= 0) && (d(2) ~= 0);
            dist_m = spacing_m * (is_diag * sqrt(2) + (~is_diag) * 1.0);
            movement_times(step) = dist_m / max(0.1, speed_ms);
            
            curr_r = next_r;
            curr_c = next_c;
            walk_indices(step + 1) = idx_from_rc(curr_r, curr_c);
        end
        
    case 'momentum_walk'  % Smooth random walk with momentum bias (70% straight)
        curr_r = randi(grid_size);
        curr_c = randi(grid_size);
        walk_indices(1) = idx_from_rc(curr_r, curr_c);
        
        dirs = [-1 -1; -1 0; -1 1; 0 -1; 0 1; 1 -1; 1 0; 1 1];
        d = dirs(randi(size(dirs, 1)), :);
        
        for step = 1:n_steps
            if rand() > 0.70  % 30% chance to turn
                d = dirs(randi(size(dirs, 1)), :);
            end
            
            next_r = curr_r + d(1);
            next_c = curr_c + d(2);
            
            if next_r < 1 || next_r > grid_size || next_c < 1 || next_c > grid_size
                % Pick any valid neighbor if hitting boundary
                d = dirs(randi(size(dirs, 1)), :);
                next_r = max(1, min(grid_size, curr_r + d(1)));
                next_c = max(1, min(grid_size, curr_c + d(2)));
            end
            
            is_diag = (curr_r ~= next_r) && (curr_c ~= next_c);
            dist_m = spacing_m * (is_diag * sqrt(2) + (~is_diag) * 1.0);
            movement_times(step) = dist_m / max(0.1, speed_ms);
            
            curr_r = next_r;
            curr_c = next_c;
            walk_indices(step + 1) = idx_from_rc(curr_r, curr_c);
        end
        
    case 'waypoint_tour'  % Waypoint destination tour
        n_waypoints = 5;
        waypoints = zeros(n_waypoints, 2);
        for w = 1:n_waypoints
            waypoints(w, :) = [randi(grid_size), randi(grid_size)];
        end
        
        curr_r = waypoints(1, 1);
        curr_c = waypoints(1, 2);
        walk_indices(1) = idx_from_rc(curr_r, curr_c);
        
        wp_idx = 2;
        for step = 1:n_steps
            target_r = waypoints(wp_idx, 1);
            target_c = waypoints(wp_idx, 2);
            
            % Step towards target waypoint
            dr = sign(target_r - curr_r);
            dc = sign(target_c - curr_c);
            
            if dr == 0 && dc == 0
                % Reached waypoint, advance to next
                wp_idx = mod(wp_idx, n_waypoints) + 1;
                target_r = waypoints(wp_idx, 1);
                target_c = waypoints(wp_idx, 2);
                dr = sign(target_r - curr_r);
                dc = sign(target_c - curr_c);
            end
            
            next_r = curr_r + dr;
            next_c = curr_c + dc;
            
            is_diag = (dr ~= 0) && (dc ~= 0);
            dist_m = spacing_m * (is_diag * sqrt(2) + (~is_diag) * 1.0);
            movement_times(step) = dist_m / max(0.1, speed_ms);
            
            curr_r = next_r;
            curr_c = next_c;
            walk_indices(step + 1) = idx_from_rc(curr_r, curr_c);
        end
        
    otherwise  % Straight arterial transit
        % Start at a random boundary point
        side = randi(4);
        if side == 1, curr_r = 1; curr_c = randi(grid_size); dr = 1; dc = 0; end
        if side == 2, curr_r = grid_size; curr_c = randi(grid_size); dr = -1; dc = 0; end
        if side == 3, curr_r = randi(grid_size); curr_c = 1; dr = 0; dc = 1; end
        if side == 4, curr_r = randi(grid_size); curr_c = grid_size; dr = 0; dc = -1; end
        
        walk_indices(1) = idx_from_rc(curr_r, curr_c);
        
        for step = 1:n_steps
            next_r = curr_r + dr;
            next_c = curr_c + dc;
            
            if next_r < 1 || next_r > grid_size || next_c < 1 || next_c > grid_size
                dr = -dr;
                dc = -dc;
                next_r = curr_r + dr;
                next_c = curr_c + dc;
            end
            
            is_diag = (dr ~= 0) && (dc ~= 0);
            dist_m = spacing_m * (is_diag * sqrt(2) + (~is_diag) * 1.0);
            movement_times(step) = dist_m / max(0.1, speed_ms);
            
            curr_r = next_r;
            curr_c = next_c;
            walk_indices(step + 1) = idx_from_rc(curr_r, curr_c);
        end
end
end
