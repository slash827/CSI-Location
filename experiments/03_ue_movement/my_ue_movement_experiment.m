%% MY UE MOVEMENT EXPERIMENT
% Single UE moving in a simple environment - observing CSI and CQI
% Based on simulate_ue_movement_v2_tracks.m, simplified for your experiment

clear; clc; close all;

%% ========== CONFIGURATION (EDIT THESE) ==========

% Radio parameters
fc = 3.5e9;              % Frequency: 3.5 GHz (5G mid-band)
BW = 100e6;              % Bandwidth: 100 MHz
Nsc = 256;               % Number of subcarriers
TxPowerPerSC_dBm = 0;    % Transmit power per subcarrier (dBm)
NoiseFigure_dB = 7;      % UE noise figure

% Movement parameters
T = 50;                  % Number of time steps (snapshots)
start_pos = [20; 10; 1.5];   % Start position [x; y; z] meters
end_pos = [80; 50; 1.5];     % End position [x; y; z] meters

% Base station
BS_pos = [0; 0; 25];     % BS at origin, 25m height

% Scenario (choose one):
scenario = '3GPP_38.901_UMa_LOS';   % Urban Macro, Line-of-Sight
% scenario = '3GPP_38.901_UMa_NLOS'; % Urban Macro, Non-Line-of-Sight (more multipath)
% scenario = '3GPP_38.901_UMi_LOS';  % Urban Micro, LOS
% scenario = '3GPP_38.901_InH_LOS';  % Indoor Hotspot, LOS

%% ========== SETUP ==========

fprintf('=== Simulation Setup ===\n');
fprintf('Frequency: %.2f GHz\n', fc/1e9);
fprintf('Bandwidth: %.0f MHz\n', BW/1e6);
fprintf('Subcarriers: %d\n', Nsc);
fprintf('Time steps: %d\n', T);
fprintf('Scenario: %s\n', scenario);
fprintf('======================\n\n');

% Create linear trajectory
X = linspace(start_pos(1), end_pos(1), T);
Y = linspace(start_pos(2), end_pos(2), T);
Z = linspace(start_pos(3), end_pos(3), T);
P = [X; Y; Z];  % 3 x T matrix of positions

SCS_Hz = BW / Nsc;  % Subcarrier spacing
fvec = linspace(-BW/2, BW/2, Nsc);  % Frequency axis (baseband)

%% ========== QuaDRiGa SIMULATION ==========

fprintf('Setting up QuaDRiGa...\n');

% Simulation parameters
s = qd_simulation_parameters;
s.center_frequency = fc;
s.sample_density = 2;
s.use_absolute_delays = 1;

% Layout
l = qd_layout(s);
l.tx_position = BS_pos;
l.tx_array = qd_arrayant('omni');
l.rx_array = qd_arrayant('omni');
l.set_scenario(scenario);

% Try using track API (time-consistent channels)
use_track = true;
try
    fprintf('Creating UE track...\n');
    trk = qd_track;
    trk.name = 'MyMovingUE';
    trk.initial_position = P(:,1);
    trk.positions = P;  % Set entire trajectory
    l.rx_track = {trk};
    
    fprintf('Generating channels along track...\n');
    c = l.get_channels;
    Htaps = c.coeff;   % [Nrx x Ntx x Ntaps x T]
    taus = c.delay;    % [1 x Ntaps x T]
    
    if size(Htaps, 4) ~= T
        error('Snapshot mismatch');
    end
    fprintf('✓ Track-based generation successful!\n\n');
catch ME
    warning('Track API failed (%s). Using fallback method.\n', ME.message);
    use_track = false;
end

%% ========== PROCESS CHANNELS ==========

fprintf('Processing channels and computing metrics...\n');

% Storage arrays
CQI_wb = zeros(T, 1);
SINR_wb = zeros(T, 1);
RSS_wb = zeros(T, 1);
CSI_magnitude = zeros(Nsc, T);
CSI_phase = zeros(Nsc, T);
CSI_complex = cell(T, 1);

% CQI thresholds (NR-like)
CQI_thr_dB = [-Inf, -6.7, -4.7, -2.3, 0.2, 2.4, 4.3, 5.9, ...
              8.1, 10.3, 11.7, 14.1, 16.3, 18.7, 21.0, 22.7];

% Process each snapshot
if use_track
    % Time-consistent channels from track
    for t = 1:T
        h = squeeze(Htaps(1,1,:,t));    % Taps at time t
        tau = squeeze(taus(1,:,t));     % Delays at time t
        
        % Convert time-domain taps to frequency-domain CSI
        Hsc = zeros(1, 1, Nsc);
        for k = 1:Nsc
            Hsc(1,1,k) = sum(h .* exp(-1j*2*pi*fvec(k).*tau));
        end
        
        % Store CSI
        CSI_complex{t} = squeeze(Hsc);
        CSI_magnitude(:, t) = abs(CSI_complex{t});
        CSI_phase(:, t) = angle(CSI_complex{t});
        
        % Compute metrics
        [RSS_wb(t), SINR_wb(t), CQI_wb(t)] = compute_metrics(...
            Hsc, TxPowerPerSC_dBm, SCS_Hz, NoiseFigure_dB, CQI_thr_dB);
        
        if mod(t, 10) == 0
            fprintf('  Processed %d/%d snapshots\n', t, T);
        end
    end
else
    % Fallback: regenerate channel at each position
    for t = 1:T
        l.rx_position = P(:,t);
        c = l.get_channels;
        h = squeeze(c.coeff(1,1,:,1));
        tau = squeeze(c.delay(1,:,1));
        
        Hsc = zeros(1, 1, Nsc);
        for k = 1:Nsc
            Hsc(1,1,k) = sum(h .* exp(-1j*2*pi*fvec(k).*tau));
        end
        
        CSI_complex{t} = squeeze(Hsc);
        CSI_magnitude(:, t) = abs(CSI_complex{t});
        CSI_phase(:, t) = angle(CSI_complex{t});
        
        [RSS_wb(t), SINR_wb(t), CQI_wb(t)] = compute_metrics(...
            Hsc, TxPowerPerSC_dBm, SCS_Hz, NoiseFigure_dB, CQI_thr_dB);
        
        if mod(t, 10) == 0
            fprintf('  Processed %d/%d snapshots\n', t, T);
        end
    end
end

fprintf('✓ Processing complete!\n\n');

%% ========== RESULTS SUMMARY ==========

fprintf('=== RESULTS SUMMARY ===\n');
fprintf('Average CQI: %.2f (range: %d to %d)\n', mean(CQI_wb), min(CQI_wb), max(CQI_wb));
fprintf('Average SINR: %.2f dB (range: %.2f to %.2f dB)\n', ...
    mean(SINR_wb), min(SINR_wb), max(SINR_wb));
fprintf('Average RSS: %.2f dBm (range: %.2f to %.2f dBm)\n', ...
    mean(RSS_wb), min(RSS_wb), max(RSS_wb));
fprintf('======================\n\n');

%% ========== VISUALIZATION ==========

fprintf('Creating plots...\n');

% Figure 1: CQI over time
figure('Name', 'CQI Evolution', 'Position', [100 100 800 500]);
stairs(1:T, CQI_wb, 'LineWidth', 2, 'Color', [0.2 0.4 0.8]);
xlabel('Time Step', 'FontSize', 12);
ylabel('CQI (0-15)', 'FontSize', 12);
title('Channel Quality Indicator Over Time', 'FontSize', 14);
grid on;
ylim([-0.5, 15.5]);

% Figure 2: UE Trajectory with BS
figure('Name', 'UE Movement', 'Position', [150 150 800 600]);
plot(X, Y, 'b-', 'LineWidth', 2.5); hold on;
plot(X(1), Y(1), 'go', 'MarkerSize', 12, 'MarkerFaceColor', 'g', 'LineWidth', 2);
plot(X(end), Y(end), 'ro', 'MarkerSize', 12, 'MarkerFaceColor', 'r', 'LineWidth', 2);
plot(BS_pos(1), BS_pos(2), '^', 'MarkerSize', 15, 'MarkerFaceColor', [0.8 0.2 0.2], ...
    'MarkerEdgeColor', 'k', 'LineWidth', 2);
quiver(X(1:5:end-1), Y(1:5:end-1), diff(X(1:5:end)), diff(Y(1:5:end)), 0, 'k', 'LineWidth', 1.5);
xlabel('X [m]', 'FontSize', 12);
ylabel('Y [m]', 'FontSize', 12);
legend('UE Path', 'Start', 'End', 'Base Station', 'Direction', 'Location', 'best', 'FontSize', 10);
title('UE Trajectory (Top-Down View)', 'FontSize', 14);
grid on;
axis equal;

% Figure 3: CSI Magnitude Heatmap
figure('Name', 'CSI Magnitude', 'Position', [200 200 900 600]);
imagesc(1:T, 1:Nsc, 20*log10(CSI_magnitude + eps));  % Convert to dB
xlabel('Time Step', 'FontSize', 12);
ylabel('Subcarrier Index', 'FontSize', 12);
title('CSI Magnitude [dB] Over Time and Frequency', 'FontSize', 14);
colorbar;
colormap('jet');
clim([min(20*log10(CSI_magnitude(:) + eps)), max(20*log10(CSI_magnitude(:) + eps))]);

% Figure 4: RSS and SINR Evolution
figure('Name', 'RSS and SINR', 'Position', [250 250 900 700]);

subplot(3,1,1);
plot(1:T, RSS_wb, 'LineWidth', 2, 'Color', [0.8 0.3 0.3]);
xlabel('Time Step', 'FontSize', 11);
ylabel('RSS [dBm]', 'FontSize', 11);
title('Received Signal Strength Over Time', 'FontSize', 12);
grid on;

subplot(3,1,2);
plot(1:T, SINR_wb, 'LineWidth', 2, 'Color', [0.3 0.7 0.3]);
xlabel('Time Step', 'FontSize', 11);
ylabel('SINR [dB]', 'FontSize', 11);
title('Signal-to-Interference-plus-Noise Ratio Over Time', 'FontSize', 12);
grid on;

subplot(3,1,3);
stairs(1:T, CQI_wb, 'LineWidth', 2, 'Color', [0.3 0.3 0.8]);
xlabel('Time Step', 'FontSize', 11);
ylabel('CQI (0-15)', 'FontSize', 11);
title('Channel Quality Indicator Over Time', 'FontSize', 12);
grid on;
ylim([-0.5, 15.5]);

% Figure 5: Distance vs CQI
distance_to_BS = sqrt((X - BS_pos(1)).^2 + (Y - BS_pos(2)).^2);
figure('Name', 'Distance vs CQI', 'Position', [300 300 800 500]);
scatter(distance_to_BS, CQI_wb, 60, 1:T, 'filled');
xlabel('Distance to BS [m]', 'FontSize', 12);
ylabel('CQI (0-15)', 'FontSize', 12);
title('Channel Quality vs Distance to Base Station', 'FontSize', 14);
colorbar;
colormap('cool');
c = colorbar;
c.Label.String = 'Time Step';
grid on;

fprintf('✓ All plots created!\n\n');

%% ========== SAVE RESULTS ==========

% Create results table
results_table = table((1:T)', X', Y', Z', RSS_wb, SINR_wb, CQI_wb, distance_to_BS', ...
    'VariableNames', {'TimeStep', 'X_m', 'Y_m', 'Z_m', 'RSS_dBm', 'SINR_dB', 'CQI', 'Distance_m'});

% Display first 10 rows
fprintf('=== First 10 Rows of Results ===\n');
disp(results_table(1:min(10,T), :));

% Save to files
csv_file = 'my_experiment_results.csv';
mat_file = 'my_experiment_data.mat';

writetable(results_table, csv_file);
save(mat_file, 'CSI_complex', 'CSI_magnitude', 'CSI_phase', 'P', ...
    'results_table', 'Nsc', 'BW', 'fc', 'scenario', 'BS_pos');

fprintf('\n=== Files Saved ===\n');
fprintf('CSV: %s\n', csv_file);
fprintf('MAT: %s\n', mat_file);
fprintf('===================\n\n');

fprintf('✓✓✓ EXPERIMENT COMPLETE! ✓✓✓\n');

%% ========== HELPER FUNCTION ==========

function [RSS_dBm_wb, SINR_dB_wb, CQI_wb] = compute_metrics(Hsc, TxPerSC_dBm, SCS_Hz, NF_dB, CQI_thr_dB)
    % Compute wideband RSS, SINR, and CQI from frequency-domain CSI
    
    % Channel gain per subcarrier
    Gk = abs(squeeze(Hsc)).^2;
    
    % Signal power per subcarrier
    Pt_W_sc = 10^((TxPerSC_dBm - 30) / 10);  % Tx power in Watts
    S_W_sc = Pt_W_sc .* Gk;                  % Signal power per SC
    
    % Wideband RSS (sum across subcarriers, convert to dBm)
    RSS_dBm_wb = 10*log10(sum(S_W_sc) + eps) + 30;
    
    % Noise power per subcarrier
    kB = 1.38064852e-23;  % Boltzmann constant
    T_K = 290;            % Temperature (Kelvin)
    NF_lin = 10^(NF_dB / 10);
    N_W_sc = kB * T_K * SCS_Hz * NF_lin;
    
    % SINR per subcarrier (linear)
    SINR_lin_sc = S_W_sc ./ max(N_W_sc, eps);
    
    % Wideband SINR (average in linear domain, convert to dB)
    SINR_dB_wb = 10*log10(mean(SINR_lin_sc) + eps);
    
    % CQI (threshold-based)
    idx = find(SINR_dB_wb >= CQI_thr_dB, 1, 'last') - 1;
    if isempty(idx)
        idx = 0;
    end
    CQI_wb = max(0, min(15, idx));
end
