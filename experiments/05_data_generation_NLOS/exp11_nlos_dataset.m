%% Experiment 11: NLOS-Enhanced Large-Scale Dataset Generation
% Generate diverse CSI dataset with mixed LOS/NLOS scenarios for robust ML training
%
% Key Features:
%   - 30% Pure LOS (open corridors)
%   - 25% Light NLOS (single obstacle)
%   - 25% Moderate NLOS (multiple walls)
%   - 20% Heavy NLOS (deep indoor)
%
% Output: 32,000 training samples, 8,000 validation samples
% Expected runtime: 15-20 minutes

clear; close all; clc;

%% Setup
fprintf('========================================\n');
fprintf('EXP11: NLOS-ENHANCED DATA GENERATION\n');
fprintf('========================================\n\n');

% Add utils to path
script_dir = fileparts(mfilename('fullpath'));
project_root = fileparts(fileparts(script_dir));
utils_path = fullfile(project_root, 'utils');
addpath(utils_path);

% Load configuration
run('config_nlos_dataset.m');

% Setup output directory
output_dir = ExperimentUtils.createResultsDir('exp11');
dataset_dir = fullfile(output_dir, 'dataset');
trajectories_dir = fullfile(output_dir, 'trajectories');
analysis_dir = fullfile(output_dir, 'analysis');
mkdir(dataset_dir);
mkdir(trajectories_dir);
mkdir(analysis_dir);

fprintf('Output directory: %s\n\n', output_dir);

%% Initialize QuaDRiGa
fprintf('Initializing QuaDRiGa...\n');

% Create layout (will be updated per trajectory with different scenarios)
l = qd_layout;

% Configure base stations
l.no_tx = size(config.bs.positions, 1);
for i = 1:l.no_tx
    l.tx_position(:, i) = config.bs.positions(i, :)';
    l.tx_array(i) = qd_arrayant('omni');
end

fprintf('✓ Created %d base stations\n', l.no_tx);

%% Calculate trajectory and NLOS counts
fprintf('\n--- Trajectory Distribution ---\n');
traj_types = fieldnames(config.trajectory_distribution);
traj_counts = struct();
for i = 1:length(traj_types)
    type = traj_types{i};
    count = round(config.n_trajectories * config.trajectory_distribution.(type));
    traj_counts.(type) = count;
    fprintf('  %s: %d trajectories (%.1f%%)\n', type, count, ...
            100 * config.trajectory_distribution.(type));
end

% Adjust for rounding errors
total_traj = sum(structfun(@(x) x, traj_counts));
if total_traj ~= config.n_trajectories
    diff = config.n_trajectories - total_traj;
    traj_counts.linear = traj_counts.linear + diff;
    fprintf('  Adjusted linear: %d (rounding correction: %+d)\n', ...
            traj_counts.linear, diff);
end

fprintf('\n--- NLOS Distribution ---\n');
nlos_types = fieldnames(config.nlos_distribution);
nlos_counts = struct();
for i = 1:length(nlos_types)
    type = nlos_types{i};
    count = round(config.n_trajectories * config.nlos_distribution.(type));
    nlos_counts.(type) = count;
    fprintf('  %s: %d trajectories (%.1f%%)\n', type, count, ...
            100 * config.nlos_distribution.(type));
end

% Adjust for rounding errors
total_nlos = sum(structfun(@(x) x, nlos_counts));
if total_nlos ~= config.n_trajectories
    diff = config.n_trajectories - total_nlos;
    nlos_counts.pure_los = nlos_counts.pure_los + diff;
    fprintf('  Adjusted pure_los: %d (rounding correction: %+d)\n', ...
            nlos_counts.pure_los, diff);
end

fprintf('\nTotal trajectories: %d\n\n', config.n_trajectories);

%% Generate NLOS assignment for each trajectory
fprintf('Assigning NLOS conditions to trajectories...\n');

% Create shuffled assignment to ensure proper mixing
nlos_assignment = cell(config.n_trajectories, 1);
idx = 1;
for i = 1:length(nlos_types)
    type = nlos_types{i};
    count = nlos_counts.(type);
    for j = 1:count
        nlos_assignment{idx} = type;
        idx = idx + 1;
    end
end

% Shuffle to randomize order
nlos_assignment = nlos_assignment(randperm(config.n_trajectories));

fprintf('✓ NLOS conditions assigned\n\n');

%% Generate all trajectories
fprintf('Generating trajectories...\n');
fprintf('Progress: [');
progress_bar_length = 50;
progress_interval = ceil(config.n_trajectories / progress_bar_length);

all_trajectories = cell(config.n_trajectories, 1);
trajectory_labels = cell(config.n_trajectories, 1);
traj_idx = 1;

% Helper function for random position in bounds
random_pos = @() [config.scenario.bounds.x_min + ...
                 (config.scenario.bounds.x_max - config.scenario.bounds.x_min) * rand(), ...
                 config.scenario.bounds.y_min + ...
                 (config.scenario.bounds.y_max - config.scenario.bounds.y_min) * rand()];

% Generate each trajectory type (same as exp10)
for type_idx = 1:length(traj_types)
    type = traj_types{type_idx};
    n_type = traj_counts.(type);
    
    for i = 1:n_type
        switch type
            case 'linear'
                start_pos = random_pos();
                angle = 2*pi*rand();
                distance = config.linear.min_distance + ...
                          (config.linear.max_distance - config.linear.min_distance) * rand();
                end_pos = start_pos + distance * [cos(angle), sin(angle)];
                
                % Ensure end_pos is in bounds
                end_pos(1) = max(config.scenario.bounds.x_min, ...
                               min(config.scenario.bounds.x_max, end_pos(1)));
                end_pos(2) = max(config.scenario.bounds.y_min, ...
                               min(config.scenario.bounds.y_max, end_pos(2)));
                
                traj = generate_linear_trajectory(start_pos, end_pos, ...
                    config.n_timesteps, 'randomize', config.linear.randomize);
                
            case 'circular'
                center = random_pos();
                radius = config.circular.min_radius + ...
                        (config.circular.max_radius - config.circular.min_radius) * rand();
                revolutions = config.circular.revolutions(1) + ...
                            diff(config.circular.revolutions) * rand();
                direction = {'cw', 'ccw'};
                dir = direction{randi(2)};
                
                traj = generate_circular_trajectory(center, radius, ...
                    config.n_timesteps, 'direction', dir, 'revolutions', revolutions);
                
            case 'zigzag'
                start_pos = random_pos();
                angle = 2*pi*rand();
                distance = 40 + 30*rand();
                end_pos = start_pos + distance * [cos(angle), sin(angle)];
                
                end_pos(1) = max(config.scenario.bounds.x_min, ...
                               min(config.scenario.bounds.x_max, end_pos(1)));
                end_pos(2) = max(config.scenario.bounds.y_min, ...
                               min(config.scenario.bounds.y_max, end_pos(2)));
                
                amplitude = config.zigzag.amplitude_range(1) + ...
                          diff(config.zigzag.amplitude_range) * rand();
                frequency = randi(config.zigzag.frequency_range);
                
                traj = generate_zigzag_trajectory(start_pos, end_pos, ...
                    config.n_timesteps, 'amplitude', amplitude, 'frequency', frequency);
                
            case 'random_walk'
                start_pos = random_pos();
                step_size = config.random_walk.step_size_range(1) + ...
                          diff(config.random_walk.step_size_range) * rand();
                
                traj = generate_random_walk(start_pos, config.n_timesteps, ...
                    'step_size', step_size, ...
                    'bounds', [config.scenario.bounds.x_min, config.scenario.bounds.x_max, ...
                              config.scenario.bounds.y_min, config.scenario.bounds.y_max], ...
                    'smoothing', config.random_walk.smoothing);
                
            case 'grid'
                spacing = config.grid.spacing_range(1) + ...
                         diff(config.grid.spacing_range) * rand();
                
                traj = generate_grid_trajectory(...
                    [config.scenario.bounds.x_min, config.scenario.bounds.x_max, ...
                     config.scenario.bounds.y_min, config.scenario.bounds.y_max], ...
                    spacing, config.n_timesteps);
                
            case 'spiral'
                center = random_pos();
                radius_start = config.spiral.radius_start_range(1) + ...
                             diff(config.spiral.radius_start_range) * rand();
                radius_end = config.spiral.radius_end_range(1) + ...
                           diff(config.spiral.radius_end_range) * rand();
                revolutions = config.spiral.revolutions_range(1) + ...
                            diff(config.spiral.revolutions_range) * rand();
                direction = {'out', 'in'};
                dir = direction{randi(2)};
                
                traj = generate_spiral_trajectory(center, config.n_timesteps, ...
                    'radius_start', radius_start, 'radius_end', radius_end, ...
                    'revolutions', revolutions, 'direction', dir);
                
            case 'figure8'
                center = random_pos();
                size_val = config.figure8.size_range(1) + ...
                          diff(config.figure8.size_range) * rand();
                
                traj = generate_figure8_trajectory(center, size_val, config.n_timesteps);
        end
        
        % Ensure trajectory is within bounds
        traj(:, 1) = max(config.scenario.bounds.x_min, ...
                        min(config.scenario.bounds.x_max, traj(:, 1)));
        traj(:, 2) = max(config.scenario.bounds.y_min, ...
                        min(config.scenario.bounds.y_max, traj(:, 2)));
        
        % Store trajectory
        all_trajectories{traj_idx} = traj;
        trajectory_labels{traj_idx} = type;
        traj_idx = traj_idx + 1;
        
        % Update progress bar
        if mod(traj_idx-1, progress_interval) == 0
            fprintf('=');
        end
    end
end

fprintf(']\n✓ Generated %d trajectories\n\n', config.n_trajectories);

%% Simulate CSI for all trajectories with NLOS conditions
fprintf('Simulating CSI data with mixed LOS/NLOS scenarios...\n');
fprintf('This will take 15-20 minutes...\n\n');

% Initialize storage
n_train_per_traj = round(config.n_timesteps * config.train_ratio);
n_val_per_traj = config.n_timesteps - n_train_per_traj;

train_data = struct();
val_data = struct();
nlos_metadata = struct();
nlos_metadata.train_conditions = [];  % NLOS type for each train sample
nlos_metadata.val_conditions = [];    % NLOS type for each val sample
nlos_metadata.train_scenarios = {};   % Scenario name for each train sample
nlos_metadata.val_scenarios = {};     % Scenario name for each val sample

% Map NLOS type to numeric code for easier analysis
nlos_type_map = struct('pure_los', 1, 'light_nlos', 2, 'moderate_nlos', 3, 'heavy_nlos', 4);

tic;

for t = 1:config.n_trajectories
    % Get NLOS condition for this trajectory
    nlos_type = nlos_assignment{t};
    scenario_name = config.nlos_scenarios.(nlos_type);
    nlos_code = nlos_type_map.(nlos_type);
    
    % Set scenario for this trajectory
    l.set_scenario(scenario_name);
    
    % Create track
    track_positions = [all_trajectories{t}'; ...
                      ones(1, config.n_timesteps) * config.ue.height];
    
    track = qd_track('linear', 0, pi/4);
    track.positions = track_positions;
    track.scenario = scenario_name;
    
    % Add track to layout
    l.track(1) = track;
    
    % Generate channel
    c = l.get_channels();
    
    % Extract features for each time step
    for ts = 1:config.n_timesteps
        % Initialize feature arrays for this timestep
        all_h_freq = [];
        
        % Loop through each BS
        for bs_idx = 1:length(c)
            % Get channel from this BS at this time step
            h_freq = c(bs_idx).fr(config.scenario.bandwidth, config.scenario.n_subcarriers, ts);
            all_h_freq = [all_h_freq; h_freq(:)];  % Concatenate
        end
        
        % Extract features (combined from all BSs)
        features = struct();
        
        % Wideband features
        features.CQI_wb = mean(10*log10(abs(all_h_freq).^2 + eps));
        features.RSRP = 10*log10(mean(abs(all_h_freq).^2));
        features.SINR_wb = features.RSRP - (-90);  % Simplified
        
        % Per-subcarrier features
        features.RSS_per_sc = 10*log10(abs(all_h_freq).^2 + eps);
        features.SINR_per_sc = features.RSS_per_sc - (-90);
        features.H_mag_per_sc = abs(all_h_freq);
        
        % Position
        pos = [track_positions(1, ts); track_positions(2, ts)];
        
        % Store in train or val with NLOS metadata
        if ts <= n_train_per_traj
            if t == 1 && ts == 1
                % Initialize training
                train_data = features;
                train_data.positions_x = pos(1);
                train_data.positions_y = pos(2);
            else
                % Append
                train_data.CQI_wb(end+1) = features.CQI_wb;
                train_data.RSRP(end+1) = features.RSRP;
                train_data.SINR_wb(end+1) = features.SINR_wb;
                train_data.RSS_per_sc(:, end+1) = features.RSS_per_sc;
                train_data.SINR_per_sc(:, end+1) = features.SINR_per_sc;
                train_data.H_mag_per_sc(:, end+1) = features.H_mag_per_sc;
                train_data.positions_x(end+1) = pos(1);
                train_data.positions_y(end+1) = pos(2);
            end
            % Store NLOS metadata
            nlos_metadata.train_conditions(end+1) = nlos_code;
            nlos_metadata.train_scenarios{end+1} = scenario_name;
        else
            if t == 1 && ts == n_train_per_traj + 1
                % Initialize validation
                val_data = features;
                val_data.positions_x = pos(1);
                val_data.positions_y = pos(2);
            else
                % Append
                val_data.CQI_wb(end+1) = features.CQI_wb;
                val_data.RSRP(end+1) = features.RSRP;
                val_data.SINR_wb(end+1) = features.SINR_wb;
                val_data.RSS_per_sc(:, end+1) = features.RSS_per_sc;
                val_data.SINR_per_sc(:, end+1) = features.SINR_per_sc;
                val_data.H_mag_per_sc(:, end+1) = features.H_mag_per_sc;
                val_data.positions_x(end+1) = pos(1);
                val_data.positions_y(end+1) = pos(2);
            end
            % Store NLOS metadata
            nlos_metadata.val_conditions(end+1) = nlos_code;
            nlos_metadata.val_scenarios{end+1} = scenario_name;
        end
    end
    
    % Progress update
    if mod(t, 10) == 0
        elapsed = toc;
        est_total = elapsed / t * config.n_trajectories;
        est_remaining = est_total - elapsed;
        fprintf('  Processed %d/%d trajectories (%.1f%%) - ETA: %.1f min\n', ...
                t, config.n_trajectories, 100*t/config.n_trajectories, est_remaining/60);
    end
    
    % Plot selected trajectories with NLOS label
    if config.output.generate_plots && mod(t, config.output.plot_frequency) == 0
        fig = figure('Visible', 'off');
        plot(all_trajectories{t}(:,1), all_trajectories{t}(:,2), 'b-', 'LineWidth', 2);
        hold on;
        plot(all_trajectories{t}(1,1), all_trajectories{t}(1,2), 'go', ...
             'MarkerSize', 10, 'MarkerFaceColor', 'g');
        plot(all_trajectories{t}(end,1), all_trajectories{t}(end,2), 'ro', ...
             'MarkerSize', 10, 'MarkerFaceColor', 'r');
        
        % Plot BSs
        plot(config.bs.positions(:,1), config.bs.positions(:,2), 'k^', ...
             'MarkerSize', 12, 'MarkerFaceColor', 'k');
        
        xlabel('X Position (m)'); ylabel('Y Position (m)');
        title(sprintf('Trajectory %d (%s, %s)', t, trajectory_labels{t}, ...
                     strrep(nlos_type, '_', ' ')));
        grid on; axis equal;
        xlim([config.scenario.bounds.x_min, config.scenario.bounds.x_max]);
        ylim([config.scenario.bounds.y_min, config.scenario.bounds.y_max]);
        
        ExperimentUtils.saveFigures(fig, sprintf('trajectory_%03d', t), trajectories_dir);
        close(fig);
    end
end

total_time = toc;
fprintf('\n✓ Simulation complete in %.1f minutes\n\n', total_time/60);

%% Save dataset
fprintf('Saving dataset...\n');

% Save training data
save(fullfile(dataset_dir, 'train_data.mat'), '-struct', 'train_data', '-v7.3');
fprintf('✓ Saved training data: %d samples\n', length(train_data.positions_x));

% Save validation data
save(fullfile(dataset_dir, 'val_data.mat'), '-struct', 'val_data', '-v7.3');
fprintf('✓ Saved validation data: %d samples\n', length(val_data.positions_x));

% Save NLOS metadata
save(fullfile(dataset_dir, 'nlos_metadata.mat'), '-struct', 'nlos_metadata', '-v7.3');
fprintf('✓ Saved NLOS metadata\n\n');

%% Generate NLOS analysis plots
if config.output.generate_nlos_analysis
    fprintf('Generating NLOS analysis...\n');
    
    % Plot 1: NLOS distribution
    fig1 = figure('Visible', 'off', 'Position', [100, 100, 1200, 800]);
    
    subplot(2, 2, 1);
    nlos_train_hist = histcounts(nlos_metadata.train_conditions, 0.5:1:4.5);
    bar([1 2 3 4], nlos_train_hist);
    set(gca, 'XTickLabel', {'Pure LOS', 'Light NLOS', 'Moderate NLOS', 'Heavy NLOS'});
    title('Training Set NLOS Distribution');
    ylabel('Number of Samples');
    grid on;
    
    subplot(2, 2, 2);
    nlos_val_hist = histcounts(nlos_metadata.val_conditions, 0.5:1:4.5);
    bar([1 2 3 4], nlos_val_hist);
    set(gca, 'XTickLabel', {'Pure LOS', 'Light NLOS', 'Moderate NLOS', 'Heavy NLOS'});
    title('Validation Set NLOS Distribution');
    ylabel('Number of Samples');
    grid on;
    
    % Plot 2: Feature comparison LOS vs NLOS
    subplot(2, 2, 3);
    los_mask = nlos_metadata.train_conditions == 1;
    nlos_mask = nlos_metadata.train_conditions > 1;
    histogram(train_data.RSRP(los_mask), 50, 'FaceAlpha', 0.5, 'DisplayName', 'LOS');
    hold on;
    histogram(train_data.RSRP(nlos_mask), 50, 'FaceAlpha', 0.5, 'DisplayName', 'NLOS');
    xlabel('RSRP (dBm)'); ylabel('Count');
    title('RSRP Distribution: LOS vs NLOS');
    legend; grid on;
    
    subplot(2, 2, 4);
    scatter(train_data.positions_x(los_mask), train_data.positions_y(los_mask), ...
            10, 'b', 'filled', 'DisplayName', 'LOS', 'MarkerFaceAlpha', 0.3);
    hold on;
    scatter(train_data.positions_x(nlos_mask), train_data.positions_y(nlos_mask), ...
            10, 'r', 'filled', 'DisplayName', 'NLOS', 'MarkerFaceAlpha', 0.3);
    xlabel('X Position (m)'); ylabel('Y Position (m)');
    title('Spatial Distribution: LOS vs NLOS');
    legend; grid on; axis equal;
    
    ExperimentUtils.saveFigures(fig1, 'nlos_analysis', analysis_dir);
    close(fig1);
    
    fprintf('✓ NLOS analysis plots saved\n\n');
end

%% Generate report
fprintf('Generating experiment report...\n');

fid = ExperimentUtils.createReportHeader(output_dir, ...
    'EXPERIMENT 11: NLOS-ENHANCED LARGE-SCALE DATA GENERATION');

fprintf(fid, '--- CONFIGURATION ---\n');
fprintf(fid, 'Total trajectories: %d\n', config.n_trajectories);
fprintf(fid, 'Timesteps per trajectory: %d\n', config.n_timesteps);
fprintf(fid, 'Train ratio: %.1f%%\n\n', 100*config.train_ratio);

fprintf(fid, '--- NLOS DISTRIBUTION ---\n');
for i = 1:length(nlos_types)
    type = nlos_types{i};
    fprintf(fid, '%s: %d trajectories (%.1f%%)\n', type, nlos_counts.(type), ...
            100*config.nlos_distribution.(type));
end

fprintf(fid, '\n--- TRAJECTORY DISTRIBUTION ---\n');
for i = 1:length(traj_types)
    type = traj_types{i};
    fprintf(fid, '%s: %d (%.1f%%)\n', type, traj_counts.(type), ...
            100*config.trajectory_distribution.(type));
end

fprintf(fid, '\n--- DATASET STATISTICS ---\n');
fprintf(fid, 'Training samples: %d\n', length(train_data.positions_x));
fprintf(fid, 'Validation samples: %d\n', length(val_data.positions_x));
fprintf(fid, 'Total samples: %d\n', length(train_data.positions_x) + length(val_data.positions_x));

% Calculate features per sample
n_wideband = 3;  % CQI_wb, RSRP, SINR_wb
n_per_sc = size(train_data.RSS_per_sc, 1);  % Should be 1024 * n_bs
n_features = n_wideband + 3 * n_per_sc;  % 3 types: RSS, SINR, H_mag
fprintf(fid, 'Features per sample: %d\n', n_features);
fprintf(fid, '  - Wideband: %d (CQI, RSRP, SINR)\n', n_wideband);
fprintf(fid, '  - Per-subcarrier: %d × 3 types = %d\n', n_per_sc, 3*n_per_sc);

fprintf(fid, '\n--- NLOS SAMPLE DISTRIBUTION ---\n');
fprintf(fid, 'Training:\n');
for i = 1:4
    count = sum(nlos_metadata.train_conditions == i);
    pct = 100 * count / length(nlos_metadata.train_conditions);
    fprintf(fid, '  Type %d: %d samples (%.1f%%)\n', i, count, pct);
end
fprintf(fid, 'Validation:\n');
for i = 1:4
    count = sum(nlos_metadata.val_conditions == i);
    pct = 100 * count / length(nlos_metadata.val_conditions);
    fprintf(fid, '  Type %d: %d samples (%.1f%%)\n', i, count, pct);
end

fprintf(fid, '\n--- FEATURE STATISTICS ---\n');
fprintf(fid, 'Training RSRP:\n');
fprintf(fid, '  Range: %.2f to %.2f dBm\n', min(train_data.RSRP), max(train_data.RSRP));
fprintf(fid, '  Mean: %.2f ± %.2f dBm\n', mean(train_data.RSRP), std(train_data.RSRP));
fprintf(fid, '  LOS samples: %.2f ± %.2f dBm\n', ...
        mean(train_data.RSRP(nlos_metadata.train_conditions==1)), ...
        std(train_data.RSRP(nlos_metadata.train_conditions==1)));
fprintf(fid, '  NLOS samples: %.2f ± %.2f dBm\n', ...
        mean(train_data.RSRP(nlos_metadata.train_conditions>1)), ...
        std(train_data.RSRP(nlos_metadata.train_conditions>1)));

fprintf(fid, '\n--- RUNTIME ---\n');
fprintf(fid, 'Total time: %.1f minutes\n', total_time/60);
fprintf(fid, 'Time per trajectory: %.2f seconds\n', total_time/config.n_trajectories);
fprintf(fid, 'Samples per second: %.2f\n', ...
        (length(train_data.positions_x) + length(val_data.positions_x)) / total_time);

files_generated = {
    'train_data.mat',
    'val_data.mat',
    'nlos_metadata.mat',
    'nlos_analysis.png',
    'experiment_report.txt'
};
if config.output.generate_plots
    files_generated{end+1} = sprintf('trajectory_*.png (every %d)', config.output.plot_frequency);
end

ExperimentUtils.closeReport(fid, files_generated);
fprintf('✓ Report saved\n');

%% Summary
fprintf('\n========================================\n');
fprintf('EXPERIMENT 11 COMPLETE!\n');
fprintf('========================================\n\n');
fprintf('📁 Output directory: %s\n', output_dir);
fprintf('📊 Training samples: %d\n', length(train_data.positions_x));
fprintf('📊 Validation samples: %d\n', length(val_data.positions_x));
fprintf('🎯 NLOS Distribution:\n');
fprintf('   - Pure LOS: %d samples (%.1f%%)\n', ...
        sum(nlos_metadata.train_conditions==1) + sum(nlos_metadata.val_conditions==1), ...
        100 * (sum(nlos_metadata.train_conditions==1) + sum(nlos_metadata.val_conditions==1)) / ...
        (length(nlos_metadata.train_conditions) + length(nlos_metadata.val_conditions)));
fprintf('   - Light NLOS: %d samples (%.1f%%)\n', ...
        sum(nlos_metadata.train_conditions==2) + sum(nlos_metadata.val_conditions==2), ...
        100 * (sum(nlos_metadata.train_conditions==2) + sum(nlos_metadata.val_conditions==2)) / ...
        (length(nlos_metadata.train_conditions) + length(nlos_metadata.val_conditions)));
fprintf('   - Moderate NLOS: %d samples (%.1f%%)\n', ...
        sum(nlos_metadata.train_conditions==3) + sum(nlos_metadata.val_conditions==3), ...
        100 * (sum(nlos_metadata.train_conditions==3) + sum(nlos_metadata.val_conditions==3)) / ...
        (length(nlos_metadata.train_conditions) + length(nlos_metadata.val_conditions)));
fprintf('   - Heavy NLOS: %d samples (%.1f%%)\n', ...
        sum(nlos_metadata.train_conditions==4) + sum(nlos_metadata.val_conditions==4), ...
        100 * (sum(nlos_metadata.train_conditions==4) + sum(nlos_metadata.val_conditions==4)) / ...
        (length(nlos_metadata.train_conditions) + length(nlos_metadata.val_conditions)));
fprintf('⏱️  Total time: %.1f minutes\n\n', total_time/60);
fprintf('🎯 Next step: Train ML models on NLOS-enhanced dataset!\n');
fprintf('   Update ml_training/config.py with this dataset path\n');
fprintf('   Compare performance with LOS-only (exp10) results\n\n');
