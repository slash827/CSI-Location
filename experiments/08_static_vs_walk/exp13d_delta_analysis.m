%% EXPERIMENT 13D: Random Walk Delta Analysis
% Based on Exp 13B, but focused on analyzing the statistics of DELTAS
% (differences) in metrics between adjacent grid points.
%
% Goal: Estimate distribution of differences for each directed edge.
% Settings: 3000 steps for better statistics.
%
% Grid configuration:
%   7 - 8 - 9
%   4 - 5 - 6
%   1 - 2 - 3

clear; clc; close all;

%% Setup
fprintf('========================================\n');
fprintf('EXP13D: Random Walk Delta Analysis\n');
fprintf('========================================\n\n');

% Add utils to path
script_dir = fileparts(mfilename('fullpath'));
project_root = fileparts(fileparts(script_dir));
utils_path = fullfile(project_root, 'utils');
addpath(utils_path);

%% Configuration
config = struct();

% Grid parameters
config.grid_size = 3;           % 3x3 grid
config.spacing = 1.5;           % 1.5 meters between points
config.ue_height = 1.5;         % UE height in meters
config.grid_offset = [10, 0];   % Closer to BS
config.position_jitter = 0.1;   % 10 cm random variation in position

% Random walk parameters
config.n_steps = 3000;          % INCREASED to 3000 for statistics
config.ue_speed = 1.5;          % UE walking speed in m/s
config.step_duration = config.spacing / config.ue_speed;

% Simulation parameters
config.center_frequency = 3e9;
config.bandwidth = 100e6;
config.n_subcarriers = 256;
config.scenario = '3GPP_38.901_UMa_NLOS';

% Base station configuration
config.bs_position = [0; 0; 25];

% Generate grid positions
[X, Y] = meshgrid(0:config.spacing:(config.grid_size-1)*config.spacing, ...
                  0:config.spacing:(config.grid_size-1)*config.spacing);
config.grid_positions = [X(:) + config.grid_offset(1), ...
                         Y(:) + config.grid_offset(2), ...
                         ones(config.grid_size^2, 1) * config.ue_height];
config.n_points = config.grid_size^2;

% Build adjacency map
config.neighbors = cell(config.n_points, 1);
for row = 1:config.grid_size
    for col = 1:config.grid_size
        idx = (row-1)*config.grid_size + col;
        neighbors = [];
        if col < config.grid_size, neighbors = [neighbors, idx+1]; end % Right
        if col > 1, neighbors = [neighbors, idx-1]; end % Left
        if row < config.grid_size, neighbors = [neighbors, idx+config.grid_size]; end % Up
        if row > 1, neighbors = [neighbors, idx-config.grid_size]; end % Down
        config.neighbors{idx} = neighbors;
    end
end

fprintf('Configuration:\n');
fprintf('  Grid: %dx%d = %d points\n', config.grid_size, config.grid_size, config.n_points);
fprintf('  Steps: %d\n', config.n_steps);
fprintf('  Scenario: %s\n\n', config.scenario);

%% Generate random walk path
fprintf('Generating random walk path...\n');
rng('shuffle');
walk_path = zeros(config.n_steps + 1, 1);
walk_path(1) = 5; % Start at center

for step = 1:config.n_steps
    current = walk_path(step);
    neighbors = config.neighbors{current};
    next = neighbors(randi(length(neighbors)));
    walk_path(step + 1) = next;
end

% Visit counts
visit_counts = histcounts(walk_path, 1:(config.n_points+1));
fprintf('  Min visits per point: %d\n', min(visit_counts(1:config.n_points)));
fprintf('  Max visits per point: %d\n\n', max(visit_counts(1:config.n_points)));

%% Build continuous trajectory
fprintf('Building QuaDRiGa-compatible track...\n');
n_snapshots = config.n_steps + 1;
walk_grid_positions = zeros(3, n_snapshots);
for step = 1:n_snapshots
    pt = walk_path(step);
    walk_grid_positions(:, step) = config.grid_positions(pt, :)';
end

% Add position jitter to simulate realistic walking (never hitting exact same point)
jitter = (rand(3, n_snapshots) - 0.5) * 2 * config.position_jitter;
jitter(3, :) = 0; % Keep height constant
walk_grid_positions = walk_grid_positions + jitter;

movements = diff(walk_grid_positions, 1, 2);
step_distances = sqrt(sum(movements.^2, 1));
total_distance = sum(step_distances);
fprintf('  Total path length: %.1f m\n\n', total_distance);

%% Main simulation (QuaDRiGa)
fprintf('Running simulation...\n');
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
metrics.path_loss = zeros(n_snapshots, 1);

fvec = linspace(-config.bandwidth/2, config.bandwidth/2, config.n_subcarriers);
m = CSIMetrics('SubcarrierSpacing', config.bandwidth/config.n_subcarriers, ...
               'TxPowerPerSC_dBm', 0, 'NoiseFigure_dB', 7);

try
    s = qd_simulation_parameters;
    s.center_frequency = config.center_frequency;
    s.use_absolute_delays = 1;
    s.show_progress_bars = 0;
    s.samples_per_meter = n_snapshots / total_distance;
    
    l = qd_layout(s);
    l.no_tx = 1;
    l.tx_position = config.bs_position;
    l.tx_array = qd_arrayant('omni');
    l.rx_array = qd_arrayant('omni');
    
    trk = qd_track([]);
    trk.name = 'RandomWalk';
    trk.initial_position = walk_grid_positions(:, 1);
    trk.positions = walk_grid_positions;
    trk.no_snapshots = size(walk_grid_positions, 2);
    trk.scenario = {config.scenario};
    trk.set_speed(config.ue_speed);
    l.track(1,1) = trk;
    
    fprintf('  Generating channels...\n');
    c = l.get_channels;
    
    coeff_dims = size(c.coeff);
    n_generated = coeff_dims(4);
    
    if n_generated < n_snapshots * 0.9
        error('Generated too few snapshots: %d vs %d', n_generated, n_snapshots);
    end
    
    sample_indices = round(linspace(1, n_generated, n_snapshots));
    
    for step_idx = 1:n_snapshots
        snap_idx = sample_indices(step_idx);
        
        coeff = c.coeff(:,:,:,snap_idx);
        delays = c.delay(:,:,:,snap_idx);
        
        h_paths = squeeze(coeff);
        tau_paths = squeeze(delays);
        H_freq = (h_paths(:).' * exp(-1j * 2 * pi * tau_paths(:) * fvec(:).')).';
        
        csi_data.H_freq{step_idx} = H_freq;
        csi_data.H_mag(:, step_idx) = abs(H_freq);
        csi_data.H_phase(:, step_idx) = angle(H_freq);
        
        H_sc = reshape(H_freq, [1, 1, config.n_subcarriers]);
        out = m.compute(H_sc);
        
        metrics.RSS_wb(step_idx) = out.RSS_dBm_wb;
        metrics.SINR_wb(step_idx) = out.SINR_dB_wb;
        metrics.CQI_wb(step_idx) = out.CQI_wb;
        
        stats = ExperimentUtils.calculateChannelStats(squeeze(coeff), squeeze(delays) * 1e9);
        metrics.path_loss(step_idx) = stats.path_loss_dB;
        
        if mod(step_idx, 500) == 0
            fprintf('    Processed %d/%d snapshots...\n', step_idx, n_snapshots);
        end
    end
    
catch ME
    error('Simulation failed: %s', ME.message);
end

elapsed_time = toc;
fprintf('  Done in %.1f seconds.\n\n', elapsed_time);

%% Analyze Directed Transitions (Deltas)
fprintf('Analyzing directed transition deltas...\n');

% Define all possible directed edges based on neighbors
directed_edges = [];
for u = 1:config.n_points
    neighbors = config.neighbors{u};
    for v = neighbors
        directed_edges = [directed_edges; u, v];
    end
end

delta_stats = struct();
all_deltas_rss = []; 

fprintf('\nTransition Delta Statistics (Mean +/- Std):\n');
fprintf('%-10s | %-10s | %-20s | %-20s\n', 'From->To', 'Count', 'Delta RSS (dB)', 'Delta SINR (dB)');
fprintf('%s\n', repmat('-', 1, 75));

% Store distributions for overlap analysis
distributions = struct();

for i = 1:size(directed_edges, 1)
    u = directed_edges(i, 1);
    v = directed_edges(i, 2);
    
    % Find indices where transition u -> v occurs
    idx = find(walk_path(1:end-1) == u & walk_path(2:end) == v);
    count = length(idx);
    
    if count > 0
        % Calculate deltas
        d_rss = metrics.RSS_wb(idx+1) - metrics.RSS_wb(idx);
        d_sinr = metrics.SINR_wb(idx+1) - metrics.SINR_wb(idx);
        
        % Store stats
        key = sprintf('edge_%d_%d', u, v);
        delta_stats.(key).count = count;
        delta_stats.(key).rss_mean = mean(d_rss);
        delta_stats.(key).rss_std = std(d_rss);
        delta_stats.(key).rss_min = min(d_rss);
        delta_stats.(key).rss_max = max(d_rss);
        delta_stats.(key).sinr_mean = mean(d_sinr);
        delta_stats.(key).sinr_std = std(d_sinr);
        delta_stats.(key).raw_rss_deltas = d_rss;
        
        distributions.(key) = d_rss;
        
        fprintf('%2d -> %2d   | %4d       | %6.2f +/- %5.2f    | %6.2f +/- %5.2f\n', ...
            u, v, count, mean(d_rss), std(d_rss), mean(d_sinr), std(d_sinr));
    end
end

%% Check for Overlap / Distinctiveness
fprintf('\nChecking distinctiveness of distributions (simple overlap check)...\n');
% We can check if the 1-std intervals overlap for inverse pairs
fprintf('%-10s | %-25s | %-25s | %-10s\n', 'Pair', 'Forward (Mean+/-Std)', 'Reverse (Mean+/-Std)', 'Overlap?');
fprintf('%s\n', repmat('-', 1, 80));

processed_pairs = [];
for i = 1:size(directed_edges, 1)
    u = directed_edges(i, 1);
    v = directed_edges(i, 2);
    
    % Avoid processing same pair twice (u,v and v,u)
    pair_id = sort([u, v]);
    pair_str = sprintf('%d-%d', pair_id(1), pair_id(2));
    
    if ismember(pair_str, processed_pairs)
        continue;
    end
    processed_pairs = [processed_pairs; string(pair_str)];
    
    key_fwd = sprintf('edge_%d_%d', u, v);
    key_rev = sprintf('edge_%d_%d', v, u);
    
    if isfield(delta_stats, key_fwd) && isfield(delta_stats, key_rev)
        m1 = delta_stats.(key_fwd).rss_mean;
        s1 = delta_stats.(key_fwd).rss_std;
        m2 = delta_stats.(key_rev).rss_mean;
        s2 = delta_stats.(key_rev).rss_std;
        
        % Check overlap of [mean-std, mean+std]
        range1 = [m1-s1, m1+s1];
        range2 = [m2-s2, m2+s2];
        
        overlap = (range1(1) <= range2(2)) && (range2(1) <= range1(2));
        
        fprintf('%2d <-> %2d  | %6.2f +/- %5.2f       | %6.2f +/- %5.2f       | %s\n', ...
            u, v, m1, s1, m2, s2, ternary(overlap, 'YES', 'NO'));
    end
end

%% Save results
output_dir = fullfile(project_root, 'results', sprintf('exp13d_%s', datestr(now, 'yyyy-mm-dd_HH-MM-SS')));
if ~exist(output_dir, 'dir'), mkdir(output_dir); end

save(fullfile(output_dir, 'delta_analysis_results.mat'), ...
     'config', 'walk_path', 'metrics', 'delta_stats', 'distributions');
fprintf('\nSaved results to %s\n', output_dir);

function result = ternary(condition, true_val, false_val)
    if condition, result = true_val; else, result = false_val; end
end
