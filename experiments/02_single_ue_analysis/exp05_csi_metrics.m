%% EXPERIMENT 05: CSI Metrics (RSS, SINR, CQI)
% Learn: Calculate practical wireless metrics from CSI
% Time: 15 minutes
%
% What you'll see:
% - RSS (Received Signal Strength) in dBm
% - SINR (Signal-to-Interference-plus-Noise Ratio) in dB
% - CQI (Channel Quality Indicator) 0-15
% - How to use CSIMetrics class
%
% Expected output:
% - Metrics for each subcarrier and wideband
% - Understanding of quality thresholds

clear; clc; close all;

% Add utils to path
utils_path = fullfile(fileparts(fileparts(mfilename('fullpath'))), '..', 'utils');
addpath(utils_path);

fprintf('========================================\n');
fprintf('EXPERIMENT 05: CSI Metrics\n');
fprintf('========================================\n\n');

%% Step 1: Generate channel and compute frequency CSI (REFACTORED)
fprintf('Step 1: Generating channel...\n');

params = struct(...
    'center_frequency', 3.5e9, ...
    'rx_position', [75; 0; 1.5], ...
    'scenario', '3GPP_38.901_UMa_LOS', ...
    'use_absolute_delays', 1);

[h_t, tau_ns] = ExperimentUtils.generateChannel(params);
tau = tau_ns / 1e9;  % Convert to seconds

% Convert to frequency domain
BW = 100e6;
Nsc = 256;
fvec = linspace(-BW/2, BW/2, Nsc);

H_freq = ExperimentUtils.convertToFrequency(h_t, tau, fvec);
H_sc = reshape(H_freq, [1, 1, Nsc]);  % Reshape for CSIMetrics

fprintf('  ✓ Generated CSI for %d subcarriers\n\n', Nsc);

%% Step 2: Calculate metrics using CSIMetrics class
fprintf('Step 2: Calculating wireless metrics...\n');

% Create CSIMetrics object with configuration
m = CSIMetrics( ...
    'SubcarrierSpacing', BW/Nsc, ...      % Hz
    'TxPowerPerSC_dBm', 0, ...            % 0 dBm = 1 mW per subcarrier
    'NoiseFigure_dB', 7, ...              % Typical UE noise figure
    'InterfPerSC_dBm', -Inf, ...          % No interference
    'MIMOCombine', 'sumPow', ...          % SISO: just magnitude squared
    'RBSizeSC', 12);                      % 5G NR standard

% Compute all metrics
out = m.compute(H_sc);

fprintf('  ✓ Metrics computed\n\n');

%% Step 3: Display results
fprintf('========================================\n');
fprintf('WIDEBAND METRICS (Averaged over all subcarriers)\n');
fprintf('========================================\n');
fprintf('RSS (Received Signal Strength):\n');
fprintf('  %.2f dBm\n', out.RSS_dBm_wb);
fprintf('  Interpretation: Total received power\n\n');

fprintf('SINR (Signal-to-Interference-plus-Noise Ratio):\n');
fprintf('  %.2f dB\n', out.SINR_dB_wb);
fprintf('  Interpretation:\n');
if out.SINR_dB_wb > 20
    fprintf('    → Excellent channel (>20 dB)\n');
elseif out.SINR_dB_wb > 10
    fprintf('    → Good channel (10-20 dB)\n');
elseif out.SINR_dB_wb > 0
    fprintf('    → Fair channel (0-10 dB)\n');
else
    fprintf('    → Poor channel (<0 dB)\n');
end
fprintf('\n');

fprintf('CQI (Channel Quality Indicator):\n');
fprintf('  %d (scale 0-15)\n', out.CQI_wb);
fprintf('  Interpretation:\n');
fprintf('    0-3:   Very poor (QPSK, low code rate)\n');
fprintf('    4-9:   Fair to good (QPSK/16QAM)\n');
fprintf('    10-15: Excellent (64QAM/256QAM, high code rate)\n\n');

%% Step 4: Per-subcarrier analysis
fprintf('========================================\n');
fprintf('PER-SUBCARRIER STATISTICS\n');
fprintf('========================================\n');

RSS_sc = out.RSS_dBm_sc;
SINR_sc = out.SINR_dB_sc;
CQI_sc = out.CQI_sc;

fprintf('RSS per subcarrier:\n');
fprintf('  Mean: %.2f dBm\n', mean(RSS_sc));
fprintf('  Min:  %.2f dBm (subcarrier %d)\n', min(RSS_sc), find(RSS_sc == min(RSS_sc), 1));
fprintf('  Max:  %.2f dBm (subcarrier %d)\n\n', max(RSS_sc), find(RSS_sc == max(RSS_sc), 1));

fprintf('SINR per subcarrier:\n');
fprintf('  Mean: %.2f dB\n', mean(SINR_sc));
fprintf('  Std:  %.2f dB (variation due to frequency selectivity)\n', std(SINR_sc));
fprintf('  Min:  %.2f dB (subcarrier %d)\n', min(SINR_sc), find(SINR_sc == min(SINR_sc), 1));
fprintf('  Max:  %.2f dB (subcarrier %d)\n\n', max(SINR_sc), find(SINR_sc == max(SINR_sc), 1));

fprintf('CQI per subcarrier:\n');
fprintf('  Mode (most common): %d\n', mode(CQI_sc));
fprintf('  Range: %d to %d\n', min(CQI_sc), max(CQI_sc));
fprintf('  Variation: %.2f CQI units (std)\n\n', std(double(CQI_sc)));

%% Step 5: Visualizations
fprintf('Creating visualizations...\n');

fig1 = ExperimentUtils.createFigure('Experiment 05 - CSI Metrics', 'square');

% Plot 1: RSS per subcarrier
subplot(3, 3, 1);
plot(1:Nsc, RSS_sc, 'LineWidth', 1.5);
xlabel('Subcarrier Index');
ylabel('RSS (dBm)');
title('Received Signal Strength per Subcarrier');
grid on;
yline(mean(RSS_sc), 'r--', 'Mean');

% Plot 2: SINR per subcarrier
subplot(3, 3, 2);
plot(1:Nsc, SINR_sc, 'LineWidth', 1.5);
xlabel('Subcarrier Index');
ylabel('SINR (dB)');
title('SINR per Subcarrier');
grid on;
yline(mean(SINR_sc), 'r--', 'Mean');
yline(0, 'k--', 'SINR = 0 dB');

% Plot 3: CQI per subcarrier
subplot(3, 3, 3);
stairs(1:Nsc, CQI_sc, 'LineWidth', 1.5);
xlabel('Subcarrier Index');
ylabel('CQI (0-15)');
title('Channel Quality Indicator per Subcarrier');
grid on;
ylim([-0.5, 15.5]);
yline(out.CQI_wb, 'r--', 'Wideband CQI');

% Plot 4: CQI histogram
subplot(3, 3, 4);
histogram(CQI_sc, 'BinEdges', -0.5:1:15.5, 'FaceColor', [0.3 0.6 0.8]);
xlabel('CQI Value');
ylabel('Number of Subcarriers');
title('CQI Distribution');
grid on;

% Plot 5: SINR histogram
subplot(3, 3, 5);
histogram(SINR_sc, 30, 'FaceColor', [0.3 0.8 0.6]);
xlabel('SINR (dB)');
ylabel('Count');
title('SINR Distribution');
grid on;
xline(mean(SINR_sc), 'r--', 'Mean', 'LineWidth', 2);

% Plot 6: RSS vs SINR scatter
subplot(3, 3, 6);
scatter(RSS_sc, SINR_sc, 30, 1:Nsc, 'filled');
xlabel('RSS (dBm)');
ylabel('SINR (dB)');
title('RSS vs SINR per Subcarrier');
colorbar;
grid on;

% Plot 7: CQI thresholds
subplot(3, 3, 7);
CQI_thresholds = m.CQIThresholds_dB;
bar(0:15, CQI_thresholds);
xlabel('CQI Value');
ylabel('SINR Threshold (dB)');
title('CQI Mapping (SINR Thresholds)');
grid on;
yline(out.SINR_dB_wb, 'r--', sprintf('Your SINR: %.1f dB', out.SINR_dB_wb), 'LineWidth', 2);

% Plot 8: Per-RB CQI
subplot(3, 3, 8);
NRB = size(out.CQI_RB, 1);
stairs(1:NRB, out.CQI_RB, 'LineWidth', 2);
xlabel('Resource Block (RB) Index');
ylabel('CQI (0-15)');
title(sprintf('CQI per RB (12 subcarriers/RB, %d RBs total)', NRB));
grid on;
ylim([-0.5, 15.5]);

% Plot 9: Summary text
subplot(3, 3, 9);
axis off;
summary_text = sprintf([...
    'SUMMARY\n\n' ...
    'Wideband:\n' ...
    '  RSS:  %.1f dBm\n' ...
    '  SINR: %.1f dB\n' ...
    '  CQI:  %d\n\n' ...
    'Per-Subcarrier:\n' ...
    '  SINR range: [%.1f, %.1f] dB\n' ...
    '  CQI range:  [%d, %d]\n\n' ...
    'Configuration:\n' ...
    '  BW: %.0f MHz\n' ...
    '  Subcarriers: %d\n' ...
    '  RBs: %d\n' ...
    '  Tx Power: %d dBm/SC\n' ...
    '  NF: %d dB'], ...
    out.RSS_dBm_wb, out.SINR_dB_wb, out.CQI_wb, ...
    min(SINR_sc), max(SINR_sc), min(CQI_sc), max(CQI_sc), ...
    BW/1e6, Nsc, NRB, m.TxPowerPerSC_dBm, m.NoiseFigure_dB);
text(0.1, 0.5, summary_text, 'FontSize', 10, 'FontName', 'Courier', ...
    'VerticalAlignment', 'middle');

fprintf('  ✓ All plots created\n\n');

%% Step 6: Experiment with different distances
fprintf('========================================\n');
fprintf('BONUS: Effect of Distance on Metrics\n');
fprintf('========================================\n');

distances = [25, 50, 100, 150];
RSS_vs_dist = zeros(1, length(distances));
SINR_vs_dist = zeros(1, length(distances));
CQI_vs_dist = zeros(1, length(distances));

fprintf('Testing different distances...\n');
for i = 1:length(distances)
    % Generate channel at distance (REFACTORED)
    params_temp = params;
    params_temp.rx_position = [distances(i); 0; 1.5];
    
    [h_t_temp, tau_ns_temp] = ExperimentUtils.generateChannel(params_temp);
    H_freq_temp = ExperimentUtils.convertToFrequency(h_t_temp, tau_ns_temp/1e9, fvec);
    H_sc_temp = reshape(H_freq_temp, [1, 1, Nsc]);
    
    out_temp = m.compute(H_sc_temp);
    RSS_vs_dist(i) = out_temp.RSS_dBm_wb;
    SINR_vs_dist(i) = out_temp.SINR_dB_wb;
    CQI_vs_dist(i) = out_temp.CQI_wb;
end

fprintf('\nDistance vs Metrics:\n');
fprintf('  Dist (m)  |  RSS (dBm)  |  SINR (dB)  |  CQI\n');
fprintf('  -----------------------------------------------\n');
for i = 1:length(distances)
    fprintf('  %6d    |   %7.2f   |   %7.2f   |  %3d\n', ...
        distances(i), RSS_vs_dist(i), SINR_vs_dist(i), CQI_vs_dist(i));
end

% Plot distance effect
fig2 = ExperimentUtils.createFigure('Experiment 05 - Distance Effect', 'wide');

subplot(1, 3, 1);
plot(distances, RSS_vs_dist, 'o-', 'LineWidth', 2, 'MarkerSize', 10);
xlabel('Distance (m)');
ylabel('RSS (dBm)');
title('RSS vs Distance');
grid on;

subplot(1, 3, 2);
plot(distances, SINR_vs_dist, 'o-', 'LineWidth', 2, 'MarkerSize', 10);
xlabel('Distance (m)');
ylabel('SINR (dB)');
title('SINR vs Distance');
grid on;

subplot(1, 3, 3);
stairs(distances, CQI_vs_dist, 'o-', 'LineWidth', 2, 'MarkerSize', 10);
xlabel('Distance (m)');
ylabel('CQI (0-15)');
title('CQI vs Distance');
grid on;
ylim([-0.5, 15.5]);

%% Save results (REFACTORED)
fprintf('\nSaving results...\n');

% Create results directory
results_dir = ExperimentUtils.createResultsDir('exp05');

% Ensure figures are current and save
figure(fig1);
current_fig1 = gcf;
figure(fig2);
current_fig2 = gcf;
ExperimentUtils.saveFigures({current_fig1, current_fig2}, {'csi_metrics', 'distance_effect'}, results_dir);

% Create report
fid = ExperimentUtils.createReportHeader(results_dir, 'EXPERIMENT 05: CSI Metrics (RSS, SINR, CQI)');

% Write simulation parameters
params.bandwidth = BW;
params.num_subcarriers = Nsc;
ExperimentUtils.writeSimParams(fid, params);

fprintf(fid, '--- CSI METRICS CONFIGURATION ---\n');
fprintf(fid, 'Tx Power per Subcarrier: %d dBm\n', m.TxPowerPerSC_dBm);
fprintf(fid, 'Noise Figure: %d dB\n', m.NoiseFigure_dB);
fprintf(fid, 'Interference Power: %s dBm\n', num2str(m.InterfPerSC_dBm));
fprintf(fid, 'MIMO Combining: %s\n', m.MIMOCombine);
fprintf(fid, 'RB Size: %d subcarriers\n', m.RBSizeSC);
fprintf(fid, 'Number of RBs: %d\n\n', size(out.CQI_RB, 1));

fprintf(fid, '--- WIDEBAND METRICS ---\n');
fprintf(fid, 'RSS (Received Signal Strength): %.2f dBm\n', out.RSS_dBm_wb);
fprintf(fid, 'SINR (Signal-to-Interference-plus-Noise): %.2f dB\n', out.SINR_dB_wb);
fprintf(fid, 'CQI (Channel Quality Indicator): %d (scale 0-15)\n\n', out.CQI_wb);

fprintf(fid, 'SINR Quality Assessment:\n');
if out.SINR_dB_wb > 20
    fprintf(fid, '  → Excellent channel (>20 dB): High data rates possible\n');
elseif out.SINR_dB_wb > 10
    fprintf(fid, '  → Good channel (10-20 dB): Moderate to high data rates\n');
elseif out.SINR_dB_wb > 0
    fprintf(fid, '  → Fair channel (0-10 dB): Basic data rates\n');
else
    fprintf(fid, '  → Poor channel (<0 dB): Limited connectivity\n');
end
fprintf(fid, '\nCQI Interpretation:\n');
fprintf(fid, '  0-3:   Very poor (QPSK, low code rate)\n');
fprintf(fid, '  4-9:   Fair to good (QPSK/16QAM)\n');
fprintf(fid, '  10-15: Excellent (64QAM/256QAM, high code rate)\n\n');

fprintf(fid, '--- PER-SUBCARRIER STATISTICS ---\n');
fprintf(fid, 'RSS per Subcarrier:\n');
fprintf(fid, '  Mean: %.2f dBm\n', mean(RSS_sc));
fprintf(fid, '  Std:  %.2f dBm\n', std(RSS_sc));
fprintf(fid, '  Min:  %.2f dBm (subcarrier %d)\n', min(RSS_sc), find(RSS_sc == min(RSS_sc), 1));
fprintf(fid, '  Max:  %.2f dBm (subcarrier %d)\n\n', max(RSS_sc), find(RSS_sc == max(RSS_sc), 1));

fprintf(fid, 'SINR per Subcarrier:\n');
fprintf(fid, '  Mean: %.2f dB\n', mean(SINR_sc));
fprintf(fid, '  Std:  %.2f dB (frequency selectivity)\n', std(SINR_sc));
fprintf(fid, '  Min:  %.2f dB (subcarrier %d)\n', min(SINR_sc), find(SINR_sc == min(SINR_sc), 1));
fprintf(fid, '  Max:  %.2f dB (subcarrier %d)\n\n', max(SINR_sc), find(SINR_sc == max(SINR_sc), 1));

fprintf(fid, 'CQI per Subcarrier:\n');
fprintf(fid, '  Mode: %d (most common)\n', mode(CQI_sc));
fprintf(fid, '  Mean: %.2f\n', mean(double(CQI_sc)));
fprintf(fid, '  Std:  %.2f\n', std(double(CQI_sc)));
fprintf(fid, '  Min:  %d (subcarrier %d)\n', min(CQI_sc), find(CQI_sc == min(CQI_sc), 1));
fprintf(fid, '  Max:  %d (subcarrier %d)\n\n', max(CQI_sc), find(CQI_sc == max(CQI_sc), 1));

fprintf(fid, '--- DISTANCE ANALYSIS ---\n');
fprintf(fid, 'Tested Distances: %s m\n\n', mat2str(distances));
fprintf(fid, 'Distance (m) | RSS (dBm) | SINR (dB) | CQI\n');
fprintf(fid, '-------------------------------------------\n');
for i = 1:length(distances)
    fprintf(fid, '    %6d   |  %7.2f  |  %7.2f  | %3d\n', ...
        distances(i), RSS_vs_dist(i), SINR_vs_dist(i), CQI_vs_dist(i));
end
fprintf(fid, '\nObservations:\n');
fprintf(fid, '  RSS degradation (25m to 150m): %.2f dB\n', RSS_vs_dist(1) - RSS_vs_dist(end));
fprintf(fid, '  SINR degradation (25m to 150m): %.2f dB\n', SINR_vs_dist(1) - SINR_vs_dist(end));
fprintf(fid, '  CQI degradation (25m to 150m): %d levels\n\n', CQI_vs_dist(1) - CQI_vs_dist(end));

fprintf(fid, '--- KEY INSIGHTS ---\n');
fprintf(fid, '• RSS measures total received power (path loss)\n');
fprintf(fid, '• SINR determines achievable data rate (signal quality)\n');
fprintf(fid, '• CQI provides discrete quality levels (0-15) for scheduling\n');
fprintf(fid, '• Metrics vary across subcarriers due to frequency selectivity\n');
fprintf(fid, '• All metrics degrade monotonically with distance\n');
fprintf(fid, '• CSIMetrics class automates industry-standard calculations\n\n');

fprintf(fid, '--- ML RELEVANCE ---\n');
fprintf(fid, 'These metrics are essential features for ML-based positioning:\n');
fprintf(fid, '\nFeatures for Location Prediction:\n');
fprintf(fid, '  - Wideband RSS/SINR/CQI (overall signal quality)\n');
fprintf(fid, '  - Per-subcarrier statistics (mean, std, min, max)\n');
fprintf(fid, '  - CQI distribution (histogram, mode, range)\n');
fprintf(fid, '  - SINR dynamic range (max - min)\n');
fprintf(fid, '  - RSS vs SINR correlation\n');
fprintf(fid, '  - Per-RB CQI pattern\n\n');

fprintf(fid, 'Why These Metrics Matter:\n');
fprintf(fid, '  1. RSS ∝ 1/distance² (path loss) → distance estimation\n');
fprintf(fid, '  2. SINR pattern varies with position → spatial fingerprint\n');
fprintf(fid, '  3. CQI distribution reveals multipath richness\n');
fprintf(fid, '  4. Frequency selectivity indicates scattering environment\n\n');

ExperimentUtils.closeReport(fid, {'csi_metrics.png', 'csi_metrics.fig', ...
    'distance_effect.png', 'distance_effect.fig', 'experiment_report.txt'});

fprintf('  ✓ Results saved to: %s\n', results_dir);
fprintf('     - csi_metrics.png\n');
fprintf('     - csi_metrics.fig\n');
fprintf('     - distance_effect.png\n');
fprintf('     - distance_effect.fig\n');
fprintf('     - experiment_report.txt\n');

fprintf('\n========================================\n');
fprintf('Key Takeaways:\n');
fprintf('  1. RSS: Received power decreases with distance\n');
fprintf('  2. SINR: Signal-to-Noise ratio (determines data rate)\n');
fprintf('  3. CQI: Quantized quality metric (0-15 for scheduling)\n');
fprintf('  4. CSIMetrics class automates calculations\n');
fprintf('  5. Metrics vary per subcarrier (frequency selectivity)\n');
fprintf('  6. All metrics degrade with increasing distance\n\n');
fprintf('Next: Run exp06_parameter_effects.m\n');
fprintf('========================================\n');
