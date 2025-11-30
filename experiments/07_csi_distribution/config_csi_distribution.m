% Configuration for CSI Distribution Study
% ========================================
% This experiment studies the statistical distribution of CSI at fixed
% locations by simulating multiple observations at each grid point.

%% Dataset Parameters
config = struct();

% Grid configuration
config.grid = struct();
config.grid.plane_size = [200, 200];      % [x, y] size in meters (200x200m)
config.grid.grid_points = [20, 20];       % [nx, ny] number of grid points (20x20)
config.grid.n_samples_per_point = 100;    % Number of CSI samples per grid point
config.grid.z_height = 1.5;               % UE height in meters

% Calculate grid spacing automatically
config.grid.spacing_x = config.grid.plane_size(1) / (config.grid.grid_points(1) - 1);
config.grid.spacing_y = config.grid.plane_size(2) / (config.grid.grid_points(2) - 1);

%% Scenario Parameters
config.scenario = struct();

% 5G parameters
config.scenario.type = '3GPP_38.901_UMi';  % Urban Micro (heterogeneous environment)
config.scenario.frequency = 3e9;            % 3 GHz (5G mid-band)
config.scenario.bandwidth = 100e6;          % 100 MHz
config.scenario.n_subcarriers = 256;        % Number of subcarriers

% Environment configuration (heterogeneous with LOS and NLOS)
config.scenario.los_probability = 0.5;     % 50% LOS, 50% NLOS for heterogeneity
config.scenario.use_3gpp_baseline = true;  % Use 3GPP channel model

%% Base Station Configuration
config.bs = struct();

% Single BS in the center of the plane
center_x = config.grid.plane_size(1) / 2;
center_y = config.grid.plane_size(2) / 2;

config.bs.position = [center_x; center_y; 25];  % [x, y, z] in meters, BS at 25m height
config.bs.n_antennas = 4;                        % Number of antennas
config.bs.antenna_spacing = 0.5;                 % lambda/2 spacing
config.bs.tx_power_dbm = 30;                     % 30 dBm (1 W)

%% UE Configuration
config.ue = struct();
config.ue.n_antennas = 1;                  % Single antenna UE
config.ue.height = config.grid.z_height;   % Height in meters
config.ue.noise_figure_db = 9;             % Noise figure

%% QuaDRiGa Parameters
config.quadriga = struct();
config.quadriga.sample_rate = 100e6;       % 100 MHz
config.quadriga.use_absolute_delays = true;
config.quadriga.show_progress_bars = false; % Disable for cleaner output

%% CSI Extraction Parameters
config.csi = struct();
config.csi.extract_time_domain = true;     % Save time-domain channel
config.csi.extract_freq_domain = true;     % Save frequency-domain channel
config.csi.extract_metrics = true;         % Calculate RSS, SINR, CQI

%% Statistical Analysis Configuration
config.analysis = struct();
config.analysis.compute_mean = true;       % Compute mean CSI at each point
config.analysis.compute_variance = true;   % Compute variance
config.analysis.compute_std = true;        % Compute standard deviation
config.analysis.compute_percentiles = [5, 25, 50, 75, 95]; % Percentiles to compute
config.analysis.fit_distributions = true;  % Fit statistical distributions

%% Output Configuration
config.output = struct();
config.output.save_raw_samples = true;     % Save all 100 samples per grid point
config.output.save_statistics = true;      % Save computed statistics
config.output.generate_plots = true;       % Generate visualization plots
config.output.plot_frequency = 20;         % Plot every Nth grid point
config.output.verbose = true;              % Detailed console output

% Visualization options
config.output.plot_heatmaps = true;        % Generate heatmaps of CSI statistics
config.output.plot_distributions = true;   % Plot CSI distributions at sample points
config.output.plot_3d = true;              % Generate 3D visualizations

%% Random Seed (for reproducibility)
config.random_seed = 42;
rng(config.random_seed);

%% Derived Parameters
% Total number of grid points
config.total_grid_points = config.grid.grid_points(1) * config.grid.grid_points(2);

% Total number of samples
config.total_samples = config.total_grid_points * config.grid.n_samples_per_point;

% Grid point coordinates
[grid_x, grid_y] = meshgrid(...
    linspace(0, config.grid.plane_size(1), config.grid.grid_points(1)), ...
    linspace(0, config.grid.plane_size(2), config.grid.grid_points(2)));

config.grid.x_coords = grid_x;
config.grid.y_coords = grid_y;

%% Display Configuration Summary
fprintf('========================================\n');
fprintf('CSI DISTRIBUTION STUDY CONFIGURATION\n');
fprintf('========================================\n\n');

fprintf('Grid Configuration:\n');
fprintf('  Plane size: %.0f x %.0f meters\n', ...
    config.grid.plane_size(1), config.grid.plane_size(2));
fprintf('  Grid resolution: %d x %d points\n', ...
    config.grid.grid_points(1), config.grid.grid_points(2));
fprintf('  Grid spacing: %.2f x %.2f meters\n', ...
    config.grid.spacing_x, config.grid.spacing_y);
fprintf('  Total grid points: %d\n', config.total_grid_points);
fprintf('  Samples per point: %d\n', config.grid.n_samples_per_point);
fprintf('  Total samples: %d\n\n', config.total_samples);

fprintf('Network Configuration:\n');
fprintf('  Technology: 5G (3GPP 38.901)\n');
fprintf('  Frequency: %.1f GHz\n', config.scenario.frequency / 1e9);
fprintf('  Bandwidth: %.0f MHz\n', config.scenario.bandwidth / 1e6);
fprintf('  Subcarriers: %d\n', config.scenario.n_subcarriers);
fprintf('  Scenario: %s\n', config.scenario.type);
fprintf('  LOS Probability: %.0f%%\n\n', config.scenario.los_probability * 100);

fprintf('Base Station:\n');
fprintf('  Position: [%.1f, %.1f, %.1f] m\n', ...
    config.bs.position(1), config.bs.position(2), config.bs.position(3));
fprintf('  Location: Center of plane\n');
fprintf('  TX Power: %d dBm\n', config.bs.tx_power_dbm);
fprintf('  Antennas: %d\n\n', config.bs.n_antennas);

fprintf('Expected Runtime:\n');
fprintf('  Estimated: %.1f - %.1f minutes\n', ...
    config.total_samples * 0.1 / 60, config.total_samples * 0.2 / 60);
fprintf('  (depends on hardware)\n\n');

fprintf('========================================\n\n');
