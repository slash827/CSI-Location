% Configuration for Urban Mixed Indoor/Outdoor Dataset Generation
% ==================================================================
% 
% This configuration creates a realistic urban scenario combining:
%   - Outdoor open areas (streets, plazas) - Pure LOS dominant
%   - Outdoor obstructed areas (trees, vehicles) - Light NLOS
%   - Indoor light areas (glass buildings, malls) - Moderate NLOS
%   - Indoor heavy areas (concrete buildings) - Heavy NLOS
%
% Scenario: 300m × 300m urban block with hybrid BS deployment
% Frequency: 3.0 GHz (5G mid-band with better penetration)
% Total: 200,000 samples (2000 trajectories × 100 samples)

%% Dataset Parameters
config = struct();

% ========================================
% APPEND MODE - Set to append to previous run
% ========================================
config.APPEND_MODE = true;  % Set to true to add more samples to existing run
config.APPEND_TO_DIR = 'exp13_2025-11-26_20-23-00';   % Specify directory to append to (e.g., 'exp13_2025-11-26_18-22-55')
% When APPEND_MODE = true:
%   - Loads existing train/val data and metadata
%   - Adds new trajectories to existing dataset
%   - Must have same configuration (n_timesteps, train_ratio, features)

% ========================================
% DEBUG MODE - Set to true for quick testing
% ========================================
config.DEBUG_MODE = false;  % Set to true for small test run
% When DEBUG_MODE = true:
%   - Only 10 trajectories
%   - Only 20 samples per trajectory
%   - Plots every 2nd trajectory
%   - Total: 200 samples (~1-2 minutes)

% Total number of trajectories (optimized for speed and diversity)
if config.DEBUG_MODE
    config.n_trajectories = 10;    % DEBUG: Small test
    fprintf('\n⚠️  DEBUG MODE ENABLED - Running small test (10 trajectories)\n\n');
else
    config.n_trajectories = 1000;  % PRODUCTION: Good trajectory diversity
end

% Samples per trajectory
if config.DEBUG_MODE
    config.n_timesteps = 20;       % DEBUG: Quick test
else
    config.n_timesteps = 100;      % PRODUCTION: 100K total samples (fast + realistic)
end

config.train_ratio = 0.8;      % 80% train, 20% validation

%% Urban Zone Distribution
% Each sample is assigned to a zone type based on its position
config.zone_distribution = struct(...
    'outdoor_open', 0.40, ...      % 40% outdoor open (streets, plazas)
    'outdoor_obstructed', 0.15, ... % 15% outdoor with obstacles (trees, vehicles)
    'indoor_light', 0.25, ...      % 25% indoor light (glass, open malls)
    'indoor_heavy', 0.20 ...       % 20% indoor heavy (concrete, closed)
);

% Map zones to NLOS conditions
% outdoor_open → mostly pure_los (80% LOS, 20% light NLOS)
% outdoor_obstructed → light_nlos (20% LOS, 60% light, 20% moderate)
% indoor_light → moderate_nlos (10% light, 70% moderate, 20% heavy)
% indoor_heavy → heavy_nlos (10% moderate, 90% heavy)

config.zone_nlos_mapping = struct(...
    'outdoor_open', struct('pure_los', 0.80, 'light_nlos', 0.20, 'moderate_nlos', 0.00, 'heavy_nlos', 0.00), ...
    'outdoor_obstructed', struct('pure_los', 0.20, 'light_nlos', 0.60, 'moderate_nlos', 0.20, 'heavy_nlos', 0.00), ...
    'indoor_light', struct('pure_los', 0.00, 'light_nlos', 0.10, 'moderate_nlos', 0.70, 'heavy_nlos', 0.20), ...
    'indoor_heavy', struct('pure_los', 0.00, 'light_nlos', 0.00, 'moderate_nlos', 0.10, 'heavy_nlos', 0.90) ...
);

% NLOS scenario mapping for QuaDRiGa
config.nlos_scenarios = struct(...
    'pure_los', '3GPP_38.901_UMa_LOS', ...       % No obstruction
    'light_nlos', '3GPP_38.901_UMa_NLOS', ...    % Single obstruction
    'moderate_nlos', '3GPP_38.901_UMa_NLOS', ... % Multiple obstructions
    'heavy_nlos', '3GPP_38.901_UMa_NLOS' ...     % Heavy obstruction (same scenario, different zones)
);

%% Trajectory Distribution (Same diversity as exp11)
config.trajectory_distribution = struct(...
    'linear', 0.25, ...        % 25% straight lines (walking along streets)
    'circular', 0.10, ...      % 10% circles
    'zigzag', 0.15, ...        % 15% zigzag (avoiding obstacles)
    'random_walk', 0.25, ...   % 25% random walk (browsing, wandering)
    'grid', 0.05, ...          % 5% grid pattern (systematic coverage)
    'spiral', 0.05, ...        % 5% spiral
    'figure8', 0.05, ...       % 5% figure-8
    'stop_and_go', 0.10 ...    % 10% stop-and-go (NEW - realistic shopping/browsing)
);

% Validate trajectory distribution sums to 1.0
traj_sum = config.trajectory_distribution.linear + ...
           config.trajectory_distribution.circular + ...
           config.trajectory_distribution.zigzag + ...
           config.trajectory_distribution.random_walk + ...
           config.trajectory_distribution.grid + ...
           config.trajectory_distribution.spiral + ...
           config.trajectory_distribution.figure8 + ...
           config.trajectory_distribution.stop_and_go;
assert(abs(traj_sum - 1.0) < 1e-6, 'Trajectory distribution must sum to 1.0!');

%% Scenario Parameters - URBAN SCALE
config.scenario = struct();

% Frequency and bandwidth (3 GHz for better penetration)
config.scenario.frequency = 3.0e9;   % 3.0 GHz (5G mid-band)
config.scenario.bandwidth = 100e6;   % 100 MHz
config.scenario.n_subcarriers = 2048; % 2048 subcarriers (finer resolution)

% Environment bounds (300m × 300m urban block)
config.scenario.bounds = struct(...
    'x_min', 0, ...
    'x_max', 300, ...
    'y_min', 0, ...
    'y_max', 300 ...
);

%% Base Station Configuration - HYBRID DEPLOYMENT (6 BSs)
config.bs = struct();

% Strategic BS placement:
% - 2 corner BSs (macro coverage) at high altitude
% - 2 outdoor small cells along main paths
% - 2 indoor small cells for building coverage

config.bs.positions = [
    % Corner BSs (Macro - rooftop mounted)
    50,  50,  25;     % BS1 - SW corner (high)
    250, 250, 25;     % BS2 - NE corner (high)
    
    % Outdoor Small Cells (street poles)
    150, 75,  10;     % BS3 - South street
    150, 225, 10;     % BS4 - North street
    
    % Indoor Small Cells (ceiling mounted)
    75,  150, 6;      % BS5 - West building
    225, 150, 6       % BS6 - East building
];

config.bs.types = {'macro', 'macro', 'outdoor_small', 'outdoor_small', 'indoor_small', 'indoor_small'};
config.bs.n_antennas = 4;
config.bs.antenna_spacing = 0.5;  % lambda/2

% Transmit power (varied by type)
config.bs.tx_power_dbm = [35, 35, 30, 30, 27, 27];  % Macro higher, indoor lower

%% UE Configuration - VARIABLE HEIGHT
config.ue = struct();
config.ue.n_antennas = 1;
config.ue.height_min = 0.8;   % Sitting, phone low (NEW)
config.ue.height_max = 1.8;   % Standing, phone raised (NEW)
config.ue.velocity = 1.2;     % m/s (slightly faster urban walking)

% Noise figure
config.ue.noise_figure_db = 9;

%% Trajectory Generation Parameters (Scaled for larger area)

% Linear trajectories
config.linear = struct(...
    'min_distance', 50, ...     % Longer paths in urban area
    'max_distance', 200, ...    % Can walk across significant portion
    'randomize', true ...       % Add perturbations
);

% Circular trajectories
config.circular = struct(...
    'min_radius', 20, ...
    'max_radius', 80, ...
    'revolutions', [0.5, 1.5] ...
);

% Zigzag trajectories
config.zigzag = struct(...
    'amplitude_range', [5, 15], ...    % Larger zigzags
    'frequency_range', [2, 6] ...
);

% Random walk
config.random_walk = struct(...
    'step_size_range', [2.0, 5.0], ... % Larger steps
    'smoothing', 5 ...
);

% Grid pattern
config.grid = struct(...
    'spacing_range', [15, 30] ...  % Wider grid spacing
);

% Spiral trajectories
config.spiral = struct(...
    'radius_start_range', [10, 20], ...
    'radius_end_range', [50, 80], ...
    'revolutions_range', [2, 4] ...
);

% Figure-8 trajectories
config.figure8 = struct(...
    'size_range', [20, 50] ...  % Larger figure-8
);

% Stop-and-go trajectories (NEW)
config.stop_and_go = struct(...
    'segment_length', [10, 30], ...    % Walk distance between stops
    'stop_duration', [3, 8], ...       % Timesteps to stop
    'n_stops', [2, 5] ...              % Number of stops per trajectory
);

%% QuaDRiGa Parameters
config.quadriga = struct();
config.quadriga.sample_rate = 100e6;  % 100 MHz
config.quadriga.use_absolute_delays = true;
config.quadriga.show_progress_bars = true;

%% Output Configuration
config.output = struct();
config.output.save_raw_channels = false;        % Save only processed features
config.output.save_zone_metadata = true;        % Save zone info per sample
config.output.save_nlos_metadata = true;        % Save NLOS condition per sample
config.output.save_ue_heights = true;           % Save UE height per sample (NEW)
config.output.generate_plots = true;            % Generate trajectory plots

% Adjust plot frequency based on mode
if config.DEBUG_MODE
    config.output.plot_frequency = 2;           % DEBUG: Plot every 2nd trajectory
else
    config.output.plot_frequency = 100;         % PRODUCTION: Plot every 100th
end

config.output.generate_zone_analysis = true;    % Generate zone analysis plots
config.output.generate_bs_visualization = true; % Visualize BS placement
config.output.verbose = true;

%% Feature Extraction
config.features = struct();
config.features.extract_wideband = true;         % CQI, RSRP, SINR
config.features.extract_per_subcarrier = true;   % RSS, SINR, H_mag per SC

%% Validation
config.validation = struct();
config.validation.check_coverage = true;         % Verify spatial coverage
config.validation.min_samples_per_region = 50;   % Samples per 30x30m region (10×10 grid)
config.validation.check_diversity = true;        % Check trajectory diversity
config.validation.check_zone_distribution = true; % Verify zone mix

%% Random Seed (for reproducibility)
config.random_seed = 42;
rng(config.random_seed);

%% Display Configuration Summary
fprintf('\n========================================\n');
fprintf('URBAN MIXED SCENARIO CONFIGURATION\n');
fprintf('========================================\n\n');

fprintf('--- SCALE ---\n');
fprintf('Area: %d × %d m² (%.1f hectares)\n', ...
    config.scenario.bounds.x_max - config.scenario.bounds.x_min, ...
    config.scenario.bounds.y_max - config.scenario.bounds.y_min, ...
    ((config.scenario.bounds.x_max - config.scenario.bounds.x_min) * ...
     (config.scenario.bounds.y_max - config.scenario.bounds.y_min)) / 10000);
fprintf('Total Trajectories: %d\n', config.n_trajectories);
fprintf('Samples per Trajectory: %d\n', config.n_timesteps);
fprintf('Total Samples: %s\n', num2str(config.n_trajectories * config.n_timesteps, '%d'));
fprintf('Train/Val Split: %.1f%% / %.1f%%\n\n', 100*config.train_ratio, 100*(1-config.train_ratio));

fprintf('--- FREQUENCY CONFIGURATION ---\n');
fprintf('Center Frequency: %.1f GHz\n', config.scenario.frequency / 1e9);
fprintf('Bandwidth: %.0f MHz\n', config.scenario.bandwidth / 1e6);
fprintf('Subcarriers: %d\n', config.scenario.n_subcarriers);
fprintf('Subcarrier Spacing: %.2f kHz\n\n', (config.scenario.bandwidth / config.scenario.n_subcarriers) / 1e3);

fprintf('--- BASE STATION DEPLOYMENT ---\n');
fprintf('Total BSs: %d\n', size(config.bs.positions, 1));
for i = 1:size(config.bs.positions, 1)
    fprintf('  BS%d (%s): (%.0f, %.0f, %.0f)m, %d dBm\n', ...
        i, config.bs.types{i}, ...
        config.bs.positions(i, 1), config.bs.positions(i, 2), config.bs.positions(i, 3), ...
        config.bs.tx_power_dbm(i));
end

fprintf('\n--- ZONE DISTRIBUTION (Target) ---\n');
zones = fieldnames(config.zone_distribution);
for i = 1:length(zones)
    zone = zones{i};
    fprintf('  %-20s %.1f%%\n', [zone ':'], 100 * config.zone_distribution.(zone));
end

fprintf('\n--- TRAJECTORY TYPES ---\n');
types = fieldnames(config.trajectory_distribution);
for i = 1:length(types)
    type = types{i};
    count = round(config.n_trajectories * config.trajectory_distribution.(type));
    fprintf('  %-15s %4d trajectories (%.1f%%)\n', ...
        [upper(type(1)) type(2:end) ':'], count, ...
        100 * config.trajectory_distribution.(type));
end

fprintf('\n--- UE CONFIGURATION ---\n');
fprintf('Height Range: %.1f - %.1f m (variable)\n', config.ue.height_min, config.ue.height_max);
fprintf('Velocity: %.1f m/s\n', config.ue.velocity);

fprintf('\n========================================\n\n');
