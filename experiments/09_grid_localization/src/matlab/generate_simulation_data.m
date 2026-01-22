%% Grid Localization Data Generation
% This script generates channel simulation data using QuaDRiGa
% All analysis (train/test, models, evaluation) is done in Python
%
% Output: simulation_data.mat containing:
%   - metrics (RSS, SINR, CQI)
%   - walk_path (locations)
%   - config (grid, neighbors, etc.)

clear; clc; close all;

%% Setup paths
script_dir = fileparts(mfilename('fullpath'));
experiment_root = fileparts(fileparts(script_dir));  % experiments/09_grid_localization
workspace_root = fileparts(fileparts(experiment_root));  % CSI-Location
utils_path = fullfile(workspace_root, 'utils');  % Utils at workspace root
addpath(utils_path);

fprintf('=== Grid Localization Data Generation ===\n\n');

%% Load Configuration
% Config file is in ../../configs/ relative to src/matlab/
config_file = fullfile(experiment_root, 'configs', 'data_generation_config.jsonc');
if ~exist(config_file, 'file')
    error('Configuration file not found: %s', config_file);
end

fprintf('Loading configuration from: data_generation_config.jsonc\n');
config_json = read_jsonc(config_file);

%% Build configuration
config = struct();
config.grid_size = config_json.grid.size;
config.spacing = config_json.grid.spacing;
config.ue_height = config_json.grid.ue_height;
config.grid_offset = config_json.grid.grid_offset;
config.position_jitter = config_json.grid.position_jitter;

% Neighbor connectivity (4 or 8)
if isfield(config_json.grid, 'neighbor_connectivity')
    config.neighbor_connectivity = config_json.grid.neighbor_connectivity;
else
    config.neighbor_connectivity = 4;  % Default to 4-neighbors
end

% Calculate n_steps
if isfield(config_json.movement, 'steps_per_point')
    config.steps_per_point = config_json.movement.steps_per_point;
    config.n_steps = config.steps_per_point * config.grid_size * config.grid_size;
    fprintf('Using steps_per_point=%d -> n_steps=%d (%dx%d grid)\n', ...
        config.steps_per_point, config.n_steps, config.grid_size, config.grid_size);
elseif isfield(config_json.movement, 'n_steps')
    config.n_steps = config_json.movement.n_steps;
    config.steps_per_point = ceil(config.n_steps / (config.grid_size * config.grid_size));
    fprintf('Using legacy n_steps=%d (steps_per_point=%d)\n', ...
        config.n_steps, config.steps_per_point);
else
    error('Configuration must specify either "steps_per_point" or "n_steps"');
end

config.ue_speed = config_json.movement.ue_speed;
config.step_duration = config.spacing / config.ue_speed;
config.center_frequency = config_json.channel.center_frequency;
config.bandwidth = config_json.channel.bandwidth;
config.n_subcarriers = config_json.channel.n_subcarriers;
config.scenario = config_json.channel.scenario;
config.bs_position = config_json.base_station.position;

%% Generate grid positions
[X, Y] = meshgrid(0:config.spacing:(config.grid_size-1)*config.spacing, ...
                  0:config.spacing:(config.grid_size-1)*config.spacing);
config.grid_positions = [X(:) + config.grid_offset(1), ...
                         Y(:) + config.grid_offset(2), ...
                         ones(config.grid_size^2, 1) * config.ue_height];
config.n_points = config.grid_size^2;

%% Build adjacency map
config.neighbors = cell(config.n_points, 1);
for row = 1:config.grid_size
    for col = 1:config.grid_size
        idx = (row-1)*config.grid_size + col;
        neighbors = [];
        
        % 4-connectivity: up, down, left, right
        if col < config.grid_size, neighbors = [neighbors, idx+1]; end          % Right
        if col > 1, neighbors = [neighbors, idx-1]; end                         % Left
        if row < config.grid_size, neighbors = [neighbors, idx+config.grid_size]; end  % Down
        if row > 1, neighbors = [neighbors, idx-config.grid_size]; end          % Up
        
        % 8-connectivity: add diagonals
        if config.neighbor_connectivity == 8
            if row > 1 && col > 1, neighbors = [neighbors, idx-config.grid_size-1]; end       % Up-Left
            if row > 1 && col < config.grid_size, neighbors = [neighbors, idx-config.grid_size+1]; end  % Up-Right
            if row < config.grid_size && col > 1, neighbors = [neighbors, idx+config.grid_size-1]; end  % Down-Left
            if row < config.grid_size && col < config.grid_size, neighbors = [neighbors, idx+config.grid_size+1]; end  % Down-Right
        end
        
        config.neighbors{idx} = neighbors;
    end
end

fprintf('Grid: %dx%d (%d points), Spacing: %.1fm, Connectivity: %d-neighbors\n', ...
    config.grid_size, config.grid_size, config.n_points, config.spacing, config.neighbor_connectivity);

%% Check for interferers
if isfield(config_json.base_station, 'interferers') && ...
   config_json.base_station.interferers.enabled
    interferers_enabled = true;
    interferer_positions = config_json.base_station.interferers.positions;
    interferer_tx_power = config_json.base_station.interferers.tx_power_dbm;
    
    % Convert to proper format
    if iscell(interferer_positions)
        interferer_positions = cell2mat(cellfun(@(x) x(:)', interferer_positions, 'UniformOutput', false));
    end
    n_interferers = size(interferer_positions, 1);
    fprintf('Using %d interfering base stations\n', n_interferers);
else
    interferers_enabled = false;
    n_interferers = 0;
    fprintf('No interfering base stations\n');
end

%% Generate random walk path
fprintf('\nGenerating random walk path (%d steps)...\n', config.n_steps);

% Use random seed from config
rng(config_json.experiment.random_seed);

% Generate random walk (constrained to grid neighbors)
walk_indices = zeros(config.n_steps + 1, 1);
walk_indices(1) = ceil(config.n_points / 2);  % Start from center

% Track movement times (longer for diagonal movements)
movement_times = zeros(config.n_steps, 1);

for step = 1:config.n_steps
    current = walk_indices(step);
    neighbors = config.neighbors{current};
    next = neighbors(randi(length(neighbors)));
    walk_indices(step + 1) = next;
    
    % Calculate if this is a diagonal movement
    if config.neighbor_connectivity == 8
        % Convert indices to row/col
        current_row = ceil(current / config.grid_size);
        current_col = mod(current - 1, config.grid_size) + 1;
        next_row = ceil(next / config.grid_size);
        next_col = mod(next - 1, config.grid_size) + 1;
        
        % Check if diagonal (both row and col change)
        is_diagonal = (current_row ~= next_row) && (current_col ~= next_col);
        
        if is_diagonal
            % Diagonal: sqrt(2) * spacing distance at constant speed
            movement_times(step) = sqrt(2) * config.step_duration;
        else
            % Straight: normal spacing distance
            movement_times(step) = config.step_duration;
        end
    else
        % 4-connectivity: all movements are straight
        movement_times(step) = config.step_duration;
    end
end

% Build trajectory positions
n_snapshots = config.n_steps + 1;
walk_grid_positions = zeros(n_snapshots, 3);
for step = 1:n_snapshots
    pt = walk_indices(step);
    walk_grid_positions(step, :) = config.grid_positions(pt, :);
end

% Add position jitter
jitter = (rand(n_snapshots, 3) - 0.5) * 2 * config.position_jitter;
jitter(:, 3) = 0;  % No jitter in height
walk_positions_jittered = walk_grid_positions + jitter;

% Package walk data
walk_path = struct();
walk_path.grid_point_indices = walk_indices;
walk_path.positions = walk_grid_positions;
walk_path.positions_jittered = walk_positions_jittered;
walk_path.movement_times = movement_times;  % Time for each step (accounts for diagonal)

% Statistics
visit_counts = histcounts(walk_indices, 1:(config.n_points+1));
fprintf('Walk statistics:\n');
fprintf('  Unique points visited: %d/%d\n', length(unique(walk_indices)), config.n_points);
fprintf('  Visit distribution: min=%d, max=%d\n', min(visit_counts), max(visit_counts));

%% Setup QuaDRiGa
fprintf('\nSetting up QuaDRiGa channel simulation...\n');

% Create layout
l = qd_layout;
l.set_scenario(config.scenario);

% Base station configuration
if interferers_enabled
    % Multiple base stations
    n_bs_total = 1 + n_interferers;
    l.no_tx = n_bs_total;
    
    % Serving BS
    l.tx_position(:, 1) = config.bs_position';
    l.tx_array(1) = qd_arrayant('omni');
    
    % Interfering BSs
    for i = 1:n_interferers
        l.tx_position(:, i+1) = interferer_positions(i, :)';
        l.tx_array(i+1) = qd_arrayant('omni');
    end
else
    % Single BS
    l.no_tx = 1;
    l.tx_position = config.bs_position';
    l.tx_array = qd_arrayant('omni');
end

% UE
l.no_rx = 1;
l.rx_array = qd_arrayant('omni');
l.rx_track = qd_track('linear', 0, 0);
l.rx_track.positions = walk_path.positions_jittered';
l.rx_track.scenario = {config.scenario};

fprintf('QuaDRiGa setup complete:\n');
fprintf('  Scenario: %s\n', config.scenario);
fprintf('  Base stations: %d\n', l.no_tx);
fprintf('  UE trajectory points: %d\n', size(l.rx_track.positions, 2));

%% Run channel simulation
fprintf('\nRunning channel simulation...\n');
tic;
[h_channel, ~] = l.get_channels;
sim_time = toc;
fprintf('Channel simulation complete (%.1f seconds)\n', sim_time);

%% Extract channel coefficients
fprintf('\nExtracting channel coefficients...\n');

% Extract serving BS channel (handle both cell array and struct array)
if interferers_enabled
    % Multi-BS: get_channels returns struct array or cell array
    if iscell(h_channel)
        ch = h_channel{1, 1};  % Serving BS (cell array)
        ch_interferers = h_channel(1, 2:end);  % Interferers
    else
        ch = h_channel(1, 1);  % Serving BS (struct array)
        ch_interferers = h_channel(1, 2:end);  % Interferers
    end
else
    % Single BS
    if iscell(h_channel)
        ch = h_channel{1};
    else
        ch = h_channel;
    end
    ch_interferers = [];
end

% Get number of snapshots
n_snapshots = size(ch.coeff, 4);

% Preallocate
H_serving = zeros(config.n_subcarriers, n_snapshots);

for t = 1:n_snapshots
    H_t = ch.fr(config.bandwidth, config.n_subcarriers, t);
    H_serving(:, t) = H_t(:);
end

fprintf('Extracted channels: %d subcarriers x %d snapshots\n', ...
    config.n_subcarriers, n_snapshots);

%% Extract Angle of Arrival (AoA) and Timing Advance
fprintf('\nExtracting AoA and Timing Advance...\n');

% Preallocate
aoa_azimuth = zeros(n_snapshots, 1);  % Azimuth angle in degrees
aoa_elevation = zeros(n_snapshots, 1); % Elevation angle in degrees
timing_advance = zeros(n_snapshots, 1); % Timing advance in microseconds

for t = 1:n_snapshots
    % Extract delay information
    delays = ch.delay(1, 1, :, t);  % Delays for all paths at snapshot t
    path_gains = abs(ch.coeff(1, 1, :, t));  % Path gains
    
    % Timing Advance: Use first arrival (minimum delay)
    % Convert from seconds to microseconds
    timing_advance(t) = min(delays(:)) * 1e6;
    
    % Angle of Arrival: Power-weighted average or dominant path
    % Extract arrival angles (azimuth and elevation)
    if isfield(ch, 'par')
        % Use channel parameters if available
        aoa_az = ch.par.AoA_cb(1, :, t);  % Azimuth angles
        aoa_el = ch.par.EoA_cb(1, :, t);  % Elevation angles
        
        % Power-weighted average (using path gains as weights)
        path_power = path_gains(:).^2;
        path_power = path_power / sum(path_power);  % Normalize to sum to 1
        
        aoa_azimuth(t) = sum(aoa_az(:) .* path_power);
        aoa_elevation(t) = sum(aoa_el(:) .* path_power);
    else
        % Fallback: estimate from UE position relative to BS
        ue_pos = walk_path.positions_jittered(t, :);
        bs_pos = config.bs_position;
        
        % Calculate azimuth angle (in degrees, 0 = North, clockwise)
        dx = ue_pos(1) - bs_pos(1);
        dy = ue_pos(2) - bs_pos(2);
        dz = ue_pos(3) - bs_pos(3);
        
        aoa_azimuth(t) = atan2d(dx, dy);  % Azimuth
        horizontal_dist = sqrt(dx^2 + dy^2);
        aoa_elevation(t) = -atan2d(dz, horizontal_dist);  % Elevation (negative = below BS)
    end
end

fprintf('AoA and TA extracted for %d snapshots\n', n_snapshots);
fprintf('  AoA Azimuth range: [%.2f, %.2f] degrees\n', min(aoa_azimuth), max(aoa_azimuth));
fprintf('  AoA Elevation range: [%.2f, %.2f] degrees\n', min(aoa_elevation), max(aoa_elevation));
fprintf('  Timing Advance range: [%.3f, %.3f] μs\n', min(timing_advance), max(timing_advance));
fprintf('  NOTE: Clean AoA saved; noise/quantization applied during ML training\n');
%% Compute interference (if applicable)
if interferers_enabled
    fprintf('\nComputing interference from %d interfering BSs...\n', n_interferers);
    
    % Preallocate interference power matrix
    I_dBm_sc = zeros(config.n_subcarriers, n_snapshots);
    
    for bs_idx = 1:n_interferers
        if iscell(ch_interferers)
            ch_interf = ch_interferers{bs_idx};
        else
            ch_interf = ch_interferers(bs_idx);
        end
        
        for t = 1:n_snapshots
            H_interf = ch_interf.fr(config.bandwidth, config.n_subcarriers, t);
            
            % Interference power per subcarrier
            I_linear = abs(H_interf(:)).^2 * (10^(interferer_tx_power/10) / 1000);
            I_dBm_sc(:, t) = I_dBm_sc(:, t) + I_linear;
        end
    end
    
    % Convert total interference to dBm
    I_dBm_sc = 10 * log10(I_dBm_sc * 1000);
    
    fprintf('Interference computation complete\n');
else
    I_dBm_sc = [];
end

%% Compute metrics
fprintf('\nComputing RSS, SINR, and CQI...\n');

% Initialize CSIMetrics object
fvec = linspace(-config.bandwidth/2, config.bandwidth/2, config.n_subcarriers);
m = CSIMetrics('SubcarrierSpacing', config.bandwidth/config.n_subcarriers, ...
               'TxPowerPerSC_dBm', 0, ...
               'NoiseFigure_dB', 7, ...
               'InterfPerSC_dBm', -Inf);

% Preallocate
metrics = struct();
metrics.rss_wb = zeros(n_snapshots, 1);
metrics.sinr_wb = zeros(n_snapshots, 1);
metrics.cqi_wb = zeros(n_snapshots, 1);
metrics.aoa_azimuth = zeros(n_snapshots, 1);
metrics.aoa_elevation = zeros(n_snapshots, 1);
metrics.timing_advance = zeros(n_snapshots, 1);

tx_power_dbm = config_json.base_station.tx_power_dbm;

for t = 1:n_snapshots
    H = H_serving(:, t);
    H_sc = reshape(H, [1, 1, config.n_subcarriers]);
    
    if interferers_enabled
        I_vec = I_dBm_sc(:, t);
        out = m.compute(H_sc, 'InterfPerSC_dBmVec', I_vec);
    else
        out = m.compute(H_sc);
    end
    
    metrics.rss_wb(t) = out.RSS_dBm_wb;
    metrics.sinr_wb(t) = out.SINR_dB_wb;
    metrics.cqi_wb(t) = out.CQI_wb;
    metrics.aoa_azimuth(t) = aoa_azimuth(t);
    metrics.aoa_elevation(t) = aoa_elevation(t);
    metrics.timing_advance(t) = timing_advance(t);
end

fprintf('Metrics computed for %d snapshots\n', n_snapshots);
fprintf('  RSS range: [%.2f, %.2f] dBm\n', min(metrics.rss_wb), max(metrics.rss_wb));
fprintf('  SINR range: [%.2f, %.2f] dB\n', min(metrics.sinr_wb), max(metrics.sinr_wb));
fprintf('  CQI range: [%.2f, %.2f]\n', min(metrics.cqi_wb), max(metrics.cqi_wb));
fprintf('  AoA Azimuth range: [%.2f, %.2f] degrees\n', min(metrics.aoa_azimuth), max(metrics.aoa_azimuth));
fprintf('  AoA Elevation range: [%.2f, %.2f] degrees\n', min(metrics.aoa_elevation), max(metrics.aoa_elevation));
fprintf('  Timing Advance range: [%.3f, %.3f] μs\n', min(metrics.timing_advance), max(metrics.timing_advance));

%% Create output directory
scenario_type = 'LOS';
if contains(config.scenario, 'NLOS')
    scenario_type = 'NLOS';
end

timestamp = datestr(now, 'yyyy-mm-dd_HH-MM-SS');
grid_subdir = sprintf('grid_%dx%d', config.grid_size, config.grid_size);
output_dir = fullfile(workspace_root, 'results', 'grid_localization', grid_subdir, ...
                      sprintf('sim_data_%s_%s', scenario_type, timestamp));

if ~exist(output_dir, 'dir')
    mkdir(output_dir);
end

%% Save simulation data
fprintf('\nSaving simulation data...\n');

output_file = fullfile(output_dir, 'simulation_data.mat');
save(output_file, 'metrics', 'walk_path', 'config', '-v7');

% Copy configuration to output (preserves generation parameters with data)
copyfile(config_file, fullfile(output_dir, 'data_generation_config.jsonc'));

fprintf('Simulation data saved to:\n');
fprintf('  %s\n', output_dir);
fprintf('  - simulation_data.mat (metrics, walk_path, config)\n');
fprintf('  - data_generation_config.jsonc (generation parameters)\n');

%% Generate data visualization plots
fprintf('\n=== Generating Data Visualization Plots ===\n');

plot_script = fullfile(script_dir, '..', 'python', 'plot_data_generation.py');

if exist(plot_script, 'file')
    python_cmd = sprintf('python "%s" "%s"', plot_script, output_dir);
    [status, cmdout] = system(python_cmd);
    
    if status == 0
        fprintf('%s\n', cmdout);
        fprintf('[SUCCESS] Data visualization plots generated!\n');
    else
        warning('Data visualization failed. You can run it manually:\n  %s', python_cmd);
        fprintf('%s\n', cmdout);
    end
else
    fprintf('Note: Plotting script not found at: %s\n', plot_script);
    fprintf('You can generate plots manually with:\n');
    fprintf('  python plot_data_generation.py "%s"\n', output_dir);
end

%% Call Python ML pipeline (if configured)
if isfield(config_json.output, 'auto_run_pipeline') && config_json.output.auto_run_pipeline
    fprintf('\n=== Calling Python Pipeline ===\n');
    
    pipeline_script = fullfile(script_dir, '..', 'python', 'localization_pipeline.py');
    
    if exist(pipeline_script, 'file')
        python_cmd = sprintf('python "%s" --data-dir "%s"', pipeline_script, output_dir);
        [status, cmdout] = system(python_cmd);
        
        if status == 0
            fprintf('%s\n', cmdout);
            fprintf('[SUCCESS] Python pipeline completed!\n');
        else
            warning('Python pipeline failed. You can run it manually:\n  %s', python_cmd);
            fprintf('%s\n', cmdout);
        end
    else
        fprintf('Note: Python pipeline not found at: %s\n', pipeline_script);
        fprintf('You can run analysis manually with:\n');
        fprintf('  python localization_pipeline.py --data-dir "%s"\n', output_dir);
    end
else
    fprintf('\n[Note] Auto-run pipeline disabled. Run ML pipeline manually with:\n');
    fprintf('  python experiments\\09_grid_localization\\src\\python\\localization_pipeline.py --data-dir "%s"\n', output_dir);
end

fprintf('\n=== Data Generation Complete ===\n');
