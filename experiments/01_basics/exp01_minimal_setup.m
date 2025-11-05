%% EXPERIMENT 01: Minimal QuaDRiGa Setup
% Learn: Basic QuaDRiGa structure, CSI matrix dimensions
% Time: 5 minutes
% 
% What you'll see:
% - How to create a simple BS-UE link
% - CSI matrix structure [Rx x Tx x Taps x Snapshots]
% - Basic impulse response plot
%
% Expected output:
% - CSI matrix size: [1 1 5 1] (approximately)
% - Plot showing 5 multipath taps

clear; clc; close all;

% Add utils to path (correct relative path from experiments/01_basics/)
utils_path = fullfile(fileparts(fileparts(mfilename('fullpath'))), '..', 'utils');
addpath(utils_path);

fprintf('========================================\n');
fprintf('EXPERIMENT 01: Minimal QuaDRiGa Setup\n');
fprintf('========================================\n\n');

%% Step 1-6: Generate channel (REFACTORED - was 60+ lines, now 8 lines!)
fprintf('Steps 1-6: Setting up and generating channel...\n');

params = struct(...
    'center_frequency', 3.5e9, ...
    'sample_density', 2, ...
    'rx_position', [50; 0; 1.5], ...
    'scenario', '3GPP_38.901_UMa_LOS');

[h_taps, delays_ns, c, l] = ExperimentUtils.generateChannel(params);

fprintf('  ✓ Frequency: %.2f GHz\n', params.center_frequency/1e9);
fprintf('  ✓ Sample density: %d\n', params.sample_density);
fprintf('  ✓ BS position: [%d, %d, %d] meters\n', l.tx_position(1), l.tx_position(2), l.tx_position(3));
fprintf('  ✓ UE position: [%d, %d, %.1f] meters\n', params.rx_position(1), params.rx_position(2), params.rx_position(3));
fprintf('  ✓ Distance: %.2f meters\n', norm(params.rx_position - l.tx_position));
fprintf('  ✓ Scenario: Urban Macro, Line of Sight\n');
fprintf('  ✓ Channel generated successfully!\n\n');

%% Step 7: Examine CSI
fprintf('Step 7: Examining CSI matrix...\n');
H = c.coeff;  % [Rx x Tx x Taps x Snapshots]
fprintf('  CSI matrix size: %s\n', mat2str(size(H)));
fprintf('    - Rx antennas: %d\n', size(H,1));
fprintf('    - Tx antennas: %d\n', size(H,2));
fprintf('    - Multipath taps: %d\n', size(H,3));
fprintf('    - Time snapshots: %d\n\n', size(H,4));

fprintf('  Complex tap values:\n');
for i = 1:length(h_taps)
    fprintf('    Tap %d: %.6f %+.6fi  (magnitude: %.6f)\n', ...
        i, real(h_taps(i)), imag(h_taps(i)), abs(h_taps(i)));
end

%% Step 8: Visualize
fprintf('\nStep 8: Creating visualization...\n');
fig = ExperimentUtils.createFigure('Experiment 01 - Channel Impulse Response', 'square');
stem(1:length(h_taps), abs(h_taps), 'LineWidth', 2, 'MarkerSize', 8);
xlabel('Tap Index', 'FontSize', 12);
ylabel('|h| (Magnitude)', 'FontSize', 12);
title('Channel Impulse Response - Multipath Taps', 'FontSize', 14);
grid on;

% Add text annotation
distance = norm(params.rx_position - l.tx_position);
text(0.02, 0.95, sprintf('Distance: %.1fm\nScenario: UMa LOS', distance), ...
    'Units', 'normalized', 'FontSize', 10, ...
    'BackgroundColor', 'white', 'EdgeColor', 'black');

fprintf('  ✓ Plot created\n');

%% Step 9: Save results (REFACTORED - was 50+ lines, now 20 lines!)
fprintf('\nStep 9: Saving results...\n');

% Create results directory
results_dir = ExperimentUtils.createResultsDir('exp01');

% Ensure figure is current and get its handle
figure(fig);
current_fig = gcf;

% Save figures
ExperimentUtils.saveFigures(current_fig, 'channel_impulse_response', results_dir);

% Calculate statistics
stats = ExperimentUtils.calculateChannelStats(h_taps, delays_ns);

% Create report
fid = ExperimentUtils.createReportHeader(results_dir, 'EXPERIMENT 01: Minimal QuaDRiGa Setup');

% Write simulation parameters
params.tx_position = l.tx_position;
ExperimentUtils.writeSimParams(fid, params);

fprintf(fid, '--- GEOMETRY ---\n');
fprintf(fid, 'Distance: %.2f m\n\n', distance);

fprintf(fid, '--- CHANNEL CHARACTERISTICS ---\n');
fprintf(fid, 'CSI Matrix Size: %s\n', mat2str(size(H)));
fprintf(fid, 'Rx Antennas: %d\n', size(H,1));
fprintf(fid, 'Tx Antennas: %d\n', size(H,2));
fprintf(fid, 'Multipath Taps: %d\n', size(H,3));
fprintf(fid, 'Time Snapshots: %d\n\n', size(H,4));

fprintf(fid, '--- MULTIPATH TAPS ---\n');
for i = 1:length(h_taps)
    fprintf(fid, 'Tap %d: %.6f %+.6fi (magnitude: %.6f)\n', ...
        i, real(h_taps(i)), imag(h_taps(i)), abs(h_taps(i)));
end
fprintf(fid, '\nStrongest Tap: %d (magnitude: %.6f)\n', stats.dominant_tap_idx, max(abs(h_taps)));
fprintf(fid, 'Total Power: %.6e\n', stats.total_power);
fprintf(fid, 'Path Loss: %.2f dB\n\n', stats.path_loss_dB);

fprintf(fid, '--- KEY INSIGHTS ---\n');
fprintf(fid, '• CSI matrix is 4D: [Rx × Tx × Taps × Snapshots]\n');
fprintf(fid, '• Each tap represents a multipath component\n');
fprintf(fid, '• First tap usually strongest (direct/LOS path)\n');
fprintf(fid, '• Tap magnitudes decay with delay\n\n');

ExperimentUtils.closeReport(fid, {'channel_impulse_response.png', ...
    'channel_impulse_response.fig', 'experiment_report.txt'});

fprintf('  ✓ Results saved to: %s\n', results_dir);
fprintf('     - channel_impulse_response.png\n');
fprintf('     - channel_impulse_response.fig\n');
fprintf('     - experiment_report.txt\n\n');

%% Summary
fprintf('========================================\n');
fprintf('EXPERIMENT COMPLETE!\n');
fprintf('========================================\n');
fprintf('Key Takeaways:\n');
fprintf('  1. QuaDRiGa needs: parameters → layout → scenario → channels\n');
fprintf('  2. CSI matrix is 4D: [Rx × Tx × Taps × Snapshots]\n');
fprintf('  3. Each tap represents a multipath component\n');
fprintf('  4. First tap usually strongest (direct path)\n\n');
fprintf('Next: Run exp02_distance_comparison.m\n');
fprintf('========================================\n');
