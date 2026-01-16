%% EXPERIMENT 13E (CORRECTED): Fair Comparison of Static vs Transition-Based Localization
% CRITICAL FIX: The original exp13e compared two DIFFERENT problems:
%   - Static: 9-class classification (which grid point?)
%   - Transition: 24-class classification (which edge?) ← WRONG!
%
% This version corrects the comparison. Both methods now solve the SAME problem:
%   - Problem: Predict which of the 9 grid points the UE is at
%   - Method 1 (Static): Use only RSS → predict location (1-9)
%   - Method 2 (Transition): Use RSS + Delta → predict location (1-9)
%
% Research question: Does adding delta (Δ) information improve localization accuracy?
%   Accuracy(RSS, Δ) > Accuracy(RSS) ???
%
% Grid configuration:
%   7 - 8 - 9
%   4 - 5 - 6
%   1 - 2 - 3

clear; clc; close all;

%% Setup
fprintf('========================================\n');
fprintf('EXP13E (CORRECTED): Fair Comparison\n');
fprintf('Static vs Transition-Based Localization\n');
fprintf('========================================\n\n');

% Add utils to path
script_dir = fileparts(mfilename('fullpath'));
project_root = fileparts(fileparts(script_dir));
utils_path = fullfile(project_root, 'utils');
addpath(utils_path);

fprintf('Experiment Directory: 09_grid_localization\n');

%% Load Configuration from JSON
config_file = fullfile(script_dir, 'config.json');
if ~exist(config_file, 'file')
    error('Configuration file not found: %s\nPlease create config.json', config_file);
end

fprintf('Loading configuration from: config.json\n');
config_json = jsondecode(fileread(config_file));

% Build config struct from JSON
config = struct();
config.grid_size = config_json.grid.size;
config.spacing = config_json.grid.spacing;
config.ue_height = config_json.grid.ue_height;
config.grid_offset = config_json.grid.grid_offset;
config.position_jitter = config_json.grid.position_jitter;

% Calculate n_steps: prefer steps_per_point (new), fallback to n_steps (old)
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
    error('Configuration must specify either "steps_per_point" or "n_steps" in movement section');
end

config.ue_speed = config_json.movement.ue_speed;
config.step_duration = config.spacing / config.ue_speed;
config.center_frequency = config_json.channel.center_frequency;
config.bandwidth = config_json.channel.bandwidth;
config.n_subcarriers = config_json.channel.n_subcarriers;
config.scenario = config_json.channel.scenario;
config.bs_position = config_json.base_station.position;

% Classification parameters
if isfield(config_json.classification, 'max_history_length')
    config.max_history_length = config_json.classification.max_history_length;
else
    config.max_history_length = 3;  % Default for backward compatibility
end

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

fprintf('Configuration:\n');
fprintf('  Grid: %dx%d points, Spacing: %.1f m\n', config.grid_size, config.grid_size, config.spacing);
fprintf('  Steps: %d, Scenario: %s\n\n', config.n_steps, config.scenario);

%% Generate random walk
fprintf('Generating random walk...\n');
rng(config_json.experiment.random_seed);  % Use seed from config
walk_path = zeros(config.n_steps + 1, 1);
walk_path(1) = 5;

for step = 1:config.n_steps
    current = walk_path(step);
    neighbors = config.neighbors{current};
    next = neighbors(randi(length(neighbors)));
    walk_path(step + 1) = next;
end

visit_counts = histcounts(walk_path, 1:(config.n_points+1));
fprintf('  Visit distribution: min=%d, max=%d\n\n', min(visit_counts), max(visit_counts));

%% Build trajectory and run simulation
fprintf('Running QuaDRiGa simulation...\n');
n_snapshots = config.n_steps + 1;
walk_grid_positions = zeros(3, n_snapshots);
for step = 1:n_snapshots
    pt = walk_path(step);
    walk_grid_positions(:, step) = config.grid_positions(pt, :)';
end

% Add position jitter
jitter = (rand(3, n_snapshots) - 0.5) * 2 * config.position_jitter;
jitter(3, :) = 0;
walk_trajectory = walk_grid_positions + jitter;

% Configure QuaDRiGa (matching original exp13e)
fprintf('  Setting up simulation...\n');
s = qd_simulation_parameters;
s.center_frequency = config.center_frequency;
s.use_absolute_delays = 1;
s.show_progress_bars = 0;

l = qd_layout(s);

% Check if interfering BSs are enabled
use_interferers = false;
if isfield(config_json.base_station, 'interferers')
    if config_json.base_station.interferers.enabled
        use_interferers = true;
        n_interferers = length(config_json.base_station.interferers.positions);
        fprintf('  Using %d interfering base stations\n', n_interferers);
    end
end

if use_interferers
    % Multi-BS setup: serving BS + interferers
    l.no_tx = 1 + n_interferers;
    
    % Serving BS (BS 1)
    l.tx_position(:, 1) = config.bs_position;
    l.tx_array(1, 1) = qd_arrayant('omni');
    
    % Interfering BSs
    % positions is a cell array of arrays in JSON, convert to matrix
    interf_positions = config_json.base_station.interferers.positions;
    for i = 1:n_interferers
        if iscell(interf_positions)
            % Cell array (older MATLAB JSON parsing)
            l.tx_position(:, i+1) = interf_positions{i}(:);
        else
            % Matrix (newer MATLAB JSON parsing or already a matrix)
            l.tx_position(:, i+1) = interf_positions(i, :)';
        end
        l.tx_array(1, i+1) = qd_arrayant('omni');
    end
else
    % Single BS setup (original)
    l.no_tx = 1;
    l.tx_position = config.bs_position;
    l.tx_array = qd_arrayant('omni');
end

l.rx_array = qd_arrayant('omni');

% Create track (no interpolation - use discrete snapshots)
trk = qd_track([]);
trk.name = 'RandomWalk';
trk.initial_position = walk_trajectory(:, 1);
trk.positions = walk_trajectory;
trk.no_snapshots = n_snapshots;
trk.scenario = {config.scenario};
trk.set_speed(config.ue_speed);
l.track(1,1) = trk;

% Run simulation
fprintf('  Generating channels (this may take 1-2 minutes)...\n');
tic;
ch_all = l.get_channels();
fprintf('  Channel generation complete (%.1f seconds)\n', toc);

% Extract serving BS channel
if use_interferers
    % With multiple BSs, get_channels returns a struct array or cell array
    if iscell(ch_all)
        ch = ch_all{1, 1};  % Cell array indexing
        ch_interferers = ch_all(1, 2:end);
    else
        % Struct array indexing (more common)
        ch = ch_all(1, 1);  % Serving BS only
        ch_interferers = ch_all(1, 2:end);  % Interfering BSs
    end
else
    ch = ch_all;  % Single BS (original behavior)
    ch_interferers = [];
end

% Compute CSI metrics
fprintf('Computing CSI metrics...\n');
tic;

% Initialize CSIMetrics object
fvec = linspace(-config.bandwidth/2, config.bandwidth/2, config.n_subcarriers);

% Get interference parameter from config (use -Inf if not specified or -999)
interference_dbm = -Inf;
if isfield(config_json.channel, 'interference_per_sc_dbm')
    if config_json.channel.interference_per_sc_dbm > -900
        interference_dbm = config_json.channel.interference_per_sc_dbm;
        fprintf('  Using interference: %.1f dBm per subcarrier\n', interference_dbm);
    else
        fprintf('  No interference (ideal scenario)\n');
    end
end

m = CSIMetrics('SubcarrierSpacing', config.bandwidth/config.n_subcarriers, ...
               'TxPowerPerSC_dBm', 0, 'NoiseFigure_dB', 7, ...
               'InterfPerSC_dBm', interference_dbm);

% DEBUG: Verify interference parameter
fprintf('  CSIMetrics initialized with InterfPerSC_dBm = %.1f dBm\n', m.InterfPerSC_dBm);

% Initialize metric storage
metrics = struct();
metrics.RSS_wb = zeros(n_snapshots, 1);
metrics.SINR_wb = zeros(n_snapshots, 1);
metrics.CQI_wb = zeros(n_snapshots, 1);

% Compute interference from interfering BSs (if enabled)
if use_interferers
    fprintf('  Computing interference from %d interfering BSs...\n', n_interferers);
    interference_W_sc = zeros(config.n_subcarriers, n_snapshots);  % [Nsc x Ns]
    
    Pt_W_sc = 10^((config_json.base_station.interferers.tx_power_dbm - 30) / 10);
    
    for bs_idx = 1:n_interferers
        if iscell(ch_interferers)
            ch_int = ch_interferers{bs_idx};
        else
            ch_int = ch_interferers(bs_idx);
        end
        
        for snap_idx = 1:n_snapshots
            coeff_int = ch_int.coeff(:,:,:,snap_idx);
            delays_int = ch_int.delay(:,:,:,snap_idx);
            
            h_paths_int = squeeze(coeff_int);
            tau_paths_int = squeeze(delays_int);
            H_freq_int = (h_paths_int(:).' * exp(-1j * 2 * pi * tau_paths_int(:) * fvec(:).')).';            
            
            % Compute interference power per subcarrier
            G_sc_int = abs(H_freq_int).^2;
            I_W_sc = Pt_W_sc * G_sc_int;
            
            interference_W_sc(:, snap_idx) = interference_W_sc(:, snap_idx) + I_W_sc;
        end
    end
    
    fprintf('  Interference computation complete\n');
end

% Compute metrics for each snapshot
progress_interval = max(1, floor(n_snapshots / 10));
for snap_idx = 1:n_snapshots
    if mod(snap_idx, progress_interval) == 0
        fprintf('  Processing metrics: %d/%d (%.0f%%)...\n', snap_idx, n_snapshots, snap_idx/n_snapshots*100);
    end
    
    % Serving BS channel (BS 1)
    coeff = ch.coeff(:,:,:,snap_idx);
    delays = ch.delay(:,:,:,snap_idx);
    
    h_paths = squeeze(coeff);
    tau_paths = squeeze(delays);
    H_freq = (h_paths(:).' * exp(-1j * 2 * pi * tau_paths(:) * fvec(:).')).';
    
    H_sc = reshape(H_freq, [1, 1, config.n_subcarriers]);
    
    % Pass interference if multi-BS is enabled
    if use_interferers
        % Convert interference from Watts to dBm per subcarrier
        I_dBm_sc = 10*log10(interference_W_sc(:, snap_idx) + eps) + 30;
        out = m.compute(H_sc, 'InterfPerSC_dBmVec', I_dBm_sc);
    else
        % Use flat interference from config (original behavior)
        out = m.compute(H_sc);
    end
    
    metrics.RSS_wb(snap_idx) = out.RSS_dBm_wb;
    metrics.SINR_wb(snap_idx) = out.SINR_dB_wb;
    metrics.CQI_wb(snap_idx) = out.CQI_wb;
end

fprintf('  Computed: RSS, SINR, CQI (%.1f seconds)\n\n', toc);

%% STEP 1: Extract Static Distributions (same as before)
fprintf('=== STEP 1: Static Distribution Extraction ===\n');
tic;

static_data = struct();
for pt = 1:config.n_points
    mask = (walk_path == pt);
    samples = sum(mask);
    
    static_data(pt).point = pt;
    static_data(pt).samples = samples;
    static_data(pt).rss_mean = mean(metrics.RSS_wb(mask));
    static_data(pt).rss_std = std(metrics.RSS_wb(mask));
    static_data(pt).sinr_mean = mean(metrics.SINR_wb(mask));
    static_data(pt).sinr_std = std(metrics.SINR_wb(mask));
    static_data(pt).cqi_mean = mean(metrics.CQI_wb(mask));
    static_data(pt).cqi_std = std(metrics.CQI_wb(mask));
end

fprintf('Static distributions extracted for %d points (%.1f seconds)\n\n', config.n_points, toc);

%% STEP 2: Extract Transition Distributions (same as before)
fprintf('=== STEP 2: Transition Distribution Extraction ===\n');
tic;

% Find all possible directed edges
directed_edges = [];
for pt = 1:config.n_points
    neighbors = config.neighbors{pt};
    for n = neighbors
        directed_edges = [directed_edges; pt, n];
    end
end

% Extract delta distributions for each edge
transition_data = struct();
idx = 1;
for i = 1:size(directed_edges, 1)
    u = directed_edges(i, 1);
    v = directed_edges(i, 2);
    
    % Find transitions u → v
    trans_idx = find(walk_path(1:end-1) == u & walk_path(2:end) == v);
    
    if length(trans_idx) > 0
        rss_deltas = metrics.RSS_wb(trans_idx+1) - metrics.RSS_wb(trans_idx);
        sinr_deltas = metrics.SINR_wb(trans_idx+1) - metrics.SINR_wb(trans_idx);
        cqi_deltas = metrics.CQI_wb(trans_idx+1) - metrics.CQI_wb(trans_idx);
        
        transition_data(idx).from = u;
        transition_data(idx).to = v;
        transition_data(idx).samples = length(trans_idx);
        transition_data(idx).rss_mean = mean(rss_deltas);
        transition_data(idx).rss_std = std(rss_deltas);
        transition_data(idx).sinr_mean = mean(sinr_deltas);
        transition_data(idx).sinr_std = std(sinr_deltas);
        transition_data(idx).cqi_mean = mean(cqi_deltas);
        transition_data(idx).cqi_std = std(cqi_deltas);
        idx = idx + 1;
    end
end

fprintf('Transition distributions extracted for %d directed edges (%.1f seconds)\n\n', length(transition_data), toc);

%% STEP 3: CORRECTED CLASSIFICATION - FAIR COMPARISON
fprintf('=== STEP 3: FAIR COMPARISON (Both methods predict location 1-9) ===\n');
total_start = tic;

% Split data into train/test
test_ratio = config_json.classification.test_ratio;
rng(config_json.experiment.random_seed);  % Use seed from config for reproducibility
test_indices = false(n_snapshots, 1);
test_indices(randperm(n_snapshots, round(n_snapshots * test_ratio))) = true;
train_indices = ~test_indices;

% Get test samples (use all test indices like the original)
test_samples = find(test_indices);
n_test = length(test_samples);

fprintf('Train samples: %d, Test samples: %d\n\n', sum(train_indices), n_test);

% Store results for all metrics
results = struct();
metric_names = {'RSS', 'SINR', 'CQI'};
metric_fields = {'RSS_wb', 'SINR_wb', 'CQI_wb'};
metric_data_fields = {'rss', 'sinr', 'cqi'};

for m_idx = 1:length(metric_names)
    metric_name = metric_names{m_idx};
    metric_field = metric_fields{m_idx};
    data_field = metric_data_fields{m_idx};
    
    fprintf('--- %s Classification ---\n', metric_name);
    
    %% METHOD 1: Static Classification (baseline)
    fprintf('Training static model...\n');
    
    % Train static distributions on training set only
    static_train = struct();
    for pt = 1:config.n_points
        mask = (walk_path == pt) & train_indices;
        vals = metrics.(metric_field)(mask);
        static_train(pt).mean = mean(vals);
        static_train(pt).std = std(vals);
        if static_train(pt).std == 0
            static_train(pt).std = 1e-6;  % Prevent division by zero
        end
    end
    
    % Test static classification
    fprintf('Testing static classification (%d samples)...\n', n_test);
    predictions_static = zeros(n_test, 1);
    true_labels = walk_path(test_samples);
    
    progress_interval = max(1, floor(n_test / 10));
    for i = 1:n_test
        if mod(i, progress_interval) == 0
            fprintf('  Static: %d/%d (%.0f%%)\n', i, n_test, i/n_test*100);
        end
        test_val = metrics.(metric_field)(test_samples(i));
        
        % Calculate likelihood P(RSS | location=j) for each point
        likelihoods = zeros(config.n_points, 1);
        for pt = 1:config.n_points
            mu = static_train(pt).mean;
            sigma = static_train(pt).std;
            likelihoods(pt) = normpdf(test_val, mu, sigma);
        end
        
        [~, predictions_static(i)] = max(likelihoods);
    end
    
    acc_static = sum(predictions_static == true_labels) / n_test * 100;
    fprintf('  Static accuracy: %.2f%%\n', acc_static);
    
    %% METHOD 2: Transition-Based Classification (USING TRANSITION DISTRIBUTIONS)
    fprintf('Training transition model...\n');
    
    % Build lookup table for transition distributions (from → to)
    % This maps (from_point, to_point) → index in trans_train array
    trans_lookup = containers.Map('KeyType', 'char', 'ValueType', 'any');
    
    % Train transition delta distributions on training set
    trans_train = struct();
    for i = 1:length(transition_data)
        u = transition_data(i).from;
        v = transition_data(i).to;
        
        % Find training transitions u → v
        trans_idx = find(walk_path(1:end-1) == u & walk_path(2:end) == v);
        train_trans = trans_idx(train_indices(trans_idx));
        
        if length(train_trans) > 10  % Need sufficient samples
            deltas = metrics.(metric_field)(train_trans+1) - metrics.(metric_field)(train_trans);
            
            trans_train(i).from = u;
            trans_train(i).to = v;
            trans_train(i).mean_delta = mean(deltas);
            trans_train(i).std_delta = std(deltas);
            
            % Add to lookup table
            key = sprintf('%d_%d', u, v);
            trans_lookup(key) = i;
        else
            trans_train(i).from = u;
            trans_train(i).to = v;
            trans_train(i).mean_delta = 0;
            trans_train(i).std_delta = inf;  % No data - will get zero probability
            
            key = sprintf('%d_%d', u, v);
            trans_lookup(key) = i;
        end
    end
    
    % Test transition-based classification with different history lengths
    history_lengths = 1:config.max_history_length;  % Number of transitions to look back
    predictions_transition = cell(length(history_lengths), 1);
    acc_transition = zeros(length(history_lengths), 1);
    mae_transition = zeros(length(history_lengths), 1);
    
    for h_idx = 1:length(history_lengths)
        history_len = history_lengths(h_idx);
        fprintf('Testing transition-based classification (history=%d, %d samples)...\n', history_len, n_test);
        predictions_transition{h_idx} = zeros(n_test, 1);
        
        progress_interval = max(1, floor(n_test / 10));
        for i = 1:n_test
            if mod(i, progress_interval) == 0
                fprintf('  Transition (h=%d): %d/%d (%.0f%%)\n', history_len, i, n_test, i/n_test*100);
            end
            t_idx = test_samples(i);
            
            % Need at least history_len previous samples
            if t_idx <= history_len
                % Not enough history - fall back to static only
                metric_current = metrics.(metric_field)(t_idx);
                posterior = zeros(config.n_points, 1);
                for j = 1:config.n_points
                    posterior(j) = normpdf(metric_current, static_train(j).mean, static_train(j).std);
                end
            else
                % Use current measurement and deltas from history
                metric_current = metrics.(metric_field)(t_idx);
                
                % Collect historical deltas
                deltas_observed = zeros(history_len, 1);
                for h = 1:history_len
                    deltas_observed(h) = metrics.(metric_field)(t_idx - h + 1) - metrics.(metric_field)(t_idx - h);
                end
                
                % For each candidate current location j, evaluate all valid paths
                posterior = zeros(config.n_points, 1);
                
                for j = 1:config.n_points
                    % P(metric_current | location=j) - current position likelihood
                    prob_current = normpdf(metric_current, static_train(j).mean, static_train(j).std);
                    
                    % Find the most likely path through history using iterative approach
                    % For simplicity: just multiply probabilities for each delta in sequence
                    max_path_likelihood = 0;
                    
                    if history_len == 1
                        % Single transition: just check immediate neighbors
                        neighbor_list = config.neighbors{j};
                        for prev_point = neighbor_list
                            key = sprintf('%d_%d', prev_point, j);
                            if trans_lookup.isKey(key)
                                idx = trans_lookup(key);
                                mean_delta = trans_train(idx).mean_delta;
                                std_delta = trans_train(idx).std_delta;
                                if isfinite(std_delta) && std_delta > 0
                                    prob_delta = normpdf(deltas_observed(1), mean_delta, std_delta);
                                    if prob_delta > max_path_likelihood
                                        max_path_likelihood = prob_delta;
                                    end
                                end
                            end
                        end
                    else
                        % Multiple transitions: evaluate each delta independently and multiply
                        % This is a simplification - not exploring all paths, but evaluating
                        % transition probabilities for observed deltas
                        neighbor_list = config.neighbors{j};
                        for prev_point = neighbor_list
                            % Check first transition (most recent)
                            key1 = sprintf('%d_%d', prev_point, j);
                            if trans_lookup.isKey(key1)
                                idx1 = trans_lookup(key1);
                                mean_delta1 = trans_train(idx1).mean_delta;
                                std_delta1 = trans_train(idx1).std_delta;
                                if isfinite(std_delta1) && std_delta1 > 0
                                    prob1 = normpdf(deltas_observed(1), mean_delta1, std_delta1);
                                    
                                    % For longer history, check second transition
                                    if history_len >= 2
                                        % Check neighbors of prev_point
                                        neighbors2 = config.neighbors{prev_point};
                                        for prev_point2 = neighbors2
                                            key2 = sprintf('%d_%d', prev_point2, prev_point);
                                            if trans_lookup.isKey(key2)
                                                idx2 = trans_lookup(key2);
                                                mean_delta2 = trans_train(idx2).mean_delta;
                                                std_delta2 = trans_train(idx2).std_delta;
                                                if isfinite(std_delta2) && std_delta2 > 0
                                                    prob2 = normpdf(deltas_observed(2), mean_delta2, std_delta2);
                                                    
                                                    % For 3-step history, check third transition
                                                    if history_len >= 3
                                                        neighbors3 = config.neighbors{prev_point2};
                                                        for prev_point3 = neighbors3
                                                            key3 = sprintf('%d_%d', prev_point3, prev_point2);
                                                            if trans_lookup.isKey(key3)
                                                                idx3 = trans_lookup(key3);
                                                                mean_delta3 = trans_train(idx3).mean_delta;
                                                                std_delta3 = trans_train(idx3).std_delta;
                                                                if isfinite(std_delta3) && std_delta3 > 0
                                                                    prob3 = normpdf(deltas_observed(3), mean_delta3, std_delta3);
                                                                    path_prob = prob1 * prob2 * prob3;
                                                                    if path_prob > max_path_likelihood
                                                                        max_path_likelihood = path_prob;
                                                                    end
                                                                end
                                                            end
                                                        end
                                                    else
                                                        % History length = 2
                                                        path_prob = prob1 * prob2;
                                                        if path_prob > max_path_likelihood
                                                            max_path_likelihood = path_prob;
                                                        end
                                                    end
                                                end
                                            end
                                        end
                                    end
                                end
                            end
                        end
                    end
                    
                    % Joint probability: current location matches AND path through history matches
                    posterior(j) = prob_current * max_path_likelihood;
                end
            end
            
            % Predict location with highest posterior
            [~, predictions_transition{h_idx}(i)] = max(posterior);
        end
        
        acc_transition(h_idx) = sum(predictions_transition{h_idx} == true_labels) / n_test * 100;
        fprintf('  Transition (h=%d) accuracy: %.2f%%\n', history_len, acc_transition(h_idx));
    end
    
    % Compute Mean Absolute Error (in grid points)
    % Calculate geometric distance on the grid for each prediction
    static_errors = zeros(n_test, 1);
    transition_errors = cell(length(history_lengths), 1);
    for h_idx = 1:length(history_lengths)
        transition_errors{h_idx} = zeros(n_test, 1);
    end
    
    for i = 1:n_test
        % Convert point indices to row/col
        true_row = ceil(true_labels(i) / config.grid_size);
        true_col = mod(true_labels(i) - 1, config.grid_size) + 1;
        
        pred_static_row = ceil(predictions_static(i) / config.grid_size);
        pred_static_col = mod(predictions_static(i) - 1, config.grid_size) + 1;
        
        % Manhattan distance on the grid for static
        static_errors(i) = abs(true_row - pred_static_row) + abs(true_col - pred_static_col);
        
        % For each history length
        for h_idx = 1:length(history_lengths)
            pred_trans_row = ceil(predictions_transition{h_idx}(i) / config.grid_size);
            pred_trans_col = mod(predictions_transition{h_idx}(i) - 1, config.grid_size) + 1;
            transition_errors{h_idx}(i) = abs(true_row - pred_trans_row) + abs(true_col - pred_trans_col);
        end
    end
    
    mae_static = mean(static_errors);
    for h_idx = 1:length(history_lengths)
        mae_transition(h_idx) = mean(transition_errors{h_idx});
    end
    
    fprintf('  Static MAE: %.3f grid points\n', mae_static);
    for h_idx = 1:length(history_lengths)
        fprintf('  Transition (h=%d) MAE: %.3f grid points\n', history_lengths(h_idx), mae_transition(h_idx));
    end
    
    % Compute confusion matrices
    cm_static = zeros(config.n_points, config.n_points);
    cm_transition = cell(length(history_lengths), 1);
    for h_idx = 1:length(history_lengths)
        cm_transition{h_idx} = zeros(config.n_points, config.n_points);
    end
    
    for i = 1:n_test
        cm_static(true_labels(i), predictions_static(i)) = ...
            cm_static(true_labels(i), predictions_static(i)) + 1;
        for h_idx = 1:length(history_lengths)
            cm_transition{h_idx}(true_labels(i), predictions_transition{h_idx}(i)) = ...
                cm_transition{h_idx}(true_labels(i), predictions_transition{h_idx}(i)) + 1;
        end
    end
    
    % Store results for all history lengths
    results.(data_field).static_acc = acc_static;
    results.(data_field).transition_acc = acc_transition;  % Array of all history lengths
    results.(data_field).history_lengths = history_lengths;
    results.(data_field).mae_static = mae_static;
    results.(data_field).mae_transition = mae_transition;  % Array of all history lengths
    results.(data_field).cm_static = cm_static;
    results.(data_field).cm_transition = cm_transition;  % Cell array of all history lengths
    results.(data_field).predictions_static = predictions_static;
    results.(data_field).predictions_transition = predictions_transition;  % Cell array of all history lengths
    
    % Compute improvements for each history length
    for h_idx = 1:length(history_lengths)
        improvement_acc = acc_transition(h_idx) - acc_static;
        if mae_static > 0
            improvement_mae = (mae_static - mae_transition(h_idx)) / mae_static * 100;
        else
            improvement_mae = 0;
        end
        fprintf('  History=%d: Accuracy improvement %+.2f%%, MAE improvement %+.2f%%\n', ...
            history_lengths(h_idx), improvement_acc, improvement_mae);
    end
    fprintf('  Time for %s: %.1f seconds\n\n', metric_name, toc);
end

fprintf('Total classification time: %.1f seconds\n\n', toc(total_start));

%% STEP 4: Analysis and Visualization
fprintf('=== STEP 4: Results Summary ===\n\n');

fprintf('Fair Comparison Results (Both methods predict location 1-%d):\n', config.n_points);
fprintf('\n=== ACCURACY ===\n');
fprintf('%-10s | %-12s | %-15s | %-15s | %-15s | %-12s\n', 'Metric', 'Static', 'Trans(h=1)', 'Trans(h=2)', 'Trans(h=3)', 'Best Improv');
fprintf('%s\n', repmat('-', 1, 95));
for metric_idx = 1:length(metric_fields)
    metric_name = strrep(metric_fields{metric_idx}, '_wb', '');
    metric_name = upper(metric_name);
    data_field = lower(metric_fields{metric_idx}(1:end-3));  % Remove '_wb'
    fprintf('%-10s | %10.2f%% |', metric_name, results.(data_field).static_acc);
    for h_idx = 1:length(history_lengths)
        fprintf(' %13.2f%% |', results.(data_field).transition_acc(h_idx));
    end
    best_improvement = max(results.(data_field).transition_acc - results.(data_field).static_acc);
    fprintf(' %+10.2f%%\n', best_improvement);
end

fprintf('\n=== MEAN ABSOLUTE ERROR (grid points) ===\n');
fprintf('%-10s | %-12s | %-15s | %-15s | %-15s | %-15s\n', 'Metric', 'Static', 'Trans(h=1)', 'Trans(h=2)', 'Trans(h=3)', 'Best Improv(%)');
fprintf('%s\n', repmat('-', 1, 100));
for metric_idx = 1:length(metric_fields)
    metric_name = strrep(metric_fields{metric_idx}, '_wb', '');
    metric_name = upper(metric_name);
    data_field = lower(metric_fields{metric_idx}(1:end-3));
    fprintf('%-10s | %10.3f |', metric_name, results.(data_field).mae_static);
    for h_idx = 1:length(history_lengths)
        fprintf(' %13.3f |', results.(data_field).mae_transition(h_idx));
    end
    if results.(data_field).mae_static > 0
        mae_improvements = (results.(data_field).mae_static - results.(data_field).mae_transition) / results.(data_field).mae_static * 100;
        best_mae_improvement = max(mae_improvements);
    else
        best_mae_improvement = 0;
    end
    fprintf(' %+13.2f%%\n', best_mae_improvement);
end
fprintf('\n');

% Determine winner (using h=1 for primary comparison)
if results.rss.transition_acc(1) - results.rss.static_acc > 1
    fprintf('**WINNER: Transition-based approach** (Delta helps!)\n');
    fprintf('Interpretation: Movement history provides useful geometric information.\n\n');
elseif results.rss.transition_acc(1) - results.rss.static_acc < -1
    fprintf('**WINNER: Static approach** (Delta hurts!)\n');
    fprintf('Interpretation: Delta variance amplification outweighs benefits.\n\n');
else
    fprintf('**RESULT: Tie** (Delta is neutral)\n');
    fprintf('Interpretation: Delta neither helps nor hurts significantly.\n\n');
end

% Check for overfitting (performance degrades with longer history)
fprintf('=== HISTORY LENGTH ANALYSIS (RSS) ===\n');
fprintf('Checking for overfitting as history length increases:\n');
for h_idx = 1:length(history_lengths)
    fprintf('  h=%d: Accuracy=%.2f%%, MAE=%.3f\n', history_lengths(h_idx), ...
        results.rss.transition_acc(h_idx), results.rss.mae_transition(h_idx));
end
if results.rss.transition_acc(3) < results.rss.transition_acc(1)
    fprintf('⚠️  OVERFITTING DETECTED: Performance degrades with longer history\n');
elseif results.rss.transition_acc(3) > results.rss.transition_acc(2) && ...
       results.rss.transition_acc(2) > results.rss.transition_acc(1)
    fprintf('✓ IMPROVEMENT: Longer history consistently helps\n');
else
    fprintf('➡️  MIXED: No clear trend with history length\n');
end
fprintf('\n');

%% Save results
fprintf('Saving results...\n');
grid_subdir = sprintf('grid_%dx%d', config.grid_size, config.grid_size);
base_dir = fullfile(project_root, 'results', 'grid_localization', grid_subdir);
if ~exist(base_dir, 'dir'), mkdir(base_dir); end
% Extract LOS/NLOS from scenario name
if contains(config.scenario, 'LOS') && ~contains(config.scenario, 'NLOS')
    scenario_type = 'LOS';
elseif contains(config.scenario, 'NLOS')
    scenario_type = 'NLOS';
else
    scenario_type = 'other';
end

output_dir = fullfile(base_dir, sprintf('exp13e_%s_%s', datestr(now, 'yyyy-mm-dd_HH-MM-SS'), scenario_type));
if ~exist(output_dir, 'dir'), mkdir(output_dir); end

save(fullfile(output_dir, 'corrected_comparison_results.mat'), ...
     'config', 'walk_path', 'metrics', 'static_data', 'transition_data', ...
     'results', 'static_train', 'trans_train');

% Copy configuration JSON to results for reproducibility
copyfile(config_file, fullfile(output_dir, 'experiment_config.json'));
fprintf('Configuration copied to: %s\n', fullfile(output_dir, 'experiment_config.json'));

% Generate report
fprintf('Generating report...\n');
generate_corrected_report(output_dir, config, static_data, transition_data, results);

% Generate plots with Python
if config_json.output.generate_plots
    fprintf('\nGenerating plots with Python...\n');
    plot_script = fullfile(script_dir, 'plot_results.py');
    
    if exist(plot_script, 'file')
        % Call Python script with UTF-8 encoding
        python_cmd = sprintf('python "%s" "%s"', plot_script, output_dir);
        [status, cmdout] = system(python_cmd);
        
        if status == 0
            fprintf('%s\n', cmdout);
            fprintf('[SUCCESS] Plots generated successfully!\n');
        else
            warning('Python plotting failed. Error:\n%s', cmdout);
            fprintf('You can manually generate plots later with:\n');
            fprintf('  python plot_results.py "%s"\n', output_dir);
        end
    else
        fprintf('Note: plot_results.py not found. Skipping plots.\n');
    end
end

fprintf('\n========================================\n');
fprintf('Experiment complete!\n');
fprintf('Results saved to:\n  %s\n', output_dir);
fprintf('========================================\n');
