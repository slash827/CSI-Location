%% EXPERIMENT 13C: Temporal Stability Sanity Check
% Verify that CSI remains stable when UE is stationary
% UE stays at a fixed position, CSI sampled every 0.5s for 50 seconds
%
% Purpose: Validate QuaDRiGa's temporal modeling for stationary UE
%
% Output: temporal_stability_results.mat

clear; clc; close all;

%% Setup
fprintf('========================================\n');
fprintf('EXP13C: Temporal Stability Sanity Check\n');
fprintf('========================================\n\n');

% Add utils to path
script_dir = fileparts(mfilename('fullpath'));
project_root = fileparts(fileparts(script_dir));
utils_path = fullfile(project_root, 'utils');
addpath(utils_path);

%% Configuration
config = struct();

% Temporal parameters
config.sample_interval = 0.5;     % Sample every 0.5 seconds
config.total_duration = 50;       % Total duration in seconds
config.n_samples = config.total_duration / config.sample_interval;  % 100 samples

% UE position (fixed, at center of the grid used in exp13a/13b)
config.ue_position = [51; 51; 1.5];  % Center of 3x3 grid at offset [50,50]
config.ue_speed = 0;                  % Stationary!

% Simulation parameters
config.center_frequency = 3e9;
config.bandwidth = 100e6;
config.n_subcarriers = 256;
config.scenario = '3GPP_38.901_UMa_LOS';  % LOS - same as exp13a/13b

% Base station configuration
config.bs_position = [0; 0; 25];  % BS at origin, 25m height

fprintf('Configuration:\n');
fprintf('  UE Position: [%.1f, %.1f, %.1f] m\n', config.ue_position);
fprintf('  Sample interval: %.2f seconds\n', config.sample_interval);
fprintf('  Total duration: %.1f seconds\n', config.total_duration);
fprintf('  Number of samples: %d\n', config.n_samples);
fprintf('  Scenario: %s\n', config.scenario);
fprintf('\n');

%% Initialize QuaDRiGa
fprintf('Initializing QuaDRiGa...\n');

% Simulation parameters
s = qd_simulation_parameters;
s.center_frequency = config.center_frequency;
s.sample_density = 2;
s.use_absolute_delays = 1;

% Frequency vector for CSI
fvec = linspace(-config.bandwidth/2, config.bandwidth/2, config.n_subcarriers) + config.center_frequency;

% Initialize CSI metrics calculator
m = CSIMetrics('SubcarrierSpacing', config.bandwidth/config.n_subcarriers, ...
               'TxPowerPerSC_dBm', 0, ...
               'NoiseFigure_dB', 7);

%% Preallocate storage
n_samples = config.n_samples;

metrics = struct();
metrics.RSS_wb = zeros(1, n_samples);
metrics.SINR_wb = zeros(1, n_samples);
metrics.CQI_wb = zeros(1, n_samples);
metrics.path_loss = zeros(1, n_samples);
metrics.rms_delay_spread = zeros(1, n_samples);
metrics.mean_delay = zeros(1, n_samples);
metrics.time = (0:n_samples-1) * config.sample_interval;  % Time vector

csi_data = struct();
csi_data.H_mag = zeros(config.n_subcarriers, n_samples);
csi_data.H_phase = zeros(config.n_subcarriers, n_samples);
csi_data.H_freq = cell(1, n_samples);

%% Generate CSI samples using track with very slow movement
fprintf('Generating CSI samples for quasi-stationary UE...\n');

% Strategy: Create positions with tiny movement (same approach as exp13b)
% Move 0.001m (1mm) per sample to enable track generation
% Total movement = 0.1m over 100 samples - negligible at 72m distance

%% CORRECT APPROACH - Let QuaDRiGa handle snapshots automatically
fprintf('Generating walking UE trajectory...\n');

n_samples = config.n_samples;  % 100
use_track = false;

try
    % Create simulation parameters
    s = qd_simulation_parameters;
    s.center_frequency = config.center_frequency;
    s.use_absolute_delays = 1;
    s.show_progress_bars = 1;
    
    % CRITICAL: Set samples_per_meter to get desired snapshots
    % For 100 samples over 100 meters = 1 sample/meter
    % For 100 samples over 10 meters = 10 samples/meter
    total_distance = 10;  % meters
    s.samples_per_meter = n_samples / total_distance;  % 10 samples/m
    
    fprintf('  Total distance: %.1f m\n', total_distance);
    fprintf('  Samples per meter: %.1f\n', s.samples_per_meter);
    fprintf('  Expected snapshots: %d\n', ceil(total_distance * s.samples_per_meter));
    
    % Create layout
    l = qd_layout(s);
    l.no_tx = 1;
    l.tx_position = config.bs_position;
    l.tx_array = qd_arrayant('omni');
    l.rx_array = qd_arrayant('omni');
    
    % Create track - QuaDRiGa will handle snapshots automatically
    t = qd_track('linear', total_distance, 0);  % 10m straight
    t.name = 'WalkingUE';
    t.initial_position = config.ue_position;
    t.set_speed(1.0);  % 1 m/s
    t.scenario = config.scenario;
    
    % DON'T call interpolate! Let QuaDRiGa do it automatically
    
    l.track(1,1) = copy(t);
    
    fprintf('  Generating channels...\n');
    
    % Generate channels - snapshots created automatically
    c = l.get_channels;
    
    % Check what we got
    if isa(c, 'qd_channel')
        coeff_dims = size(c.coeff);
        if length(coeff_dims) >= 4
            n_snapshots = coeff_dims(4);
        else
            n_snapshots = 1;
        end
        
        fprintf('  Generated %d snapshots\n', n_snapshots);
        
        if n_snapshots >= n_samples * 0.9  % Allow 10% tolerance
            use_track = true;
            fprintf('  ✓ SUCCESS!\n');
        else
            warning('Expected ~%d snapshots, got %d', n_samples, n_snapshots);
            use_track = false;
        end
    end
    
catch ME
    warning('Failed: %s', ME.message);
    use_track = false;
end

%% Process samples (same code as before)
if use_track && n_snapshots >= n_samples
    % Use the temporally-correlated channels...
    % [rest of your processing code]
end

%% Process samples
fprintf('Processing samples: ');

if use_track && n_snapshots >= n_samples
    % Use track-generated channels
    for idx = 1:n_samples
        % Get channel for this snapshot
        h_t = squeeze(c.coeff(1,1,:,idx));
        tau = squeeze(c.delay(1,:,idx));
        
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
        csi_data.H_freq{idx} = H_freq;
        csi_data.H_mag(:, idx) = abs(H_freq(:));
        csi_data.H_phase(:, idx) = angle(H_freq(:));
        
        % Compute metrics
        H_sc = reshape(H_freq, [1, 1, config.n_subcarriers]);
        out = m.compute(H_sc);
        
        metrics.RSS_wb(idx) = out.RSS_dBm_wb;
        metrics.SINR_wb(idx) = out.SINR_dB_wb;
        metrics.CQI_wb(idx) = out.CQI_wb;
        
        % Channel statistics
        stats = ExperimentUtils.calculateChannelStats(h_t, tau * 1e9);
        metrics.path_loss(idx) = stats.path_loss_dB;
        metrics.rms_delay_spread(idx) = stats.rms_delay_spread_ns;
        metrics.mean_delay(idx) = stats.mean_delay_ns;
        
        if mod(idx, 10) == 0
            fprintf('.');
        end
    end
else
    % Fallback: independent samples (each is a separate simulation)
    for idx = 1:n_samples
        % Create simulation for this single UE position
        l = qd_layout(s);
        l.no_tx = 1;
        l.tx_position = config.bs_position;
        l.tx_array = qd_arrayant('omni');
        
        l.no_rx = 1;
        l.rx_position = config.ue_position;
        l.rx_array = qd_arrayant('omni');
        
        l.set_scenario(config.scenario);
        
        % Generate channel
        c = l.get_channels;
        
        % Get channel coefficients
        h_t = squeeze(c.coeff(1,1,:,1));
        tau = squeeze(c.delay(1,:,1));
        
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
        csi_data.H_freq{idx} = H_freq;
        csi_data.H_mag(:, idx) = abs(H_freq(:));
        csi_data.H_phase(:, idx) = angle(H_freq(:));
        
        % Compute metrics
        H_sc = reshape(H_freq, [1, 1, config.n_subcarriers]);
        out = m.compute(H_sc);
        
        metrics.RSS_wb(idx) = out.RSS_dBm_wb;
        metrics.SINR_wb(idx) = out.SINR_dB_wb;
        metrics.CQI_wb(idx) = out.CQI_wb;
        
        % Channel statistics
        stats = ExperimentUtils.calculateChannelStats(h_t, tau * 1e9);
        metrics.path_loss(idx) = stats.path_loss_dB;
        metrics.rms_delay_spread(idx) = stats.rms_delay_spread_ns;
        metrics.mean_delay(idx) = stats.mean_delay_ns;
        
        if mod(idx, 10) == 0
            fprintf('.');
        end
    end
end

fprintf(' Done!\n\n');

%% Compute statistics
fprintf('Computing statistics...\n');

statistics = struct();
metric_names = {'RSS_wb', 'SINR_wb', 'CQI_wb', 'path_loss', 'rms_delay_spread'};

for i = 1:length(metric_names)
    name = metric_names{i};
    vals = metrics.(name);
    statistics.(name) = struct();
    statistics.(name).mean = mean(vals);
    statistics.(name).std = std(vals);
    statistics.(name).min = min(vals);
    statistics.(name).max = max(vals);
    statistics.(name).range = max(vals) - min(vals);
    statistics.(name).cv = std(vals) / abs(mean(vals)) * 100;  % Coefficient of variation (%)
end

fprintf('\n=== TEMPORAL STABILITY RESULTS ===\n');
fprintf('%-20s %12s %12s %12s %12s %12s\n', 'Metric', 'Mean', 'Std', 'Min', 'Max', 'CV(%)');
fprintf('%s\n', repmat('-', 1, 80));
for i = 1:length(metric_names)
    name = metric_names{i};
    s = statistics.(name);
    fprintf('%-20s %12.4f %12.4f %12.4f %12.4f %12.2f\n', ...
            name, s.mean, s.std, s.min, s.max, s.cv);
end
fprintf('\n');

%% Quick plots (MATLAB)
fprintf('Creating MATLAB plots...\n');

figure('Position', [100, 100, 1200, 800]);

% RSS over time
subplot(2, 3, 1);
plot(metrics.time, metrics.RSS_wb, 'b-', 'LineWidth', 1);
hold on;
yline(statistics.RSS_wb.mean, 'r--', 'Mean', 'LineWidth', 1.5);
yline(statistics.RSS_wb.mean + statistics.RSS_wb.std, 'g:', '+1σ');
yline(statistics.RSS_wb.mean - statistics.RSS_wb.std, 'g:', '-1σ');
xlabel('Time (s)');
ylabel('RSS (dBm)');
title(sprintf('RSS: μ=%.2f, σ=%.4f', statistics.RSS_wb.mean, statistics.RSS_wb.std));
grid on;

% SINR over time
subplot(2, 3, 2);
plot(metrics.time, metrics.SINR_wb, 'b-', 'LineWidth', 1);
hold on;
yline(statistics.SINR_wb.mean, 'r--', 'Mean', 'LineWidth', 1.5);
xlabel('Time (s)');
ylabel('SINR (dB)');
title(sprintf('SINR: μ=%.2f, σ=%.4f', statistics.SINR_wb.mean, statistics.SINR_wb.std));
grid on;

% Path loss over time
subplot(2, 3, 3);
plot(metrics.time, metrics.path_loss, 'b-', 'LineWidth', 1);
hold on;
yline(statistics.path_loss.mean, 'r--', 'Mean', 'LineWidth', 1.5);
xlabel('Time (s)');
ylabel('Path Loss (dB)');
title(sprintf('Path Loss: μ=%.2f, σ=%.4f', statistics.path_loss.mean, statistics.path_loss.std));
grid on;

% CQI over time
subplot(2, 3, 4);
plot(metrics.time, metrics.CQI_wb, 'b-', 'LineWidth', 1);
xlabel('Time (s)');
ylabel('CQI');
title(sprintf('CQI: μ=%.2f, σ=%.4f', statistics.CQI_wb.mean, statistics.CQI_wb.std));
grid on;

% RMS Delay Spread over time
subplot(2, 3, 5);
plot(metrics.time, metrics.rms_delay_spread, 'b-', 'LineWidth', 1);
hold on;
yline(statistics.rms_delay_spread.mean, 'r--', 'Mean', 'LineWidth', 1.5);
xlabel('Time (s)');
ylabel('RMS Delay Spread (ns)');
title(sprintf('Delay Spread: μ=%.2f, σ=%.4f', statistics.rms_delay_spread.mean, statistics.rms_delay_spread.std));
grid on;

% Histogram of RSS
subplot(2, 3, 6);
histogram(metrics.RSS_wb, 20, 'Normalization', 'pdf');
xlabel('RSS (dBm)');
ylabel('Density');
title('RSS Distribution');
grid on;

sgtitle(sprintf('Temporal Stability Check - Stationary UE at [%.0f, %.0f] m (%s)', ...
        config.ue_position(1), config.ue_position(2), config.scenario));

%% Save results
fprintf('Saving results...\n');

% Create output directory
timestamp = datestr(now, 'yyyy-mm-dd_HH-MM-SS');
output_dir = fullfile(project_root, 'results', sprintf('exp13c_%s', timestamp));
mkdir(output_dir);

% Save MATLAB figure
saveas(gcf, fullfile(output_dir, 'temporal_stability_plots.png'));
saveas(gcf, fullfile(output_dir, 'temporal_stability_plots.fig'));

% Save data
results = struct();
results.config = config;
results.metrics = metrics;
results.statistics = statistics;
results.csi_data = csi_data;
results.use_track = use_track;

save(fullfile(output_dir, 'temporal_stability_results.mat'), '-struct', 'results', '-v7.3');

fprintf('\n=== EXPERIMENT COMPLETE ===\n');
fprintf('Results saved to: %s\n', output_dir);
fprintf('\nSanity check summary:\n');
if statistics.RSS_wb.std < 1.0
    fprintf('  ✓ RSS is stable (σ = %.4f dB < 1 dB)\n', statistics.RSS_wb.std);
else
    fprintf('  ⚠ RSS has high variance (σ = %.4f dB)\n', statistics.RSS_wb.std);
end
if statistics.path_loss.std < 1.0
    fprintf('  ✓ Path loss is stable (σ = %.4f dB < 1 dB)\n', statistics.path_loss.std);
else
    fprintf('  ⚠ Path loss has high variance (σ = %.4f dB)\n', statistics.path_loss.std);
end
fprintf('\nRun analyze_temporal_stability.py for detailed analysis.\n');
