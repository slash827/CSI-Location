%% EXPERIMENT 03: LOS vs NLOS Comparison
% Learn: How obstacles affect CSI (Line of Sight vs Non-Line of Sight)
% Time: 10 minutes
%
% What you'll see:
% - LOS: Strong first tap, few reflections
% - NLOS: Power spread across many taps (rich scattering)
% - Higher delay spread in NLOS
%
% Expected output:
% - Side-by-side comparison plots
% - Delay spread statistics

clear; clc; close all;

% Add utils to path
utils_path = fullfile(fileparts(fileparts(mfilename('fullpath'))), '..', 'utils');
addpath(utils_path);

fprintf('========================================\n');
fprintf('EXPERIMENT 03: LOS vs NLOS Comparison\n');
fprintf('========================================\n\n');

%% Setup
scenarios = {'3GPP_38.901_UMa_LOS', '3GPP_38.901_UMa_NLOS'};
scenario_names = {'Line of Sight (LOS)', 'Non-Line of Sight (NLOS)'};
H_scenarios = cell(1, 2);
delays_scenarios = cell(1, 2);
stats_scenarios = cell(1, 2);

%% Create figure
fig = ExperimentUtils.createFigure('Experiment 03 - LOS vs NLOS', 'square');

%% Run both scenarios (REFACTORED - cleaner with utilities)
for idx = 1:2
    fprintf('=== %s ===\n', scenario_names{idx});
    
    % Generate channel using utility
    params = struct(...
        'center_frequency', 3.5e9, ...
        'rx_position', [75; 0; 1.5], ...
        'scenario', scenarios{idx}, ...
        'use_absolute_delays', 1);
    
    [H_scenarios{idx}, delays_scenarios{idx}] = ExperimentUtils.generateChannel(params);
    
    % Calculate statistics
    stats_scenarios{idx} = ExperimentUtils.calculateChannelStats(H_scenarios{idx}, delays_scenarios{idx});
    
    fprintf('  Number of taps: %d\n', stats_scenarios{idx}.num_taps);
    fprintf('  Path loss: %.2f dB\n', stats_scenarios{idx}.path_loss_dB);
    fprintf('  RMS delay spread: %.2f ns\n', stats_scenarios{idx}.rms_delay_spread_ns);
    fprintf('  Dominant tap power: %.1f%% of total\n\n', ...
        stats_scenarios{idx}.dominant_tap_ratio * 100);
    
    % Plot 1: Impulse response
    subplot(3, 2, idx);
    stem(1:length(H_scenarios{idx}), abs(H_scenarios{idx}), 'LineWidth', 2);
    xlabel('Tap Index');
    ylabel('|h|');
    title(sprintf('%s - Impulse Response', scenario_names{idx}));
    grid on;
    
    % Plot 2: Power delay profile
    subplot(3, 2, 2 + idx);
    stem(delays_scenarios{idx}, abs(H_scenarios{idx}), 'LineWidth', 2);
    xlabel('Delay (ns)');
    ylabel('|h|');
    title(sprintf('%s - Delay Profile', scenario_names{idx}));
    grid on;
    
    % Plot 3: Power in dB
    subplot(3, 2, 4 + idx);
    power_profile = abs(H_scenarios{idx}).^2;
    power_dB = 10*log10(power_profile);
    stem(1:length(power_dB), power_dB, 'LineWidth', 2);
    xlabel('Tap Index');
    ylabel('Power (dB)');
    title(sprintf('%s - Power Profile', scenario_names{idx}));
    grid on;
end

%% Direct comparison
fprintf('========================================\n');
fprintf('COMPARISON SUMMARY\n');
fprintf('========================================\n');

% Power distribution
power_LOS = abs(H_scenarios{1}).^2;
power_NLOS = abs(H_scenarios{2}).^2;

fprintf('Power Distribution:\n');
fprintf('  LOS - Dominant tap:  %.1f%% of total\n', 100*max(power_LOS)/sum(power_LOS));
fprintf('  NLOS - Dominant tap: %.1f%% of total\n', 100*max(power_NLOS)/sum(power_NLOS));

fprintf('\nDelay Spread:\n');
fprintf('  LOS:  %.2f ns (small - paths arrive close in time)\n', ...
    std(delays_scenarios{1}));
fprintf('  NLOS: %.2f ns (large - paths widely spread)\n', ...
    std(delays_scenarios{2}));

fprintf('\nNumber of Significant Taps (>10%% max power):\n');
fprintf('  LOS:  %d taps\n', sum(power_LOS > 0.1*max(power_LOS)));
fprintf('  NLOS: %d taps\n', sum(power_NLOS > 0.1*max(power_NLOS)));

%% Save results (REFACTORED)
fprintf('\nSaving results...\n');

% Create results directory
results_dir = ExperimentUtils.createResultsDir('exp03');

% Ensure figure is current and save
figure(fig);
ExperimentUtils.saveFigures(gcf, 'los_vs_nlos', results_dir);

% Create report
fid = ExperimentUtils.createReportHeader(results_dir, 'EXPERIMENT 03: LOS vs NLOS Comparison');

% Write simulation parameters
params = struct(...
    'center_frequency', 3.5e9, ...
    'sample_density', 2, ...
    'tx_position', [0; 0; 25], ...
    'rx_position', [75; 0; 1.5]);

ExperimentUtils.writeSimParams(fid, params);

% Get statistics (already calculated)
power_LOS = abs(H_scenarios{1}).^2;
power_NLOS = abs(H_scenarios{2}).^2;

fprintf(fid, '--- LINE OF SIGHT (LOS) ---\n');
fprintf(fid, 'Scenario: 3GPP_38.901_UMa_LOS\n');
fprintf(fid, 'Number of Taps: %d\n', stats_scenarios{1}.num_taps);
fprintf(fid, 'Path Loss: %.2f dB\n', stats_scenarios{1}.path_loss_dB);
fprintf(fid, 'RMS Delay Spread: %.2f ns\n', stats_scenarios{1}.rms_delay_spread_ns);
fprintf(fid, 'Dominant Tap Power: %.1f%% of total\n', stats_scenarios{1}.dominant_tap_ratio*100);
fprintf(fid, 'Significant Taps (>10%% max): %d\n\n', sum(power_LOS > 0.1*max(power_LOS)));

fprintf(fid, '--- NON-LINE OF SIGHT (NLOS) ---\n');
fprintf(fid, 'Scenario: 3GPP_38.901_UMa_NLOS\n');
fprintf(fid, 'Number of Taps: %d\n', stats_scenarios{2}.num_taps);
fprintf(fid, 'Path Loss: %.2f dB\n', stats_scenarios{2}.path_loss_dB);
fprintf(fid, 'RMS Delay Spread: %.2f ns\n', stats_scenarios{2}.rms_delay_spread_ns);
fprintf(fid, 'Dominant Tap Power: %.1f%% of total\n', stats_scenarios{2}.dominant_tap_ratio*100);
fprintf(fid, 'Significant Taps (>10%% max): %d\n\n', sum(power_NLOS > 0.1*max(power_NLOS)));

fprintf(fid, '--- COMPARISON ---\n');
fprintf(fid, 'Path Loss Difference: %.2f dB (NLOS vs LOS)\n', stats_scenarios{2}.path_loss_dB - stats_scenarios{1}.path_loss_dB);
fprintf(fid, 'Delay Spread Ratio: %.2fx (NLOS/LOS)\n', stats_scenarios{2}.rms_delay_spread_ns / stats_scenarios{1}.rms_delay_spread_ns);
fprintf(fid, 'Tap Count Ratio: %.2fx (NLOS/LOS)\n', stats_scenarios{2}.num_taps / stats_scenarios{1}.num_taps);
fprintf(fid, '\nPower Distribution:\n');
fprintf(fid, '  LOS - Dominant tap:  %.1f%% of total\n', stats_scenarios{1}.dominant_tap_ratio*100);
fprintf(fid, '  NLOS - Dominant tap: %.1f%% of total\n\n', stats_scenarios{2}.dominant_tap_ratio*100);

fprintf(fid, '--- KEY INSIGHTS ---\n');
fprintf(fid, '• LOS: Power concentrated in first tap (direct path)\n');
fprintf(fid, '• NLOS: Power spread across many taps (rich scattering)\n');
fprintf(fid, '• NLOS: Higher delay spread → frequency-selective fading\n');
fprintf(fid, '• NLOS: More multipath components\n');
fprintf(fid, '• NLOS: Higher path loss (obstacles block signal)\n\n');

fprintf(fid, '--- ML RELEVANCE ---\n');
fprintf(fid, 'LOS/NLOS classification is important for positioning.\n');
fprintf(fid, 'Features for ML:\n');
fprintf(fid, '  - Dominant tap power ratio\n');
fprintf(fid, '  - RMS delay spread\n');
fprintf(fid, '  - Number of significant taps\n');
fprintf(fid, '  - Power distribution (concentrated vs spread)\n');
fprintf(fid, '  - Path loss\n\n');

ExperimentUtils.closeReport(fid, {'los_vs_nlos.png', 'los_vs_nlos.fig', 'experiment_report.txt'});

fprintf('  ✓ Results saved to: %s\n', results_dir);
fprintf('     - los_vs_nlos.png\n');
fprintf('     - los_vs_nlos.fig\n');
fprintf('     - experiment_report.txt\n');

fprintf('\n========================================\n');
fprintf('Key Takeaways:\n');
fprintf('  1. LOS: Power concentrated in first tap\n');
fprintf('  2. NLOS: Power spread across many taps (rich scattering)\n');
fprintf('  3. NLOS: Higher delay spread → frequency selectivity\n');
fprintf('  4. NLOS: More multipath components\n\n');
fprintf('Next: experiments/02_single_ue_analysis/\n');
fprintf('========================================\n');
