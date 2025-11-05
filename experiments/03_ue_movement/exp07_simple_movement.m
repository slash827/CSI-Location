%% EXPERIMENT 07: Simple UE Movement
% Learn: Track CSI as UE moves along a linear path
% Time: 20 minutes
%
% What you'll see:
% - How CSI changes with UE position
% - RSS decrease as UE moves away from BS
% - CQI degradation with distance
% - Spatial correlation in CSI
%
% Expected output:
% - Trajectory visualization
% - CSI evolution over time/position
% - RSS, SINR, CQI vs position plots

clear; clc; close all;

% Add utils to path
utils_path = fullfile(fileparts(fileparts(mfilename('fullpath'))), '..', 'utils');
addpath(utils_path);

fprintf('========================================\n');
fprintf('EXPERIMENT 07: Simple UE Movement\n');
fprintf('========================================\n\n');

%% Setup simulation parameters
s = qd_simulation_parameters;
s.center_frequency = 3.5e9;
s.sample_density = 2;
s.use_absolute_delays = 1;

%% Setup layout with moving UE
l = qd_layout(s);

% Base station (fixed)
l.tx_position = [0; 0; 25];  % 25m height
l.tx_array = qd_arrayant('omni');

% UE trajectory: Linear path moving away from BS
start_pos = [20; 0; 1.5];    % Starting position (20m from BS)
end_pos = [150; 0; 1.5];     % Ending position (150m from BS)
n_snapshots = 50;            % Number of position samples

% Create trajectory manually
x_traj = linspace(start_pos(1), end_pos(1), n_snapshots);
y_traj = linspace(start_pos(2), end_pos(2), n_snapshots);
z_traj = start_pos(3) * ones(1, n_snapshots);
trajectory = [x_traj; y_traj; z_traj];

% Set track for moving UE - use linear and set number of snapshots
track = qd_track('linear', end_pos(1) - start_pos(1), 0);
track.scenario = '3GPP_38.901_UMa_LOS';
track.initial_position = start_pos;
track.no_snapshots = n_snapshots;  % Set number of snapshots explicitly

l.track(1,1) = track;
l.rx_array = qd_arrayant('omni');

fprintf('Configuration:\n');
fprintf('  Scenario: %s\n', track.scenario{1});
fprintf('  Start position: [%.1f, %.1f, %.1f] m\n', start_pos);
fprintf('  End position: [%.1f, %.1f, %.1f] m\n', end_pos);
fprintf('  Total distance: %.1f m\n', end_pos(1) - start_pos(1));
fprintf('  Number of snapshots: %d\n', n_snapshots);
fprintf('  Distance per snapshot: %.2f m\n', (end_pos(1) - start_pos(1)) / (n_snapshots - 1));
fprintf('\n');

%% Generate channels
fprintf('Generating channels...\n');
tic;
c = l.get_channels;
gen_time = toc;
fprintf('  Generation time: %.2f seconds\n', gen_time);
fprintf('  Channel size: [%d Rx, %d Tx, %d Taps, %d Snapshots]\n', size(c.coeff));
fprintf('\n');

%% Extract CSI at each snapshot
fprintf('Processing snapshots...\n');

% Frequency domain parameters
BW = 100e6;
Nsc = 256;
fvec = linspace(-BW/2, BW/2, Nsc);

% Storage for metrics
distances = zeros(1, n_snapshots);
RSS_wb = zeros(1, n_snapshots);
SINR_wb = zeros(1, n_snapshots);
CQI_wb = zeros(1, n_snapshots);
path_loss = zeros(1, n_snapshots);
rms_delay = zeros(1, n_snapshots);

% Initialize CSI metrics calculator
m = CSIMetrics('SubcarrierSpacing', BW/Nsc, ...
               'TxPowerPerSC_dBm', 0, ...
               'NoiseFigure_dB', 7);

% Process each snapshot
for snap = 1:n_snapshots
    % Get time-domain channel for this snapshot
    h_t = squeeze(c.coeff(1,1,:,snap));
    tau = squeeze(c.delay(1,:,snap));
    
    % Ensure same size and remove zero-power taps
    n_taps = min(length(h_t), length(tau));
    h_t = h_t(1:n_taps);
    tau = tau(1:n_taps);
    
    valid_idx = abs(h_t) > 1e-10;
    h_t = h_t(valid_idx);
    tau = tau(valid_idx);
    
    % Calculate distance
    ue_pos = trajectory(:, snap);
    distances(snap) = norm(ue_pos - l.tx_position);
    
    % Calculate channel statistics
    stats = ExperimentUtils.calculateChannelStats(h_t, tau);
    path_loss(snap) = stats.path_loss_dB;
    rms_delay(snap) = stats.rms_delay_spread_ns;
    
    % Convert to frequency domain
    H_sc = zeros(1, 1, Nsc);
    for k = 1:Nsc
        H_sc(1,1,k) = sum(h_t .* exp(-1j * 2*pi * fvec(k) .* tau));
    end
    
    % Compute CSI metrics
    out = m.compute(H_sc);
    RSS_wb(snap) = out.RSS_dBm_wb;
    SINR_wb(snap) = out.SINR_dB_wb;
    CQI_wb(snap) = out.CQI_wb;
    
    if mod(snap, 10) == 0
        fprintf('  Processed %d/%d snapshots...\n', snap, n_snapshots);
    end
end
fprintf('Done!\n\n');

%% Create results directory
results_dir = ExperimentUtils.createResultsDir('exp07');

%% Visualization 1: Trajectory and Setup
fig1 = ExperimentUtils.createFigure('Experiment 07 - Trajectory', 'square');

% Plot trajectory in 2D
plot(trajectory(1,:), trajectory(2,:), 'b-', 'LineWidth', 2);
hold on;
plot(l.tx_position(1), l.tx_position(2), 'r^', 'MarkerSize', 15, 'MarkerFaceColor', 'r');
plot(trajectory(1,1), trajectory(2,1), 'go', 'MarkerSize', 10, 'MarkerFaceColor', 'g');
plot(trajectory(1,end), trajectory(2,end), 'ro', 'MarkerSize', 10, 'MarkerFaceColor', 'r');
hold off;

xlabel('X Position (m)');
ylabel('Y Position (m)');
title('UE Trajectory (Linear Movement)');
legend('Trajectory', 'Base Station', 'Start', 'End', 'Location', 'best');
grid on;
axis equal;

figure(fig1);
ExperimentUtils.saveFigures(gcf, 'trajectory', results_dir);

%% Visualization 2: CSI Metrics vs Distance
fig2 = ExperimentUtils.createFigure('Experiment 07 - Metrics vs Distance', 'wide');

subplot(2, 2, 1);
plot(distances, RSS_wb, 'o-', 'LineWidth', 2, 'MarkerSize', 6);
xlabel('Distance (m)');
ylabel('RSS (dBm)');
title('Received Signal Strength vs Distance');
grid on;

subplot(2, 2, 2);
plot(distances, SINR_wb, 'o-', 'LineWidth', 2, 'MarkerSize', 6, 'Color', [0.8 0.4 0]);
xlabel('Distance (m)');
ylabel('SINR (dB)');
title('Signal-to-Noise Ratio vs Distance');
grid on;

subplot(2, 2, 3);
stairs(distances, CQI_wb, 'o-', 'LineWidth', 2, 'MarkerSize', 6, 'Color', [0.2 0.6 0.2]);
xlabel('Distance (m)');
ylabel('CQI (0-15)');
title('Channel Quality Indicator vs Distance');
grid on;
ylim([-0.5, 15.5]);

subplot(2, 2, 4);
plot(distances, path_loss, 'o-', 'LineWidth', 2, 'MarkerSize', 6, 'Color', [0.6 0.2 0.6]);
xlabel('Distance (m)');
ylabel('Path Loss (dB)');
title('Path Loss vs Distance');
grid on;

figure(fig2);
ExperimentUtils.saveFigures(gcf, 'metrics_vs_distance', results_dir);

%% Visualization 3: Time Series View
fig3 = ExperimentUtils.createFigure('Experiment 07 - Time Evolution', 'wide');

subplot(3, 1, 1);
plot(1:n_snapshots, RSS_wb, 'o-', 'LineWidth', 2);
xlabel('Snapshot Index');
ylabel('RSS (dBm)');
title('RSS Evolution Over Time');
grid on;

subplot(3, 1, 2);
plot(1:n_snapshots, SINR_wb, 'o-', 'LineWidth', 2, 'Color', [0.8 0.4 0]);
xlabel('Snapshot Index');
ylabel('SINR (dB)');
title('SINR Evolution Over Time');
grid on;

subplot(3, 1, 3);
stairs(1:n_snapshots, CQI_wb, 'o-', 'LineWidth', 2, 'Color', [0.2 0.6 0.2]);
xlabel('Snapshot Index');
ylabel('CQI (0-15)');
title('CQI Evolution Over Time');
grid on;
ylim([-0.5, 15.5]);

figure(fig3);
ExperimentUtils.saveFigures(gcf, 'time_evolution', results_dir);

%% Visualization 4: Correlation Analysis
fig4 = ExperimentUtils.createFigure('Experiment 07 - Spatial Correlation', 'wide');

% Calculate correlation in RSS
subplot(1, 2, 1);
% Normalize RSS for correlation
RSS_norm = (RSS_wb - mean(RSS_wb)) / std(RSS_wb);
max_lag = 20;
[acf, lags] = xcorr(RSS_norm, max_lag, 'coeff');
lag_distances = lags * (end_pos(1) - start_pos(1)) / (n_snapshots - 1);

plot(lag_distances, acf, 'o-', 'LineWidth', 2);
xlabel('Spatial Lag (m)');
ylabel('Autocorrelation');
title('RSS Spatial Autocorrelation');
grid on;

% Calculate correlation distance (where ACF drops to 0.5)
corr_dist_idx = find(acf(max_lag+1:end) < 0.5, 1);
if ~isempty(corr_dist_idx)
    corr_dist = lag_distances(max_lag + corr_dist_idx);
    hold on;
    plot([0 corr_dist], [0.5 0.5], 'r--', 'LineWidth', 1.5);
    plot(corr_dist, 0.5, 'ro', 'MarkerSize', 10, 'MarkerFaceColor', 'r');
    text(corr_dist, 0.6, sprintf('  %.1fm', corr_dist), 'FontSize', 10);
    hold off;
end

% Moving average to show trend
subplot(1, 2, 2);
window_size = 5;
RSS_smooth = movmean(RSS_wb, window_size);
SINR_smooth = movmean(SINR_wb, window_size);

yyaxis left;
plot(distances, RSS_wb, 'o', 'MarkerSize', 4, 'Color', [0.7 0.7 1]);
hold on;
plot(distances, RSS_smooth, '-', 'LineWidth', 2.5, 'Color', [0 0 1]);
ylabel('RSS (dBm)');

yyaxis right;
plot(distances, SINR_wb, 's', 'MarkerSize', 4, 'Color', [1 0.7 0.7]);
plot(distances, SINR_smooth, '-', 'LineWidth', 2.5, 'Color', [1 0 0]);
ylabel('SINR (dB)');
hold off;

xlabel('Distance (m)');
title('Smoothed Metrics (Moving Average)');
legend('RSS (raw)', 'RSS (smooth)', 'SINR (raw)', 'SINR (smooth)', 'Location', 'best');
grid on;

figure(fig4);
ExperimentUtils.saveFigures(gcf, 'spatial_correlation', results_dir);

%% Analysis and Report
fid = ExperimentUtils.createReportHeader(results_dir, 'EXPERIMENT 07: Simple UE Movement');

fprintf(fid, 'CONFIGURATION\n');
fprintf(fid, '=============\n\n');

% Create params struct for report
report_params = struct();
report_params.center_frequency = s.center_frequency;
report_params.sample_density = s.sample_density;
report_params.bandwidth = BW;
report_params.num_subcarriers = Nsc;
report_params.scenario = track.scenario{1};
report_params.tx_position = l.tx_position;
ExperimentUtils.writeSimParams(fid, report_params);

fprintf(fid, '\nTrajectory:\n');
fprintf(fid, '  Type: Linear\n');
fprintf(fid, '  Start: [%.1f, %.1f, %.1f] m\n', start_pos);
fprintf(fid, '  End: [%.1f, %.1f, %.1f] m\n', end_pos);
fprintf(fid, '  Total distance: %.1f m\n', end_pos(1) - start_pos(1));
fprintf(fid, '  Snapshots: %d\n', n_snapshots);
fprintf(fid, '  Step size: %.2f m\n\n', (end_pos(1) - start_pos(1)) / (n_snapshots - 1));

fprintf(fid, 'RESULTS\n');
fprintf(fid, '=======\n\n');

fprintf(fid, 'RSS Statistics:\n');
fprintf(fid, '  Min: %.2f dBm (at %.1f m)\n', min(RSS_wb), distances(find(RSS_wb == min(RSS_wb), 1)));
fprintf(fid, '  Max: %.2f dBm (at %.1f m)\n', max(RSS_wb), distances(find(RSS_wb == max(RSS_wb), 1)));
fprintf(fid, '  Mean: %.2f dBm\n', mean(RSS_wb));
fprintf(fid, '  Range: %.2f dB\n\n', max(RSS_wb) - min(RSS_wb));

fprintf(fid, 'SINR Statistics:\n');
fprintf(fid, '  Min: %.2f dB (at %.1f m)\n', min(SINR_wb), distances(find(SINR_wb == min(SINR_wb), 1)));
fprintf(fid, '  Max: %.2f dB (at %.1f m)\n', max(SINR_wb), distances(find(SINR_wb == max(SINR_wb), 1)));
fprintf(fid, '  Mean: %.2f dB\n', mean(SINR_wb));
fprintf(fid, '  Range: %.2f dB\n\n', max(SINR_wb) - min(SINR_wb));

fprintf(fid, 'CQI Statistics:\n');
fprintf(fid, '  Min: %d (at %.1f m)\n', min(CQI_wb), distances(find(CQI_wb == min(CQI_wb), 1)));
fprintf(fid, '  Max: %d (at %.1f m)\n', max(CQI_wb), distances(find(CQI_wb == max(CQI_wb), 1)));
fprintf(fid, '  Mean: %.1f\n', mean(CQI_wb));
fprintf(fid, '  Median: %d\n\n', median(CQI_wb));

fprintf(fid, 'Path Loss Statistics:\n');
fprintf(fid, '  Min: %.2f dB (at %.1f m)\n', min(path_loss), distances(find(path_loss == min(path_loss), 1)));
fprintf(fid, '  Max: %.2f dB (at %.1f m)\n', max(path_loss), distances(find(path_loss == max(path_loss), 1)));
fprintf(fid, '  Mean: %.2f dB\n', mean(path_loss));
fprintf(fid, '  Range: %.2f dB\n\n', max(path_loss) - min(path_loss));

if ~isempty(corr_dist_idx)
    fprintf(fid, 'Spatial Correlation:\n');
    fprintf(fid, '  Correlation distance (50%% threshold): %.1f m\n', corr_dist);
    fprintf(fid, '  Interpretation: CSI remains correlated within ~%.1f m\n\n', corr_dist);
end

fprintf(fid, 'KEY INSIGHTS\n');
fprintf(fid, '============\n\n');
fprintf(fid, '1. Distance Effect:\n');
fprintf(fid, '   - RSS decreases as UE moves away from BS\n');
fprintf(fid, '   - Approximately %.1f dB drop over %.1f m\n', max(RSS_wb) - min(RSS_wb), end_pos(1) - start_pos(1));
fprintf(fid, '   - Path loss follows expected trend\n\n');

fprintf(fid, '2. Quality Degradation:\n');
fprintf(fid, '   - SINR drops from %.1f to %.1f dB\n', max(SINR_wb), min(SINR_wb));
fprintf(fid, '   - CQI decreases from %d to %d\n', max(CQI_wb), min(CQI_wb));
fprintf(fid, '   - Link quality degrades with distance\n\n');

fprintf(fid, '3. Spatial Correlation:\n');
fprintf(fid, '   - CSI shows spatial continuity\n');
fprintf(fid, '   - Nearby positions have similar CSI\n');
fprintf(fid, '   - Important for tracking and prediction\n\n');

fprintf(fid, '4. For ML Location Prediction:\n');
fprintf(fid, '   - RSS is strong distance indicator\n');
fprintf(fid, '   - SINR and CQI provide additional features\n');
fprintf(fid, '   - Temporal smoothing may improve accuracy\n');
fprintf(fid, '   - Consider multiple trajectories for training\n\n');

files_generated = {
    'trajectory.png', 'trajectory.fig', ...
    'metrics_vs_distance.png', 'metrics_vs_distance.fig', ...
    'time_evolution.png', 'time_evolution.fig', ...
    'spatial_correlation.png', 'spatial_correlation.fig'
};
ExperimentUtils.closeReport(fid, files_generated);

%% Console Summary
fprintf('========================================\n');
fprintf('SUMMARY\n');
fprintf('========================================\n\n');

fprintf('RSS: %.2f to %.2f dBm (%.1f dB range)\n', max(RSS_wb), min(RSS_wb), max(RSS_wb) - min(RSS_wb));
fprintf('SINR: %.2f to %.2f dB (%.1f dB range)\n', max(SINR_wb), min(SINR_wb), max(SINR_wb) - min(SINR_wb));
fprintf('CQI: %d to %d (range: %d)\n', max(CQI_wb), min(CQI_wb), max(CQI_wb) - min(CQI_wb));

if ~isempty(corr_dist_idx)
    fprintf('Spatial correlation distance: %.1f m\n', corr_dist);
end
fprintf('\n');

fprintf('Results saved to: %s\n', results_dir);
fprintf('\n');

fprintf('========================================\n');
fprintf('KEY INSIGHTS\n');
fprintf('========================================\n\n');

fprintf('✓ CSI changes smoothly with UE position\n');
fprintf('✓ RSS is strong indicator of distance\n');
fprintf('✓ SINR and CQI degrade with distance\n');
fprintf('✓ Spatial correlation exists in CSI\n');
fprintf('✓ Tracking is feasible for moving UE\n\n');

fprintf('Next: exp08_trajectory_types.m\n');
fprintf('Learn about different movement patterns!\n');
fprintf('========================================\n');
