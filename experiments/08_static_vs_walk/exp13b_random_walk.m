%% EXPERIMENT 13B: Random Walk CSI Simulation
% Single UE performs random walk on 3x3 grid (900 steps)
% Uses QuaDRiGa tracks for time-correlated channel generation
% UE moves at 1 m/s (1 second per step for 1m spacing)
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
fprintf('EXP13B: Random Walk CSI Simulation\n');
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
config.spacing = 2;           % 1.5 meters between points
config.ue_height = 1.5;         % UE height in meters
config.grid_offset = [10, 0];  % Closer to BS for more geometric diversity

% Random walk parameters
config.n_steps = 900;           % Total steps in random walk
config.ue_speed = 2;          % UE walking speed in m/s
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
% Grid indexing:
%   7 - 8 - 9
%   4 - 5 - 6
%   1 - 2 - 3
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
fprintf('  Expected visits per point: ~%d\n', round(config.n_steps / config.n_points));
fprintf('  Scenario: %s (LOS)\n', config.scenario);
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

%% Initialize storage
fprintf('Initializing storage...\n');

% CSI storage per step
csi_data = struct();
csi_data.H_freq = cell(config.n_steps + 1, 1);  % Full frequency response
csi_data.H_mag = zeros(config.n_subcarriers, config.n_steps + 1);
csi_data.H_phase = zeros(config.n_subcarriers, config.n_steps + 1);
csi_data.position_idx = walk_path;  % Which grid point at each step

% Metrics storage per step
metrics = struct();
metrics.RSS_wb = zeros(config.n_steps + 1, 1);
metrics.SINR_wb = zeros(config.n_steps + 1, 1);
metrics.CQI_wb = zeros(config.n_steps + 1, 1);
metrics.RSS_sc = zeros(config.n_subcarriers, config.n_steps + 1);
metrics.SINR_sc = zeros(config.n_subcarriers, config.n_steps + 1);
metrics.path_loss = zeros(config.n_steps + 1, 1);
metrics.rms_delay_spread = zeros(config.n_steps + 1, 1);
metrics.mean_delay = zeros(config.n_steps + 1, 1);

% Transition storage (differences between consecutive steps)
transitions = struct();
transitions.from_point = walk_path(1:end-1);
transitions.to_point = walk_path(2:end);
transitions.H_mag_diff = zeros(config.n_subcarriers, config.n_steps);
transitions.H_phase_diff = zeros(config.n_subcarriers, config.n_steps);
transitions.RSS_wb_diff = zeros(config.n_steps, 1);
transitions.SINR_wb_diff = zeros(config.n_steps, 1);
transitions.CQI_wb_diff = zeros(config.n_steps, 1);
transitions.path_loss_diff = zeros(config.n_steps, 1);

fprintf('  ✓ Storage initialized\n\n');

%% Setup CSI metrics calculator
m = CSIMetrics('SubcarrierSpacing', config.bandwidth/config.n_subcarriers, ...
               'TxPowerPerSC_dBm', 0, ...
               'NoiseFigure_dB', 7);

%% Build trajectory positions from walk path
fprintf('Building trajectory from random walk path...\n');

% Convert walk path indices to 3D positions
n_snapshots = config.n_steps + 1;
walk_positions = zeros(3, n_snapshots);
for step = 1:n_snapshots
    pt = walk_path(step);
    walk_positions(:, step) = config.grid_positions(pt, :)';
end

fprintf('  Total trajectory: %d snapshots\n', n_snapshots);
fprintf('  Start position: [%.1f, %.1f, %.1f] m (grid point %d)\n', ...
        walk_positions(:,1)', walk_path(1));
fprintf('  End position: [%.1f, %.1f, %.1f] m (grid point %d)\n', ...
        walk_positions(:,end)', walk_path(end));
fprintf('\n');

%% Main simulation using QuaDRiGa tracks
fprintf('Running random walk simulation with time-correlated channels...\n');
fprintf('UE speed: %.1f m/s, Step duration: %.1f s\n\n', config.ue_speed, config.step_duration);
tic;

% Frequency vector for conversion
fvec = linspace(-config.bandwidth/2, config.bandwidth/2, config.n_subcarriers);

% Try to use track-based generation for time correlation
use_track = true;
try
    % Create simulation parameters
    s = qd_simulation_parameters;
    s.center_frequency = config.center_frequency;
    s.sample_density = 2;
    s.use_absolute_delays = 1;
    
    % Create layout
    l = qd_layout(s);
    l.no_tx = 1;
    l.tx_position = config.bs_position;
    l.tx_array = qd_arrayant('omni');
    l.rx_array = qd_arrayant('omni');
    
    % Create track for the random walk
    trk = qd_track;
    trk.name = 'RandomWalkUE';
    trk.initial_position = walk_positions(:, 1);
    trk.positions = walk_positions;  % 3 x n_snapshots matrix
    trk.scenario = {config.scenario};
    
    % Attach track to layout
    l.rx_track = {trk};
    
    fprintf('Generating time-correlated channels along track...\n');
    fprintf('(This may take a few minutes for %d snapshots)\n', n_snapshots);
    
    % Generate channels along the entire track
    c = l.get_channels;
    
    % Verify we got all snapshots
    coeff_size = size(c.coeff);
    if length(coeff_size) < 4 || coeff_size(4) ~= n_snapshots
        warning('Expected %d snapshots, got %d. Falling back to step-by-step.', ...
                n_snapshots, coeff_size(end));
        use_track = false;
    else
        fprintf('  ✓ Generated %d time-correlated snapshots\n', coeff_size(4));
    end
catch ME
    warning('RandomWalk:TrackFailed', 'Track-based generation failed: %s. Falling back to step-by-step generation.', ME.message);
    use_track = false;
end

fprintf('Progress: ');

% Initialize per-grid-point metric storage
metrics_by_point = struct();
for pt = 1:config.n_points
    metrics_by_point(pt).RSS = [];
    metrics_by_point(pt).SINR = [];
    metrics_by_point(pt).CQI = [];
end

if use_track

    % Process all snapshots from track-generated channels
    for step = 1:n_snapshots
        % Get channel for this snapshot
        h_t = squeeze(c.coeff(1,1,:,step));
        tau = squeeze(c.delay(1,:,step));
        
        % Ensure same dimensions
        n_taps = min(length(h_t), length(tau));
        h_t = h_t(1:n_taps);
        tau = tau(1:n_taps);
        
        % Remove zero-power taps
        valid_idx = abs(h_t) > 1e-12;
        h_t = h_t(valid_idx);
        tau = tau(valid_idx);
        
        % Convert to frequency domain
        H_freq = ExperimentUtils.convertToFrequency(h_t, tau, fvec);
        
        % Store CSI
        csi_data.H_freq{step} = H_freq;
        csi_data.H_mag(:, step) = abs(H_freq(:));
        csi_data.H_phase(:, step) = angle(H_freq(:));
        
        % Compute metrics
        H_sc = reshape(H_freq, [1, 1, config.n_subcarriers]);
        out = m.compute(H_sc);
        
        metrics.RSS_wb(step) = out.RSS_dBm_wb;
        metrics.SINR_wb(step) = out.SINR_dB_wb;
        metrics.CQI_wb(step) = out.CQI_wb;
        metrics.RSS_sc(:, step) = out.RSS_dBm_sc;
        metrics.SINR_sc(:, step) = out.SINR_dB_sc;
        
        % Channel statistics
        stats = ExperimentUtils.calculateChannelStats(h_t, tau * 1e9);
        metrics.path_loss(step) = stats.path_loss_dB;
        metrics.rms_delay_spread(step) = stats.rms_delay_spread_ns;
        metrics.mean_delay(step) = stats.mean_delay_ns;
        
        % Store metrics by grid point
        pt = walk_path(step);
        metrics_by_point(pt).RSS = [metrics_by_point(pt).RSS, metrics.RSS_wb(step)];
        metrics_by_point(pt).SINR = [metrics_by_point(pt).SINR, metrics.SINR_wb(step)];
        metrics_by_point(pt).CQI = [metrics_by_point(pt).CQI, metrics.CQI_wb(step)];
        
        % Compute transition differences (if not first step)
        if step > 1
            t_idx = step - 1;
            transitions.H_mag_diff(:, t_idx) = csi_data.H_mag(:, step) - csi_data.H_mag(:, step-1);
            transitions.H_phase_diff(:, t_idx) = wrapToPi(csi_data.H_phase(:, step) - csi_data.H_phase(:, step-1));
            transitions.RSS_wb_diff(t_idx) = metrics.RSS_wb(step) - metrics.RSS_wb(step-1);
            transitions.SINR_wb_diff(t_idx) = metrics.SINR_wb(step) - metrics.SINR_wb(step-1);
            transitions.CQI_wb_diff(t_idx) = metrics.CQI_wb(step) - metrics.CQI_wb(step-1);
            transitions.path_loss_diff(t_idx) = metrics.path_loss(step) - metrics.path_loss(step-1);
        end
        
        % Progress indicator
        if mod(step, 90) == 0
            fprintf('.');
        end
    end
else
    % Fallback: step-by-step generation (no time correlation)
    fprintf('\n[Using step-by-step generation - no time correlation]\n');
    fprintf('Progress: ');
    
    for step = 1:n_snapshots
        % Get current position
        pos = walk_positions(:, step);
        
        % Create simulation for this single UE position
        s = qd_simulation_parameters;
        s.center_frequency = config.center_frequency;
        s.sample_density = 2;
        s.use_absolute_delays = 1;
        
        % Create layout with single UE
        l = qd_layout(s);
        l.no_tx = 1;
        l.tx_position = config.bs_position;
        l.tx_array = qd_arrayant('omni');
        
        l.no_rx = 1;
        l.rx_position = pos;
        l.rx_array = qd_arrayant('omni');
        
        l.set_scenario(config.scenario);
        
        % Generate channel
        c = l.get_channels;
        
        % Get channel coefficients
        h_t = squeeze(c.coeff(1,1,:,1));
        tau = squeeze(c.delay(1,:,1));
        
        % Ensure same dimensions
        n_taps = min(length(h_t), length(tau));
        h_t = h_t(1:n_taps);
        tau = tau(1:n_taps);
        
        % Remove zero-power taps
        valid_idx = abs(h_t) > 1e-12;
        h_t = h_t(valid_idx);
        tau = tau(valid_idx);
        
        % Convert to frequency domain
        H_freq = ExperimentUtils.convertToFrequency(h_t, tau, fvec);
        
        % Store CSI
        csi_data.H_freq{step} = H_freq;
        csi_data.H_mag(:, step) = abs(H_freq(:));
        csi_data.H_phase(:, step) = angle(H_freq(:));
        
        % Compute metrics
        H_sc = reshape(H_freq, [1, 1, config.n_subcarriers]);
        out = m.compute(H_sc);
        
        metrics.RSS_wb(step) = out.RSS_dBm_wb;
        metrics.SINR_wb(step) = out.SINR_dB_wb;
        metrics.CQI_wb(step) = out.CQI_wb;
        metrics.RSS_sc(:, step) = out.RSS_dBm_sc;
        metrics.SINR_sc(:, step) = out.SINR_dB_sc;
        
        % Channel statistics
        stats = ExperimentUtils.calculateChannelStats(h_t, tau * 1e9);
        metrics.path_loss(step) = stats.path_loss_dB;
        metrics.rms_delay_spread(step) = stats.rms_delay_spread_ns;
        metrics.mean_delay(step) = stats.mean_delay_ns;
        
        % Store metrics by grid point
        pt = walk_path(step);
        metrics_by_point(pt).RSS = [metrics_by_point(pt).RSS, metrics.RSS_wb(step)];
        metrics_by_point(pt).SINR = [metrics_by_point(pt).SINR, metrics.SINR_wb(step)];
        metrics_by_point(pt).CQI = [metrics_by_point(pt).CQI, metrics.CQI_wb(step)];
        
        % Compute transition differences (if not first step)
        if step > 1
            t_idx = step - 1;
            transitions.H_mag_diff(:, t_idx) = csi_data.H_mag(:, step) - csi_data.H_mag(:, step-1);
            transitions.H_phase_diff(:, t_idx) = wrapToPi(csi_data.H_phase(:, step) - csi_data.H_phase(:, step-1));
            transitions.RSS_wb_diff(t_idx) = metrics.RSS_wb(step) - metrics.RSS_wb(step-1);
            transitions.SINR_wb_diff(t_idx) = metrics.SINR_wb(step) - metrics.SINR_wb(step-1);
            transitions.CQI_wb_diff(t_idx) = metrics.CQI_wb(step) - metrics.CQI_wb(step-1);
            transitions.path_loss_diff(t_idx) = metrics.path_loss(step) - metrics.path_loss(step-1);
        end
        
        % Progress indicator
        if mod(step, 90) == 0
            fprintf('.');
        end
    end
end

elapsed_time = toc;
fprintf('\n✓ Simulation complete in %.1f seconds (%.2f min)\n', elapsed_time, elapsed_time/60);
if use_track
    fprintf('  (Used time-correlated track-based generation)\n');
else
    fprintf('  (Used step-by-step generation - channels are independent)\n');
end
fprintf('\n');

%% Compute and display overall standard deviations
fprintf('\n=== OVERALL TEMPORAL STATISTICS ===\n');
fprintf('RSS  - Mean: %.2f dBm, Std: %.4f dB\n', mean(metrics.RSS_wb), std(metrics.RSS_wb));
fprintf('SINR - Mean: %.2f dB,  Std: %.4f dB\n', mean(metrics.SINR_wb), std(metrics.SINR_wb));
fprintf('CQI  - Mean: %.2f,     Std: %.4f\n', mean(metrics.CQI_wb), std(metrics.CQI_wb));
fprintf('\n');

%% Create transition pair index (which static adjacent pair matches each transition)
% This maps each walk transition to its corresponding static adjacent pair
fprintf('Mapping transitions to static adjacent pairs...\n');

% Load static pair definitions (same as exp13a)
static_pairs = [];
for row = 1:config.grid_size
    for col = 1:config.grid_size
        idx = (row-1)*config.grid_size + col;
        % Right neighbor
        if col < config.grid_size
            static_pairs = [static_pairs; idx, idx+1];
        end
        % Up neighbor
        if row < config.grid_size
            static_pairs = [static_pairs; idx, idx+config.grid_size];
        end
    end
end

% Map each transition to a static pair (direction-agnostic)
transitions.static_pair_idx = zeros(config.n_steps, 1);
for t_idx = 1:config.n_steps
    from_pt = transitions.from_point(t_idx);
    to_pt = transitions.to_point(t_idx);
    
    % Find matching pair (either direction)
    for pair_idx = 1:size(static_pairs, 1)
        if (static_pairs(pair_idx, 1) == from_pt && static_pairs(pair_idx, 2) == to_pt) || ...
           (static_pairs(pair_idx, 1) == to_pt && static_pairs(pair_idx, 2) == from_pt)
            transitions.static_pair_idx(t_idx) = pair_idx;
            % Also store direction relative to static pair
            if static_pairs(pair_idx, 1) == from_pt
                transitions.direction(t_idx) = 1;  % Same direction
            else
                transitions.direction(t_idx) = -1; % Opposite direction
            end
            break;
        end
    end
end

% Count transitions per pair
pair_transition_counts = histcounts(transitions.static_pair_idx, 0.5:(size(static_pairs,1)+0.5));
fprintf('  Transitions per static pair:\n');
for pair_idx = 1:size(static_pairs, 1)
    fprintf('    Pair %d (%d->%d): %d transitions\n', pair_idx, ...
            static_pairs(pair_idx,1), static_pairs(pair_idx,2), pair_transition_counts(pair_idx));
end
fprintf('\n');

%% Create output directory
output_dir = ExperimentUtils.createResultsDir('exp13b');
fprintf('Output directory: %s\n', output_dir);

%% Save results
fprintf('Saving results...\n');

results = struct();
results.config = config;
results.walk_path = walk_path;
results.visit_counts = visit_counts;
results.csi_data = csi_data;
results.metrics = metrics;
results.transitions = transitions;
results.static_pairs = static_pairs;
results.pair_transition_counts = pair_transition_counts;
results.grid_positions = config.grid_positions;
results.ue_positions = walk_positions';  % Store as N x 3 for Python compatibility
results.elapsed_time = elapsed_time;
results.use_track = use_track;  % Whether time-correlated channels were used

save(fullfile(output_dir, 'random_walk_results.mat'), '-struct', 'results', '-v7.3');
fprintf('  ✓ Saved random_walk_results.mat\n');

%% Save per-grid-point CSVs
fprintf('Saving per-grid-point CSVs...\n');

for pt = 1:config.n_points
    % Get data for this point
    rss_vals = metrics_by_point(pt).RSS(:);
    sinr_vals = metrics_by_point(pt).SINR(:);
    cqi_vals = metrics_by_point(pt).CQI(:);
    
    n_visits = length(rss_vals);
    
    if n_visits > 0
        % Create table with visit index and metrics
        T = table((1:n_visits)', rss_vals, sinr_vals, cqi_vals, ...
                  'VariableNames', {'Visit', 'RSS_dBm', 'SINR_dB', 'CQI'});
        
        % Save CSV
        csv_filename = sprintf('grid_point_%d_metrics.csv', pt);
        writetable(T, fullfile(output_dir, csv_filename));
        fprintf('  ✓ Saved %s (%d visits)\n', csv_filename, n_visits);
    end
end

%% Print per-grid-point statistics
fprintf('\n=== PER-GRID-POINT STATISTICS ===\n');
fprintf('%-8s %8s %10s %10s %10s %10s %10s\n', 'Point', 'Visits', 'RSS_std', 'SINR_std', 'CQI_std', 'RSS_mean', 'SINR_mean');
fprintf('%s\n', repmat('-', 1, 76));

for pt = 1:config.n_points
    n_visits = length(metrics_by_point(pt).RSS);
    if n_visits > 1
        rss_std = std(metrics_by_point(pt).RSS);
        sinr_std = std(metrics_by_point(pt).SINR);
        cqi_std = std(metrics_by_point(pt).CQI);
        rss_mean = mean(metrics_by_point(pt).RSS);
        sinr_mean = mean(metrics_by_point(pt).SINR);
        fprintf('%-8d %8d %10.4f %10.4f %10.4f %10.2f %10.2f\n', ...
                pt, n_visits, rss_std, sinr_std, cqi_std, rss_mean, sinr_mean);
    else
        fprintf('%-8d %8d %10s %10s %10s %10s %10s\n', pt, n_visits, 'N/A', 'N/A', 'N/A', 'N/A', 'N/A');
    end
end
fprintf('\n');

%% Visualization 1: Random walk trajectory
fig1 = ExperimentUtils.createFigure('Random Walk - Trajectory', 'square');

% Create walk trajectory coordinates
walk_coords = config.grid_positions(walk_path, 1:2);

% Plot with color gradient for time
scatter(walk_coords(:,1), walk_coords(:,2), 20, 1:(config.n_steps+1), 'filled', 'MarkerFaceAlpha', 0.3);
colorbar;
hold on;

% Plot grid points
scatter(config.grid_positions(:,1), config.grid_positions(:,2), 200, 'k', 'LineWidth', 2);

% Label points with visit counts
for pt = 1:config.n_points
    text(config.grid_positions(pt,1), config.grid_positions(pt,2)+0.15, ...
         sprintf('%d\n(%d)', pt, visit_counts(pt)), 'HorizontalAlignment', 'center', 'FontSize', 9);
end

% Plot BS
plot(config.bs_position(1), config.bs_position(2), 'r^', 'MarkerSize', 15, ...
     'MarkerFaceColor', 'r');

xlabel('X (m)');
ylabel('Y (m)');
title(sprintf('Random Walk Path (%d steps)', config.n_steps));
colormap(jet);
c = colorbar;
c.Label.String = 'Step number';
axis equal;
grid on;

ExperimentUtils.saveFigures(fig1, 'random_walk_trajectory', output_dir);

%% Visualization 2: RSS over time
fig2 = ExperimentUtils.createFigure('Random Walk - RSS Evolution', 'wide');

subplot(2, 1, 1);
plot(1:(config.n_steps+1), metrics.RSS_wb, 'b-', 'LineWidth', 1);
xlabel('Step');
ylabel('RSS (dBm)');
title('RSS over Random Walk');
grid on;

subplot(2, 1, 2);
histogram(transitions.RSS_wb_diff, 50);
xlabel('RSS Difference (dB)');
ylabel('Count');
title('Distribution of RSS Differences (Consecutive Steps)');
grid on;

ExperimentUtils.saveFigures(fig2, 'random_walk_rss', output_dir);

%% Visualization 3: Compare with different pairs
fig3 = ExperimentUtils.createFigure('Random Walk - Differences by Pair', 'wide');

n_pairs = size(static_pairs, 1);
colors = lines(n_pairs);

subplot(1, 2, 1);
hold on;
for pair_idx = 1:n_pairs
    mask = transitions.static_pair_idx == pair_idx;
    if sum(mask) > 0
        histogram(transitions.RSS_wb_diff(mask), 20, 'FaceColor', colors(pair_idx,:), ...
                  'FaceAlpha', 0.5, 'DisplayName', sprintf('%d→%d', static_pairs(pair_idx,1), static_pairs(pair_idx,2)));
    end
end
hold off;
xlabel('RSS Difference (dB)');
ylabel('Count');
title('RSS Diff by Transition Pair');
legend('Location', 'best');
grid on;

subplot(1, 2, 2);
hold on;
for pair_idx = 1:n_pairs
    mask = transitions.static_pair_idx == pair_idx;
    if sum(mask) > 0
        histogram(transitions.path_loss_diff(mask), 20, 'FaceColor', colors(pair_idx,:), ...
                  'FaceAlpha', 0.5, 'DisplayName', sprintf('%d→%d', static_pairs(pair_idx,1), static_pairs(pair_idx,2)));
    end
end
hold off;
xlabel('Path Loss Difference (dB)');
ylabel('Count');
title('Path Loss Diff by Transition Pair');
legend('Location', 'best');
grid on;

ExperimentUtils.saveFigures(fig3, 'random_walk_by_pair', output_dir);

%% Generate report
fid = ExperimentUtils.createReportHeader(output_dir, 'EXP13B: Random Walk CSI Simulation');

fprintf(fid, '--- CONFIGURATION ---\n');
fprintf(fid, 'Grid size: %dx%d = %d points\n', config.grid_size, config.grid_size, config.n_points);
fprintf(fid, 'Spacing: %.1f m\n', config.spacing);
fprintf(fid, 'UE height: %.1f m\n', config.ue_height);
fprintf(fid, 'UE speed: %.1f m/s\n', config.ue_speed);
fprintf(fid, 'Time per step: %.1f seconds\n', config.step_duration);
fprintf(fid, 'Random walk steps: %d\n', config.n_steps);
fprintf(fid, 'Total walk duration: %.1f seconds (%.1f minutes)\n', ...
        config.n_steps * config.step_duration, config.n_steps * config.step_duration / 60);
fprintf(fid, 'Center frequency: %.2f GHz\n', config.center_frequency/1e9);
fprintf(fid, 'Bandwidth: %.1f MHz\n', config.bandwidth/1e6);
fprintf(fid, 'Subcarriers: %d\n', config.n_subcarriers);
fprintf(fid, 'Scenario: %s\n', config.scenario);
if use_track
    fprintf(fid, 'Channel generation: Track-based (time-correlated)\n\n');
else
    fprintf(fid, 'Channel generation: Step-by-step (independent snapshots)\n\n');
end

fprintf(fid, '--- VISIT STATISTICS ---\n');
for pt = 1:config.n_points
    fprintf(fid, 'Point %d: %d visits\n', pt, visit_counts(pt));
end
fprintf(fid, '\n');

fprintf(fid, '--- TRANSITION STATISTICS ---\n');
for pair_idx = 1:size(static_pairs, 1)
    fprintf(fid, 'Pair %d (%d<->%d): %d transitions\n', pair_idx, ...
            static_pairs(pair_idx,1), static_pairs(pair_idx,2), pair_transition_counts(pair_idx));
end
fprintf(fid, '\n');

fprintf(fid, '--- CSI STATISTICS ---\n');
fprintf(fid, 'RSS (dBm):\n');
fprintf(fid, '  Mean: %.2f dBm\n', mean(metrics.RSS_wb));
fprintf(fid, '  Std: %.2f dB\n', std(metrics.RSS_wb));
fprintf(fid, '  Range: [%.2f, %.2f] dBm\n', min(metrics.RSS_wb), max(metrics.RSS_wb));

fprintf(fid, '\nTransition Differences:\n');
fprintf(fid, '  RSS diff - Mean: %.4f dB, Std: %.4f dB\n', mean(transitions.RSS_wb_diff), std(transitions.RSS_wb_diff));
fprintf(fid, '  SINR diff - Mean: %.4f dB, Std: %.4f dB\n', mean(transitions.SINR_wb_diff), std(transitions.SINR_wb_diff));
fprintf(fid, '  Path loss diff - Mean: %.4f dB, Std: %.4f dB\n', mean(transitions.path_loss_diff), std(transitions.path_loss_diff));

fprintf(fid, '\n--- RUNTIME ---\n');
fprintf(fid, 'Elapsed time: %.1f seconds (%.2f min)\n\n', elapsed_time, elapsed_time/60);

files_generated = {'random_walk_results.mat', 'random_walk_trajectory.png', ...
                   'random_walk_rss.png', 'random_walk_by_pair.png', 'experiment_report.txt'};
ExperimentUtils.closeReport(fid, files_generated);

%% Summary
fprintf('\n========================================\n');
fprintf('SUMMARY\n');
fprintf('========================================\n');
fprintf('Random walk: %d steps on %dx%d grid\n', config.n_steps, config.grid_size, config.grid_size);
fprintf('UE speed: %.1f m/s, Time per step: %.1f s\n', config.ue_speed, config.step_duration);
fprintf('Total walk duration: %.1f seconds (%.1f minutes)\n', ...
        config.n_steps * config.step_duration, config.n_steps * config.step_duration / 60);
if use_track
    fprintf('Channel generation: Track-based (time-correlated)\n');
else
    fprintf('Channel generation: Step-by-step (independent snapshots)\n');
end
fprintf('Visit counts: min=%d, max=%d, mean=%.1f\n', min(visit_counts), max(visit_counts), mean(visit_counts));
fprintf('\nRSS Statistics:\n');
fprintf('  Mean: %.2f dBm, Std: %.2f dB\n', mean(metrics.RSS_wb), std(metrics.RSS_wb));
fprintf('  Transition diff std: %.4f dB\n', std(transitions.RSS_wb_diff));
fprintf('\nResults saved to: %s\n', output_dir);
fprintf('\nNext: Run analyze_static_vs_walk.py to compare distributions\n');
fprintf('========================================\n');
