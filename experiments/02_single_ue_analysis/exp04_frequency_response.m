%% EXPERIMENT 04: Frequency Response
% Learn: Convert time-domain taps to frequency-domain CSI
% Time: 15 minutes
%
% What you'll see:
% - Time-domain impulse response (taps)
% - Frequency-domain channel response (subcarriers)
% - Frequency-selective fading (peaks and nulls)
% - Coherence bandwidth estimation
%
% Expected output:
% - CSI across 256 subcarriers
% - Frequency-selective fading pattern

clear; clc; close all;

% Add utils to path
utils_path = fullfile(fileparts(fileparts(mfilename('fullpath'))), '..', 'utils');
addpath(utils_path);

fprintf('========================================\n');
fprintf('EXPERIMENT 04: Frequency Response\n');
fprintf('========================================\n\n');

%% Step 1: Generate channel (REFACTORED)
fprintf('Step 1: Generating channel...\n');

params = struct(...
    'center_frequency', 3.5e9, ...
    'rx_position', [100; 50; 1.5], ...
    'scenario', '3GPP_38.901_UMa_NLOS', ...
    'use_absolute_delays', 1);

[h_t, tau_ns] = ExperimentUtils.generateChannel(params);
tau = tau_ns / 1e9;  % Convert to seconds for frequency calculation

fprintf('  ✓ Generated %d multipath taps\n', length(h_t));
fprintf('  ✓ Delay range: %.2f to %.2f ns\n\n', min(tau_ns), max(tau_ns));

%% Step 2: Convert to frequency domain (REFACTORED)
fprintf('Step 2: Converting to frequency domain...\n');

% Define frequency grid (like OFDM subcarriers)
BW = 100e6;          % 100 MHz bandwidth
Nsc = 256;           % Number of subcarriers
fvec = linspace(-BW/2, BW/2, Nsc);  % Frequency axis (Hz)

% Use utility function for conversion
H_freq = ExperimentUtils.convertToFrequency(h_t, tau, fvec);

H_mag = abs(H_freq);                    % Magnitude
H_phase = angle(H_freq) * 180/pi;       % Phase in degrees
H_dB = 20*log10(H_mag + eps);           % Magnitude in dB

fprintf('  ✓ Computed CSI for %d subcarriers\n', Nsc);
fprintf('  ✓ Subcarrier spacing: %.2f kHz\n', BW/Nsc/1e3);
fprintf('  ✓ Frequency range: %.2f to %.2f MHz\n\n', min(fvec)/1e6, max(fvec)/1e6);

%% Step 3: Analyze frequency selectivity
fprintf('Step 3: Analyzing frequency selectivity...\n');

% Find peaks and nulls (ensure H_mag is a vector)
H_mag_vec = H_mag(:);
[peaks, peak_locs] = findpeaks(H_mag_vec);
[nulls, null_locs] = findpeaks(-H_mag_vec);
nulls = -nulls;

fprintf('  Number of peaks: %d\n', length(peaks));
fprintf('  Number of nulls: %d\n', length(nulls));
fprintf('  Dynamic range: %.2f dB\n', max(H_dB) - min(H_dB));

% Coherence bandwidth (frequency range where H is correlated)
H_autocorr = xcorr(H_mag_vec, 'normalized');
coherence_idx = find(H_autocorr(Nsc:end) < 0.5, 1);
if ~isempty(coherence_idx)
    coherence_BW = coherence_idx * (BW/Nsc) / 1e6;
    fprintf('  Coherence bandwidth: ~%.2f MHz\n\n', coherence_BW);
else
    fprintf('  Coherence bandwidth: > %.2f MHz (flat fading)\n\n', BW/1e6);
end

%% Step 4: Comprehensive visualization
fprintf('Step 4: Creating visualizations...\n');

% Create figure using utility
fig = ExperimentUtils.createFigure('Experiment 04 - Frequency Response', 'square');

% Plot 1: Time-domain impulse response
subplot(3, 3, 1);
stem(tau_ns, abs(h_t), 'LineWidth', 2);
xlabel('Delay (ns)');
ylabel('|h(τ)|');
title('Time-Domain: Impulse Response');
grid on;

% Plot 2: Frequency response magnitude (linear)
subplot(3, 3, 2);
plot(fvec/1e6, H_mag, 'LineWidth', 1.5);
xlabel('Frequency (MHz)');
ylabel('|H(f)|');
title('Frequency-Domain: Channel Gain (Linear)');
grid on;
hold on;
if ~isempty(peak_locs)
    plot(fvec(peak_locs)/1e6, H_mag_vec(peak_locs), 'r^', 'MarkerSize', 8, 'LineWidth', 2);
end
if ~isempty(null_locs)
    plot(fvec(null_locs)/1e6, H_mag_vec(null_locs), 'bv', 'MarkerSize', 8, 'LineWidth', 2);
end
legend('Channel Gain', 'Peaks', 'Nulls', 'Location', 'best');
hold off;

% Plot 3: Frequency response magnitude (dB)
subplot(3, 3, 3);
plot(fvec/1e6, H_dB, 'LineWidth', 1.5);
xlabel('Frequency (MHz)');
ylabel('|H(f)| (dB)');
title('Channel Gain (dB scale)');
grid on;
yline(max(H_dB) - 3, 'r--', '3dB below max');

% Plot 4: Phase response
subplot(3, 3, 4);
plot(fvec/1e6, H_phase, 'LineWidth', 1.5, 'Color', [0.9 0.4 0.1]);
xlabel('Frequency (MHz)');
ylabel('Phase (degrees)');
title('Phase Response');
grid on;

% Plot 5: Complex plane (first 50 subcarriers)
subplot(3, 3, 5);
plot(real(H_freq(1:50)), imag(H_freq(1:50)), 'o-', 'LineWidth', 1.5);
xlabel('Real');
ylabel('Imaginary');
title('CSI in Complex Plane (first 50 SC)');
grid on;
axis equal;

% Plot 6: Magnitude vs subcarrier index
subplot(3, 3, 6);
plot(1:Nsc, H_mag, 'LineWidth', 1.5);
xlabel('Subcarrier Index');
ylabel('|H(k)|');
title('Magnitude per Subcarrier');
grid on;

% Plot 7: Autocorrelation
subplot(3, 3, 7);
plot(-Nsc+1:Nsc-1, H_autocorr, 'LineWidth', 1.5);
xlabel('Lag (subcarriers)');
ylabel('Correlation');
title('Frequency Autocorrelation');
grid on;
yline(0.5, 'r--', 'Coherence threshold');

% Plot 8: Power Spectral Density
subplot(3, 3, 8);
PSD = abs(H_freq).^2;
plot(fvec/1e6, 10*log10(PSD + eps), 'LineWidth', 1.5);
xlabel('Frequency (MHz)');
ylabel('Power (dB)');
title('Power Spectral Density');
grid on;

% Plot 9: Cumulative power distribution
subplot(3, 3, 9);
sorted_power = sort(PSD, 'descend');
cumulative = cumsum(sorted_power) / sum(sorted_power) * 100;
plot(1:Nsc, cumulative, 'LineWidth', 2);
xlabel('Subcarrier Index (sorted by power)');
ylabel('Cumulative Power (%)');
title('Power Concentration');
grid on;
yline(90, 'r--', '90% of power');

fprintf('  ✓ All plots created\n');

%% Save results (REFACTORED)
fprintf('\nSaving results...\n');

% Create results directory
results_dir = ExperimentUtils.createResultsDir('exp04');

% Ensure figure is current and save
figure(fig);
ExperimentUtils.saveFigures(gcf, 'frequency_response', results_dir);

% Save results to dedicated timestamped folder
timestamp = datestr(now, 'yyyy-mm-dd_HH-MM-SS');
results_base_dir = fullfile(fileparts(fileparts(mfilename('fullpath'))), '..', 'results');
results_dir = fullfile(results_base_dir, ['exp04_' timestamp]);
if ~exist(results_dir, 'dir')
    mkdir(results_dir);
end

% Save plots
png_path = fullfile(results_dir, 'frequency_response.png');
fig_path = fullfile(results_dir, 'frequency_response.fig');
current_fig = gcf;
saveas(current_fig, png_path);
savefig(current_fig, fig_path);

% Calculate statistics
stats = ExperimentUtils.calculateChannelStats(h_t, tau_ns);

% Create comprehensive text report
fid = ExperimentUtils.createReportHeader(results_dir, 'EXPERIMENT 04: Frequency Response Analysis');

% Write simulation parameters
params.bandwidth = BW;
params.num_subcarriers = Nsc;
ExperimentUtils.writeSimParams(fid, params);

fprintf(fid, '--- CHANNEL CHARACTERISTICS ---\n');
fprintf(fid, 'Number of Multipath Taps: %d\n', stats.num_taps);
fprintf(fid, 'Delay Spread: %.2f ns (min) to %.2f ns (max)\n', stats.delay_range_ns(1), stats.delay_range_ns(2));
fprintf(fid, 'RMS Delay Spread: %.2f ns\n', stats.rms_delay_spread_ns);
fprintf(fid, 'Path Loss: %.2f dB\n\n', stats.path_loss_dB);

fprintf(fid, '--- FREQUENCY DOMAIN ANALYSIS ---\n');
fprintf(fid, 'Bandwidth: %.2f MHz\n', BW/1e6);
fprintf(fid, 'Number of Subcarriers: %d\n', Nsc);
fprintf(fid, 'Subcarrier Spacing: %.2f kHz\n', BW/Nsc/1e3);
fprintf(fid, 'Frequency Range: %.2f to %.2f MHz\n\n', min(fvec)/1e6, max(fvec)/1e6);

fprintf(fid, '--- FREQUENCY SELECTIVITY ---\n');
fprintf(fid, 'Number of Peaks: %d\n', length(peaks));
fprintf(fid, 'Number of Nulls: %d\n', length(nulls));
fprintf(fid, 'Dynamic Range: %.2f dB\n', max(H_dB) - min(H_dB));
fprintf(fid, 'Max Channel Gain: %.2f dB at %.2f MHz\n', max(H_dB), fvec(find(H_mag == max(H_mag), 1))/1e6);
fprintf(fid, 'Min Channel Gain: %.2f dB at %.2f MHz\n', min(H_dB), fvec(find(H_mag == min(H_mag), 1))/1e6);
if ~isempty(coherence_idx)
    fprintf(fid, 'Coherence Bandwidth: ~%.2f MHz\n\n', coherence_BW);
else
    fprintf(fid, 'Coherence Bandwidth: > %.2f MHz (flat fading)\n\n', BW/1e6);
end

fprintf(fid, '--- POWER ANALYSIS ---\n');
fprintf(fid, 'Total Power: %.2e\n', sum(PSD));
fprintf(fid, 'Peak Power: %.2e at subcarrier %d\n', max(PSD), find(PSD == max(PSD), 1));
fprintf(fid, 'Average Power per Subcarrier: %.2e\n', mean(PSD));
fprintf(fid, 'Power Std Dev: %.2e\n\n', std(PSD));

fprintf(fid, '--- KEY INSIGHTS ---\n');
fprintf(fid, '• Time-domain: %d discrete multipath taps\n', length(h_t));
fprintf(fid, '• Frequency-domain: %d subcarriers spanning %.2f MHz\n', Nsc, BW/1e6);
fprintf(fid, '• Frequency-selective fading with %.2f dB dynamic range\n', max(H_dB) - min(H_dB));
fprintf(fid, '• Channel varies significantly across frequency\n');
fprintf(fid, '• CSI pattern is unique to this UE position\n');
fprintf(fid, '• ML models can learn position from CSI features\n\n');

fprintf(fid, '--- ML RELEVANCE ---\n');
fprintf(fid, 'This experiment demonstrates how CSI varies across frequency.\n');
fprintf(fid, 'Different UE positions will produce different frequency patterns.\n');
fprintf(fid, 'Features for ML:\n');
fprintf(fid, '  - Channel gain statistics (mean, std, min, max)\n');
fprintf(fid, '  - Peak/null locations and magnitudes\n');
fprintf(fid, '  - Coherence bandwidth\n');
fprintf(fid, '  - Power distribution\n');
fprintf(fid, '  - Frequency correlation structure\n\n');

ExperimentUtils.closeReport(fid, {'frequency_response.png', 'frequency_response.fig', 'experiment_report.txt'});

fprintf('  ✓ Results saved to: %s\n', results_dir);
fprintf('     - frequency_response.png\n');
fprintf('     - frequency_response.fig\n');
fprintf('     - experiment_report.txt\n\n');

%% Step 5: Key insights
fprintf('========================================\n');
fprintf('KEY INSIGHTS\n');
fprintf('========================================\n');

fprintf('\nTime vs Frequency Domain:\n');
fprintf('  • Time: %d discrete taps\n', length(h_t));
fprintf('  • Frequency: %d subcarriers (continuous spectrum)\n', Nsc);

fprintf('\nFrequency Selectivity:\n');
fprintf('  • Dynamic range: %.2f dB\n', max(H_dB) - min(H_dB));
fprintf('  • Max gain: %.2f dB at %.2f MHz\n', max(H_dB), fvec(find(H_mag == max(H_mag), 1))/1e6);
fprintf('  • Min gain: %.2f dB at %.2f MHz\n', min(H_dB), fvec(find(H_mag == min(H_mag), 1))/1e6);

fprintf('\nWhy This Matters for ML:\n');
fprintf('  • Different frequencies experience different fading\n');
fprintf('  • CSI pattern changes with UE position\n');
fprintf('  • ML can learn position-to-CSI mapping\n');

fprintf('\n========================================\n');
fprintf('Key Takeaways:\n');
fprintf('  1. Time-domain taps → Frequency-domain CSI via FFT-like transform\n');
fprintf('  2. Frequency-selective fading: Different subcarriers = different gains\n');
fprintf('  3. Coherence bandwidth: Frequency range with similar fading\n');
fprintf('  4. More multipath → More frequency selectivity\n\n');
fprintf('Next: Run exp05_csi_metrics.m\n');
fprintf('========================================\n');
