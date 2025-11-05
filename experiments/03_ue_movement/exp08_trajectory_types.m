%% EXPERIMENT 08: Trajectory Types
% Learn: Compare different UE movement patterns
% Time: 25 minutes
%
% What you'll see:
% - Linear vs Circular vs Random trajectories
% - How movement pattern affects CSI variation
% - Velocity effects on CSI correlation
% - Pattern-specific characteristics
%
% Expected output:
% - Multiple trajectory visualizations
% - CSI comparison across patterns
% - Statistical differences

clear; clc; close all;

% Add utils to path
utils_path = fullfile(fileparts(fileparts(mfilename('fullpath'))), '..', 'utils');
addpath(utils_path);

fprintf('========================================\n');
fprintf('EXPERIMENT 08: Trajectory Types\n');
fprintf('========================================\n\n');

%% Common simulation parameters
s = qd_simulation_parameters;
s.center_frequency = 3.5e9;
s.sample_density = 2;
s.use_absolute_delays = 1;

% Base station (fixed for all trajectories)
bs_position = [50; 50; 25];  % Center of area

% Frequency domain parameters
BW = 100e6;
Nsc = 256;
fvec = linspace(-BW/2, BW/2, Nsc);

% CSI metrics calculator
m = CSIMetrics('SubcarrierSpacing', BW/Nsc, ...
               'TxPowerPerSC_dBm', 0, ...
               'NoiseFigure_dB', 7);

n_snapshots = 60;

%% Trajectory 1: Linear
fprintf('========================================\n');
fprintf('TRAJECTORY 1: Linear Movement\n');
fprintf('========================================\n\n');

l1 = qd_layout(s);
l1.tx_position = bs_position;
l1.tx_array = qd_arrayant('omni');

% Linear: 10m to 90m in X, constant Y=50
start_pos1 = [10; 50; 1.5];
end_pos1 = [90; 50; 1.5];

% Create linear trajectory
track1 = qd_track('linear', end_pos1(1) - start_pos1(1), 0);
track1.scenario = '3GPP_38.901_UMa_LOS';
track1.initial_position = start_pos1;
track1.no_snapshots = n_snapshots;

l1.track(1,1) = track1;
l1.rx_array = qd_arrayant('omni');

fprintf('Generating linear trajectory channels...\n');
c1 = l1.get_channels;
fprintf('Done! Size: [%d, %d, %d, %d]\n\n', size(c1.coeff));

% Process snapshots
[traj1, dist1, RSS1, SINR1, CQI1] = processTrajectory(c1, l1, bs_position, BW, Nsc, m);

%% Trajectory 2: Circular
fprintf('========================================\n');
fprintf('TRAJECTORY 2: Circular Movement\n');
fprintf('========================================\n\n');

l2 = qd_layout(s);
l2.tx_position = bs_position;
l2.tx_array = qd_arrayant('omni');

% Circular: Radius 30m around BS
track2 = qd_track('circular', 30, pi);  % 30m radius, pi radians (half circle)
track2.scenario = '3GPP_38.901_UMa_LOS';
track2.initial_position = bs_position + [30; 0; -23.5];  % Start at radius 30m
track2.no_snapshots = n_snapshots;

l2.track(1,1) = track2;
l2.rx_array = qd_arrayant('omni');

fprintf('Generating circular trajectory channels...\n');
c2 = l2.get_channels;
fprintf('Done! Size: [%d, %d, %d, %d]\n\n', size(c2.coeff));

% Process snapshots
[traj2, dist2, RSS2, SINR2, CQI2] = processTrajectory(c2, l2, bs_position, BW, Nsc, m);

%% Trajectory 3: Random Walk
fprintf('========================================\n');
fprintf('TRAJECTORY 3: Random Walk\n');
fprintf('========================================\n\n');

l3 = qd_layout(s);
l3.tx_position = bs_position;
l3.tx_array = qd_arrayant('omni');

% Create random walk trajectory manually
rng(42);  % For reproducibility
start_pos3 = [30; 30; 1.5];
traj3_manual = zeros(3, n_snapshots);
traj3_manual(:, 1) = start_pos3;

step_size = 2;  % 2m steps
for i = 2:n_snapshots
    % Random direction
    angle = rand * 2*pi;
    step = step_size * [cos(angle); sin(angle); 0];
    
    % Take step
    next_pos = traj3_manual(:, i-1) + step;
    
    % Keep within bounds [10, 90] x [10, 90]
    next_pos(1) = max(10, min(90, next_pos(1)));
    next_pos(2) = max(10, min(90, next_pos(2)));
    next_pos(3) = 1.5;
    
    traj3_manual(:, i) = next_pos;
end

% Create track object and manually set positions
track3 = qd_track([]);  % Empty track
track3.scenario = '3GPP_38.901_UMa_LOS';
track3.initial_position = start_pos3;
track3.positions = traj3_manual;
track3.no_snapshots = n_snapshots;

l3.track(1,1) = track3;
l3.rx_array = qd_arrayant('omni');

fprintf('Generating random walk trajectory channels...\n');
c3 = l3.get_channels;
fprintf('Done! Size: [%d, %d, %d, %d]\n\n', size(c3.coeff));

% Process snapshots
[traj3, dist3, RSS3, SINR3, CQI3] = processTrajectory(c3, l3, bs_position, BW, Nsc, m);

%% Create results directory
results_dir = ExperimentUtils.createResultsDir('exp08');

%% Visualization 1: Trajectories Comparison
fig1 = ExperimentUtils.createFigure('Experiment 08 - Trajectories', 'square');

plot(traj1(1,:), traj1(2,:), 'b-', 'LineWidth', 2.5);
hold on;
plot(traj2(1,:), traj2(2,:), 'r-', 'LineWidth', 2.5);
plot(traj3(1,:), traj3(2,:), 'g-', 'LineWidth', 2.5);

% Mark start and end points
plot(traj1(1,1), traj1(2,1), 'bo', 'MarkerSize', 12, 'MarkerFaceColor', 'b');
plot(traj1(1,end), traj1(2,end), 'bs', 'MarkerSize', 12, 'MarkerFaceColor', 'b');
plot(traj2(1,1), traj2(2,1), 'ro', 'MarkerSize', 12, 'MarkerFaceColor', 'r');
plot(traj2(1,end), traj2(2,end), 'rs', 'MarkerSize', 12, 'MarkerFaceColor', 'r');
plot(traj3(1,1), traj3(2,1), 'go', 'MarkerSize', 12, 'MarkerFaceColor', 'g');
plot(traj3(1,end), traj3(2,end), 'gs', 'MarkerSize', 12, 'MarkerFaceColor', 'g');

% Mark BS
plot(bs_position(1), bs_position(2), 'k^', 'MarkerSize', 20, 'MarkerFaceColor', 'k');
hold off;

xlabel('X Position (m)');
ylabel('Y Position (m)');
title('Three Trajectory Types');
legend('Linear', 'Circular', 'Random Walk', 'Location', 'best');
grid on;
axis equal;
xlim([0 100]);
ylim([0 100]);

figure(fig1);
ExperimentUtils.saveFigures(gcf, 'trajectories', results_dir);

%% Visualization 2: Distance Profiles
fig2 = ExperimentUtils.createFigure('Experiment 08 - Distance Profiles', 'wide');

subplot(1, 3, 1);
plot(1:length(dist1), dist1, 'b-', 'LineWidth', 2);
xlabel('Snapshot');
ylabel('Distance to BS (m)');
title('Linear Trajectory');
grid on;
ylim([0 max([dist1, dist2, dist3])+10]);

subplot(1, 3, 2);
plot(1:length(dist2), dist2, 'r-', 'LineWidth', 2);
xlabel('Snapshot');
ylabel('Distance to BS (m)');
title('Circular Trajectory');
grid on;
ylim([0 max([dist1, dist2, dist3])+10]);

subplot(1, 3, 3);
plot(1:length(dist3), dist3, 'g-', 'LineWidth', 2);
xlabel('Snapshot');
ylabel('Distance to BS (m)');
title('Random Walk');
grid on;
ylim([0 max([dist1, dist2, dist3])+10]);

figure(fig2);
ExperimentUtils.saveFigures(gcf, 'distance_profiles', results_dir);

%% Visualization 3: RSS Comparison
fig3 = ExperimentUtils.createFigure('Experiment 08 - RSS Comparison', 'wide');

subplot(2, 2, 1);
plot(1:length(RSS1), RSS1, 'b-', 'LineWidth', 2);
hold on;
plot(1:length(RSS2), RSS2, 'r-', 'LineWidth', 2);
plot(1:length(RSS3), RSS3, 'g-', 'LineWidth', 2);
hold off;
xlabel('Snapshot');
ylabel('RSS (dBm)');
title('RSS Over Time');
legend('Linear', 'Circular', 'Random', 'Location', 'best');
grid on;

subplot(2, 2, 2);
plot(dist1, RSS1, 'b.', 'MarkerSize', 10);
hold on;
plot(dist2, RSS2, 'r.', 'MarkerSize', 10);
plot(dist3, RSS3, 'g.', 'MarkerSize', 10);
hold off;
xlabel('Distance (m)');
ylabel('RSS (dBm)');
title('RSS vs Distance');
legend('Linear', 'Circular', 'Random', 'Location', 'best');
grid on;

subplot(2, 2, 3);
histogram(RSS1, 15, 'FaceColor', 'b', 'FaceAlpha', 0.5);
hold on;
histogram(RSS2, 15, 'FaceColor', 'r', 'FaceAlpha', 0.5);
histogram(RSS3, 15, 'FaceColor', 'g', 'FaceAlpha', 0.5);
hold off;
xlabel('RSS (dBm)');
ylabel('Count');
title('RSS Distribution');
legend('Linear', 'Circular', 'Random');
grid on;

subplot(2, 2, 4);
boxplot([RSS1', RSS2', RSS3'], 'Labels', {'Linear', 'Circular', 'Random'});
ylabel('RSS (dBm)');
title('RSS Statistics');
grid on;

figure(fig3);
ExperimentUtils.saveFigures(gcf, 'rss_comparison', results_dir);

%% Visualization 4: SINR and CQI Comparison
fig4 = ExperimentUtils.createFigure('Experiment 08 - Quality Metrics', 'wide');

subplot(2, 2, 1);
plot(1:length(SINR1), SINR1, 'b-', 'LineWidth', 2);
hold on;
plot(1:length(SINR2), SINR2, 'r-', 'LineWidth', 2);
plot(1:length(SINR3), SINR3, 'g-', 'LineWidth', 2);
hold off;
xlabel('Snapshot');
ylabel('SINR (dB)');
title('SINR Over Time');
legend('Linear', 'Circular', 'Random', 'Location', 'best');
grid on;

subplot(2, 2, 2);
stairs(1:length(CQI1), CQI1, 'b-', 'LineWidth', 2);
hold on;
stairs(1:length(CQI2), CQI2, 'r-', 'LineWidth', 2);
stairs(1:length(CQI3), CQI3, 'g-', 'LineWidth', 2);
hold off;
xlabel('Snapshot');
ylabel('CQI (0-15)');
title('CQI Over Time');
legend('Linear', 'Circular', 'Random', 'Location', 'best');
grid on;
ylim([-0.5 15.5]);

subplot(2, 2, 3);
boxplot([SINR1', SINR2', SINR3'], 'Labels', {'Linear', 'Circular', 'Random'});
ylabel('SINR (dB)');
title('SINR Statistics');
grid on;

subplot(2, 2, 4);
boxplot([CQI1', CQI2', CQI3'], 'Labels', {'Linear', 'Circular', 'Random'});
ylabel('CQI (0-15)');
title('CQI Statistics');
grid on;

figure(fig4);
ExperimentUtils.saveFigures(gcf, 'quality_comparison', results_dir);

%% Visualization 5: Variability Analysis
fig5 = ExperimentUtils.createFigure('Experiment 08 - Variability', 'wide');

% Calculate derivatives (rate of change)
dRSS1 = [0, diff(RSS1)];
dRSS2 = [0, diff(RSS2)];
dRSS3 = [0, diff(RSS3)];

subplot(2, 2, 1);
plot(1:length(dRSS1), abs(dRSS1), 'b-', 'LineWidth', 1.5);
hold on;
plot(1:length(dRSS2), abs(dRSS2), 'r-', 'LineWidth', 1.5);
plot(1:length(dRSS3), abs(dRSS3), 'g-', 'LineWidth', 1.5);
hold off;
xlabel('Snapshot');
ylabel('|dRSS/dt| (dB/step)');
title('RSS Rate of Change');
legend('Linear', 'Circular', 'Random', 'Location', 'best');
grid on;

subplot(2, 2, 2);
histogram(abs(dRSS1), 20, 'FaceColor', 'b', 'FaceAlpha', 0.5);
hold on;
histogram(abs(dRSS2), 20, 'FaceColor', 'r', 'FaceAlpha', 0.5);
histogram(abs(dRSS3), 20, 'FaceColor', 'g', 'FaceAlpha', 0.5);
hold off;
xlabel('|dRSS/dt| (dB/step)');
ylabel('Count');
title('RSS Variability Distribution');
legend('Linear', 'Circular', 'Random');
grid on;

% Calculate standard deviation in windows
window = 5;
subplot(2, 2, 3);
RSS1_std = movstd(RSS1, window);
RSS2_std = movstd(RSS2, window);
RSS3_std = movstd(RSS3, window);

plot(1:length(RSS1_std), RSS1_std, 'b-', 'LineWidth', 2);
hold on;
plot(1:length(RSS2_std), RSS2_std, 'r-', 'LineWidth', 2);
plot(1:length(RSS3_std), RSS3_std, 'g-', 'LineWidth', 2);
hold off;
xlabel('Snapshot');
ylabel('Local Std Dev (dB)');
title(sprintf('RSS Variability (Window=%d)', window));
legend('Linear', 'Circular', 'Random', 'Location', 'best');
grid on;

% Autocorrelation comparison
subplot(2, 2, 4);
RSS1_norm = (RSS1 - mean(RSS1)) / std(RSS1);
RSS2_norm = (RSS2 - mean(RSS2)) / std(RSS2);
RSS3_norm = (RSS3 - mean(RSS3)) / std(RSS3);

max_lag = 15;
[acf1, ~] = xcorr(RSS1_norm, max_lag, 'coeff');
[acf2, ~] = xcorr(RSS2_norm, max_lag, 'coeff');
[acf3, lags] = xcorr(RSS3_norm, max_lag, 'coeff');

plot(lags, acf1, 'b-', 'LineWidth', 2);
hold on;
plot(lags, acf2, 'r-', 'LineWidth', 2);
plot(lags, acf3, 'g-', 'LineWidth', 2);
plot([min(lags) max(lags)], [0.5 0.5], 'k--', 'LineWidth', 1);
hold off;
xlabel('Lag (snapshots)');
ylabel('Autocorrelation');
title('RSS Temporal Correlation');
legend('Linear', 'Circular', 'Random', 'Location', 'best');
grid on;

figure(fig5);
ExperimentUtils.saveFigures(gcf, 'variability_analysis', results_dir);

%% Statistical Analysis
fprintf('========================================\n');
fprintf('STATISTICAL COMPARISON\n');
fprintf('========================================\n\n');

fprintf('RSS Statistics:\n');
fprintf('  Linear:   Mean=%.2f dBm, Std=%.2f dB, Range=%.2f dB\n', ...
    mean(RSS1), std(RSS1), max(RSS1)-min(RSS1));
fprintf('  Circular: Mean=%.2f dBm, Std=%.2f dB, Range=%.2f dB\n', ...
    mean(RSS2), std(RSS2), max(RSS2)-min(RSS2));
fprintf('  Random:   Mean=%.2f dBm, Std=%.2f dB, Range=%.2f dB\n\n', ...
    mean(RSS3), std(RSS3), max(RSS3)-min(RSS3));

fprintf('SINR Statistics:\n');
fprintf('  Linear:   Mean=%.2f dB, Std=%.2f dB\n', mean(SINR1), std(SINR1));
fprintf('  Circular: Mean=%.2f dB, Std=%.2f dB\n', mean(SINR2), std(SINR2));
fprintf('  Random:   Mean=%.2f dB, Std=%.2f dB\n\n', mean(SINR3), std(SINR3));

fprintf('CQI Statistics:\n');
fprintf('  Linear:   Mean=%.1f, Median=%d, Std=%.2f\n', mean(CQI1), median(CQI1), std(CQI1));
fprintf('  Circular: Mean=%.1f, Median=%d, Std=%.2f\n', mean(CQI2), median(CQI2), std(CQI2));
fprintf('  Random:   Mean=%.1f, Median=%d, Std=%.2f\n\n', mean(CQI3), median(CQI3), std(CQI3));

fprintf('Variability (RSS rate of change):\n');
fprintf('  Linear:   Mean=%.3f dB/step, Max=%.3f dB/step\n', mean(abs(dRSS1)), max(abs(dRSS1)));
fprintf('  Circular: Mean=%.3f dB/step, Max=%.3f dB/step\n', mean(abs(dRSS2)), max(abs(dRSS2)));
fprintf('  Random:   Mean=%.3f dB/step, Max=%.3f dB/step\n\n', mean(abs(dRSS3)), max(abs(dRSS3)));

fprintf('Distance Statistics:\n');
fprintf('  Linear:   Mean=%.1f m, Std=%.1f m, Range=%.1f m\n', ...
    mean(dist1), std(dist1), max(dist1)-min(dist1));
fprintf('  Circular: Mean=%.1f m, Std=%.1f m, Range=%.1f m\n', ...
    mean(dist2), std(dist2), max(dist2)-min(dist2));
fprintf('  Random:   Mean=%.1f m, Std=%.1f m, Range=%.1f m\n\n', ...
    mean(dist3), std(dist3), max(dist3)-min(dist3));

%% Save report
fid = ExperimentUtils.createReportHeader(results_dir, 'EXPERIMENT 08: Trajectory Types');

fprintf(fid, 'CONFIGURATION\n');
fprintf(fid, '=============\n\n');

% Create params struct for report
report_params = struct();
report_params.center_frequency = s.center_frequency;
report_params.sample_density = s.sample_density;
report_params.bandwidth = BW;
report_params.num_subcarriers = Nsc;
report_params.scenario = '3GPP_38.901_UMa_LOS';
report_params.tx_position = bs_position;
ExperimentUtils.writeSimParams(fid, report_params);
fprintf(fid, '\n');

fprintf(fid, 'TRAJECTORIES\n');
fprintf(fid, '============\n\n');
fprintf(fid, '1. Linear: 10m to 90m in X direction\n');
fprintf(fid, '2. Circular: 30m radius, half circle\n');
fprintf(fid, '3. Random Walk: 2m steps, bounded area\n');
fprintf(fid, 'Snapshots per trajectory: %d\n\n', n_snapshots);

fprintf(fid, 'STATISTICAL COMPARISON\n');
fprintf(fid, '======================\n\n');
fprintf(fid, 'RSS Statistics:\n');
fprintf(fid, '  Linear:   Mean=%.2f dBm, Std=%.2f dB\n', mean(RSS1), std(RSS1));
fprintf(fid, '  Circular: Mean=%.2f dBm, Std=%.2f dB\n', mean(RSS2), std(RSS2));
fprintf(fid, '  Random:   Mean=%.2f dBm, Std=%.2f dB\n\n', mean(RSS3), std(RSS3));

fprintf(fid, 'SINR Statistics:\n');
fprintf(fid, '  Linear:   Mean=%.2f dB, Std=%.2f dB\n', mean(SINR1), std(SINR1));
fprintf(fid, '  Circular: Mean=%.2f dB, Std=%.2f dB\n', mean(SINR2), std(SINR2));
fprintf(fid, '  Random:   Mean=%.2f dB, Std=%.2f dB\n\n', mean(SINR3), std(SINR3));

fprintf(fid, 'KEY INSIGHTS\n');
fprintf(fid, '============\n\n');
fprintf(fid, '1. Linear Trajectory:\n');
fprintf(fid, '   - Monotonic distance change\n');
fprintf(fid, '   - Smooth RSS variation\n');
fprintf(fid, '   - Predictable pattern\n');
fprintf(fid, '   - Good for testing algorithms\n\n');

fprintf(fid, '2. Circular Trajectory:\n');
fprintf(fid, '   - Constant distance to BS\n');
fprintf(fid, '   - More stable RSS\n');
fprintf(fid, '   - Lower variability\n');
fprintf(fid, '   - Tests angular effects\n\n');

fprintf(fid, '3. Random Walk:\n');
fprintf(fid, '   - Unpredictable movement\n');
fprintf(fid, '   - Higher variability\n');
fprintf(fid, '   - More realistic scenario\n');
fprintf(fid, '   - Challenging for prediction\n\n');

fprintf(fid, '4. For ML Training:\n');
fprintf(fid, '   - Use diverse trajectory types\n');
fprintf(fid, '   - Random walks most realistic\n');
fprintf(fid, '   - Linear/circular for validation\n');
fprintf(fid, '   - Balance dataset across patterns\n\n');

files_generated = {
    'trajectories.png', 'trajectories.fig', ...
    'distance_profiles.png', 'distance_profiles.fig', ...
    'rss_comparison.png', 'rss_comparison.fig', ...
    'quality_comparison.png', 'quality_comparison.fig', ...
    'variability_analysis.png', 'variability_analysis.fig'
};
ExperimentUtils.closeReport(fid, files_generated);

fprintf('Results saved to: %s\n\n', results_dir);

fprintf('========================================\n');
fprintf('KEY INSIGHTS\n');
fprintf('========================================\n\n');

fprintf('✓ Different trajectories show different CSI patterns\n');
fprintf('✓ Linear: Monotonic change (good for testing)\n');
fprintf('✓ Circular: Stable RSS (tests angular effects)\n');
fprintf('✓ Random: Most realistic (challenging)\n');
fprintf('✓ Variability differs by trajectory type\n');
fprintf('✓ Need diverse training data for robust ML\n\n');

fprintf('Next: exp09_multi_trajectory.m\n');
fprintf('Generate large datasets for ML training!\n');
fprintf('========================================\n');

%% Helper function
function [trajectory, distances, RSS, SINR, CQI] = processTrajectory(c, l, bs_pos, BW, Nsc, metrics)
    % Process channel snapshots and extract metrics
    
    n_snaps = size(c.coeff, 4);
    fvec = linspace(-BW/2, BW/2, Nsc);
    
    trajectory = zeros(3, n_snaps);
    distances = zeros(1, n_snaps);
    RSS = zeros(1, n_snaps);
    SINR = zeros(1, n_snaps);
    CQI = zeros(1, n_snaps);
    
    for snap = 1:n_snaps
        % Get UE position
        ue_pos = l.track(1).positions(:, snap);
        trajectory(:, snap) = ue_pos;
        distances(snap) = norm(ue_pos - bs_pos);
        
        % Get channel
        h_t = squeeze(c.coeff(1,1,:,snap));
        tau = squeeze(c.delay(1,:,snap));
        
        % Ensure same size and remove zero-power taps
        n_taps = min(length(h_t), length(tau));
        h_t = h_t(1:n_taps);
        tau = tau(1:n_taps);
        
        valid_idx = abs(h_t) > 1e-10;
        h_t = h_t(valid_idx);
        tau = tau(valid_idx);
        
        % Convert to frequency domain
        H_sc = zeros(1, 1, Nsc);
        for k = 1:Nsc
            H_sc(1,1,k) = sum(h_t .* exp(-1j * 2*pi * fvec(k) .* tau));
        end
        
        % Compute metrics
        out = metrics.compute(H_sc);
        RSS(snap) = out.RSS_dBm_wb;
        SINR(snap) = out.SINR_dB_wb;
        CQI(snap) = out.CQI_wb;
    end
end
