%% EXPERIMENT 09: Multi-Trajectory Dataset Generation
% Learn: Generate large datasets for ML training
% Time: 30-60 minutes (depending on dataset size)
%
% What you'll see:
% - Batch generation of multiple trajectories
% - Dataset organization and saving
% - Feature extraction at scale
% - Train/validation split
%
% Expected output:
% - Large CSI dataset with ground truth locations
% - Ready for ML training
% - Statistical summary of dataset

clear; clc; close all;

% Add utils to path
utils_path = fullfile(fileparts(fileparts(mfilename('fullpath'))), '..', 'utils');
addpath(utils_path);

fprintf('========================================\n');
fprintf('EXPERIMENT 09: Multi-Trajectory Dataset\n');
fprintf('========================================\n\n');

%% Configuration
% Dataset parameters
n_trajectories = 20;          % Number of trajectories to generate
n_snapshots_per_traj = 40;    % Snapshots per trajectory
train_ratio = 0.8;            % 80% train, 20% validation

% Simulation area
area_min = [10; 10];          % Min [x, y] in meters
area_max = [90; 90];          % Max [x, y] in meters
ue_height = 1.5;              % UE height in meters

% System parameters
s = qd_simulation_parameters;
s.center_frequency = 3.5e9;
s.sample_density = 2;
s.use_absolute_delays = 1;

% Base station (fixed)
bs_position = [50; 50; 25];

% Frequency domain parameters
BW = 100e6;
Nsc = 256;
fvec = linspace(-BW/2, BW/2, Nsc);

% CSI metrics calculator
m = CSIMetrics('SubcarrierSpacing', BW/Nsc, ...
               'TxPowerPerSC_dBm', 0, ...
               'NoiseFigure_dB', 7);

fprintf('Dataset Configuration:\n');
fprintf('  Number of trajectories: %d\n', n_trajectories);
fprintf('  Snapshots per trajectory: %d\n', n_snapshots_per_traj);
fprintf('  Total samples: %d\n', n_trajectories * n_snapshots_per_traj);
fprintf('  Train/Val split: %.0f%%/%.0f%%\n', train_ratio*100, (1-train_ratio)*100);
fprintf('  Area: [%.0f,%.0f] x [%.0f,%.0f] m\n', area_min(1), area_max(1), area_min(2), area_max(2));
fprintf('  BS position: [%.0f, %.0f, %.0f] m\n\n', bs_position);

%% Initialize storage
total_samples = n_trajectories * n_snapshots_per_traj;

% Ground truth
positions_x = zeros(total_samples, 1);
positions_y = zeros(total_samples, 1);
distances = zeros(total_samples, 1);

% CSI features
RSS_wb = zeros(total_samples, 1);
SINR_wb = zeros(total_samples, 1);
CQI_wb = zeros(total_samples, 1);
RSS_per_sc = zeros(total_samples, Nsc);
SINR_per_sc = zeros(total_samples, Nsc);
H_mag_per_sc = zeros(total_samples, Nsc);

% Metadata
trajectory_id = zeros(total_samples, 1);
snapshot_id = zeros(total_samples, 1);

sample_idx = 1;  % Global sample counter

%% Generate trajectories
fprintf('========================================\n');
fprintf('GENERATING TRAJECTORIES\n');
fprintf('========================================\n\n');

rng(123);  % For reproducibility

total_start_time = tic;

for traj = 1:n_trajectories
    fprintf('Trajectory %d/%d: ', traj, n_trajectories);
    traj_start_time = tic;
    
    % Random trajectory type (50% random walk, 30% linear, 20% curved)
    traj_type = rand;
    
    if traj_type < 0.5
        % Random walk
        start_pos = [rand * (area_max(1) - area_min(1)) + area_min(1);
                     rand * (area_max(2) - area_min(2)) + area_min(2);
                     ue_height];
        
        traj_positions = generateRandomWalk(start_pos, n_snapshots_per_traj, ...
                                           area_min, area_max, 2.5);
        type_str = 'Random Walk';
        
    elseif traj_type < 0.8
        % Linear trajectory
        start_pos = [rand * (area_max(1) - area_min(1)) + area_min(1);
                     rand * (area_max(2) - area_min(2)) + area_min(2);
                     ue_height];
        
        angle = rand * 2*pi;
        distance = 30 + rand * 40;  % 30-70m total distance
        end_pos = start_pos + distance * [cos(angle); sin(angle); 0];
        
        % Clip to area
        end_pos(1) = max(area_min(1), min(area_max(1), end_pos(1)));
        end_pos(2) = max(area_min(2), min(area_max(2), end_pos(2)));
        
        traj_positions = zeros(3, n_snapshots_per_traj);
        for i = 1:n_snapshots_per_traj
            alpha = (i-1) / (n_snapshots_per_traj-1);
            traj_positions(:, i) = (1-alpha)*start_pos + alpha*end_pos;
        end
        type_str = 'Linear';
        
    else
        % Curved trajectory (partial circle/arc)
        center = [rand * (area_max(1) - area_min(1)) + area_min(1);
                  rand * (area_max(2) - area_min(2)) + area_min(2)];
        radius = 15 + rand * 20;  % 15-35m radius
        start_angle = rand * 2*pi;
        arc_angle = (0.3 + rand * 0.7) * pi;  % 0.3π to π radians
        
        traj_positions = zeros(3, n_snapshots_per_traj);
        for i = 1:n_snapshots_per_traj
            alpha = (i-1) / (n_snapshots_per_traj-1);
            angle = start_angle + alpha * arc_angle;
            pos = center + radius * [cos(angle); sin(angle)];
            
            % Clip to area
            pos(1) = max(area_min(1), min(area_max(1), pos(1)));
            pos(2) = max(area_min(2), min(area_max(2), pos(2)));
            
            traj_positions(:, i) = [pos; ue_height];
        end
        type_str = 'Curved';
    end
    
    % Create QuaDRiGa layout for this trajectory
    l = qd_layout(s);
    l.tx_position = bs_position;
    l.tx_array = qd_arrayant('omni');
    
    % Create track and set positions manually
    track = qd_track([]);  % Empty track
    track.scenario = '3GPP_38.901_UMa_LOS';
    track.initial_position = traj_positions(:, 1);
    track.positions = traj_positions;
    track.no_snapshots = n_snapshots_per_traj;
    
    l.track(1,1) = track;
    l.rx_array = qd_arrayant('omni');
    
    % Generate channels
    c = l.get_channels;
    
    % Process each snapshot
    for snap = 1:n_snapshots_per_traj
        % Ground truth
        ue_pos = traj_positions(:, snap);
        positions_x(sample_idx) = ue_pos(1);
        positions_y(sample_idx) = ue_pos(2);
        distances(sample_idx) = norm(ue_pos - bs_position);
        
        % Metadata
        trajectory_id(sample_idx) = traj;
        snapshot_id(sample_idx) = snap;
        
        % Get time-domain channel
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
        
        % Compute CSI metrics
        out = m.compute(H_sc);
        
        % Store wideband features
        RSS_wb(sample_idx) = out.RSS_dBm_wb;
        SINR_wb(sample_idx) = out.SINR_dB_wb;
        CQI_wb(sample_idx) = out.CQI_wb;
        
        % Store per-subcarrier features
        RSS_per_sc(sample_idx, :) = out.RSS_dBm_sc;
        SINR_per_sc(sample_idx, :) = out.SINR_dB_sc;
        H_mag_per_sc(sample_idx, :) = 20*log10(abs(squeeze(H_sc)) + eps);
        
        sample_idx = sample_idx + 1;
    end
    
    traj_time = toc(traj_start_time);
    fprintf('%s - %.2f seconds\n', type_str, traj_time);
end

total_time = toc(total_start_time);
fprintf('\nTotal generation time: %.2f seconds\n', total_time);
fprintf('Time per sample: %.3f seconds\n\n', total_time / total_samples);

%% Split into train and validation
fprintf('========================================\n');
fprintf('SPLITTING DATASET\n');
fprintf('========================================\n\n');

% Random shuffle
rng(456);
perm = randperm(total_samples);

n_train = round(train_ratio * total_samples);
n_val = total_samples - n_train;

train_idx = perm(1:n_train);
val_idx = perm(n_train+1:end);

fprintf('Training samples: %d (%.1f%%)\n', n_train, 100*n_train/total_samples);
fprintf('Validation samples: %d (%.1f%%)\n\n', n_val, 100*n_val/total_samples);

%% Create dataset structures
train_data = struct();
train_data.positions_x = positions_x(train_idx);
train_data.positions_y = positions_y(train_idx);
train_data.distances = distances(train_idx);
train_data.RSS_wb = RSS_wb(train_idx);
train_data.SINR_wb = SINR_wb(train_idx);
train_data.CQI_wb = CQI_wb(train_idx);
train_data.RSS_per_sc = RSS_per_sc(train_idx, :);
train_data.SINR_per_sc = SINR_per_sc(train_idx, :);
train_data.H_mag_per_sc = H_mag_per_sc(train_idx, :);
train_data.trajectory_id = trajectory_id(train_idx);
train_data.snapshot_id = snapshot_id(train_idx);

val_data = struct();
val_data.positions_x = positions_x(val_idx);
val_data.positions_y = positions_y(val_idx);
val_data.distances = distances(val_idx);
val_data.RSS_wb = RSS_wb(val_idx);
val_data.SINR_wb = SINR_wb(val_idx);
val_data.CQI_wb = CQI_wb(val_idx);
val_data.RSS_per_sc = RSS_per_sc(val_idx, :);
val_data.SINR_per_sc = SINR_per_sc(val_idx, :);
val_data.H_mag_per_sc = H_mag_per_sc(val_idx, :);
val_data.trajectory_id = trajectory_id(val_idx);
val_data.snapshot_id = snapshot_id(val_idx);

%% Save datasets
results_dir = ExperimentUtils.createResultsDir('exp09');

dataset_dir = fullfile(results_dir, 'dataset');
mkdir(dataset_dir);

fprintf('Saving datasets...\n');
save(fullfile(dataset_dir, 'train_data.mat'), 'train_data', '-v7.3');
save(fullfile(dataset_dir, 'val_data.mat'), 'val_data', '-v7.3');

% Save metadata
metadata = struct();
metadata.n_trajectories = n_trajectories;
metadata.n_snapshots_per_traj = n_snapshots_per_traj;
metadata.total_samples = total_samples;
metadata.n_train = n_train;
metadata.n_val = n_val;
metadata.BW = BW;
metadata.Nsc = Nsc;
metadata.center_frequency = s.center_frequency;
metadata.bs_position = bs_position;
metadata.area_min = area_min;
metadata.area_max = area_max;
metadata.generation_time = total_time;
metadata.timestamp = datetime('now');

save(fullfile(dataset_dir, 'metadata.mat'), 'metadata');

fprintf('Datasets saved to: %s\n\n', dataset_dir);

%% Create results directory and visualizations
fprintf('========================================\n');
fprintf('CREATING VISUALIZATIONS\n');
fprintf('========================================\n\n');

%% Visualization 1: Spatial Coverage
fig1 = ExperimentUtils.createFigure('Experiment 09 - Spatial Coverage', 'square');

% Plot all trajectories colored by trajectory ID
scatter(positions_x, positions_y, 30, trajectory_id, 'filled', 'MarkerFaceAlpha', 0.6);
hold on;
plot(bs_position(1), bs_position(2), 'k^', 'MarkerSize', 20, 'MarkerFaceColor', 'k');
hold off;

xlabel('X Position (m)');
ylabel('Y Position (m)');
title(sprintf('Dataset Spatial Coverage (%d trajectories, %d samples)', ...
              n_trajectories, total_samples));
colormap(jet(n_trajectories));
colorbar('Ticks', 1:max(1, floor(n_trajectories/10)):n_trajectories, 'TickLabels', ...
         arrayfun(@num2str, 1:max(1, floor(n_trajectories/10)):n_trajectories, 'UniformOutput', false));
ylabel(colorbar, 'Trajectory ID');
grid on;
axis equal;
xlim([area_min(1)-5, area_max(1)+5]);
ylim([area_min(2)-5, area_max(2)+5]);

figure(fig1);
ExperimentUtils.saveFigures(gcf, 'spatial_coverage', results_dir);

%% Visualization 2: Train/Val Split
fig2 = ExperimentUtils.createFigure('Experiment 09 - Train/Val Split', 'wide');

subplot(1, 2, 1);
scatter(train_data.positions_x, train_data.positions_y, 30, 'b', 'filled', 'MarkerFaceAlpha', 0.4);
hold on;
plot(bs_position(1), bs_position(2), 'k^', 'MarkerSize', 20, 'MarkerFaceColor', 'k');
hold off;
xlabel('X Position (m)');
ylabel('Y Position (m)');
title(sprintf('Training Set (%d samples)', n_train));
grid on;
axis equal;
xlim([area_min(1)-5, area_max(1)+5]);
ylim([area_min(2)-5, area_max(2)+5]);

subplot(1, 2, 2);
scatter(val_data.positions_x, val_data.positions_y, 30, 'r', 'filled', 'MarkerFaceAlpha', 0.4);
hold on;
plot(bs_position(1), bs_position(2), 'k^', 'MarkerSize', 20, 'MarkerFaceColor', 'k');
hold off;
xlabel('X Position (m)');
ylabel('Y Position (m)');
title(sprintf('Validation Set (%d samples)', n_val));
grid on;
axis equal;
xlim([area_min(1)-5, area_max(1)+5]);
ylim([area_min(2)-5, area_max(2)+5]);

figure(fig2);
ExperimentUtils.saveFigures(gcf, 'train_val_split', results_dir);

%% Visualization 3: Feature Distributions
fig3 = ExperimentUtils.createFigure('Experiment 09 - Feature Distributions', 'wide');

subplot(2, 3, 1);
histogram(RSS_wb, 30, 'FaceColor', [0.3 0.6 0.9]);
xlabel('RSS (dBm)');
ylabel('Count');
title('RSS Distribution');
grid on;

subplot(2, 3, 2);
histogram(SINR_wb, 30, 'FaceColor', [0.9 0.6 0.3]);
xlabel('SINR (dB)');
ylabel('Count');
title('SINR Distribution');
grid on;

subplot(2, 3, 3);
histogram(CQI_wb, 0.5:1:15.5, 'FaceColor', [0.3 0.9 0.6]);
xlabel('CQI (0-15)');
ylabel('Count');
title('CQI Distribution');
grid on;

subplot(2, 3, 4);
histogram(distances, 30, 'FaceColor', [0.9 0.3 0.6]);
xlabel('Distance to BS (m)');
ylabel('Count');
title('Distance Distribution');
grid on;

subplot(2, 3, 5);
scatter(distances, RSS_wb, 10, 'filled', 'MarkerFaceAlpha', 0.3);
xlabel('Distance (m)');
ylabel('RSS (dBm)');
title('RSS vs Distance');
grid on;

subplot(2, 3, 6);
scatter(distances, SINR_wb, 10, 'filled', 'MarkerFaceAlpha', 0.3);
xlabel('Distance (m)');
ylabel('SINR (dB)');
title('SINR vs Distance');
grid on;

figure(fig3);
ExperimentUtils.saveFigures(gcf, 'feature_distributions', results_dir);

%% Visualization 4: Frequency Domain Features
fig4 = ExperimentUtils.createFigure('Experiment 09 - Frequency Features', 'wide');

% Plot mean and std of H_mag across all samples
mean_H_mag = mean(H_mag_per_sc, 1);
std_H_mag = std(H_mag_per_sc, 1);

subplot(2, 2, 1);
plot(1:Nsc, mean_H_mag, 'b-', 'LineWidth', 2);
hold on;
plot(1:Nsc, mean_H_mag + std_H_mag, 'r--', 'LineWidth', 1);
plot(1:Nsc, mean_H_mag - std_H_mag, 'r--', 'LineWidth', 1);
hold off;
xlabel('Subcarrier Index');
ylabel('|H(f)| (dB)');
title('Mean Channel Magnitude ± Std');
legend('Mean', '+Std', '-Std', 'Location', 'best');
grid on;

subplot(2, 2, 2);
imagesc(1:Nsc, 1:min(100, total_samples), H_mag_per_sc(1:min(100, total_samples), :));
xlabel('Subcarrier Index');
ylabel('Sample Index');
title('Channel Magnitude Heatmap (first 100 samples)');
colorbar;
ylabel(colorbar, '|H(f)| (dB)');

subplot(2, 2, 3);
plot(1:Nsc, mean(RSS_per_sc, 1), 'b-', 'LineWidth', 2);
xlabel('Subcarrier Index');
ylabel('Mean RSS (dBm)');
title('Mean RSS per Subcarrier');
grid on;

subplot(2, 2, 4);
plot(1:Nsc, mean(SINR_per_sc, 1), 'r-', 'LineWidth', 2);
xlabel('Subcarrier Index');
ylabel('Mean SINR (dB)');
title('Mean SINR per Subcarrier');
grid on;

figure(fig4);
ExperimentUtils.saveFigures(gcf, 'frequency_features', results_dir);

%% Statistics Report
fid = ExperimentUtils.createReportHeader(results_dir, 'EXPERIMENT 09: Multi-Trajectory Dataset');

fprintf(fid, 'DATASET CONFIGURATION\n');
fprintf(fid, '=====================\n\n');
fprintf(fid, 'Trajectories: %d\n', n_trajectories);
fprintf(fid, 'Snapshots per trajectory: %d\n', n_snapshots_per_traj);
fprintf(fid, 'Total samples: %d\n', total_samples);
fprintf(fid, 'Training samples: %d (%.1f%%)\n', n_train, 100*n_train/total_samples);
fprintf(fid, 'Validation samples: %d (%.1f%%)\n\n', n_val, 100*n_val/total_samples);

fprintf(fid, 'SYSTEM PARAMETERS\n');
fprintf(fid, '=================\n\n');

% Create params struct for report
report_params = struct();
report_params.center_frequency = s.center_frequency;
report_params.sample_density = s.sample_density;
report_params.bandwidth = BW;
report_params.num_subcarriers = Nsc;
report_params.scenario = '3GPP_38.901_UMa_LOS';
report_params.tx_position = bs_position;
ExperimentUtils.writeSimParams(fid, report_params);

fprintf(fid, '\nArea: [%.0f,%.0f] x [%.0f,%.0f] m\n', area_min(1), area_max(1), area_min(2), area_max(2));
fprintf(fid, 'BS position: [%.0f, %.0f, %.0f] m\n\n', bs_position);

fprintf(fid, 'DATASET STATISTICS\n');
fprintf(fid, '==================\n\n');

fprintf(fid, 'Position Statistics:\n');
fprintf(fid, '  X: Mean=%.1f m, Std=%.1f m, Range=[%.1f, %.1f]\n', ...
    mean(positions_x), std(positions_x), min(positions_x), max(positions_x));
fprintf(fid, '  Y: Mean=%.1f m, Std=%.1f m, Range=[%.1f, %.1f]\n\n', ...
    mean(positions_y), std(positions_y), min(positions_y), max(positions_y));

fprintf(fid, 'Distance Statistics:\n');
fprintf(fid, '  Mean: %.1f m\n', mean(distances));
fprintf(fid, '  Std: %.1f m\n', std(distances));
fprintf(fid, '  Min: %.1f m\n', min(distances));
fprintf(fid, '  Max: %.1f m\n\n', max(distances));

fprintf(fid, 'RSS Statistics:\n');
fprintf(fid, '  Mean: %.2f dBm\n', mean(RSS_wb));
fprintf(fid, '  Std: %.2f dB\n', std(RSS_wb));
fprintf(fid, '  Min: %.2f dBm\n', min(RSS_wb));
fprintf(fid, '  Max: %.2f dBm\n\n', max(RSS_wb));

fprintf(fid, 'SINR Statistics:\n');
fprintf(fid, '  Mean: %.2f dB\n', mean(SINR_wb));
fprintf(fid, '  Std: %.2f dB\n', std(SINR_wb));
fprintf(fid, '  Min: %.2f dB\n', min(SINR_wb));
fprintf(fid, '  Max: %.2f dB\n\n', max(SINR_wb));

fprintf(fid, 'CQI Statistics:\n');
fprintf(fid, '  Mean: %.2f\n', mean(CQI_wb));
fprintf(fid, '  Median: %d\n', median(CQI_wb));
fprintf(fid, '  Min: %d\n', min(CQI_wb));
fprintf(fid, '  Max: %d\n\n', max(CQI_wb));

fprintf(fid, 'GENERATION PERFORMANCE\n');
fprintf(fid, '======================\n\n');
fprintf(fid, 'Total time: %.2f seconds (%.2f minutes)\n', total_time, total_time/60);
fprintf(fid, 'Time per sample: %.3f seconds\n', total_time/total_samples);
fprintf(fid, 'Time per trajectory: %.2f seconds\n\n', total_time/n_trajectories);

fprintf(fid, 'FEATURE SUMMARY\n');
fprintf(fid, '===============\n\n');
fprintf(fid, 'Wideband features (per sample):\n');
fprintf(fid, '  - RSS_wb (1 value)\n');
fprintf(fid, '  - SINR_wb (1 value)\n');
fprintf(fid, '  - CQI_wb (1 value)\n\n');
fprintf(fid, 'Per-subcarrier features (per sample):\n');
fprintf(fid, '  - RSS_per_sc (%d values)\n', Nsc);
fprintf(fid, '  - SINR_per_sc (%d values)\n', Nsc);
fprintf(fid, '  - H_mag_per_sc (%d values)\n\n', Nsc);
fprintf(fid, 'Total features per sample: %d\n\n', 3 + 3*Nsc);

fprintf(fid, 'NEXT STEPS\n');
fprintf(fid, '==========\n\n');
fprintf(fid, '1. Load datasets in Python/MATLAB\n');
fprintf(fid, '2. Feature engineering and selection\n');
fprintf(fid, '3. Train ML models (Random Forest, Neural Network, etc.)\n');
fprintf(fid, '4. Evaluate on validation set\n');
fprintf(fid, '5. Fine-tune and deploy\n\n');

fprintf(fid, 'Dataset location:\n');
fprintf(fid, '  %s\n\n', dataset_dir);

files_generated = {
    'spatial_coverage.png', 'spatial_coverage.fig', ...
    'train_val_split.png', 'train_val_split.fig', ...
    'feature_distributions.png', 'feature_distributions.fig', ...
    'frequency_features.png', 'frequency_features.fig', ...
    'dataset/train_data.mat', 'dataset/val_data.mat', 'dataset/metadata.mat'
};
ExperimentUtils.closeReport(fid, files_generated);

%% Console Summary
fprintf('========================================\n');
fprintf('DATASET GENERATION COMPLETE\n');
fprintf('========================================\n\n');

fprintf('Generated: %d samples from %d trajectories\n', total_samples, n_trajectories);
fprintf('Split: %d train, %d validation\n', n_train, n_val);
fprintf('Time: %.2f seconds (%.3f sec/sample)\n\n', total_time, total_time/total_samples);

fprintf('Feature Statistics:\n');
fprintf('  RSS: %.2f ± %.2f dBm\n', mean(RSS_wb), std(RSS_wb));
fprintf('  SINR: %.2f ± %.2f dB\n', mean(SINR_wb), std(SINR_wb));
fprintf('  CQI: %.1f ± %.1f\n', mean(CQI_wb), std(CQI_wb));
fprintf('  Distance: %.1f ± %.1f m\n\n', mean(distances), std(distances));

fprintf('Saved to: %s\n\n', dataset_dir);

fprintf('========================================\n');
fprintf('✓ Level 3 Complete!\n');
fprintf('========================================\n');
fprintf('You''ve mastered:\n');
fprintf('  ✓ Simple linear movement\n');
fprintf('  ✓ Trajectory type comparison\n');
fprintf('  ✓ Large-scale dataset generation\n\n');
fprintf('Ready for machine learning!\n\n');
fprintf('Next Level: experiments/04_data_generation/\n');
fprintf('Advanced feature extraction and preprocessing!\n');
fprintf('========================================\n');

%% Helper function
function positions = generateRandomWalk(start_pos, n_steps, area_min, area_max, step_size)
    % Generate random walk trajectory within bounded area
    
    positions = zeros(3, n_steps);
    positions(:, 1) = start_pos;
    
    for i = 2:n_steps
        % Random direction
        angle = rand * 2*pi;
        step = step_size * [cos(angle); sin(angle); 0];
        
        % Take step
        next_pos = positions(:, i-1) + step;
        
        % Keep within bounds
        next_pos(1) = max(area_min(1), min(area_max(1), next_pos(1)));
        next_pos(2) = max(area_min(2), min(area_max(2), next_pos(2)));
        next_pos(3) = start_pos(3);  % Maintain height
        
        positions(:, i) = next_pos;
    end
end
