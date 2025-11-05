%% EXPERIMENT 06: Parameter Effects
% Learn: How system parameters affect CSI and metrics
% Time: 20 minutes
%
% What you'll see:
% - Effect of bandwidth on frequency selectivity
% - Effect of transmit power on SINR/CQI
% - Effect of noise figure on quality
% - Optimal parameter selection
%
% Expected output:
% - Comparison plots for different configurations
% - Understanding of parameter tradeoffs

clear; clc; close all;

% Add utils to path
utils_path = fullfile(fileparts(fileparts(mfilename('fullpath'))), '..', 'utils');
addpath(utils_path);

fprintf('========================================\n');
fprintf('EXPERIMENT 06: Parameter Effects\n');
fprintf('========================================\n\n');

%% Create results directory
results_dir = ExperimentUtils.createResultsDir('exp06');

%% Setup base configuration
s = qd_simulation_parameters;
s.center_frequency = 3.5e9;
s.sample_density = 2;
s.use_absolute_delays = 1;

l = qd_layout(s);
l.tx_position = [0; 0; 25];
l.tx_array = qd_arrayant('omni');
l.rx_position = [80; 0; 1.5];
l.rx_array = qd_arrayant('omni');
l.set_scenario('3GPP_38.901_UMa_LOS');

c = l.get_channels;
h_t = squeeze(c.coeff(1,1,:,1));
tau = squeeze(c.delay(1,:,1));

%% PART 1: Bandwidth Effects
fprintf('========================================\n');
fprintf('PART 1: Bandwidth Effects\n');
fprintf('========================================\n\n');

bandwidths = [20e6, 50e6, 100e6];  % MHz
BW_names = {'20 MHz', '50 MHz', '100 MHz'};
Nsc = 256;  % Keep constant

fig1 = figure('Name', 'Experiment 06 - Part 1: Bandwidth Effects', 'Position', [50 50 1400 500]);

for i = 1:length(bandwidths)
    BW = bandwidths(i);
    fvec = linspace(-BW/2, BW/2, Nsc);
    
    % Convert to frequency domain
    H_sc = zeros(1, 1, Nsc);
    for k = 1:Nsc
        H_sc(1,1,k) = sum(h_t .* exp(-1j * 2*pi * fvec(k) .* tau));
    end
    
    H_mag = abs(squeeze(H_sc));
    H_dB = 20*log10(H_mag + eps);
    
    % Compute metrics
    m = CSIMetrics('SubcarrierSpacing', BW/Nsc, 'TxPowerPerSC_dBm', 0, 'NoiseFigure_dB', 7);
    out = m.compute(H_sc);
    
    fprintf('Bandwidth: %s\n', BW_names{i});
    fprintf('  Subcarrier spacing: %.2f kHz\n', BW/Nsc/1e3);
    fprintf('  Frequency selectivity (std of |H|): %.4f\n', std(H_mag));
    fprintf('  SINR range: [%.2f, %.2f] dB\n', min(out.SINR_dB_sc), max(out.SINR_dB_sc));
    fprintf('  CQI wideband: %d\n\n', out.CQI_wb);
    
    % Plot
    subplot(1, 3, i);
    plot(1:Nsc, H_dB, 'LineWidth', 1.5);
    xlabel('Subcarrier Index');
    ylabel('|H(f)| (dB)');
    title(sprintf('%s (SCS: %.1f kHz)', BW_names{i}, BW/Nsc/1e3));
    grid on;
    ylim([min(H_dB(:))-5, max(H_dB(:))+5]);
end

% Save Part 1 figure
figure(fig1);
ExperimentUtils.saveFigures(gcf, 'part1_bandwidth_effects', results_dir);

fprintf('Observation:\n');
fprintf('  • Wider BW → More frequency-selective fading\n');
fprintf('  • Wider BW → Larger subcarrier spacing\n');
fprintf('  • Wider BW → More variation in channel gain\n\n');

%% PART 2: Transmit Power Effects
fprintf('========================================\n');
fprintf('PART 2: Transmit Power Effects\n');
fprintf('========================================\n\n');

tx_powers = [-10, 0, 10, 20];  % dBm per subcarrier
BW = 100e6;
fvec = linspace(-BW/2, BW/2, Nsc);

H_sc = zeros(1, 1, Nsc);
for k = 1:Nsc
    H_sc(1,1,k) = sum(h_t .* exp(-1j * 2*pi * fvec(k) .* tau));
end

RSS_vs_power = zeros(size(tx_powers));
SINR_vs_power = zeros(size(tx_powers));
CQI_vs_power = zeros(size(tx_powers));

fig2 = figure('Name', 'Experiment 06 - Part 2: Transmit Power', 'Position', [100 100 1200 400]);

fprintf('Testing different transmit powers...\n');
for i = 1:length(tx_powers)
    m = CSIMetrics('SubcarrierSpacing', BW/Nsc, ...
                   'TxPowerPerSC_dBm', tx_powers(i), ...
                   'NoiseFigure_dB', 7);
    out = m.compute(H_sc);
    
    RSS_vs_power(i) = out.RSS_dBm_wb;
    SINR_vs_power(i) = out.SINR_dB_wb;
    CQI_vs_power(i) = out.CQI_wb;
    
    fprintf('  Tx Power: %+3d dBm → RSS: %6.2f dBm, SINR: %6.2f dB, CQI: %2d\n', ...
        tx_powers(i), RSS_vs_power(i), SINR_vs_power(i), CQI_vs_power(i));
end
fprintf('\n');

subplot(1, 3, 1);
plot(tx_powers, RSS_vs_power, 'o-', 'LineWidth', 2, 'MarkerSize', 10);
xlabel('Tx Power (dBm/SC)');
ylabel('RSS (dBm)');
title('RSS vs Transmit Power');
grid on;

subplot(1, 3, 2);
plot(tx_powers, SINR_vs_power, 'o-', 'LineWidth', 2, 'MarkerSize', 10);
xlabel('Tx Power (dBm/SC)');
ylabel('SINR (dB)');
title('SINR vs Transmit Power');
grid on;

subplot(1, 3, 3);
stairs(tx_powers, CQI_vs_power, 'o-', 'LineWidth', 2, 'MarkerSize', 10);
xlabel('Tx Power (dBm/SC)');
ylabel('CQI (0-15)');
title('CQI vs Transmit Power');
grid on;
ylim([-0.5, 15.5]);

% Save Part 2 figure
figure(fig2);
ExperimentUtils.saveFigures(gcf, 'part2_transmit_power', results_dir);

fprintf('Observation:\n');
fprintf('  • Higher Tx power → Higher RSS (linear relationship)\n');
fprintf('  • Higher Tx power → Higher SINR → Better CQI\n');
fprintf('  • CQI saturates at 15 (max quality)\n\n');

%% PART 3: Noise Figure Effects
fprintf('========================================\n');
fprintf('PART 3: Noise Figure Effects\n');
fprintf('========================================\n\n');

noise_figures = [3, 7, 10, 15];  % dB
SINR_vs_NF = zeros(size(noise_figures));
CQI_vs_NF = zeros(size(noise_figures));

fig3 = figure('Name', 'Experiment 06 - Part 3: Noise Figure', 'Position', [150 150 1000 400]);

fprintf('Testing different noise figures...\n');
for i = 1:length(noise_figures)
    m = CSIMetrics('SubcarrierSpacing', BW/Nsc, ...
                   'TxPowerPerSC_dBm', 0, ...
                   'NoiseFigure_dB', noise_figures(i));
    out = m.compute(H_sc);
    
    SINR_vs_NF(i) = out.SINR_dB_wb;
    CQI_vs_NF(i) = out.CQI_wb;
    
    fprintf('  NF: %2d dB → SINR: %6.2f dB, CQI: %2d\n', ...
        noise_figures(i), SINR_vs_NF(i), CQI_vs_NF(i));
end
fprintf('\n');

subplot(1, 2, 1);
plot(noise_figures, SINR_vs_NF, 'o-', 'LineWidth', 2, 'MarkerSize', 10, 'Color', [0.8 0.3 0.3]);
xlabel('Noise Figure (dB)');
ylabel('SINR (dB)');
title('SINR vs Noise Figure');
grid on;

subplot(1, 2, 2);
stairs(noise_figures, CQI_vs_NF, 'o-', 'LineWidth', 2, 'MarkerSize', 10, 'Color', [0.3 0.6 0.8]);
xlabel('Noise Figure (dB)');
ylabel('CQI (0-15)');
title('CQI vs Noise Figure');
grid on;
ylim([-0.5, 15.5]);

% Save Part 3 figure
figure(fig3);
ExperimentUtils.saveFigures(gcf, 'part3_noise_figure', results_dir);

fprintf('Observation:\n');
fprintf('  • Higher NF → More noise → Lower SINR\n');
fprintf('  • Higher NF → Worse CQI\n');
fprintf('  • Typical UE: NF = 7-9 dB\n');
fprintf('  • High-quality UE: NF = 3-5 dB\n\n');

%% PART 4: Combined Effects (Scenario Comparison)
fprintf('========================================\n');
fprintf('PART 4: Scenario Comparison\n');
fprintf('========================================\n\n');

scenarios = {
    struct('name', 'Ideal', 'BW', 100e6, 'TxPower', 20, 'NF', 3),
    struct('name', 'Typical', 'BW', 100e6, 'TxPower', 0, 'NF', 7),
    struct('name', 'Challenging', 'BW', 20e6, 'TxPower', -10, 'NF', 10),
    struct('name', 'Extreme', 'BW', 20e6, 'TxPower', -20, 'NF', 15)
};

fprintf('Comparing different scenarios...\n');
fprintf('%-15s | BW (MHz) | Tx Power | NF (dB) | SINR (dB) | CQI\n', 'Scenario');
fprintf('------------------------------------------------------------------\n');

results = struct();
for i = 1:length(scenarios)
    sc = scenarios{i};
    BW = sc.BW;
    Nsc_temp = 256;
    fvec = linspace(-BW/2, BW/2, Nsc_temp);
    
    H_sc_temp = zeros(1, 1, Nsc_temp);
    for k = 1:Nsc_temp
        H_sc_temp(1,1,k) = sum(h_t .* exp(-1j * 2*pi * fvec(k) .* tau));
    end
    
    m = CSIMetrics('SubcarrierSpacing', BW/Nsc_temp, ...
                   'TxPowerPerSC_dBm', sc.TxPower, ...
                   'NoiseFigure_dB', sc.NF);
    out = m.compute(H_sc_temp);
    
    results(i).name = sc.name;
    results(i).SINR = out.SINR_dB_wb;
    results(i).CQI = out.CQI_wb;
    
    fprintf('%-15s | %8.0f | %+8d | %7d | %9.2f | %3d\n', ...
        sc.name, sc.BW/1e6, sc.TxPower, sc.NF, out.SINR_dB_wb, out.CQI_wb);
end
fprintf('\n');

% Visualization
fig4 = figure('Name', 'Experiment 06 - Part 4: Scenario Comparison', 'Position', [200 200 800 500]);
scenario_names = {results.name};
SINR_vals = [results.SINR];
CQI_vals = [results.CQI];

subplot(1, 2, 1);
bar(SINR_vals);
set(gca, 'XTickLabel', scenario_names);
ylabel('SINR (dB)');
title('SINR by Scenario');
grid on;

subplot(1, 2, 2);
bar(CQI_vals);
set(gca, 'XTickLabel', scenario_names);
ylabel('CQI (0-15)');
title('CQI by Scenario');
grid on;
ylim([0, 16]);

% Save Part 4 figure
figure(fig4);
ExperimentUtils.saveFigures(gcf, 'part4_scenario_comparison', results_dir);

%% Summary
fprintf('========================================\n');
fprintf('EXPERIMENT SUMMARY\n');
fprintf('========================================\n\n');

fprintf('Key Insights:\n');
fprintf('  1. BANDWIDTH:\n');
fprintf('     • Wider → More frequency selectivity\n');
fprintf('     • Affects subcarrier spacing\n');
fprintf('     • More data throughput potential\n\n');

fprintf('  2. TRANSMIT POWER:\n');
fprintf('     • Higher → Better SINR and CQI\n');
fprintf('     • But: Battery consumption increases\n');
fprintf('     • Regulatory limits apply\n\n');

fprintf('  3. NOISE FIGURE:\n');
fprintf('     • Lower → Better SINR (cleaner receiver)\n');
fprintf('     • Hardware quality matters\n');
fprintf('     • Typical UE: 7-9 dB\n\n');

fprintf('  4. TRADEOFFS:\n');
fprintf('     • Quality vs Power consumption\n');
fprintf('     • Bandwidth vs Hardware cost\n');
fprintf('     • Performance vs Device complexity\n\n');

fprintf('For ML Project:\n');
fprintf('  • Use consistent parameters across training\n');
fprintf('  • Typical config: 100 MHz, 0 dBm, 7 dB NF\n');
fprintf('  • Test robustness with parameter variations\n\n');

%% Save text report
fid = ExperimentUtils.createReportHeader(results_dir, 'EXPERIMENT 06: Parameter Effects');

fprintf(fid, 'CONFIGURATION\n');
fprintf(fid, '=============\n\n');
fprintf(fid, 'Base Configuration:\n');
fprintf(fid, '  Frequency: %.2f GHz\n', s.center_frequency/1e9);
fprintf(fid, '  Scenario: 3GPP_38.901_UMa_LOS\n');
fprintf(fid, '  Distance: 80 m\n');
fprintf(fid, '  Subcarriers: %d\n\n', Nsc);

fprintf(fid, 'PART 1: Bandwidth Effects\n');
fprintf(fid, '==========================\n\n');
fprintf(fid, 'Tested bandwidths: 20, 50, 100 MHz\n');
fprintf(fid, 'Observation: Wider BW → More frequency selectivity\n\n');

fprintf(fid, 'PART 2: Transmit Power Effects\n');
fprintf(fid, '==============================\n\n');
fprintf(fid, 'Tested powers: -10, 0, +10, +20 dBm per SC\n');
fprintf(fid, 'Result: Linear RSS increase with Tx power\n');
fprintf(fid, 'CQI saturates at 15 (maximum quality)\n\n');

fprintf(fid, 'PART 3: Noise Figure Effects\n');
fprintf(fid, '============================\n\n');
fprintf(fid, 'Tested NF: 3, 7, 10, 15 dB\n');
fprintf(fid, 'Result: Higher NF → Lower SINR and CQI\n');
fprintf(fid, 'Typical UE: 7-9 dB, High-quality: 3-5 dB\n\n');

fprintf(fid, 'PART 4: Scenario Comparison\n');
fprintf(fid, '===========================\n\n');
fprintf(fid, 'Scenarios tested:\n');
fprintf(fid, '  1. Ideal: 100MHz, +20dBm, 3dB NF\n');
fprintf(fid, '  2. Typical: 100MHz, 0dBm, 7dB NF\n');
fprintf(fid, '  3. Challenging: 20MHz, -10dBm, 10dB NF\n');
fprintf(fid, '  4. Extreme: 20MHz, -20dBm, 15dB NF\n\n');

fprintf(fid, 'KEY INSIGHTS\n');
fprintf(fid, '============\n\n');
fprintf(fid, '1. BANDWIDTH:\n');
fprintf(fid, '   - Wider → More frequency selectivity\n');
fprintf(fid, '   - Affects subcarrier spacing\n');
fprintf(fid, '   - More throughput potential\n\n');

fprintf(fid, '2. TRANSMIT POWER:\n');
fprintf(fid, '   - Higher → Better SINR and CQI\n');
fprintf(fid, '   - Battery consumption tradeoff\n');
fprintf(fid, '   - Regulatory limits apply\n\n');

fprintf(fid, '3. NOISE FIGURE:\n');
fprintf(fid, '   - Lower → Better SINR\n');
fprintf(fid, '   - Hardware quality matters\n');
fprintf(fid, '   - Typical: 7-9 dB\n\n');

fprintf(fid, '4. FOR ML PROJECT:\n');
fprintf(fid, '   - Use consistent parameters\n');
fprintf(fid, '   - Recommended: 100 MHz, 0 dBm, 7 dB NF\n');
fprintf(fid, '   - Test robustness with variations\n\n');

files_generated = {
    'part1_bandwidth_effects.png', 'part1_bandwidth_effects.fig', ...
    'part2_transmit_power.png', 'part2_transmit_power.fig', ...
    'part3_noise_figure.png', 'part3_noise_figure.fig', ...
    'part4_scenario_comparison.png', 'part4_scenario_comparison.fig'
};
ExperimentUtils.closeReport(fid, files_generated);

fprintf('Results saved to: %s\n\n', results_dir);

fprintf('========================================\n');
fprintf('✓ Level 2 Complete!\n');
fprintf('========================================\n');
fprintf('You''ve mastered:\n');
fprintf('  ✓ Frequency-domain CSI\n');
fprintf('  ✓ RSS, SINR, CQI calculations\n');
fprintf('  ✓ Parameter effects and tradeoffs\n\n');
fprintf('Next Level: experiments/03_ue_movement/\n');
fprintf('Learn to simulate moving UE and track CSI changes!\n');
fprintf('========================================\n');
