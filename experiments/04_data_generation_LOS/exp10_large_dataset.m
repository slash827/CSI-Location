%% Experiment 10: Large-Scale Dataset Generation
% Generate diverse CSI dataset with 500+ trajectories for ML training
%
% Output: 32,000+ training samples, 8,000+ validation samples
% Expected runtime: 30-60 minutes

clear; close all; clc;

%% Setup
fprintf('========================================\n');
fprintf('EXP10: LARGE-SCALE DATA GENERATION\n');
fprintf('========================================\n\n');

% Add utils to path (correct relative path from experiments/04_data_generation/)
script_dir = fileparts(mfilename('fullpath'));
project_root = fileparts(fileparts(script_dir));
utils_path = fullfile(project_root, 'utils');
addpath(utils_path);

% Load configuration
run('config_large_dataset.m');

% Setup output directory using ExperimentUtils
output_dir = ExperimentUtils.createResultsDir('exp10');
dataset_dir = fullfile(output_dir, 'dataset');
trajectories_dir = fullfile(output_dir, 'trajectories');
mkdir(dataset_dir);
mkdir(trajectories_dir);

fprintf('Output directory: %s\n\n', output_dir);

%% Initialize QuaDRiGa
fprintf('Initializing QuaDRiGa...\n');

% Create layout
l = qd_layout;
l.set_scenario(config.scenario.type);

% Configure base stations
l.no_tx = size(config.bs.positions, 1);
for i = 1:l.no_tx
    l.tx_position(:, i) = config.bs.positions(i, :)';
    l.tx_array(i) = qd_arrayant('omni');
end

fprintf('✓ Created %d base stations\n', l.no_tx);

%% Calculate trajectory counts
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
total = sum(structfun(@(x) x, traj_counts));
if total ~= config.n_trajectories
    diff = config.n_trajectories - total;
    traj_counts.linear = traj_counts.linear + diff;
    fprintf('  Adjusted linear: %d (rounding correction: %+d)\n', ...
            traj_counts.linear, diff);
end

fprintf('\nTotal trajectories: %d\n\n', config.n_trajectories);

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

% Generate each trajectory type
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
                
                % Ensure in bounds
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

%% Simulate CSI for all trajectories
fprintf('Simulating CSI data with QuaDRiGa...\n');
fprintf('This will take 30-60 minutes...\n\n');

% Initialize storage
all_features = struct();
all_positions = struct();

% Split into train and validation
n_train_per_traj = round(config.n_timesteps * config.train_ratio);
n_val_per_traj = config.n_timesteps - n_train_per_traj;

train_data = struct();
val_data = struct();

tic;

for t = 1:config.n_trajectories
    % Create track
    track_positions = [all_trajectories{t}'; ...
                      ones(1, config.n_timesteps) * config.ue.height];
    
    % Create track object
    track = qd_track('linear', 0, pi/4);
    track.positions = track_positions;
    track.scenario = config.scenario.type;
    
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
        
        % Wideband features (average across all BSs)
        features.CQI_wb = mean(10*log10(abs(all_h_freq).^2 + eps));
        features.RSRP = 10*log10(mean(abs(all_h_freq).^2));
        features.SINR_wb = features.RSRP - (-90);  % Simplified
        
        % Per-subcarrier features (concatenated from all BSs)
        features.RSS_per_sc = 10*log10(abs(all_h_freq).^2 + eps);
        features.SINR_per_sc = features.RSS_per_sc - (-90);
        features.H_mag_per_sc = abs(all_h_freq);
        
        % Position
        pos = [track_positions(1, ts); track_positions(2, ts)];
        
        % Store in train or val
        if ts <= n_train_per_traj
            if t == 1 && ts == 1
                % Initialize
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
    
    % Plot selected trajectories
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
        title(sprintf('Trajectory %d (%s)', t, trajectory_labels{t}));
        grid on; axis equal;
        xlim([config.scenario.bounds.x_min, config.scenario.bounds.x_max]);
        ylim([config.scenario.bounds.y_min, config.scenario.bounds.y_max]);
        
        % Save using ExperimentUtils
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

%% Generate report
fprintf('\nGenerating experiment report...\n');

% Use ExperimentUtils to create report header
fid = ExperimentUtils.createReportHeader(output_dir, 'EXPERIMENT 10: LARGE-SCALE DATA GENERATION');

fprintf(fid, '--- CONFIGURATION ---\n');
fprintf(fid, 'Total trajectories: %d\n', config.n_trajectories);
fprintf(fid, 'Timesteps per trajectory: %d\n', config.n_timesteps);
fprintf(fid, 'Train ratio: %.1f%%\n\n', 100*config.train_ratio);

fprintf(fid, '--- TRAJECTORY DISTRIBUTION ---\n');
for i = 1:length(traj_types)
    type = traj_types{i};
    fprintf(fid, '%s: %d (%.1f%%)\n', type, traj_counts.(type), ...
            100*config.trajectory_distribution.(type));
end

fprintf(fid, '\n--- DATASET STATISTICS ---\n');
fprintf(fid, 'Training samples: %d\n', length(train_data.positions_x));
fprintf(fid, 'Validation samples: %d\n', length(val_data.positions_x));
fprintf(fid, 'Total samples: %d\n', length(train_data.positions_x) + length(val_data.positions_x));
fprintf(fid, 'Features per sample: 771 (3 wideband + 768 per-subcarrier)\n\n');

fprintf(fid, '--- POSITION STATISTICS ---\n');
fprintf(fid, 'Training positions:\n');
fprintf(fid, '  X: %.2f to %.2f m (mean: %.2f ± %.2f)\n', ...
        min(train_data.positions_x), max(train_data.positions_x), ...
        mean(train_data.positions_x), std(train_data.positions_x));
fprintf(fid, '  Y: %.2f to %.2f m (mean: %.2f ± %.2f)\n', ...
        min(train_data.positions_y), max(train_data.positions_y), ...
        mean(train_data.positions_y), std(train_data.positions_y));

fprintf(fid, '\nValidation positions:\n');
fprintf(fid, '  X: %.2f to %.2f m (mean: %.2f ± %.2f)\n', ...
        min(val_data.positions_x), max(val_data.positions_x), ...
        mean(val_data.positions_x), std(val_data.positions_x));
fprintf(fid, '  Y: %.2f to %.2f m (mean: %.2f ± %.2f)\n\n', ...
        min(val_data.positions_y), max(val_data.positions_y), ...
        mean(val_data.positions_y), std(val_data.positions_y));

fprintf(fid, '--- RUNTIME ---\n');
fprintf(fid, 'Total time: %.1f minutes\n', total_time/60);
fprintf(fid, 'Time per trajectory: %.2f seconds\n\n', total_time/config.n_trajectories);

% Use ExperimentUtils to close report
files_generated = {
    'train_data.mat',
    'val_data.mat',
    'experiment_report.txt'
};
if config.output.generate_plots
    files_generated{end+1} = sprintf('trajectory_*.png (every %d)', config.output.plot_frequency);
    files_generated{end+1} = sprintf('trajectory_*.fig (every %d)', config.output.plot_frequency);
end

ExperimentUtils.closeReport(fid, files_generated);
fprintf('✓ Report saved\n');

%% Summary
fprintf('\n========================================\n');
fprintf('EXPERIMENT 10 COMPLETE!\n');
fprintf('========================================\n\n');
fprintf('📁 Output directory: %s\n', output_dir);
fprintf('📊 Training samples: %d\n', length(train_data.positions_x));
fprintf('📊 Validation samples: %d\n', length(val_data.positions_x));
fprintf('⏱️  Total time: %.1f minutes\n\n', total_time/60);
fprintf('🎯 Next step: Train ML models on this dataset!\n');
fprintf('   Update ml_training/config.py with this dataset path\n\n');
