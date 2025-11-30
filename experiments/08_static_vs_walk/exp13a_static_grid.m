%% EXPERIMENT 13A: Static Grid CSI Simulation
% Place 9 identical UEs on a 3x3 grid simultaneously
% Repeat 100 times to build distribution of CSI values and differences
%
% Grid configuration:
%   (0,2) -- (1,2) -- (2,2)
%     |        |        |
%   (0,1) -- (1,1) -- (2,1)
%     |        |        |
%   (0,0) -- (1,0) -- (2,0)
%
% Output: static_grid_results.mat

clear; clc; close all;

%% Setup
fprintf('========================================\n');
fprintf('EXP13A: Static Grid CSI Simulation\n');
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
config.spacing = 1.0;           % 1 meter between points
config.ue_height = 1.5;         % UE height in meters
config.grid_offset = [50, 50];  % Offset from BS to place grid center

% Simulation parameters
config.n_repetitions = 100;     % Number of independent simulations
config.center_frequency = 3e9;
config.bandwidth = 100e6;
config.n_subcarriers = 256;
config.scenario = '3GPP_38.901_UMa_LOS';  % LOS scenario

% Base station configuration
config.bs_position = [0; 0; 25];  % BS at origin, 25m height

% Generate grid positions
[X, Y] = meshgrid(0:config.spacing:(config.grid_size-1)*config.spacing, ...
                  0:config.spacing:(config.grid_size-1)*config.spacing);
config.grid_positions = [X(:) + config.grid_offset(1), ...
                         Y(:) + config.grid_offset(2), ...
                         ones(config.grid_size^2, 1) * config.ue_height];
config.n_points = config.grid_size^2;

% Define adjacent pairs (horizontal and vertical neighbors)
% Grid point indexing (1-9):
%   7 - 8 - 9
%   4 - 5 - 6
%   1 - 2 - 3
config.adjacent_pairs = [];
for row = 1:config.grid_size
    for col = 1:config.grid_size
        idx = (row-1)*config.grid_size + col;
        % Right neighbor
        if col < config.grid_size
            config.adjacent_pairs = [config.adjacent_pairs; idx, idx+1];
        end
        % Up neighbor
        if row < config.grid_size
            config.adjacent_pairs = [config.adjacent_pairs; idx, idx+config.grid_size];
        end
    end
end
config.n_adjacent_pairs = size(config.adjacent_pairs, 1);

fprintf('Configuration:\n');
fprintf('  Grid: %dx%d = %d points\n', config.grid_size, config.grid_size, config.n_points);
fprintf('  Spacing: %.1f m\n', config.spacing);
fprintf('  Repetitions: %d\n', config.n_repetitions);
fprintf('  Adjacent pairs: %d\n', config.n_adjacent_pairs);
fprintf('  Scenario: %s (LOS)\n', config.scenario);
fprintf('  Grid center offset from BS: [%.1f, %.1f] m\n', config.grid_offset);
fprintf('\n');

%% Initialize storage
fprintf('Initializing storage...\n');

% CSI storage per point
csi_data = struct();
csi_data.H_freq = cell(config.n_points, config.n_repetitions);  % Full frequency response
csi_data.H_mag = zeros(config.n_subcarriers, config.n_points, config.n_repetitions);
csi_data.H_phase = zeros(config.n_subcarriers, config.n_points, config.n_repetitions);

% Metrics storage
metrics = struct();
metrics.RSS_wb = zeros(config.n_points, config.n_repetitions);
metrics.SINR_wb = zeros(config.n_points, config.n_repetitions);
metrics.CQI_wb = zeros(config.n_points, config.n_repetitions);
metrics.RSS_sc = zeros(config.n_subcarriers, config.n_points, config.n_repetitions);
metrics.SINR_sc = zeros(config.n_subcarriers, config.n_points, config.n_repetitions);
metrics.path_loss = zeros(config.n_points, config.n_repetitions);
metrics.rms_delay_spread = zeros(config.n_points, config.n_repetitions);
metrics.mean_delay = zeros(config.n_points, config.n_repetitions);

% Differences storage (for adjacent pairs)
diffs = struct();
diffs.H_mag_diff = zeros(config.n_subcarriers, config.n_adjacent_pairs, config.n_repetitions);
diffs.H_phase_diff = zeros(config.n_subcarriers, config.n_adjacent_pairs, config.n_repetitions);
diffs.RSS_wb_diff = zeros(config.n_adjacent_pairs, config.n_repetitions);
diffs.SINR_wb_diff = zeros(config.n_adjacent_pairs, config.n_repetitions);
diffs.CQI_wb_diff = zeros(config.n_adjacent_pairs, config.n_repetitions);
diffs.path_loss_diff = zeros(config.n_adjacent_pairs, config.n_repetitions);
diffs.pair_from = config.adjacent_pairs(:,1);
diffs.pair_to = config.adjacent_pairs(:,2);

fprintf('  ✓ Storage initialized\n\n');

%% Setup CSI metrics calculator
m = CSIMetrics('SubcarrierSpacing', config.bandwidth/config.n_subcarriers, ...
               'TxPowerPerSC_dBm', 0, ...
               'NoiseFigure_dB', 7);

%% Main simulation loop
fprintf('Running static grid simulation...\n');
fprintf('Progress: ');
tic;

for rep = 1:config.n_repetitions
    % Create simulation parameters
    s = qd_simulation_parameters;
    s.center_frequency = config.center_frequency;
    s.sample_density = 2;
    s.use_absolute_delays = 1;
    
    % Create layout with 9 UEs
    l = qd_layout(s);
    l.no_tx = 1;
    l.tx_position = config.bs_position;
    l.tx_array = qd_arrayant('omni');
    
    % Add all 9 UEs with identical configuration
    l.no_rx = config.n_points;
    for pt = 1:config.n_points
        l.rx_position(:, pt) = config.grid_positions(pt, :)';
        l.rx_array(pt) = qd_arrayant('omni');  % Same antenna for all
    end
    
    % Set same scenario for all UEs
    l.set_scenario(config.scenario);
    
    % Generate channels for all UEs
    c = l.get_channels;
    
    % Frequency vector for conversion
    fvec = linspace(-config.bandwidth/2, config.bandwidth/2, config.n_subcarriers);
    
    % Process each UE
    for pt = 1:config.n_points
        % Get channel for this UE
        h_t = squeeze(c(pt).coeff(1,1,:,1));
        tau = squeeze(c(pt).delay(1,:,1));
        
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
        csi_data.H_freq{pt, rep} = H_freq;
        csi_data.H_mag(:, pt, rep) = abs(H_freq(:));
        csi_data.H_phase(:, pt, rep) = angle(H_freq(:));
        
        % Compute metrics
        H_sc = reshape(H_freq, [1, 1, config.n_subcarriers]);
        out = m.compute(H_sc);
        
        metrics.RSS_wb(pt, rep) = out.RSS_dBm_wb;
        metrics.SINR_wb(pt, rep) = out.SINR_dB_wb;
        metrics.CQI_wb(pt, rep) = out.CQI_wb;
        metrics.RSS_sc(:, pt, rep) = out.RSS_dBm_sc;
        metrics.SINR_sc(:, pt, rep) = out.SINR_dB_sc;
        
        % Channel statistics
        stats = ExperimentUtils.calculateChannelStats(h_t, tau * 1e9);
        metrics.path_loss(pt, rep) = stats.path_loss_dB;
        metrics.rms_delay_spread(pt, rep) = stats.rms_delay_spread_ns;
        metrics.mean_delay(pt, rep) = stats.mean_delay_ns;
    end
    
    % Compute differences for adjacent pairs
    for pair_idx = 1:config.n_adjacent_pairs
        pt1 = config.adjacent_pairs(pair_idx, 1);
        pt2 = config.adjacent_pairs(pair_idx, 2);
        
        diffs.H_mag_diff(:, pair_idx, rep) = csi_data.H_mag(:, pt2, rep) - csi_data.H_mag(:, pt1, rep);
        diffs.H_phase_diff(:, pair_idx, rep) = wrapToPi(csi_data.H_phase(:, pt2, rep) - csi_data.H_phase(:, pt1, rep));
        diffs.RSS_wb_diff(pair_idx, rep) = metrics.RSS_wb(pt2, rep) - metrics.RSS_wb(pt1, rep);
        diffs.SINR_wb_diff(pair_idx, rep) = metrics.SINR_wb(pt2, rep) - metrics.SINR_wb(pt1, rep);
        diffs.CQI_wb_diff(pair_idx, rep) = metrics.CQI_wb(pt2, rep) - metrics.CQI_wb(pt1, rep);
        diffs.path_loss_diff(pair_idx, rep) = metrics.path_loss(pt2, rep) - metrics.path_loss(pt1, rep);
    end
    
    % Progress indicator
    if mod(rep, 10) == 0
        fprintf('.');
    end
end

elapsed_time = toc;
fprintf('\n✓ Simulation complete in %.1f seconds\n\n', elapsed_time);

%% Create output directory
output_dir = ExperimentUtils.createResultsDir('exp13a');
fprintf('Output directory: %s\n', output_dir);

%% Save results
fprintf('Saving results...\n');

results = struct();
results.config = config;
results.csi_data = csi_data;
results.metrics = metrics;
results.diffs = diffs;
results.grid_positions = config.grid_positions;
results.adjacent_pairs = config.adjacent_pairs;
results.elapsed_time = elapsed_time;

save(fullfile(output_dir, 'static_grid_results.mat'), '-struct', 'results', '-v7.3');
fprintf('  ✓ Saved static_grid_results.mat\n');

%% Quick visualization
fig1 = ExperimentUtils.createFigure('Static Grid - RSS Distribution', 'wide');

subplot(1, 2, 1);
for pt = 1:config.n_points
    histogram(metrics.RSS_wb(pt, :), 20, 'FaceAlpha', 0.5);
    hold on;
end
xlabel('RSS (dBm)');
ylabel('Count');
title('RSS Distribution per Grid Point');
legend(arrayfun(@(x) sprintf('Point %d', x), 1:config.n_points, 'UniformOutput', false), ...
       'Location', 'best');
grid on;

subplot(1, 2, 2);
histogram(diffs.RSS_wb_diff(:), 30);
xlabel('RSS Difference (dB)');
ylabel('Count');
title('RSS Difference Distribution (Adjacent Pairs)');
grid on;

ExperimentUtils.saveFigures(fig1, 'static_grid_rss', output_dir);

%% Visualization 2: Grid layout
fig2 = ExperimentUtils.createFigure('Static Grid - Layout', 'square');

% Plot grid points
scatter(config.grid_positions(:,1), config.grid_positions(:,2), 100, ...
        mean(metrics.RSS_wb, 2), 'filled');
colorbar;
hold on;

% Plot BS
plot(config.bs_position(1), config.bs_position(2), 'r^', 'MarkerSize', 15, ...
     'MarkerFaceColor', 'r');

% Label points
for pt = 1:config.n_points
    text(config.grid_positions(pt,1)+0.1, config.grid_positions(pt,2)+0.1, ...
         sprintf('%d', pt), 'FontSize', 10);
end

% Draw connections for adjacent pairs
for pair_idx = 1:config.n_adjacent_pairs
    pt1 = config.adjacent_pairs(pair_idx, 1);
    pt2 = config.adjacent_pairs(pair_idx, 2);
    plot([config.grid_positions(pt1,1), config.grid_positions(pt2,1)], ...
         [config.grid_positions(pt1,2), config.grid_positions(pt2,2)], 'k--', 'LineWidth', 1);
end

xlabel('X (m)');
ylabel('Y (m)');
title('Grid Layout with Mean RSS (dBm)');
axis equal;
grid on;

ExperimentUtils.saveFigures(fig2, 'static_grid_layout', output_dir);

%% Generate report
fid = ExperimentUtils.createReportHeader(output_dir, 'EXP13A: Static Grid CSI Simulation');

fprintf(fid, '--- CONFIGURATION ---\n');
fprintf(fid, 'Grid size: %dx%d = %d points\n', config.grid_size, config.grid_size, config.n_points);
fprintf(fid, 'Spacing: %.1f m\n', config.spacing);
fprintf(fid, 'UE height: %.1f m\n', config.ue_height);
fprintf(fid, 'Grid center offset: [%.1f, %.1f] m\n', config.grid_offset);
fprintf(fid, 'Repetitions: %d\n', config.n_repetitions);
fprintf(fid, 'Adjacent pairs: %d\n', config.n_adjacent_pairs);
fprintf(fid, 'Center frequency: %.2f GHz\n', config.center_frequency/1e9);
fprintf(fid, 'Bandwidth: %.1f MHz\n', config.bandwidth/1e6);
fprintf(fid, 'Subcarriers: %d\n', config.n_subcarriers);
fprintf(fid, 'Scenario: %s\n\n', config.scenario);

fprintf(fid, '--- STATISTICS ---\n');
fprintf(fid, 'RSS (dBm):\n');
fprintf(fid, '  Mean: %.2f dBm\n', mean(metrics.RSS_wb(:)));
fprintf(fid, '  Std: %.2f dB\n', std(metrics.RSS_wb(:)));
fprintf(fid, '  Range: [%.2f, %.2f] dBm\n', min(metrics.RSS_wb(:)), max(metrics.RSS_wb(:)));

fprintf(fid, '\nSINR (dB):\n');
fprintf(fid, '  Mean: %.2f dB\n', mean(metrics.SINR_wb(:)));
fprintf(fid, '  Std: %.2f dB\n', std(metrics.SINR_wb(:)));

fprintf(fid, '\nAdjacent Pair Differences:\n');
fprintf(fid, '  RSS diff - Mean: %.4f dB, Std: %.4f dB\n', mean(diffs.RSS_wb_diff(:)), std(diffs.RSS_wb_diff(:)));
fprintf(fid, '  SINR diff - Mean: %.4f dB, Std: %.4f dB\n', mean(diffs.SINR_wb_diff(:)), std(diffs.SINR_wb_diff(:)));
fprintf(fid, '  Path loss diff - Mean: %.4f dB, Std: %.4f dB\n', mean(diffs.path_loss_diff(:)), std(diffs.path_loss_diff(:)));

fprintf(fid, '\n--- RUNTIME ---\n');
fprintf(fid, 'Elapsed time: %.1f seconds\n\n', elapsed_time);

files_generated = {'static_grid_results.mat', 'static_grid_rss.png', ...
                   'static_grid_layout.png', 'experiment_report.txt'};
ExperimentUtils.closeReport(fid, files_generated);

%% Summary
fprintf('\n========================================\n');
fprintf('SUMMARY\n');
fprintf('========================================\n');
fprintf('Grid: %dx%d = %d points, %d repetitions\n', config.grid_size, config.grid_size, ...
        config.n_points, config.n_repetitions);
fprintf('Total samples: %d\n', config.n_points * config.n_repetitions);
fprintf('Adjacent pair differences: %d\n', config.n_adjacent_pairs * config.n_repetitions);
fprintf('\nRSS Statistics:\n');
fprintf('  Mean: %.2f dBm, Std: %.2f dB\n', mean(metrics.RSS_wb(:)), std(metrics.RSS_wb(:)));
fprintf('  Adjacent diff std: %.4f dB\n', std(diffs.RSS_wb_diff(:)));
fprintf('\nResults saved to: %s\n', output_dir);
fprintf('\nNext: Run exp13b_random_walk.m\n');
fprintf('========================================\n');
