% Configuration for Large-Scale Dataset Generation
% ================================================

%% Dataset Parameters
config = struct();

% Total number of trajectories
config.n_trajectories = 500;

% Trajectory distribution (percentages, must sum to 1.0)
config.trajectory_distribution = struct(...
    'linear', 0.20, ...        % 20% straight lines
    'circular', 0.15, ...      % 15% circles
    'zigzag', 0.15, ...        % 15% zigzag
    'random_walk', 0.20, ...   % 20% random walk
    'grid', 0.10, ...          % 10% grid pattern
    'spiral', 0.10, ...        % 10% spiral
    'figure8', 0.10 ...        % 10% figure-8
);

% Samples per trajectory
config.n_timesteps = 80;       % Total time steps per trajectory
config.train_ratio = 0.8;      % 80% train, 20% validation

%% Scenario Parameters
config.scenario = struct();

% Indoor scenario
config.scenario.type = '3GPP_38.901_UMa_LOS';  % 3GPP Urban Macro LOS scenario
config.scenario.frequency = 3.5e9;  % 3.5 GHz
config.scenario.bandwidth = 100e6;  % 100 MHz
config.scenario.n_subcarriers = 256;

% Environment bounds
config.scenario.bounds = struct(...
    'x_min', 10, ...
    'x_max', 90, ...
    'y_min', 10, ...
    'y_max', 90, ...
    'z', 1.5 ...  % UE height (1.5m)
);

%% Base Station Configuration
config.bs = struct();

% 4 BS at corners (same as exp09)
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

%% UE Configuration
config.ue = struct();
config.ue.n_antennas = 1;
config.ue.height = 1.5;  % meters
config.ue.velocity = 1.0;  % m/s (walking speed)

% Noise figure
config.ue.noise_figure_db = 9;

%% Trajectory Generation Parameters

% Linear trajectories
config.linear = struct(...
    'min_distance', 20, ...    % Minimum path length
    'max_distance', 70, ...    % Maximum path length
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

%% QuaDRiGa Parameters
config.quadriga = struct();
config.quadriga.sample_rate = 100e6;  % 100 MHz
config.quadriga.use_absolute_delays = true;
config.quadriga.show_progress_bars = true;

%% Output Configuration
config.output = struct();
config.output.save_raw_channels = false;  % Save only processed features
config.output.generate_plots = true;      % Generate trajectory plots
config.output.plot_frequency = 50;        % Plot every Nth trajectory
config.output.verbose = true;

%% Feature Extraction
config.features = struct();
config.features.extract_wideband = true;   % CQI, RSRP, SINR
config.features.extract_per_subcarrier = true;  % RSS, SINR, H_mag per SC

%% Validation
config.validation = struct();
config.validation.check_coverage = true;   % Verify spatial coverage
config.validation.min_samples_per_region = 100;  % Samples per 10x10m region
config.validation.check_diversity = true;  % Check trajectory diversity

%% Random Seed (for reproducibility)
config.random_seed = 42;
rng(config.random_seed);

%% Helper function to get number of trajectories per type
function counts = get_trajectory_counts(config)
    types = fieldnames(config.trajectory_distribution);
    counts = struct();
    
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
