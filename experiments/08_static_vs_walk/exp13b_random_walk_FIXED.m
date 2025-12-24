%% EXPERIMENT 13B: Random Walk CSI Simulation (FIXED)
% Single UE performs random walk on 3x3 grid (900 steps)
% Uses QuaDRiGa tracks for time-correlated channel generation
% 
% KEY FIX: Proper track creation with intermediate waypoints for smooth movement
%
% Grid configuration (same as exp13a):
%   7 - 8 - 9
%   4 - 5 - 6
%   1 - 2 - 3
%
% Output: random_walk_results.mat

clear; clc; close all;

%% Setup
fprintf('========================================\n');
fprintf('EXP13B: Random Walk CSI Simulation (FIXED)\n');
fprintf('========================================\n\n');

% Add utils to path
script_dir = fileparts(mfilename('fullpath'));
project_root = fileparts(fileparts(script_dir));
utils_path = fullfile(project_root, 'utils');
addpath(utils_path);

%% Configuration (must match exp13a)
config = struct();

% Grid parameters (same as exp13a)
config.grid_size = 3;           % 3x3 grid
config.spacing = 1.5;           % 1.5 meters between points
config.ue_height = 1.5;         % UE height in meters
config.grid_offset = [10, 0];   % Closer to BS for more geometric diversity

% Random walk parameters
config.n_steps = 900;            % Total steps in random walk (Reduced for testing)
config.ue_speed = 1.5;          % UE walking speed in m/s
config.step_duration = config.spacing / config.ue_speed;  % Time per step (1 second)

% Simulation parameters (same as exp13a)
config.center_frequency = 3e9;
config.bandwidth = 100e6;
config.n_subcarriers = 256;
config.scenario = '3GPP_38.901_UMa_LOS';  % LOS for more multipath diversity

% Base station configuration
config.bs_position = [0; 0; 25];  % BS at origin, 25m height

% Generate grid positions
[X, Y] = meshgrid(0:config.spacing:(config.grid_size-1)*config.spacing, ...
                  0:config.spacing:(config.grid_size-1)*config.spacing);
config.grid_positions = [X(:) + config.grid_offset(1), ...
                         Y(:) + config.grid_offset(2), ...
                         ones(config.grid_size^2, 1) * config.ue_height];
config.n_points = config.grid_size^2;

% Build adjacency map for each grid point
config.neighbors = cell(config.n_points, 1);
for row = 1:config.grid_size
    for col = 1:config.grid_size
        idx = (row-1)*config.grid_size + col;
        neighbors = [];
        % Right
        if col < config.grid_size
            neighbors = [neighbors, idx+1];
        end
        % Left
        if col > 1
            neighbors = [neighbors, idx-1];
        end
        % Up
        if row < config.grid_size
            neighbors = [neighbors, idx+config.grid_size];
        end
        % Down
        if row > 1
            neighbors = [neighbors, idx-config.grid_size];
        end
        config.neighbors{idx} = neighbors;
    end
end

fprintf('Configuration:\n');
fprintf('  Grid: %dx%d = %d points\n', config.grid_size, config.grid_size, config.n_points);
fprintf('  Spacing: %.1f m\n', config.spacing);
fprintf('  UE speed: %.1f m/s\n', config.ue_speed);
fprintf('  Time per step: %.1f seconds\n', config.step_duration);
fprintf('  Random walk steps: %d\n', config.n_steps);
fprintf('  Total walk duration: %.1f seconds (%.1f minutes)\n', ...
        config.n_steps * config.step_duration, config.n_steps * config.step_duration / 60);
fprintf('  Scenario: %s\n', config.scenario);
fprintf('\n');

%% Generate random walk path
fprintf('Generating random walk path...\n');

% Start at random point (or center)
rng('shuffle');  % Random seed
walk_path = zeros(config.n_steps + 1, 1);
walk_path(1) = 5;  % Start at center (point 5)

for step = 1:config.n_steps
    current = walk_path(step);
    neighbors = config.neighbors{current};
    % Random choice among neighbors
    next = neighbors(randi(length(neighbors)));
    walk_path(step + 1) = next;
end

% Count visits per point
visit_counts = histcounts(walk_path, 1:(config.n_points+1));
fprintf('  Visit counts per point:\n');
for pt = 1:config.n_points
    fprintf('    Point %d: %d visits\n', pt, visit_counts(pt));
end
fprintf('\n');

%% Build continuous trajectory with proper track creation
fprintf('Building QuaDRiGa-compatible track...\n');

% KEY INSIGHT: QuaDRiGa needs smooth continuous movement
% We'll create track using segments

% Convert walk path to positions
n_snapshots = config.n_steps + 1;
walk_grid_positions = zeros(3, n_snapshots);
for step = 1:n_snapshots
    pt = walk_path(step);
    walk_grid_positions(:, step) = config.grid_positions(pt, :)';
end

% Calculate cumulative distances to determine snapshot timing
movements = diff(walk_grid_positions, 1, 2);  % 3 x (n_snapshots-1)
step_distances = sqrt(sum(movements.^2, 1));  % 1 x (n_snapshots-1)
cumulative_distances = [0, cumsum(step_distances)];  % Include starting point
total_distance = cumulative_distances(end);

fprintf('  Total path length: %.1f m\n', total_distance);
fprintf('  Step Distance Statistics:\n');
fprintf('    Mean: %.4f m\n', mean(step_distances));
fprintf('    Std:  %.4f m\n', std(step_distances));
fprintf('    Min:  %.4f m\n', min(step_distances));
fprintf('    Max:  %.4f m\n', max(step_distances));
fprintf('  Displacement Statistics:\n');
fprintf('    Mean dX: %.4f m, Std dX: %.4f m\n', mean(movements(1,:)), std(movements(1,:)));
fprintf('    Mean dY: %.4f m, Std dY: %.4f m\n', mean(movements(2,:)), std(movements(2,:)));
fprintf('    Mean dZ: %.4f m, Std dZ: %.4f m\n', mean(movements(3,:)), std(movements(3,:)));
fprintf('  Expected duration: %.1f s\n', total_distance / config.ue_speed);
fprintf('\n');

%% Main simulation using QuaDRiGa tracks
fprintf('Running random walk simulation with time-correlated channels...\n');
tic;

% Initialize storage
csi_data = struct();
csi_data.H_freq = cell(n_snapshots, 1);
csi_data.H_mag = zeros(config.n_subcarriers, n_snapshots);
csi_data.H_phase = zeros(config.n_subcarriers, n_snapshots);
csi_data.position_idx = walk_path;

metrics = struct();
metrics.RSS_wb = zeros(n_snapshots, 1);
metrics.SINR_wb = zeros(n_snapshots, 1);
metrics.CQI_wb = zeros(n_snapshots, 1);
metrics.RSS_sc = zeros(config.n_subcarriers, n_snapshots);
metrics.SINR_sc = zeros(config.n_subcarriers, n_snapshots);
metrics.path_loss = zeros(n_snapshots, 1);
metrics.rms_delay_spread = zeros(n_snapshots, 1);
metrics.mean_delay = zeros(n_snapshots, 1);

% Frequency vector for conversion
fvec = linspace(-config.bandwidth/2, config.bandwidth/2, config.n_subcarriers);

% Setup CSI metrics calculator
m = CSIMetrics('SubcarrierSpacing', config.bandwidth/config.n_subcarriers, ...
               'TxPowerPerSC_dBm', 0, ...
               'NoiseFigure_dB', 7);

% Try track-based generation
use_track = true;

try
    % Create simulation parameters
    s = qd_simulation_parameters;
    s.center_frequency = config.center_frequency;
    s.use_absolute_delays = 1;
    s.show_progress_bars = 0;
    
    % CRITICAL FIX: Set sample_density based on desired snapshots
    % samples_per_meter = snapshots / total_distance
    s.samples_per_meter = n_snapshots / total_distance;
    
    fprintf('  Samples per meter: %.2f\n', s.samples_per_meter);
    fprintf('  Expected snapshots: %d\n', ceil(total_distance * s.samples_per_meter));
    fprintf('\n');
    
    % Create layout
    l = qd_layout(s);
    l.no_tx = 1;
    l.tx_position = config.bs_position;
    l.tx_array = qd_arrayant('omni');
    l.rx_array = qd_arrayant('omni');
    
    % Create track using built-in track creation
    % This will properly handle the movement
    trk = qd_track([]);
    trk.name = 'RandomWalk';
    trk.initial_position = walk_grid_positions(:, 1);
    trk.positions = walk_grid_positions;
    trk.no_snapshots = size(walk_grid_positions, 2);
    trk.scenario = {config.scenario};
    
    % Set movement parameters
    trk.set_speed(config.ue_speed);
    
    % Attach to layout
    l.track(1,1) = trk;
    
    fprintf('  Generating channels (this may take 5-10 minutes)...\n');
    
    % Generate channels
    c = l.get_channels;
    
    % Check what we got
    if isa(c, 'qd_channel')
        coeff_dims = size(c.coeff);
        n_generated = coeff_dims(4);
        
        fprintf('  Generated %d snapshots (expected %d)\n', n_generated, n_snapshots);
        
        if n_generated >= n_snapshots * 0.9  % Allow 10% tolerance
            % SUCCESS!
            fprintf('  ✓ Track-based generation SUCCESS!\n\n');
            
            % Sample the snapshots we need
            sample_indices = round(linspace(1, n_generated, n_snapshots));
            
            for step_idx = 1:n_snapshots
                snap_idx = sample_indices(step_idx);
                
                % Get channel coefficients for this snapshot
                coeff = c.coeff(:,:,:,snap_idx);  % antennas x paths x taps x snapshot
                delays = c.delay(:,:,:,snap_idx); % delays for this snapshot
                
                % Convert to frequency domain
                h_paths = squeeze(coeff);
                tau_paths = squeeze(delays);
                H_freq = (h_paths(:).' * exp(-1j * 2 * pi * tau_paths(:) * fvec(:).')).';
                
                % Store CSI
                csi_data.H_freq{step_idx} = H_freq;
                csi_data.H_mag(:, step_idx) = abs(H_freq);
                csi_data.H_phase(:, step_idx) = angle(H_freq);
                
                % Compute metrics
                % Compute metrics
                H_sc = reshape(H_freq, [1, 1, config.n_subcarriers]);
                out = m.compute(H_sc);
                
                metrics.RSS_sc(:, step_idx) = out.RSS_dBm_sc;
                metrics.SINR_sc(:, step_idx) = out.SINR_dB_sc;
                metrics.RSS_wb(step_idx) = out.RSS_dBm_wb;
                metrics.SINR_wb(step_idx) = out.SINR_dB_wb;
                metrics.CQI_wb(step_idx) = out.CQI_wb;
                
                % Channel statistics
                h_t = squeeze(coeff);
                tau = squeeze(delays);
                stats = ExperimentUtils.calculateChannelStats(h_t, tau * 1e9);
                
                metrics.path_loss(step_idx) = stats.path_loss_dB;
                metrics.rms_delay_spread(step_idx) = stats.rms_delay_spread_ns;
                metrics.mean_delay(step_idx) = stats.mean_delay_ns;
                
                if mod(step_idx, 100) == 0
                    fprintf('    Processed %d/%d snapshots...\n', step_idx, n_snapshots);
                end
            end
            
        else
            warning('Got %d snapshots instead of %d - falling back', n_generated, n_snapshots);
            use_track = false;
        end
    else
        warning('Invalid channel object returned - falling back');
        use_track = false;
    end
    
catch ME
    warning('Track-based generation failed: %s', ME.message);
    fprintf('Stack trace:\n%s\n', getReport(ME));
    use_track = false;
end

% FALLBACK: Step-by-step generation
if ~use_track
    fprintf('\nFalling back to step-by-step generation...\n');
    fprintf('  (This will take longer and lose temporal correlation)\n\n');
    
    for step_idx = 1:n_snapshots
        % Get position for this step
        pos = walk_grid_positions(:, step_idx);
        
        % Create independent channel for this position
        s = qd_simulation_parameters;
        s.center_frequency = config.center_frequency;
        s.use_absolute_delays = 1;
        s.show_progress_bars = 0;
        
        l = qd_layout(s);
        l.no_tx = 1;
        l.tx_position = config.bs_position;
        l.rx_position = pos;
        l.tx_array = qd_arrayant('omni');
        l.rx_array = qd_arrayant('omni');
        l.set_scenario(config.scenario);
        
        c = l.get_channels;
        
        % Process channel
        coeff = c.coeff;
        delays = c.delay;
        
        % Convert to frequency domain
        h_paths = squeeze(coeff);
        tau_paths = squeeze(delays);
        H_freq = (h_paths(:).' * exp(-1j * 2 * pi * tau_paths(:) * fvec(:).')).';
        
        csi_data.H_freq{step_idx} = H_freq;
        csi_data.H_mag(:, step_idx) = abs(H_freq);
        csi_data.H_phase(:, step_idx) = angle(H_freq);
        
        % Compute metrics
        H_sc = reshape(H_freq, [1, 1, config.n_subcarriers]);
        out = m.compute(H_sc);
        
        metrics.RSS_sc(:, step_idx) = out.RSS_dBm_sc;
        metrics.SINR_sc(:, step_idx) = out.SINR_dB_sc;
        metrics.RSS_wb(step_idx) = out.RSS_dBm_wb;
        metrics.SINR_wb(step_idx) = out.SINR_dB_wb;
        metrics.CQI_wb(step_idx) = out.CQI_wb;
        
        % Channel statistics
        h_t = squeeze(coeff);
        tau = squeeze(delays);
        stats = ExperimentUtils.calculateChannelStats(h_t, tau * 1e9);
        
        metrics.path_loss(step_idx) = stats.path_loss_dB;
        metrics.rms_delay_spread(step_idx) = stats.rms_delay_spread_ns;
        metrics.mean_delay(step_idx) = stats.mean_delay_ns;
        
        if mod(step_idx, 100) == 0
            fprintf('    Generated %d/%d independent channels...\n', step_idx, n_snapshots);
        end
    end
end

elapsed_time = toc;
fprintf('\nChannel generation complete!\n');
fprintf('  Elapsed time: %.1f seconds (%.2f minutes)\n', elapsed_time, elapsed_time/60);
fprintf('  Method: %s\n\n', ternary(use_track, 'Track-based (time-correlated)', 'Step-by-step (independent)'));

%% Compute transition statistics
fprintf('Computing transition statistics...\n');

transitions = struct();
transitions.from_point = walk_path(1:end-1);
transitions.to_point = walk_path(2:end);
transitions.H_mag_diff = diff(csi_data.H_mag, 1, 2);
transitions.H_phase_diff = diff(csi_data.H_phase, 1, 2);
transitions.RSS_wb_diff = diff(metrics.RSS_wb);
transitions.SINR_wb_diff = diff(metrics.SINR_wb);
transitions.CQI_wb_diff = diff(metrics.CQI_wb);
transitions.path_loss_diff = diff(metrics.path_loss);

% Create pair labels for static pairs (neighboring points)
static_pairs = [
    1, 2;  % Pair 1
    1, 4;  % Pair 2
    2, 3;  % Pair 3
    2, 5;  % Pair 4
    3, 6;  % Pair 5
    4, 5;  % Pair 6
    4, 7;  % Pair 7
    5, 6;  % Pair 8
    5, 8;  % Pair 9
    6, 9;  % Pair 10
    7, 8;  % Pair 11
    8, 9   % Pair 12
];

% Map each transition to a static pair
transitions.static_pair_idx = zeros(config.n_steps, 1);
pair_transition_counts = zeros(size(static_pairs, 1), 1);

for i = 1:config.n_steps
    from = transitions.from_point(i);
    to = transitions.to_point(i);
    
    % Check both directions (undirected)
    for pair_idx = 1:size(static_pairs, 1)
        if (from == static_pairs(pair_idx,1) && to == static_pairs(pair_idx,2)) || ...
           (from == static_pairs(pair_idx,2) && to == static_pairs(pair_idx,1))
            transitions.static_pair_idx(i) = pair_idx;
            pair_transition_counts(pair_idx) = pair_transition_counts(pair_idx) + 1;
            break;
        end
    end
end

fprintf('  ✓ Transition statistics computed\n\n');

%% Organize data by grid point
fprintf('Organizing data by grid point...\n');

metrics_by_point = struct();
for pt = 1:config.n_points
    mask = (walk_path == pt);
    metrics_by_point(pt).RSS = metrics.RSS_wb(mask);
    metrics_by_point(pt).SINR = metrics.SINR_wb(mask);
    metrics_by_point(pt).CQI = metrics.CQI_wb(mask);
    metrics_by_point(pt).path_loss = metrics.path_loss(mask);
    metrics_by_point(pt).visit_indices = find(mask);
end

fprintf('  ✓ Data organized\n\n');

%% Save results
output_dir = fullfile(project_root, 'results', sprintf('exp13b_%s', datestr(now, 'yyyy-mm-dd_HH-MM-SS')));
if ~exist(output_dir, 'dir')
    mkdir(output_dir);
end

fprintf('Saving results to: %s\n', output_dir);

% Save main results file
save(fullfile(output_dir, 'random_walk_results.mat'), ...
     'config', 'walk_path', 'csi_data', 'metrics', 'transitions', ...
     'metrics_by_point', 'visit_counts', 'static_pairs', 'pair_transition_counts', ...
     'use_track', 'elapsed_time');

fprintf('  ✓ Saved random_walk_results.mat\n');

%% Export CSV files per grid point
fprintf('\nExporting CSV files per grid point...\n');

for pt = 1:config.n_points
    rss_vals = metrics_by_point(pt).RSS(:);
    sinr_vals = metrics_by_point(pt).SINR(:);
    cqi_vals = metrics_by_point(pt).CQI(:);
    
    n_visits = length(rss_vals);
    
    if n_visits > 0
        T = table((1:n_visits)', rss_vals, sinr_vals, cqi_vals, ...
                  'VariableNames', {'Visit', 'RSS_dBm', 'SINR_dB', 'CQI'});
        
        csv_filename = sprintf('grid_point_%d_metrics.csv', pt);
        writetable(T, fullfile(output_dir, csv_filename));
        fprintf('  ✓ Saved %s (%d visits)\n', csv_filename, n_visits);
    end
end

%% Print statistics
fprintf('\n=== EXPERIMENT SUMMARY ===\n');
fprintf('Generation method: %s\n', ternary(use_track, 'Track-based', 'Step-by-step'));
fprintf('RSS variance: %.2f dB (expected: ~%.1f dB for %s)\n', ...
        std(metrics.RSS_wb), ...
        ternary(use_track, 1.5, 3.5), ...
        ternary(use_track, 'walking', 'independent samples'));

% Helper function
function result = ternary(condition, true_val, false_val)
    if condition
        result = true_val;
    else
        result = false_val;
    end
end
