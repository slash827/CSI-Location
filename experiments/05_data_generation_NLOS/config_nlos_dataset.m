% Configuration for NLOS-Enhanced Large-Scale Dataset Generation
% ================================================================
% 
% This configuration extends exp10 with NLOS (Non-Line-of-Sight) scenarios
% to create a more realistic indoor localization dataset.
%
% Dataset composition:
%   - 30% Pure LOS (open corridors)
%   - 25% Light NLOS (single thin obstacle)
%   - 25% Moderate NLOS (multiple walls)
%   - 20% Heavy NLOS (deep indoor, thick walls)
%
% Total: 40,000 samples (500 trajectories × 80 samples)

%% Dataset Parameters
config = struct();

% Total number of trajectories (same as exp10)
config.n_trajectories = 500;

% Samples per trajectory (same as exp10)
config.n_timesteps = 80;       % Total time steps per trajectory
config.train_ratio = 0.8;      % 80% train, 20% validation

%% NLOS Distribution (NEW - Core Feature)
% Define the mix of LOS and NLOS scenarios
config.nlos_distribution = struct(...
    'pure_los', 0.30, ...       % 30% pure LOS scenarios
    'light_nlos', 0.25, ...     % 25% light NLOS (single obstacle)
    'moderate_nlos', 0.25, ...  % 25% moderate NLOS (multiple walls)
    'heavy_nlos', 0.20 ...      % 20% heavy NLOS (deep indoor)
);

% Scenario mapping for QuaDRiGa
config.nlos_scenarios = struct(...
    'pure_los', '3GPP_38.901_UMa_LOS', ...       % No obstruction
    'light_nlos', '3GPP_38.901_UMa_NLOS', ...    % Single obstruction
    'moderate_nlos', '3GPP_38.901_UMa_NLOS', ... % Multiple obstructions
    'heavy_nlos', '3GPP_38.901_UMa_NLOS' ...     % Severe obstruction
);

% Validate NLOS distribution sums to 1.0
nlos_sum = config.nlos_distribution.pure_los + ...
           config.nlos_distribution.light_nlos + ...
           config.nlos_distribution.moderate_nlos + ...
           config.nlos_distribution.heavy_nlos;
assert(abs(nlos_sum - 1.0) < 1e-6, 'NLOS distribution must sum to 1.0!');

%% Trajectory Distribution (Same as exp10)
% Keep consistent trajectory types across LOS/NLOS conditions
config.trajectory_distribution = struct(...
    'linear', 0.20, ...        % 20% straight lines
    'circular', 0.15, ...      % 15% circles
    'zigzag', 0.15, ...        % 15% zigzag
    'random_walk', 0.20, ...   % 20% random walk
    'grid', 0.10, ...          % 10% grid pattern
    'spiral', 0.10, ...        % 10% spiral
    'figure8', 0.10 ...        % 10% figure-8
);

% Validate trajectory distribution sums to 1.0
traj_sum = config.trajectory_distribution.linear + ...
           config.trajectory_distribution.circular + ...
           config.trajectory_distribution.zigzag + ...
           config.trajectory_distribution.random_walk + ...
           config.trajectory_distribution.grid + ...
           config.trajectory_distribution.spiral + ...
           config.trajectory_distribution.figure8;
assert(abs(traj_sum - 1.0) < 1e-6, 'Trajectory distribution must sum to 1.0!');

%% Scenario Parameters (Same as exp10)
config.scenario = struct();

% Frequency and bandwidth
config.scenario.frequency = 3.5e9;  % 3.5 GHz (5G mid-band)
config.scenario.bandwidth = 100e6;  % 100 MHz
config.scenario.n_subcarriers = 1024;  % 1024 subcarriers (updated from 256)

% Environment bounds (80m × 80m indoor area)
config.scenario.bounds = struct(...
    'x_min', 10, ...
    'x_max', 90, ...
    'y_min', 10, ...
    'y_max', 90, ...
    'z', 1.5 ...  % UE height (1.5m - typical user)
);

%% Base Station Configuration (Same as exp10)
config.bs = struct();

% 4 BS at corners for triangulation
config.bs.positions = [
    10, 10, 10;    % BS1 - bottom-left
    90, 10, 10;    % BS2 - bottom-right
    90, 90, 10;    % BS3 - top-right
    10, 90, 10     % BS4 - top-left
];

config.bs.n_antennas = 4;
config.bs.antenna_spacing = 0.5;  % lambda/2

% Transmit power
config.bs.tx_power_dbm = 30;  % 30 dBm (1 W)

%% UE Configuration (Same as exp10)
config.ue = struct();
config.ue.n_antennas = 1;
config.ue.height = 1.5;  % meters (typical user)
config.ue.velocity = 1.0;  % m/s (walking speed)

% Noise figure
config.ue.noise_figure_db = 9;

%% Trajectory Generation Parameters (Same as exp10)

% Linear trajectories
config.linear = struct(...
    'min_distance', 20, ...    % Minimum path length (m)
    'max_distance', 70, ...    % Maximum path length (m)
    'randomize', true ...      % Add small random perturbations
);

% Circular trajectories
config.circular = struct(...
    'min_radius', 10, ...
    'max_radius', 35, ...
    'revolutions', [0.5, 1.5] ...  % Range of revolutions
);

% Zigzag trajectories
config.zigzag = struct(...
    'amplitude_range', [3, 8], ...    % Meters
    'frequency_range', [2, 5] ...     % Number of zigzags
);

% Random walk
config.random_walk = struct(...
    'step_size_range', [1.5, 3.0], ... % Meters per step
    'smoothing', 5 ...                  % Smoothing window
);

% Grid pattern
config.grid = struct(...
    'spacing_range', [5, 10] ...  % Grid spacing in meters
);

% Spiral trajectories
config.spiral = struct(...
    'radius_start_range', [5, 10], ...
    'radius_end_range', [25, 35], ...
    'revolutions_range', [2, 4] ...
);

% Figure-8 trajectories
config.figure8 = struct(...
    'size_range', [10, 25] ...  % Size in meters
);

%% QuaDRiGa Parameters (Same as exp10)
config.quadriga = struct();
config.quadriga.sample_rate = 100e6;  % 100 MHz
config.quadriga.use_absolute_delays = true;
config.quadriga.show_progress_bars = true;

%% Output Configuration
config.output = struct();
config.output.save_raw_channels = false;      % Save only processed features
config.output.save_nlos_metadata = true;      % NEW: Save NLOS condition per sample
config.output.generate_plots = true;          % Generate trajectory plots
config.output.plot_frequency = 50;            % Plot every Nth trajectory
config.output.generate_nlos_analysis = true;  % NEW: Generate NLOS analysis plots
config.output.verbose = true;

%% Feature Extraction (Same as exp10)
config.features = struct();
config.features.extract_wideband = true;   % CQI, RSRP, SINR
config.features.extract_per_subcarrier = true;  % RSS, SINR, H_mag per SC

%% Validation
config.validation = struct();
config.validation.check_coverage = true;   % Verify spatial coverage
config.validation.min_samples_per_region = 100;  % Samples per 10x10m region
config.validation.check_diversity = true;  % Check trajectory diversity
config.validation.check_nlos_distribution = true;  % NEW: Verify NLOS mix

%% Random Seed (for reproducibility)
config.random_seed = 42;
rng(config.random_seed);

%% Display Configuration Summary
fprintf('\n========================================\n');
fprintf('NLOS-ENHANCED DATASET CONFIGURATION\n');
fprintf('========================================\n\n');

fprintf('Total Trajectories: %d\n', config.n_trajectories);
fprintf('Samples per Trajectory: %d\n', config.n_timesteps);
fprintf('Total Samples: %d\n', config.n_trajectories * config.n_timesteps);
fprintf('Train/Val Split: %.1f%% / %.1f%%\n', 100*config.train_ratio, 100*(1-config.train_ratio));

fprintf('\n--- NLOS Distribution ---\n');
fprintf('  Pure LOS:       %3d trajectories (%.1f%%)\n', ...
    round(config.n_trajectories * config.nlos_distribution.pure_los), ...
    100 * config.nlos_distribution.pure_los);
fprintf('  Light NLOS:     %3d trajectories (%.1f%%)\n', ...
    round(config.n_trajectories * config.nlos_distribution.light_nlos), ...
    100 * config.nlos_distribution.light_nlos);
fprintf('  Moderate NLOS:  %3d trajectories (%.1f%%)\n', ...
    round(config.n_trajectories * config.nlos_distribution.moderate_nlos), ...
    100 * config.nlos_distribution.moderate_nlos);
fprintf('  Heavy NLOS:     %3d trajectories (%.1f%%)\n', ...
    round(config.n_trajectories * config.nlos_distribution.heavy_nlos), ...
    100 * config.nlos_distribution.heavy_nlos);

fprintf('\n--- Trajectory Types ---\n');
types = fieldnames(config.trajectory_distribution);
for i = 1:length(types)
    type = types{i};
    count = round(config.n_trajectories * config.trajectory_distribution.(type));
    fprintf('  %-15s %3d trajectories (%.1f%%)\n', ...
        [upper(type(1)) type(2:end) ':'], count, ...
        100 * config.trajectory_distribution.(type));
end

fprintf('\n--- Frequency Configuration ---\n');
fprintf('  Center Frequency: %.2f GHz\n', config.scenario.frequency / 1e9);
fprintf('  Bandwidth: %.0f MHz\n', config.scenario.bandwidth / 1e6);
fprintf('  Subcarriers: %d\n', config.scenario.n_subcarriers);

fprintf('\n--- Spatial Configuration ---\n');
fprintf('  Area: %.0f × %.0f m²\n', ...
    config.scenario.bounds.x_max - config.scenario.bounds.x_min, ...
    config.scenario.bounds.y_max - config.scenario.bounds.y_min);
fprintf('  Base Stations: %d\n', size(config.bs.positions, 1));
fprintf('  UE Height: %.1f m\n', config.ue.height);

fprintf('\n========================================\n\n');

%% Helper Functions

% Get trajectory counts per type (corrected for rounding)
function counts = get_trajectory_counts(config)
    types = fieldnames(config.trajectory_distribution);
    counts = struct();
    
    % Initial allocation
    for i = 1:length(types)
        type = types{i};
        percentage = config.trajectory_distribution.(type);
        counts.(type) = round(config.n_trajectories * percentage);
    end
    
    % Adjust to ensure sum equals n_trajectories
    total = 0;
    for i = 1:length(types)
        total = total + counts.(types{i});
    end
    
    % Add/subtract difference from largest category
    if total ~= config.n_trajectories
        [~, idx] = max(structfun(@(x) x, counts));
        counts.(types{idx}) = counts.(types{idx}) + (config.n_trajectories - total);
    end
end

% Get NLOS type counts (corrected for rounding)
function counts = get_nlos_counts(config)
    types = fieldnames(config.nlos_distribution);
    counts = struct();
    
    % Initial allocation
    for i = 1:length(types)
        type = types{i};
        percentage = config.nlos_distribution.(type);
        counts.(type) = round(config.n_trajectories * percentage);
    end
    
    % Adjust to ensure sum equals n_trajectories
    total = 0;
    for i = 1:length(types)
        total = total + counts.(types{i});
    end
    
    % Add/subtract difference from largest category
    if total ~= config.n_trajectories
        [~, idx] = max(structfun(@(x) x, counts));
        counts.(types{idx}) = counts.(types{idx}) + (config.n_trajectories - total);
    end
end
