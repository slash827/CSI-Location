function run_from_config(config_json_path)
%RUN_FROM_CONFIG Reproduce an experiment from a saved JSON configuration
%
% Usage:
%   run_from_config('results/grid_localization/grid_3x3/exp_*/experiment_config.json')
%
% This function loads a saved experiment configuration and reruns the
% experiment with identical parameters.

    if nargin < 1
        error('Usage: run_from_config(config_json_path)');
    end
    
    % Check if file exists
    if ~exist(config_json_path, 'file')
        error('Config file not found: %s', config_json_path);
    end
    
    fprintf('========================================\n');
    fprintf('Running Experiment from Config\n');
    fprintf('========================================\n\n');
    fprintf('Loading config from: %s\n\n', config_json_path);
    
    % Load JSON configuration
    fid = fopen(config_json_path, 'r');
    json_str = fread(fid, '*char')';
    fclose(fid);
    cfg = jsondecode(json_str);
    
    % Display configuration
    fprintf('Configuration:\n');
    fprintf('  Experiment: %s\n', cfg.experiment_name);
    fprintf('  Original Run: %s\n', cfg.timestamp);
    fprintf('  Grid: %dx%d, Spacing: %.1f m\n', cfg.grid_size, cfg.grid_size, cfg.spacing);
    fprintf('  Steps: %d, Speed: %.1f m/s\n', cfg.n_steps, cfg.ue_speed);
    fprintf('  Scenario: %s\n\n', cfg.scenario);
    
    % Setup paths
    script_dir      = fileparts(mfilename('fullpath'));          % runners/
    src_matlab_dir  = fileparts(script_dir);                    % src/matlab/
    project_root    = fileparts(fileparts(src_matlab_dir));     % 09_grid_localization/
    workspace_root  = fileparts(fileparts(project_root));       % CSI-Location/
    utils_path = fullfile(workspace_root, 'utils');
    addpath(fullfile(src_matlab_dir, 'core'));
    addpath(fullfile(src_matlab_dir, 'lib'));
    addpath(utils_path);
    
    fprintf('Running from: experiments/09_grid_localization\n');
    
    % Reconstruct config struct for the experiment
    config = struct();
    config.grid_size = cfg.grid_size;
    config.spacing = cfg.spacing;
    config.ue_height = cfg.ue_height;
    config.grid_offset = cfg.grid_offset;
    config.position_jitter = cfg.position_jitter;
    config.n_steps = cfg.n_steps;
    config.ue_speed = cfg.ue_speed;
    config.step_duration = cfg.step_duration;
    config.center_frequency = cfg.center_frequency;
    config.bandwidth = cfg.bandwidth;
    config.n_subcarriers = cfg.n_subcarriers;
    config.scenario = cfg.scenario;
    config.bs_position = cfg.bs_position;
    
    % Generate grid positions
    [X, Y] = meshgrid(0:config.spacing:(config.grid_size-1)*config.spacing, ...
                      0:config.spacing:(config.grid_size-1)*config.spacing);
    config.grid_positions = [X(:) + config.grid_offset(1), ...
                             Y(:) + config.grid_offset(2), ...
                             ones(config.grid_size^2, 1) * config.ue_height];
    config.n_points = config.grid_size^2;
    
    % Build adjacency map
    config.neighbors = cell(config.n_points, 1);
    for row = 1:config.grid_size
        for col = 1:config.grid_size
            idx = (row-1)*config.grid_size + col;
            neighbors = [];
            if col < config.grid_size, neighbors = [neighbors, idx+1]; end
            if col > 1, neighbors = [neighbors, idx-1]; end
            if row < config.grid_size, neighbors = [neighbors, idx+config.grid_size]; end
            if row > 1, neighbors = [neighbors, idx-config.grid_size]; end
            config.neighbors{idx} = neighbors;
        end
    end
    
    fprintf('WARNING: This will run the full experiment, which may take 10-30 minutes.\n');
    response = input('Continue? (y/n): ', 's');
    
    if ~strcmpi(response, 'y')
        fprintf('Experiment cancelled.\n');
        return;
    end
    
    fprintf('\nStarting experiment reproduction...\n\n');
    
    %% Generate random walk (using same seed for reproducibility)
    fprintf('Generating random walk...\n');
    rng(cfg.random_seed);
    walk_path = zeros(config.n_steps + 1, 1);
    walk_path(1) = ceil(config.n_points / 2);  % Start at center
    
    for step = 1:config.n_steps
        current = walk_path(step);
        neighbors = config.neighbors{current};
        next = neighbors(randi(length(neighbors)));
        walk_path(step + 1) = next;
    end
    
    visit_counts = histcounts(walk_path, 1:(config.n_points+1));
    fprintf('  Visit distribution: min=%d, max=%d\n\n', min(visit_counts), max(visit_counts));
    
    %% Run QuaDRiGa simulation
    fprintf('Running QuaDRiGa simulation...\n');
    n_snapshots = config.n_steps + 1;
    walk_grid_positions = zeros(3, n_snapshots);
    for step = 1:n_snapshots
        pt = walk_path(step);
        walk_grid_positions(:, step) = config.grid_positions(pt, :)';
    end
    
    % Create layout
    l = qd_layout;
    l.set_scenario(config.scenario);
    l.tx_position = config.bs_position;
    
    % Create track
    t = qd_track('linear', 0, 0);
    t.name = 'RandomWalk';
    t.scenario = config.scenario;
    t.positions = walk_grid_positions;
    
    l.no_rx = 1;
    l.rx_track(1) = copy(t);
    
    fprintf('  Generating channels (this may take a while)...\n');
    tic;
    l.set_pairing;
    c = l.get_channels;
    fprintf('  Channel generation: %.1f seconds\n\n', toc);
    
    %% Compute CSI metrics
    fprintf('Computing CSI metrics...\n');
    tic;
    csi_metrics = CSIMetrics(config.center_frequency, config.bandwidth, config.n_subcarriers);
    
    if iscell(c)
        h_eff = c{1}.fr(config.bandwidth, config.n_subcarriers);
    else
        h_eff = c.fr(config.bandwidth, config.n_subcarriers);
    end
    
    metrics = struct();
    metrics.RSS_wb = zeros(n_snapshots, 1);
    metrics.SINR_wb = zeros(n_snapshots, 1);
    metrics.CQI_wb = zeros(n_snapshots, 1);
    
    for snap_idx = 1:n_snapshots
        h_snap = squeeze(h_eff(:, :, snap_idx));
        [rss, sinr, cqi] = csi_metrics.computeMetrics(h_snap);
        metrics.RSS_wb(snap_idx) = rss;
        metrics.SINR_wb(snap_idx) = sinr;
        metrics.CQI_wb(snap_idx) = cqi;
    end
    
    fprintf('  Metrics computed (%.1f seconds)\n\n', toc);
    
    fprintf('========================================\n');
    fprintf('Reproduction Complete!\n');
    fprintf('Note: This was a reproduction run. Full analysis not performed.\n');
    fprintf('To run full analysis, use exp13e_corrected_fair_comparison.m\n');
    fprintf('========================================\n');
    
    % Optionally return data
    if nargout > 0
        varargout{1} = config;
        varargout{2} = walk_path;
        varargout{3} = metrics;
    end
end
