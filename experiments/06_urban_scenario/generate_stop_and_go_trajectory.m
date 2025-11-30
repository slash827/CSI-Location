function trajectory = generate_stop_and_go_trajectory(start_pos, n_samples, varargin)
% GENERATE_STOP_AND_GO_TRAJECTORY Generate a stop-and-go trajectory
%
% Simulates realistic human movement with walking segments and stops
% (e.g., shopping, browsing, waiting)
%
% Inputs:
%   start_pos   - [x, y] starting position
%   n_samples   - Total number of samples
%   varargin    - Optional parameters:
%                 'segment_length' - [min, max] distance between stops (default: [10, 30])
%                 'stop_duration' - [min, max] timesteps to stop (default: [3, 8])
%                 'n_stops' - [min, max] number of stops (default: [2, 5])
%                 'bounds' - [x_min, x_max, y_min, y_max] (default: no bounds)
%
% Output:
%   trajectory  - [n_samples x 2] array of [x, y] positions

    % Parse optional parameters
    p = inputParser;
    addParameter(p, 'segment_length', [10, 30]);
    addParameter(p, 'stop_duration', [3, 8]);
    addParameter(p, 'n_stops', [2, 5]);
    addParameter(p, 'bounds', []);
    parse(p, varargin{:});
    
    segment_length = p.Results.segment_length;
    stop_duration = p.Results.stop_duration;
    n_stops_range = p.Results.n_stops;
    bounds = p.Results.bounds;
    
    % Determine number of stops
    n_stops = randi([n_stops_range(1), n_stops_range(2)]);
    
    % Determine stop durations
    stop_durations = randi([stop_duration(1), stop_duration(2)], 1, n_stops);
    total_stop_samples = sum(stop_durations);
    
    % Remaining samples for walking
    walking_samples = n_samples - total_stop_samples;
    
    if walking_samples < n_stops + 1
        % Not enough samples for stops and walking segments
        % Fall back to simple random walk
        trajectory = generate_random_walk(start_pos, n_samples, ...
            'step_size', mean(segment_length)/10, 'bounds', bounds);
        return;
    end
    
    % Distribute walking samples among segments
    segment_samples = distribute_samples(walking_samples, n_stops + 1);
    
    % Initialize trajectory
    trajectory = zeros(n_samples, 2);
    current_idx = 1;
    current_pos = start_pos;
    
    % Generate each segment
    for seg = 1:n_stops + 1
        % Walking segment
        n_seg_samples = segment_samples(seg);
        
        if n_seg_samples > 0
            % Determine direction and distance
            angle = 2*pi*rand();
            distance = segment_length(1) + diff(segment_length)*rand();
            target_pos = current_pos + distance * [cos(angle), sin(angle)];
            
            % Apply bounds if specified
            if ~isempty(bounds)
                target_pos(1) = max(bounds(1), min(bounds(2), target_pos(1)));
                target_pos(2) = max(bounds(3), min(bounds(4), target_pos(2)));
            end
            
            % Linear interpolation for walking
            for i = 1:n_seg_samples
                alpha = (i-1) / (n_seg_samples-1);
                trajectory(current_idx, :) = (1-alpha)*current_pos + alpha*target_pos;
                current_idx = current_idx + 1;
            end
            
            current_pos = target_pos;
        end
        
        % Stop (if not last segment)
        if seg <= n_stops
            n_stop_samples = stop_durations(seg);
            for i = 1:n_stop_samples
                trajectory(current_idx, :) = current_pos;
                current_idx = current_idx + 1;
            end
        end
    end
end

function samples = distribute_samples(total, n_segments)
    % Distribute total samples among n_segments
    samples = zeros(1, n_segments);
    remaining = total;
    
    for i = 1:n_segments-1
        % Randomly allocate, but ensure at least 1 for remaining segments
        max_alloc = remaining - (n_segments - i);
        if max_alloc < 1
            samples(i) = 0;
        else
            samples(i) = randi([1, max_alloc]);
        end
        remaining = remaining - samples(i);
    end
    
    % Last segment gets remainder
    samples(n_segments) = remaining;
end
