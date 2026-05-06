%% Grid Localization Data Generation
% This script generates channel simulation data using QuaDRiGa
% All analysis (train/test, models, evaluation) is done in Python
%
% Output: simulation_data.mat containing:
%   - metrics (RSS, SINR, CQI)
%   - walk_path (locations)
%   - config (grid, neighbors, etc.)

% Declare override globals BEFORE any clear so they survive the workspace reset.
% These are used by multi-user wrapper scripts (run_multi_user_15x15.m).
global OVERRIDE_CONFIG_NAME;
global OVERRIDE_WALK_SEED;
global OVERRIDE_N_RX_ANTENNAS;
global OVERRIDE_ANTENNA_GAIN_DB;
global OVERRIDE_UE_HEIGHT_M;
global OVERRIDE_OUTPUT_DIR;
global OVERRIDE_OUTPUT_FILENAME;
global OVERRIDE_USER_ID;
global OVERRIDE_CHANNEL_SEED;

% Only clear the workspace when running standalone (no multi-user override).
% When called from a loop in run_multi_user_15x15.m, OVERRIDE_OUTPUT_DIR is set
% and we must NOT clear the base workspace (it would destroy the loop variables).
if isempty(OVERRIDE_OUTPUT_DIR)
    clear; clc; close all;
    % Re-declare globals after clear (clear removes local references but not global data)
    global OVERRIDE_CONFIG_NAME;
    global OVERRIDE_WALK_SEED;
    global OVERRIDE_N_RX_ANTENNAS;
    global OVERRIDE_ANTENNA_GAIN_DB;
    global OVERRIDE_UE_HEIGHT_M;
    global OVERRIDE_OUTPUT_DIR;
    global OVERRIDE_OUTPUT_FILENAME;
    global OVERRIDE_USER_ID;
    global OVERRIDE_CHANNEL_SEED;
else
    clc;  % Clear console only — preserve workspace variables for the loop
end

%% Setup paths
script_dir = fileparts(mfilename('fullpath'));
experiment_root = fileparts(fileparts(script_dir));  % experiments/09_grid_localization
workspace_root = fileparts(fileparts(experiment_root));  % CSI-Location
utils_path = fullfile(workspace_root, 'utils');  % Utils at workspace root
addpath(utils_path);

fprintf('=== Grid Localization Data Generation ===\n\n');

%% Load Configuration
% Config file is in ../../configs/ relative to src/matlab/
% Check for global override from wrapper script (e.g., run_voronoi.m)
if ~isempty(OVERRIDE_CONFIG_NAME)
    config_name = OVERRIDE_CONFIG_NAME;
elseif ~exist('config_name', 'var')
    config_name = 'voronoi_config.jsonc';
end
config_file = fullfile(experiment_root, 'configs', config_name);
if ~exist(config_file, 'file')
    error('Configuration file not found: %s', config_file);
end

fprintf('Loading configuration from: %s\n', config_name);
config_json = read_jsonc(config_file);

%% Build configuration
config = struct();
config.grid_size = config_json.grid.size;
config.spacing = config_json.grid.spacing;
config.ue_height = config_json.grid.ue_height;
config.grid_offset = config_json.grid.grid_offset;
config.position_jitter = config_json.grid.position_jitter;

% UE height override for device profile experiments
if ~isempty(OVERRIDE_UE_HEIGHT_M)
    config.ue_height = OVERRIDE_UE_HEIGHT_M;
    fprintf('Device profile override: ue_height = %.2f m\n', config.ue_height);
end

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

% Ensure bs_position is a column vector [3x1] for QuaDRiGa
if numel(config.bs_position) ~= 3
    error('base_station.position must have exactly 3 elements [x, y, z]');
end
config.bs_position = reshape(config.bs_position, 3, 1);

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

% Use random seed from config (or override for multi-user device isolation)
if ~isempty(OVERRIDE_WALK_SEED)
    rng(OVERRIDE_WALK_SEED);
    fprintf('Device profile override: walk seed = %d\n', OVERRIDE_WALK_SEED);
else
    rng(config_json.experiment.random_seed);
end

% Generate random walk (constrained to grid neighbors)
walk_indices = zeros(config.n_steps + 1, 1);
walk_indices(1) = ceil(config.n_points / 2);  % Start from center

% Track movement times (longer for diagonal movements)
movement_times = zeros(config.n_steps, 1);

walk_tic = tic;
for step = 1:config.n_steps
    current = walk_indices(step);
    neighbors = config.neighbors{current};
    next = neighbors(randi(length(neighbors)));
    walk_indices(step + 1) = next;

    % Progress report every 10 000 steps
    if mod(step, 10000) == 0
        elapsed_w = toc(walk_tic);
        eta_w = elapsed_w / step * (config.n_steps - step);
        fprintf('  Walk: %d/%d steps (%.0f%%)  ETA: %.0fs\n', ...
                step, config.n_steps, step/config.n_steps*100, eta_w);
    end

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

% Check for mixed scenario (Voronoi cells)
mixed_scenario_enabled = false;
if isfield(config_json.channel, 'mixed_scenario') && ...
   config_json.channel.mixed_scenario.enabled
    mixed_scenario_enabled = true;
    
    % Check if AreaGenerator should auto-generate the Voronoi cells
    if isfield(config_json.channel.mixed_scenario, 'auto_generate') && ...
       config_json.channel.mixed_scenario.auto_generate
        
        fprintf('Auto-generating Voronoi cells via AreaGenerator...\n');
        ag_params = config_json.channel.mixed_scenario.area_generator;
        
        % Build AreaGenerator config
        ag_config = struct();
        ag_config.num_areas = ag_params.num_areas;
        ag_config.transition_width = ag_params.transition_width;
        ag_config.random_seed = config_json.experiment.random_seed;
        
        % Convert area_types from struct array / cell to cell array of strings
        if iscell(ag_params.area_types)
            ag_config.area_types = ag_params.area_types;
        else
            ag_config.area_types = arrayfun(@(x) x, ag_params.area_types, 'UniformOutput', false);
        end
        
        % Calculate area bounds from grid or use explicit value
        if ischar(ag_params.area_bounds) && strcmp(ag_params.area_bounds, 'auto')
            x_min = config.grid_offset(1) - config.spacing;
            x_max = config.grid_offset(1) + (config.grid_size) * config.spacing;
            y_min = config.grid_offset(2) - config.spacing;
            y_max = config.grid_offset(2) + (config.grid_size) * config.spacing;
            ag_config.area_bounds = [x_min, x_max, y_min, y_max];
            fprintf('  Auto-calculated bounds: [%.0f, %.0f, %.0f, %.0f]\n', ...
                x_min, x_max, y_min, y_max);
        else
            ag_config.area_bounds = ag_params.area_bounds;
        end
        
        % Generate areas using AreaGenerator
        areas = AreaGenerator.generate(ag_config);
        n_cells = length(areas);
        
        % Convert AreaGenerator output to voronoi_cells format
        voronoi_centers = zeros(n_cells, 2);
        voronoi_scenarios = cell(n_cells, 1);
        voronoi_names = cell(n_cells, 1);
        
        for i = 1:n_cells
            voronoi_centers(i, :) = areas(i).seed;
            voronoi_scenarios{i} = areas(i).scenario;
            voronoi_names{i} = areas(i).area_type;
        end
    else
        % Manual Voronoi cells from config
        voronoi_cells = config_json.channel.mixed_scenario.voronoi_cells;
        n_cells = length(voronoi_cells);
        
        % Extract Voronoi centers and scenarios
        voronoi_centers = zeros(n_cells, 2);
        voronoi_scenarios = cell(n_cells, 1);
        voronoi_names = cell(n_cells, 1);
        
        for i = 1:n_cells
            % Access struct array element (not cell array)
            cell_data = voronoi_cells(i);
            voronoi_centers(i, :) = cell_data.center;
            voronoi_scenarios{i} = cell_data.scenario;
            voronoi_names{i} = cell_data.name;
        end
    end
    
    fprintf('Using Voronoi-based mixed scenarios (%d cells):\n', n_cells);
    for i = 1:n_cells
        fprintf('  Cell %d (%s): %s at [%.1f, %.1f]\n', ...
            i, voronoi_names{i}, voronoi_scenarios{i}, ...
            voronoi_centers(i, 1), voronoi_centers(i, 2));
    end
    
    % Assign each UE position to nearest Voronoi cell
    n_snapshots = size(walk_path.positions_jittered, 1);
    voronoi_assignments = zeros(n_snapshots, 1);
    
    for t = 1:n_snapshots
        ue_pos = walk_path.positions_jittered(t, 1:2);  % [x, y]
        
        % Find nearest Voronoi center
        distances = sqrt(sum((voronoi_centers - ue_pos).^2, 2));
        [~, cell_idx] = min(distances);
        voronoi_assignments(t) = cell_idx;
    end
    
    % Store Voronoi assignments in walk_path
    walk_path.voronoi_cell_idx = voronoi_assignments;
    walk_path.voronoi_centers = voronoi_centers;
    walk_path.voronoi_scenarios = voronoi_scenarios;
    walk_path.voronoi_names = voronoi_names;
    
    % Statistics
    fprintf('Voronoi cell assignment statistics:\n');
    for i = 1:n_cells
        count = sum(voronoi_assignments == i);
        percentage = 100 * count / n_snapshots;
        fprintf('  %s: %d samples (%.1f%%)\n', voronoi_names{i}, count, percentage);
    end
end

% Create layout
l = qd_layout;

% Set scenario (will be overridden per-snapshot if mixed_scenario enabled)
if ~mixed_scenario_enabled
    l.set_scenario(config.scenario);
end

% Base station configuration
if interferers_enabled
    % Multiple base stations
    n_bs_total = 1 + n_interferers;
    l.no_tx = n_bs_total;
    
    % Serving BS
    l.tx_position(:, 1) = config.bs_position;
    l.tx_array(1) = qd_arrayant('omni');
    
    % Interfering BSs
    for i = 1:n_interferers
        l.tx_position(:, i+1) = interferer_positions(i, :)';
        l.tx_array(i+1) = qd_arrayant('omni');
    end
else
    % Single BS
    l.no_tx = 1;
    l.tx_position = config.bs_position;
    l.tx_array = qd_arrayant('omni');
end

% UE — configure antenna count for device profile experiments
if ~isempty(OVERRIDE_N_RX_ANTENNAS) && OVERRIDE_N_RX_ANTENNAS > 0
    n_rx_antennas = OVERRIDE_N_RX_ANTENNAS;
else
    n_rx_antennas = 1;  % Default: single omni antenna
end

l.no_rx = 1;
l.rx_array = qd_arrayant('omni');
if n_rx_antennas > 1
    % Replicate omni element for multi-antenna UE (MRC combining in post-processing)
    l.rx_array.no_elements = n_rx_antennas;
end
l.rx_track = qd_track('linear', 0, 0);
l.rx_track.positions = walk_path.positions_jittered';
fprintf('  UE: %d rx antenna(s), height = %.2f m\n', n_rx_antennas, config.ue_height);

% Set scenario per segment if using Voronoi cells
if mixed_scenario_enabled
    % Get the actual number of segments from the track
    % QuaDRiGa may have a different number of segments than N-1
    n_segments = l.rx_track.no_segments;
    
    fprintf('  Track has %d positions and %d segments\n', n_snapshots, n_segments);
    
    % Create scenario string for each segment
    scenario_per_segment = cell(1, n_segments);
    
    % Assign scenario based on the starting position of each segment
    for seg = 1:n_segments
        % Use the position index for this segment (segments correspond to positions 1:N-1)
        if seg <= length(voronoi_assignments)
            cell_idx = voronoi_assignments(seg);
            scenario_per_segment{seg} = voronoi_scenarios{cell_idx};
        else
            % Fallback for any extra segments
            scenario_per_segment{seg} = voronoi_scenarios{1};
        end
    end
    l.rx_track.scenario = scenario_per_segment;
else
    l.rx_track.scenario = {config.scenario};
end

fprintf('QuaDRiGa setup complete:\n');
if mixed_scenario_enabled
    fprintf('  Scenario: Mixed (Voronoi-based, %d cells)\n', n_cells);
else
    fprintf('  Scenario: %s\n', config.scenario);
end
fprintf('  Base stations: %d\n', l.no_tx);
fprintf('  UE trajectory points: %d\n', size(l.rx_track.positions, 2));

%% Run channel simulation
% Re-seed QuaDRiGa RNG if OVERRIDE_CHANNEL_SEED is set (environmental variability).
% This produces different fading/LSP realizations while keeping the walk path identical.
global OVERRIDE_CHANNEL_SEED;
if ~isempty(OVERRIDE_CHANNEL_SEED)
    rng(OVERRIDE_CHANNEL_SEED);
    fprintf('Channel seed override: %d\n', OVERRIDE_CHANNEL_SEED);
end

fprintf('\nRunning channel simulation (%d snapshots)...\n', n_snapshots);
fprintf('[%s] QuaDRiGa get_channels started\n', datestr(now, 'HH:MM:SS'));
ch_tic = tic;
[h_channel, ~] = l.get_channels;
ch_time = toc(ch_tic);
fprintf('[%s] Channel simulation complete in %.1fs  (%.2f ms/snapshot)\n', ...
        datestr(now, 'HH:MM:SS'), ch_time, ch_time/n_snapshots*1000);

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
    if n_rx_antennas > 1
        % MRC combining: H_eff(f) = sqrt( sum_i |H_i(f)|^2 )
        % H_t is [n_rx x 1 x n_subcarriers] for single serving BS
        H_mrc = sqrt(sum(abs(H_t).^2, 1));  % [1 x 1 x n_subcarriers]
        H_serving(:, t) = H_mrc(:);
    else
        H_serving(:, t) = H_t(:);
    end
end

fprintf('Extracted channels: %d subcarriers x %d snapshots\n', ...
    config.n_subcarriers, n_snapshots);

%% Extract Angle of Arrival (AoA), Timing Advance, Path Loss, and Multi-path metrics
fprintf('\nExtracting AoA, Timing Advance, Path Loss, and Multi-path metrics...\n');

% Preallocate
aoa_azimuth = zeros(n_snapshots, 1);    % Azimuth angle in degrees
aoa_elevation = zeros(n_snapshots, 1);  % Elevation angle in degrees
timing_advance = zeros(n_snapshots, 1); % Timing advance in microseconds
path_loss_db = zeros(n_snapshots, 1);   % Path loss in dB
n_multipath = zeros(n_snapshots, 1);    % Number of significant multipath components
rms_delay_spread = zeros(n_snapshots, 1); % RMS delay spread in nanoseconds
k_factor_db = zeros(n_snapshots, 1);    % K-factor (LOS/NLOS power ratio) in dB

for t = 1:n_snapshots
    % Extract delay and path gain information
    delays = ch.delay(1, 1, :, t);  % Delays for all paths at snapshot t
    path_gains = abs(ch.coeff(1, 1, :, t));  % Path gains (complex magnitude)
    path_powers = path_gains(:).^2;  % Path powers
    
    % Timing Advance: Use first arrival (minimum delay)
    % Convert from seconds to microseconds
    timing_advance(t) = min(delays(:)) * 1e6;
    
    % Path Loss: Compute from total received power
    % Path loss = -10*log10(sum of all path powers)
    total_power = sum(path_powers);
    if total_power > 0
        path_loss_db(t) = -10 * log10(total_power);
    else
        path_loss_db(t) = NaN;
    end
    
    % Number of significant multipath components
    % Count paths with power > 1% of max path power
    if max(path_powers) > 0
        significant_threshold = 0.01 * max(path_powers);
        n_multipath(t) = sum(path_powers > significant_threshold);
    else
        n_multipath(t) = 0;
    end
    
    % RMS Delay Spread (in nanoseconds)
    % sigma_tau = sqrt(E[tau^2] - E[tau]^2), weighted by power
    if total_power > 0
        delays_vec = delays(:);
        weights = path_powers / total_power;
        mean_delay = sum(delays_vec .* weights);
        mean_delay_sq = sum((delays_vec.^2) .* weights);
        rms_delay_spread(t) = sqrt(max(0, mean_delay_sq - mean_delay^2)) * 1e9;  % Convert to ns
    else
        rms_delay_spread(t) = 0;
    end
    
    % K-factor: Ratio of LOS (first/strongest path) to NLOS power
    % K = P_LOS / P_NLOS, where P_NLOS = total - P_LOS
    [max_power, los_idx] = max(path_powers);
    nlos_power = total_power - max_power;
    if nlos_power > 0 && max_power > 0
        k_factor_db(t) = 10 * log10(max_power / nlos_power);
    elseif max_power > 0
        k_factor_db(t) = 30;  % Strong LOS, cap at 30 dB
    else
        k_factor_db(t) = NaN;
    end
    
    % Angle of Arrival: Power-weighted average or dominant path
    % Extract arrival angles (azimuth and elevation)
    if isfield(ch, 'par')
        % Use channel parameters if available
        aoa_az = ch.par.AoA_cb(1, :, t);  % Azimuth angles
        aoa_el = ch.par.EoA_cb(1, :, t);  % Elevation angles
        
        % Power-weighted average (using path gains as weights)
        weights = path_powers / sum(path_powers);
        
        aoa_azimuth(t) = sum(aoa_az(:) .* weights);
        aoa_elevation(t) = sum(aoa_el(:) .* weights);
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

fprintf('Metrics extracted for %d snapshots:\n', n_snapshots);
fprintf('  AoA Azimuth range: [%.2f, %.2f] degrees\n', min(aoa_azimuth), max(aoa_azimuth));
fprintf('  AoA Elevation range: [%.2f, %.2f] degrees\n', min(aoa_elevation), max(aoa_elevation));
fprintf('  Timing Advance range: [%.3f, %.3f] μs\n', min(timing_advance), max(timing_advance));
fprintf('  Path Loss range: [%.2f, %.2f] dB\n', min(path_loss_db), max(path_loss_db));
fprintf('  Multipath count range: [%d, %d] paths\n', min(n_multipath), max(n_multipath));
fprintf('  RMS Delay Spread range: [%.2f, %.2f] ns\n', min(rms_delay_spread), max(rms_delay_spread));
fprintf('  K-factor range: [%.2f, %.2f] dB\n', min(k_factor_db), max(k_factor_db));
fprintf('  NOTE: Clean values saved; noise/quantization applied during ML training\n');
%% Compute interference (if applicable)
if interferers_enabled
    fprintf('\nComputing interference from %d interfering BSs...\n', n_interferers);

    % Preallocate interference power matrix
    I_dBm_sc = zeros(config.n_subcarriers, n_snapshots);
    % Per-BS wideband RSS (linear W) for multi-BS localization features
    rss_ibs_lin = zeros(n_snapshots, n_interferers);

    for bs_idx = 1:n_interferers
        if iscell(ch_interferers)
            ch_interf = ch_interferers{bs_idx};
        else
            ch_interf = ch_interferers(bs_idx);
        end

        for t = 1:n_snapshots
            H_interf = ch_interf.fr(config.bandwidth, config.n_subcarriers, t);

            % For multi-antenna UE, apply MRC combining to get effective channel
            % H_interf is [n_rx x 1 x n_subcarriers]; need [n_subcarriers x 1]
            if n_rx_antennas > 1
                H_interf_eff = sqrt(sum(abs(H_interf).^2, 1));  % [1 x 1 x n_sc]
            else
                H_interf_eff = H_interf;
            end

            % Interference power per subcarrier — must use same TX power reference
            % as CSIMetrics (TxPowerPerSC_dBm = 0, i.e. 1 mW = 1e-3 W per SC).
            % Relative IBS vs serving-BS TX power is preserved via rel_ibs_power.
            % BUG FIXED: original code used interferer_tx_power directly (1 W),
            % which was 30 dB higher than the serving-BS reference and made SINR
            % 30 dB too negative.
            rel_ibs_power = 10^((interferer_tx_power - config_json.base_station.tx_power_dbm) / 10);
            I_linear = abs(H_interf_eff(:)).^2 * (1e-3 * rel_ibs_power);
            I_dBm_sc(:, t) = I_dBm_sc(:, t) + I_linear;

            % Per-BS wideband RSS: mean subcarrier power for this BS
            rss_ibs_lin(t, bs_idx) = mean(I_linear);
        end
    end

    % Convert total interference to dBm
    I_dBm_sc = 10 * log10(I_dBm_sc * 1000);

    fprintf('Interference computation complete\n');
else
    I_dBm_sc = [];
    rss_ibs_lin = [];
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
metrics.path_loss = zeros(n_snapshots, 1);
metrics.n_multipath = zeros(n_snapshots, 1);
metrics.rms_delay_spread = zeros(n_snapshots, 1);
metrics.k_factor = zeros(n_snapshots, 1);

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
    metrics.path_loss(t) = path_loss_db(t);
    metrics.n_multipath(t) = n_multipath(t);
    metrics.rms_delay_spread(t) = rms_delay_spread(t);
    metrics.k_factor(t) = k_factor_db(t);
end

% Add per-BS RSS fields for multi-BS localization experiments (rss_ibs_1, rss_ibs_2, ...)
% Only populated when interferers are enabled in the config.
if interferers_enabled && ~isempty(rss_ibs_lin)
    for bs_idx = 1:n_interferers
        field_name = sprintf('rss_ibs_%d', bs_idx);
        metrics.(field_name) = 10 * log10(rss_ibs_lin(:, bs_idx) * 1000);
    end
    fprintf('  Per-interferer RSS fields added: rss_ibs_1 ... rss_ibs_%d\n', n_interferers);
end
fprintf('Metrics computed for %d snapshots\n', n_snapshots);
fprintf('  RSS range: [%.2f, %.2f] dBm\n', min(metrics.rss_wb), max(metrics.rss_wb));
fprintf('  SINR range: [%.2f, %.2f] dB\n', min(metrics.sinr_wb), max(metrics.sinr_wb));
fprintf('  CQI range: [%.2f, %.2f]\n', min(metrics.cqi_wb), max(metrics.cqi_wb));
fprintf('  Path Loss range: [%.2f, %.2f] dB\n', min(metrics.path_loss), max(metrics.path_loss));
fprintf('  K-factor range: [%.2f, %.2f] dB\n', min(metrics.k_factor), max(metrics.k_factor));
fprintf('  N Multipath range: [%d, %d]\n', min(metrics.n_multipath), max(metrics.n_multipath));
fprintf('  RMS Delay Spread range: [%.2f, %.2f] ns\n', min(metrics.rms_delay_spread), max(metrics.rms_delay_spread));

% Apply antenna gain dB offset (device profile heterogeneity experiment)
if ~isempty(OVERRIDE_ANTENNA_GAIN_DB) && OVERRIDE_ANTENNA_GAIN_DB ~= 0
    metrics.rss_wb  = metrics.rss_wb  + OVERRIDE_ANTENNA_GAIN_DB;
    metrics.sinr_wb = metrics.sinr_wb + OVERRIDE_ANTENNA_GAIN_DB;
    fprintf('Applied device antenna gain offset: %.1f dB -> RSS: [%.2f, %.2f] dBm\n', ...
        OVERRIDE_ANTENNA_GAIN_DB, min(metrics.rss_wb), max(metrics.rss_wb));
end

% Store user_id in metrics (for multi-user experiments)
if ~isempty(OVERRIDE_USER_ID)
    metrics.user_id = OVERRIDE_USER_ID;
end

%% Create output directory
if ~isempty(OVERRIDE_OUTPUT_DIR)
    % Multi-user experiment: use shared pre-created directory
    output_dir = OVERRIDE_OUTPUT_DIR;
    if ~exist(output_dir, 'dir')
        mkdir(output_dir);
    end
else
    if mixed_scenario_enabled
        scenario_type = 'voronoi';
    else
        scenario_type = 'LOS';
        if contains(config.scenario, 'NLOS')
            scenario_type = 'NLOS';
        end
    end
    timestamp = datestr(now, 'yyyy-mm-dd_HH-MM-SS');
    grid_subdir = sprintf('grid_%dx%d', config.grid_size, config.grid_size);
    output_dir = fullfile(workspace_root, 'results', 'grid_localization', grid_subdir, ...
                          sprintf('sim_data_%s_%s', scenario_type, timestamp));
    if ~exist(output_dir, 'dir')
        mkdir(output_dir);
    end
end

%% Save simulation data
fprintf('\nSaving simulation data...\n');

if ~isempty(OVERRIDE_OUTPUT_FILENAME)
    % Multi-user experiment: save flat per-user format for Python pipeline
    output_file = fullfile(output_dir, OVERRIDE_OUTPUT_FILENAME);

    % Flat arrays expected by multi_user_pipeline.py
    user_id_val   = OVERRIDE_USER_ID;
    rss           = metrics.rss_wb;               % [N x 1] dBm from serving BS
    sinr          = metrics.sinr_wb;              % [N x 1] dB from serving BS
    x_pos         = walk_path.positions(:, 1);    % [N x 1] ground truth x
    y_pos         = walk_path.positions(:, 2);    % [N x 1] ground truth y
    grid_point_id = walk_path.grid_point_indices; % [N x 1] 1-based grid index
    step_index    = (1:n_snapshots)';             % [N x 1] chronological step
    if isfield(walk_path, 'voronoi_cell_idx')
        voronoi_cell_id = walk_path.voronoi_cell_idx;  % [N x 1] 1-based cell index
    else
        voronoi_cell_id = ones(n_snapshots, 1);
    end
    device_profile = struct('n_antennas', n_rx_antennas, ...
                            'antenna_gain_db', double(OVERRIDE_ANTENNA_GAIN_DB), ...
                            'ue_height_m', config.ue_height);
    aoa_az        = aoa_azimuth;   % [N x 1] degrees, power-weighted cluster AoA
    aoa_el        = aoa_elevation; % [N x 1] degrees, power-weighted cluster EoA

    save(output_file, 'user_id_val', 'rss', 'sinr', 'aoa_az', 'aoa_el', ...
         'x_pos', 'y_pos', 'grid_point_id', 'voronoi_cell_id', ...
         'step_index', 'device_profile', '-v7');
    fprintf('Per-user data saved: %s\n', output_file);
    fprintf('  user_id=%d, n_antennas=%d, gain=%.1f dB, height=%.2f m\n', ...
        user_id_val, n_rx_antennas, OVERRIDE_ANTENNA_GAIN_DB, config.ue_height);
else
    % Standard format (existing experiments)
    output_file = fullfile(output_dir, 'simulation_data.mat');
    save(output_file, 'metrics', 'walk_path', 'config', '-v7');
    % Copy configuration to output (preserves generation parameters with data)
    copyfile(config_file, fullfile(output_dir, 'data_generation_config.jsonc'));
    fprintf('Simulation data saved to:\n');
    fprintf('  %s\n', output_dir);
    fprintf('  - simulation_data.mat (metrics, walk_path, config)\n');
    fprintf('  - data_generation_config.jsonc (generation parameters)\n');
end

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
