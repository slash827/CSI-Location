%% EXAMPLE: Refactored Experiment Using ExperimentUtils
% This shows how to use the new utility functions
% Compare this cleaner version to the original experiments

clear; clc; close all;

% Add utils to path
addpath('../../utils');

fprintf('========================================\n');
fprintf('EXAMPLE: Using ExperimentUtils\n');
fprintf('========================================\n\n');

%% Step 1: Generate channel (MUCH CLEANER!)
fprintf('Step 1: Generating channel...\n');

params = struct(...
    'center_frequency', 3.5e9, ...
    'rx_position', [75; 0; 1.5], ...
    'scenario', '3GPP_38.901_UMa_LOS');

[H_taps, delays_ns, c, l] = ExperimentUtils.generateChannel(params);
fprintf('  ✓ Generated %d taps\n\n', length(H_taps));

%% Step 2: Calculate statistics (ONE LINE!)
stats = ExperimentUtils.calculateChannelStats(H_taps, delays_ns);

fprintf('Channel Statistics:\n');
fprintf('  Path loss: %.2f dB\n', stats.path_loss_dB);
fprintf('  RMS delay spread: %.2f ns\n', stats.rms_delay_spread_ns);
fprintf('  Dominant tap: %d (%.1f%% of power)\n\n', ...
    stats.dominant_tap_idx, stats.dominant_tap_ratio*100);

%% Step 3: Convert to frequency domain (ONE LINE!)
BW = 100e6;
Nsc = 256;
fvec = linspace(-BW/2, BW/2, Nsc);
H_freq = ExperimentUtils.convertToFrequency(H_taps, delays_ns/1e9, fvec);

fprintf('  ✓ Converted to %d subcarriers\n\n', Nsc);

%% Step 4: Visualize
fig = ExperimentUtils.createFigure('Example - Clean Code', 'square');

subplot(2,2,1);
stem(delays_ns, abs(H_taps), 'LineWidth', 2);
xlabel('Delay (ns)'); ylabel('|h|');
title('Impulse Response');
grid on;

subplot(2,2,2);
plot(fvec/1e6, abs(H_freq), 'LineWidth', 1.5);
xlabel('Frequency (MHz)'); ylabel('|H(f)|');
title('Frequency Response');
grid on;

subplot(2,2,3);
plot(fvec/1e6, angle(H_freq)*180/pi, 'LineWidth', 1.5);
xlabel('Frequency (MHz)'); ylabel('Phase (degrees)');
title('Phase Response');
grid on;

subplot(2,2,4);
plot(real(H_freq), imag(H_freq), 'o-');
xlabel('Real'); ylabel('Imaginary');
title('Complex Plane');
grid on; axis equal;

%% Step 5: Save results (THREE LINES!)
results_dir = ExperimentUtils.createResultsDir('example');
ExperimentUtils.saveFigures(fig, 'example_plot', results_dir);

% Create report
fid = ExperimentUtils.createReportHeader(results_dir, 'EXAMPLE: Clean Experiment Code');

% Write parameters
params.bandwidth = BW;
params.num_subcarriers = Nsc;
params.tx_position = l.tx_position;
ExperimentUtils.writeSimParams(fid, params);

% Write statistics
fprintf(fid, '--- CHANNEL STATISTICS ---\n');
fprintf(fid, 'Number of Taps: %d\n', stats.num_taps);
fprintf(fid, 'Path Loss: %.2f dB\n', stats.path_loss_dB);
fprintf(fid, 'RMS Delay Spread: %.2f ns\n', stats.rms_delay_spread_ns);
fprintf(fid, 'Dominant Tap: %d (%.1f%% of power)\n\n', ...
    stats.dominant_tap_idx, stats.dominant_tap_ratio*100);

ExperimentUtils.closeReport(fid, {'example_plot.png', 'example_plot.fig', 'experiment_report.txt'});

fprintf('  ✓ Results saved to: %s\n\n', results_dir);

fprintf('========================================\n');
fprintf('COMPARISON:\n');
fprintf('  Without Utils: ~150 lines of code\n');
fprintf('  With Utils:    ~80 lines of code\n');
fprintf('  Code Reduction: ~47%%!\n');
fprintf('========================================\n');
