%% EXPERIMENT 02: Distance Comparison
% Learn: How distance affects CSI and path loss
% Time: 10 minutes
%
% What you'll see:
% - CSI at 3 different distances (25m, 50m, 100m)
% - Path loss increases with distance
% - Signal strength decreases exponentially
%
% Expected output:
% - 3 plots comparing impulse responses
% - Console showing path loss for each distance

clear; clc; close all;

% Add utils to path
utils_path = fullfile(fileparts(fileparts(mfilename('fullpath'))), '..', 'utils');
addpath(utils_path);

fprintf('========================================\n');
fprintf('EXPERIMENT 02: Distance Comparison\n');
fprintf('========================================\n\n');

%% Setup
distances = [25, 50, 100];  % Test distances in meters
colors = {'r', 'g', 'b'};
H_all = cell(1, 3);
stats_all = cell(1, 3);

%% Create figure
fig = ExperimentUtils.createFigure('Experiment 02 - Distance Comparison', 'square');

%% Run simulation for each distance (REFACTORED - cleaner loop)
for idx = 1:length(distances)
    dist = distances(idx);
    fprintf('Testing distance: %d meters\n', dist);
    
    % Generate channel using utility
    params = struct(...
        'center_frequency', 3.5e9, ...
        'rx_position', [dist; 0; 1.5], ...
        'scenario', '3GPP_38.901_UMa_LOS');
    
    [H_all{idx}, ~] = ExperimentUtils.generateChannel(params);
    
    % Calculate statistics
    stats_all{idx} = ExperimentUtils.calculateChannelStats(H_all{idx}, (0:length(H_all{idx})-1)');
    
    fprintf('  Number of taps: %d\n', stats_all{idx}.num_taps);
    fprintf('  Path loss: %.2f dB\n', stats_all{idx}.path_loss_dB);
    fprintf('  Dominant tap magnitude: %.6f\n\n', max(abs(H_all{idx})));
    
    % Plot impulse response
    subplot(2, 2, idx);
    stem(1:length(H_all{idx}), abs(H_all{idx}), colors{idx}, 'LineWidth', 2);
    xlabel('Tap Index');
    ylabel('|h|');
    title(sprintf('Distance: %dm (Path Loss: %.1f dB)', dist, stats_all{idx}.path_loss_dB));
    grid on;
end

%% Comparison plot
subplot(2, 2, 4);
hold on;
for idx = 1:length(distances)
    stem(1:length(H_all{idx}), abs(H_all{idx}), colors{idx}, ...
        'LineWidth', 1.5, 'DisplayName', sprintf('%dm', distances(idx)));
end
hold off;
xlabel('Tap Index');
ylabel('|h|');
title('All Distances Overlaid');
legend('Location', 'best');
grid on;

%% Analysis
fprintf('========================================\n');
fprintf('ANALYSIS\n');
fprintf('========================================\n');
fprintf('Distance vs Path Loss:\n');
for idx = 1:length(distances)
    fprintf('  %3d m → %.2f dB\n', distances(idx), stats_all{idx}.path_loss_dB);
end

fprintf('\nPath Loss Increase:\n');
fprintf('  25m to 50m: %.2f dB (doubled distance)\n', stats_all{2}.path_loss_dB - stats_all{1}.path_loss_dB);
fprintf('  50m to 100m: %.2f dB (doubled distance)\n', stats_all{3}.path_loss_dB - stats_all{2}.path_loss_dB);
fprintf('\nTheory: Doubling distance → ~6 dB increase (free space)\n');

%% Save results (REFACTORED)
fprintf('\nSaving results...\n');

% Create results directory
results_dir = ExperimentUtils.createResultsDir('exp02');

% Ensure figure is current and save
figure(fig);
ExperimentUtils.saveFigures(gcf, 'distance_comparison', results_dir);

% Create report
fid = ExperimentUtils.createReportHeader(results_dir, 'EXPERIMENT 02: Distance Comparison');

% Write simulation parameters
params = struct(...
    'center_frequency', 3.5e9, ...
    'sample_density', 2, ...
    'scenario', '3GPP_38.901_UMa_LOS', ...
    'tx_position', [0; 0; 25]);

ExperimentUtils.writeSimParams(fid, params);
fprintf(fid, 'Test Distances: %s m\n\n', mat2str(distances));

fprintf(fid, '--- RESULTS BY DISTANCE ---\n');
for idx = 1:length(distances)
    fprintf(fid, '\nDistance: %d meters\n', distances(idx));
    fprintf(fid, '  UE Position: [%d, 0, 1.5] m\n', distances(idx));
    fprintf(fid, '  Number of Taps: %d\n', stats_all{idx}.num_taps);
    fprintf(fid, '  Path Loss: %.2f dB\n', stats_all{idx}.path_loss_dB);
    fprintf(fid, '  Dominant Tap: %.6f\n', max(abs(H_all{idx})));
    fprintf(fid, '  Total Power: %.6e\n', stats_all{idx}.total_power);
end

fprintf(fid, '\n--- PATH LOSS ANALYSIS ---\n');
fprintf(fid, 'Distance vs Path Loss:\n');
for idx = 1:length(distances)
    fprintf(fid, '  %3d m → %.2f dB\n', distances(idx), stats_all{idx}.path_loss_dB);
end

fprintf(fid, '\nPath Loss Increase (doubling distance):\n');
fprintf(fid, '  25m to 50m: %.2f dB\n', stats_all{2}.path_loss_dB - stats_all{1}.path_loss_dB);
fprintf(fid, '  50m to 100m: %.2f dB\n', stats_all{3}.path_loss_dB - stats_all{2}.path_loss_dB);
fprintf(fid, '\nTheory: Doubling distance → ~6 dB increase (free space)\n');

fprintf(fid, '\n--- KEY INSIGHTS ---\n');
fprintf(fid, '• CSI magnitude decreases with distance\n');
fprintf(fid, '• Path loss increases logarithmically (~6dB per distance doubling)\n');
fprintf(fid, '• Number of taps may vary with distance\n');
fprintf(fid, '• First tap usually dominant in LOS scenarios\n');
fprintf(fid, '• Position affects received power significantly\n\n');

fprintf(fid, '--- ML RELEVANCE ---\n');
fprintf(fid, 'Distance estimation from CSI is a key ML task.\n');
fprintf(fid, 'Features for ML:\n');
fprintf(fid, '  - Total received power (path loss)\n');
fprintf(fid, '  - Dominant tap magnitude\n');
fprintf(fid, '  - Number of significant taps\n');
fprintf(fid, '  - Power distribution across taps\n\n');

ExperimentUtils.closeReport(fid, {'distance_comparison.png', ...
    'distance_comparison.fig', 'experiment_report.txt'});

fprintf('  ✓ Results saved to: %s\n', results_dir);
fprintf('     - distance_comparison.png\n');
fprintf('     - distance_comparison.fig\n');
fprintf('     - experiment_report.txt\n');

fprintf('\n========================================\n');
fprintf('Key Takeaways:\n');
fprintf('  1. CSI magnitude decreases with distance\n');
fprintf('  2. Path loss increases logarithmically\n');
fprintf('  3. Number of taps may vary with distance\n');
fprintf('  4. First tap usually dominant in LOS\n\n');
fprintf('Next: Run exp03_los_vs_nlos.m\n');
fprintf('========================================\n');
