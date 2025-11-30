%% Experiment 13: Urban Mixed Indoor/Outdoor Large-Scale Dataset Generation
% Generate diverse CSI dataset with realistic urban scenarios for robust ML training
%
% Key Features:
%   - 300m × 300m urban area (14× larger than exp11)
%   - 6 BSs: 2 macro + 2 outdoor small + 2 indoor small
%   - 3.0 GHz frequency (better penetration)
%   - Zone-based NLOS assignment (outdoor open/obstructed, indoor light/heavy)
%   - Variable UE heights (0.8-1.8m)
%   - Stop-and-go trajectories
%
% Output: 160,000 training samples, 40,000 validation samples
% Expected runtime: 2-3 hours

clear; close all; clc;

%% Setup
fprintf('========================================\n');
fprintf('EXP13: URBAN MIXED SCENARIO GENERATION\n');
fprintf('========================================\n\n');

% Add utils to path
script_dir = fileparts(mfilename('fullpath'));
project_root = fileparts(fileparts(script_dir));
utils_path = fullfile(project_root, 'utils');
addpath(utils_path);
addpath(script_dir);  % Add current directory for trajectory generators

% Load configuration
config_urban_dataset;

% Display mode
if config.DEBUG_MODE
    fprintf('🐛 DEBUG MODE: Running quick test\n');
    fprintf('   - Trajectories: %d (instead of 2000)\n', config.n_trajectories);
    fprintf('   - Samples/traj: %d (instead of 100)\n', config.n_timesteps);
    fprintf('   - Total samples: ~%d (instead of 200K)\n', config.n_trajectories * config.n_timesteps);
    fprintf('   - Estimated time: 1-2 minutes\n');
    fprintf('   ⚠️  Set config.DEBUG_MODE = false for full dataset\n\n');
else
    fprintf('🏭 PRODUCTION MODE: Full dataset generation\n');
    fprintf('   - Estimated time: 2-3 hours\n\n');
end

% Setup output directory
if config.APPEND_MODE && ~isempty(config.APPEND_TO_DIR)
    % Append mode: use existing directory
    output_dir = fullfile(fileparts(fileparts(script_dir)), 'results', config.APPEND_TO_DIR);
    if ~exist(output_dir, 'dir')
        error('Append directory not found: %s', output_dir);
    end
    fprintf('\n🔗 APPEND MODE: Adding to existing run\n');
    fprintf('   Directory: %s\n\n', config.APPEND_TO_DIR);
else
    % Normal mode: create new directory
    output_dir = ExperimentUtils.createResultsDir('exp13');
end

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

%% Calculate trajectory counts
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
    traj_diff = config.n_trajectories - total_traj;
    traj_counts.linear = traj_counts.linear + traj_diff;
    fprintf('  Adjusted linear: %d (rounding correction: %+d)\n', ...
            traj_counts.linear, traj_diff);
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
                distance = 100 + 80*rand();
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
                
            case 'stop_and_go'
                start_pos = random_pos();
                
                traj = generate_stop_and_go_trajectory(start_pos, config.n_timesteps, ...
                    'segment_length', config.stop_and_go.segment_length, ...
                    'stop_duration', config.stop_and_go.stop_duration, ...
                    'n_stops', config.stop_and_go.n_stops, ...
                    'bounds', [config.scenario.bounds.x_min, config.scenario.bounds.x_max, ...
                              config.scenario.bounds.y_min, config.scenario.bounds.y_max]);
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

%% Simulate CSI for all trajectories with zone-based NLOS
if config.DEBUG_MODE
    fprintf('Simulating CSI data with zone-based NLOS (DEBUG MODE)...\n');
    fprintf('This will take 1-2 minutes...\n\n');
else
    fprintf('Simulating CSI data with zone-based NLOS...\n');
    fprintf('This will take 2-3 hours...\n\n');
end

% Initialize storage
n_train_per_traj = round(config.n_timesteps * config.train_ratio);
n_val_per_traj = config.n_timesteps - n_train_per_traj;

% Checkpoint file for resume capability
checkpoint_file = fullfile(dataset_dir, 'checkpoint.mat');

% Check if resuming from checkpoint or appending to previous run
if exist(checkpoint_file, 'file')
    fprintf('\n⚠️  Found existing checkpoint! Loading...\n');
    checkpoint = load(checkpoint_file);
    train_data = checkpoint.train_data;
    val_data = checkpoint.val_data;
    metadata = checkpoint.metadata;
    start_traj = checkpoint.last_completed_traj + 1;
    fprintf('✓ Resuming from trajectory %d/%d\n\n', start_traj, config.n_trajectories);
elseif config.APPEND_MODE
    % Append mode: load existing completed dataset
    train_file = fullfile(dataset_dir, 'train_data.mat');
    val_file = fullfile(dataset_dir, 'val_data.mat');
    meta_file = fullfile(dataset_dir, 'metadata.mat');
    
    if ~exist(train_file, 'file') || ~exist(val_file, 'file') || ~exist(meta_file, 'file')
        error('Append mode requires existing dataset files in: %s', dataset_dir);
    end
    
    fprintf('\n📂 Loading existing dataset for append...\n');
    train_data = load(train_file);
    val_data = load(val_file);
    metadata = load(meta_file);
    
    existing_samples = length(train_data.positions_x) + length(val_data.positions_x);
    fprintf('✓ Loaded %d existing samples\n', existing_samples);
    fprintf('✓ Will add %d new samples\n', config.n_trajectories * config.n_timesteps);
    fprintf('✓ Total after append: %d samples\n\n', existing_samples + config.n_trajectories * config.n_timesteps);
    
    start_traj = 1;
else
    % Initialize from scratch
    train_data = struct();
    val_data = struct();
    metadata = struct();
    metadata.train_zones = [];          % Zone type for each train sample
    metadata.val_zones = [];            % Zone type for each val sample
    metadata.train_nlos_conditions = []; % NLOS type for each train sample
    metadata.val_nlos_conditions = [];   % NLOS type for each val sample
    metadata.train_scenarios = {};       % Scenario name for each train sample
    metadata.val_scenarios = {};         % Scenario name for each val sample
    metadata.train_ue_heights = [];      % UE height for each train sample
    metadata.val_ue_heights = [];        % UE height for each val sample
    start_traj = 1;
    fprintf('Starting fresh generation...\n\n');
end

% Map zone and NLOS types to numeric codes
zone_type_map = struct('outdoor_open', 1, 'outdoor_obstructed', 2, 'indoor_light', 3, 'indoor_heavy', 4);
nlos_type_map = struct('pure_los', 1, 'light_nlos', 2, 'moderate_nlos', 3, 'heavy_nlos', 4);

tic;
last_checkpoint_time = tic;  % Track time for periodic checkpoints

for t = start_traj:config.n_trajectories
    % Generate variable UE height for this trajectory
    ue_height = config.ue.height_min + (config.ue.height_max - config.ue.height_min) * rand();
    
    % Pre-assign zone/NLOS for each position in trajectory
    trajectory_zones = zeros(1, config.n_timesteps);
    trajectory_nlos = zeros(1, config.n_timesteps);
    trajectory_scenarios = cell(1, config.n_timesteps);
    
    track_positions = [all_trajectories{t}'; ...
                      ones(1, config.n_timesteps) * ue_height];
    
    % Pre-determine zones and NLOS for entire trajectory
    for ts = 1:config.n_timesteps
        pos_x = track_positions(1, ts);
        pos_y = track_positions(2, ts);
        zone_type = assign_zone(pos_x, pos_y, config);
        trajectory_zones(ts) = zone_type_map.(zone_type);
        
        nlos_type = assign_nlos_from_zone(zone_type, config);
        trajectory_nlos(ts) = nlos_type_map.(nlos_type);
        trajectory_scenarios{ts} = config.nlos_scenarios.(nlos_type);
    end
    
    % Use most common scenario for entire trajectory (for efficiency)
    [unique_scenarios, ~, idx] = unique(trajectory_scenarios);
    counts = histcounts(idx, 1:(length(unique_scenarios)+1));
    [~, max_idx] = max(counts);
    scenario_name = unique_scenarios{max_idx};
    
    % Create track with single scenario
    track = qd_track('linear', 0, pi/4);
    track.positions = track_positions;
    track.scenario = scenario_name;
    
    % Set scenario and generate channels ONCE for entire trajectory
    l.track(1) = track;
    l.set_scenario(scenario_name);
    c = l.get_channels();
    
    % Process each timestep - extract from pre-generated channels
    for ts = 1:config.n_timesteps
        % Get zone and NLOS codes for this position
        zone_code = trajectory_zones(ts);
        nlos_code = trajectory_nlos(ts);
        
        % Extract features for each time step
        all_h_freq = [];
        
        % Loop through each BS
        for bs_idx = 1:length(c)
            % Get channel from this BS at this time step
            h_freq = c(bs_idx).fr(config.scenario.bandwidth, config.scenario.n_subcarriers, ts);
            all_h_freq = [all_h_freq; h_freq(:)];
        end
        
        % Extract features
        features = struct();
        
        % Wideband features
        features.CQI_wb = mean(10*log10(abs(all_h_freq).^2 + eps));
        features.RSRP = 10*log10(mean(abs(all_h_freq).^2));
        features.SINR_wb = features.RSRP - (-90);
        
        % Per-subcarrier features (store as single precision to save memory)
        features.RSS_per_sc = single(10*log10(abs(all_h_freq).^2 + eps));
        features.SINR_per_sc = single(features.RSS_per_sc - (-90));
        features.H_mag_per_sc = single(abs(all_h_freq));
        
        % Position
        pos = [track_positions(1, ts); track_positions(2, ts)];
        
        % Store in train or val with metadata
        if ts <= n_train_per_traj
            if t == start_traj && ts == 1 && ~isfield(train_data, 'CQI_wb')
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
            % Store metadata
            metadata.train_zones(end+1) = zone_code;
            metadata.train_nlos_conditions(end+1) = nlos_code;
            metadata.train_scenarios{end+1} = trajectory_scenarios{ts};
            metadata.train_ue_heights(end+1) = ue_height;
        else
            if t == start_traj && ts == n_train_per_traj + 1 && ~isfield(val_data, 'CQI_wb')
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
            % Store metadata
            metadata.val_zones(end+1) = zone_code;
            metadata.val_nlos_conditions(end+1) = nlos_code;
            metadata.val_scenarios{end+1} = trajectory_scenarios{ts};
            metadata.val_ue_heights(end+1) = ue_height;
        end
    end
    
    % Progress update - Show every 10 trajectories for better visibility
    if mod(t, 10) == 0 || t == start_traj
        elapsed = toc;
        completed = t - start_traj + 1;
        remaining = config.n_trajectories - t;
        est_total = elapsed / completed * (config.n_trajectories - start_traj + 1);
        est_remaining = est_total - elapsed;
        current_time = datetime('now');
        eta_time = current_time + minutes(est_remaining);
        
        fprintf('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n');
        fprintf('📊 PROGRESS: %d/%d trajectories (%.1f%% complete)\n', ...
                t, config.n_trajectories, 100*t/config.n_trajectories);
        fprintf('⏱️  Time elapsed: %.1f min (%.2f hours)\n', elapsed/60, elapsed/3600);
        fprintf('⏳ Estimated remaining: %.1f min (%.2f hours)\n', est_remaining/60, est_remaining/3600);
        fprintf('🎯 ETA: %s\n', datestr(eta_time, 'HH:MM:SS'));
        fprintf('📈 Rate: %.2f trajectories/min (%.2f sec/trajectory)\n', ...
                completed/elapsed*60, elapsed/completed);
        fprintf('💾 Samples generated: %d training + %d validation = %d total\n', ...
                t * round(config.n_timesteps * config.train_ratio), ...
                t * (config.n_timesteps - round(config.n_timesteps * config.train_ratio)), ...
                t * config.n_timesteps);
        fprintf('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n');
    end
    
    % Save checkpoint every 50 trajectories or every 30 minutes
    checkpoint_elapsed = toc(last_checkpoint_time);
    if mod(t, 50) == 0 || checkpoint_elapsed > 1800  % 50 traj or 30 min
        fprintf('  💾 Saving checkpoint at trajectory %d...\n', t);
        checkpoint = struct();
        checkpoint.train_data = train_data;
        checkpoint.val_data = val_data;
        checkpoint.metadata = metadata;
        checkpoint.last_completed_traj = t;
        checkpoint.timestamp = datetime('now');
        save(checkpoint_file, '-struct', 'checkpoint', '-v7.3');
        last_checkpoint_time = tic;
        fprintf('  ✓ Checkpoint saved\n');
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
        
        ExperimentUtils.saveFigures(fig, sprintf('trajectory_%04d', t), trajectories_dir);
        close(fig);
    end
end

total_time = toc;
fprintf('\n✓ Simulation complete in %.1f minutes (%.2f hours)\n\n', total_time/60, total_time/3600);

%% Save dataset
fprintf('Saving dataset...\n');

% Delete checkpoint file (no longer needed)
if exist(checkpoint_file, 'file')
    delete(checkpoint_file);
    fprintf('✓ Cleaned up checkpoint file\n');
end

% Save training data
save(fullfile(dataset_dir, 'train_data.mat'), '-struct', 'train_data', '-v7.3');
fprintf('✓ Saved training data: %d samples\n', length(train_data.positions_x));

% Save validation data
save(fullfile(dataset_dir, 'val_data.mat'), '-struct', 'val_data', '-v7.3');
fprintf('✓ Saved validation data: %d samples\n', length(val_data.positions_x));

% Save metadata
save(fullfile(dataset_dir, 'metadata.mat'), '-struct', 'metadata', '-v7.3');
fprintf('✓ Saved metadata\n\n');

%% Generate analysis plots
if config.output.generate_zone_analysis
    fprintf('Generating zone and NLOS analysis...\n');
    
    fig1 = figure('Visible', 'off', 'Position', [100, 100, 1600, 1000]);
    
    % Zone distribution
    subplot(2, 3, 1);
    zone_train_hist = histcounts(metadata.train_zones, 0.5:1:4.5);
    bar([1 2 3 4], zone_train_hist);
    set(gca, 'XTickLabel', {'Outdoor\nOpen', 'Outdoor\nObstructed', 'Indoor\nLight', 'Indoor\nHeavy'});
    title('Training Set Zone Distribution');
    ylabel('Number of Samples');
    grid on;
    
    subplot(2, 3, 2);
    nlos_train_hist = histcounts(metadata.train_nlos_conditions, 0.5:1:4.5);
    bar([1 2 3 4], nlos_train_hist);
    set(gca, 'XTickLabel', {'Pure\nLOS', 'Light\nNLOS', 'Moderate\nNLOS', 'Heavy\nNLOS'});
    title('Training Set NLOS Distribution');
    ylabel('Number of Samples');
    grid on;
    
    % UE height distribution
    subplot(2, 3, 3);
    histogram(metadata.train_ue_heights, 50);
    xlabel('UE Height (m)'); ylabel('Count');
    title('Training Set UE Height Distribution');
    grid on;
    
    % Spatial distribution colored by zone
    subplot(2, 3, 4);
    scatter(train_data.positions_x, train_data.positions_y, 5, metadata.train_zones, 'filled', 'MarkerFaceAlpha', 0.3);
    colormap(gca, [0.8 0.95 0.8; 0.95 0.9 0.7; 0.85 0.9 0.95; 0.75 0.75 0.8]);
    colorbar('Ticks', [1 2 3 4], 'TickLabels', {'Outdoor Open', 'Outdoor Obst', 'Indoor Light', 'Indoor Heavy'});
    xlabel('X Position (m)'); ylabel('Y Position (m)');
    title('Spatial Distribution by Zone');
    grid on; axis equal;
    
    % RSRP by zone
    subplot(2, 3, 5);
    zones_list = [1 2 3 4];
    zone_names = {'Outdoor\nOpen', 'Outdoor\nObst', 'Indoor\nLight', 'Indoor\nHeavy'};
    rsrp_by_zone = arrayfun(@(z) mean(train_data.RSRP(metadata.train_zones == z)), zones_list);
    bar(zones_list, rsrp_by_zone);
    set(gca, 'XTickLabel', zone_names);
    ylabel('Mean RSRP (dBm)');
    title('Mean RSRP by Zone');
    grid on;
    
    % RSRP by NLOS condition
    subplot(2, 3, 6);
    nlos_list = [1 2 3 4];
    nlos_names = {'Pure\nLOS', 'Light\nNLOS', 'Moderate\nNLOS', 'Heavy\nNLOS'};
    rsrp_by_nlos = arrayfun(@(n) mean(train_data.RSRP(metadata.train_nlos_conditions == n)), nlos_list);
    bar(nlos_list, rsrp_by_nlos);
    set(gca, 'XTickLabel', nlos_names);
    ylabel('Mean RSRP (dBm)');
    title('Mean RSRP by NLOS Condition');
    grid on;
    
    ExperimentUtils.saveFigures(fig1, 'zone_nlos_analysis', analysis_dir);
    close(fig1);
    
    fprintf('✓ Analysis plots saved\n\n');
end

%% Generate report
fprintf('Generating experiment report...\n');

fid = ExperimentUtils.createReportHeader(output_dir, ...
    'EXPERIMENT 13: URBAN MIXED INDOOR/OUTDOOR DATA GENERATION');

fprintf(fid, '--- CONFIGURATION ---\n');
fprintf(fid, 'Area: %d × %d m² (%.1f hectares)\n', ...
    config.scenario.bounds.x_max - config.scenario.bounds.x_min, ...
    config.scenario.bounds.y_max - config.scenario.bounds.y_min, ...
    ((config.scenario.bounds.x_max - config.scenario.bounds.x_min) * ...
     (config.scenario.bounds.y_max - config.scenario.bounds.y_min)) / 10000);
fprintf(fid, 'Total trajectories: %d\n', config.n_trajectories);
fprintf(fid, 'Timesteps per trajectory: %d\n', config.n_timesteps);
fprintf(fid, 'Train ratio: %.1f%%\n\n', 100*config.train_ratio);

fprintf(fid, '--- FREQUENCY CONFIGURATION ---\n');
fprintf(fid, 'Center frequency: %.1f GHz\n', config.scenario.frequency / 1e9);
fprintf(fid, 'Bandwidth: %.0f MHz\n', config.scenario.bandwidth / 1e6);
fprintf(fid, 'Subcarriers: %d\n', config.scenario.n_subcarriers);
fprintf(fid, 'Subcarrier spacing: %.2f kHz\n\n', (config.scenario.bandwidth / config.scenario.n_subcarriers) / 1e3);

fprintf(fid, '--- BASE STATION DEPLOYMENT ---\n');
fprintf(fid, 'Total BSs: %d\n', size(config.bs.positions, 1));
for i = 1:size(config.bs.positions, 1)
    fprintf(fid, 'BS%d (%s): (%.0f, %.0f, %.0f)m, %d dBm\n', ...
        i, config.bs.types{i}, ...
        config.bs.positions(i, 1), config.bs.positions(i, 2), config.bs.positions(i, 3), ...
        config.bs.tx_power_dbm(i));
end

fprintf(fid, '\n--- TRAJECTORY DISTRIBUTION ---\n');
types = fieldnames(config.trajectory_distribution);
for i = 1:length(types)
    type = types{i};
    fprintf(fid, '%s: %d (%.1f%%)\n', type, traj_counts.(type), ...
            100*config.trajectory_distribution.(type));
end

fprintf(fid, '\n--- DATASET STATISTICS ---\n');
fprintf(fid, 'Training samples: %d\n', length(train_data.positions_x));
fprintf(fid, 'Validation samples: %d\n', length(val_data.positions_x));
fprintf(fid, 'Total samples: %d\n', length(train_data.positions_x) + length(val_data.positions_x));

% Calculate features per sample
n_wideband = 3;
n_per_sc = size(train_data.RSS_per_sc, 1);
n_features = n_wideband + 3 * n_per_sc;
fprintf(fid, 'Features per sample: %d\n', n_features);
fprintf(fid, '  - Wideband: %d (CQI, RSRP, SINR)\n', n_wideband);
fprintf(fid, '  - Per-subcarrier: %d × 3 types = %d\n', n_per_sc, 3*n_per_sc);

fprintf(fid, '\n--- ZONE DISTRIBUTION ---\n');
fprintf(fid, 'Training:\n');
for i = 1:4
    count = sum(metadata.train_zones == i);
    pct = 100 * count / length(metadata.train_zones);
    fprintf(fid, '  Zone %d: %d samples (%.1f%%)\n', i, count, pct);
end

fprintf(fid, '\n--- NLOS DISTRIBUTION ---\n');
fprintf(fid, 'Training:\n');
for i = 1:4
    count = sum(metadata.train_nlos_conditions == i);
    pct = 100 * count / length(metadata.train_nlos_conditions);
    fprintf(fid, '  NLOS Type %d: %d samples (%.1f%%)\n', i, count, pct);
end

fprintf(fid, '\n--- UE HEIGHT STATISTICS ---\n');
fprintf(fid, 'Training:\n');
fprintf(fid, '  Range: %.2f - %.2f m\n', min(metadata.train_ue_heights), max(metadata.train_ue_heights));
fprintf(fid, '  Mean: %.2f ± %.2f m\n', mean(metadata.train_ue_heights), std(metadata.train_ue_heights));

fprintf(fid, '\n--- FEATURE STATISTICS ---\n');
fprintf(fid, 'Training RSRP:\n');
fprintf(fid, '  Range: %.2f to %.2f dBm\n', min(train_data.RSRP), max(train_data.RSRP));
fprintf(fid, '  Mean: %.2f ± %.2f dBm\n', mean(train_data.RSRP), std(train_data.RSRP));

fprintf(fid, '\n--- RUNTIME ---\n');
fprintf(fid, 'Total time: %.1f minutes (%.2f hours)\n', total_time/60, total_time/3600);
fprintf(fid, 'Time per trajectory: %.2f seconds\n', total_time/config.n_trajectories);
fprintf(fid, 'Samples per second: %.2f\n', ...
        (length(train_data.positions_x) + length(val_data.positions_x)) / total_time);

files_generated = {
    'train_data.mat',
    'val_data.mat',
    'metadata.mat',
    'zone_nlos_analysis.png',
    'experiment_report.txt'
};
if config.output.generate_plots
    files_generated{end+1} = sprintf('trajectory_*.png (every %d)', config.output.plot_frequency);
end

ExperimentUtils.closeReport(fid, files_generated);
fprintf('✓ Report saved\n');

%% Summary
fprintf('\n========================================\n');
if config.DEBUG_MODE
    fprintf('DEBUG RUN COMPLETE!\n');
else
    fprintf('EXPERIMENT 13 COMPLETE!\n');
end
fprintf('========================================\n\n');
fprintf('📁 Output directory: %s\n', output_dir);
fprintf('📊 Training samples: %d\n', length(train_data.positions_x));
fprintf('📊 Validation samples: %d\n', length(val_data.positions_x));
fprintf('🏙️  Area: %d × %d m² (%.1f hectares)\n', ...
    config.scenario.bounds.x_max - config.scenario.bounds.x_min, ...
    config.scenario.bounds.y_max - config.scenario.bounds.y_min, ...
    ((config.scenario.bounds.x_max - config.scenario.bounds.x_min) * ...
     (config.scenario.bounds.y_max - config.scenario.bounds.y_min)) / 10000);
fprintf('📡 BSs: %d (2 macro + 2 outdoor + 2 indoor)\n', size(config.bs.positions, 1));
fprintf('📶 Frequency: %.1f GHz, Subcarriers: %d\n', config.scenario.frequency/1e9, config.scenario.n_subcarriers);
fprintf('⏱️  Total time: %.1f minutes (%.2f hours)\n\n', total_time/60, total_time/3600);

if config.DEBUG_MODE
    fprintf('🐛 DEBUG MODE was active - small test completed\n');
    fprintf('   To generate full dataset:\n');
    fprintf('   1. Edit config_urban_dataset.m\n');
    fprintf('   2. Set: config.DEBUG_MODE = false\n');
    fprintf('   3. Re-run: exp13_urban_dataset\n\n');
else
    fprintf('🎯 Next step: Train ML models on urban dataset!\n');
    fprintf('   Compare with exp10 (LOS) and exp11 (NLOS)\n\n');
end

%% Helper Functions

function zone = assign_zone(~, ~, config)
    % Randomly assign zone based on configured distribution
    % Note: x, y parameters reserved for future spatial-based assignment
    zones = fieldnames(config.zone_distribution);
    probs = structfun(@(f) f, config.zone_distribution);
    cumprobs = cumsum(probs);
    r = rand();
    idx = find(r <= cumprobs, 1, 'first');
    zone = zones{idx};
end

function nlos_type = assign_nlos_from_zone(zone_type, config)
    % Assign NLOS condition based on zone
    zone_mapping = config.zone_nlos_mapping.(zone_type);
    nlos_types = fieldnames(zone_mapping);
    probs = structfun(@(f) f, zone_mapping);
    cumprobs = cumsum(probs);
    r = rand();
    idx = find(r <= cumprobs, 1, 'first');
    nlos_type = nlos_types{idx};
end
