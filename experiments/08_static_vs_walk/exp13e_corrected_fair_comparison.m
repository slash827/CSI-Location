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

%% Configuration
config = struct();
config.grid_size = 3;
config.spacing = 2.0;           % 2 meters
config.ue_height = 1.5;
config.grid_offset = [10, 0];
config.position_jitter = 0.1;
config.n_steps = 5000;
config.ue_speed = 1.5;
config.step_duration = config.spacing / config.ue_speed;
config.center_frequency = 3e9;
config.bandwidth = 100e6;
config.n_subcarriers = 256;
% CHANGE THIS for LOS vs NLOS comparison:
config.scenario = '3GPP_38.901_UMa_NLOS';  % Options: '3GPP_38.901_UMa_LOS' or '3GPP_38.901_UMa_NLOS'
config.bs_position = [0; 0; 25];

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
rng(42);  % Fixed seed for reproducibility
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
l.no_tx = 1;
l.tx_position = config.bs_position;
l.tx_array = qd_arrayant('omni');
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
ch = l.get_channels();
fprintf('  Channel generation complete (%.1f seconds)\n', toc);

% Compute CSI metrics
fprintf('Computing CSI metrics...\n');
tic;

% Initialize CSIMetrics object
fvec = linspace(-config.bandwidth/2, config.bandwidth/2, config.n_subcarriers);
m = CSIMetrics('SubcarrierSpacing', config.bandwidth/config.n_subcarriers, ...
               'TxPowerPerSC_dBm', 0, 'NoiseFigure_dB', 7);

% Initialize metric storage
metrics = struct();
metrics.RSS_wb = zeros(n_snapshots, 1);
metrics.SINR_wb = zeros(n_snapshots, 1);
metrics.CQI_wb = zeros(n_snapshots, 1);

% Compute metrics for each snapshot
progress_interval = max(1, floor(n_snapshots / 10));
for snap_idx = 1:n_snapshots
    if mod(snap_idx, progress_interval) == 0
        fprintf('  Processing metrics: %d/%d (%.0f%%)...\n', snap_idx, n_snapshots, snap_idx/n_snapshots*100);
    end
    
    coeff = ch.coeff(:,:,:,snap_idx);
    delays = ch.delay(:,:,:,snap_idx);
    
    h_paths = squeeze(coeff);
    tau_paths = squeeze(delays);
    H_freq = (h_paths(:).' * exp(-1j * 2 * pi * tau_paths(:) * fvec(:).')).';
    
    H_sc = reshape(H_freq, [1, 1, config.n_subcarriers]);
    out = m.compute(H_sc);
    
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

% Split data into train/test (80/20)
test_ratio = 0.2;
rng(42);  % Reset seed for reproducibility
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
    
    %% METHOD 2: Transition-Based Classification (NEW IMPLEMENTATION)
    fprintf('Training transition model...\n');
    
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
        else
            trans_train(i).from = u;
            trans_train(i).to = v;
            trans_train(i).mean_delta = 0;
            trans_train(i).std_delta = inf;  % No data
        end
    end
    
    % Test transition-based classification
    fprintf('Testing transition-based classification (%d samples)...\n', n_test);
    predictions_transition = zeros(n_test, 1);
    
    progress_interval = max(1, floor(n_test / 10));
    for i = 1:n_test
        if mod(i, progress_interval) == 0
            fprintf('  Transition: %d/%d (%.0f%%)\n', i, n_test, i/n_test*100);
        end
        t_idx = test_samples(i);
        
        % Can only use previous RSS if t_idx > 1
        if t_idx == 1
            % First sample - no previous, fall back to static only
            RSS_current = metrics.(metric_field)(t_idx);
            posterior = zeros(config.n_points, 1);
            for j = 1:config.n_points
                posterior(j) = normpdf(RSS_current, static_train(j).mean, static_train(j).std);
            end
        else
            % Use both RSS_current and RSS_previous
            RSS_current = metrics.(metric_field)(t_idx);
            RSS_previous = metrics.(metric_field)(t_idx - 1);
            
            % For each candidate location j, find the best explanation considering movement constraints
            % We consider: P(j | RSS_curr, RSS_prev) by evaluating all valid (prev_loc, curr_loc=j) pairs
            
            posterior = zeros(config.n_points, 1);
            
            for j = 1:config.n_points
                % P(RSS_current | location=j) - current position likelihood
                prob_rss_current = normpdf(RSS_current, static_train(j).mean, static_train(j).std);
                
                % Find the most likely previous location among neighbors
                % This enforces the constraint: can only move between adjacent grid points
                neighbor_list = config.neighbors{j};
                
                if ~isempty(neighbor_list)
                    max_prev_likelihood = 0;
                    for prev_point = neighbor_list
                        % Likelihood that we were at prev_point given RSS_previous
                        prob_at_prev = normpdf(RSS_previous, static_train(prev_point).mean, static_train(prev_point).std);
                        
                        % Take the maximum (most likely previous location)
                        if prob_at_prev > max_prev_likelihood
                            max_prev_likelihood = prob_at_prev;
                        end
                    end
                    
                    % Joint probability: current location matches RSS_current AND 
                    % previous location (neighbor) matches RSS_previous
                    posterior(j) = prob_rss_current * max_prev_likelihood;
                else
                    % No neighbors (shouldn't happen in a grid), use only current RSS
                    posterior(j) = prob_rss_current;
                end
            end
        end
        
        % Predict location with highest posterior
        [~, predictions_transition(i)] = max(posterior);
    end
    
    acc_transition = sum(predictions_transition == true_labels) / n_test * 100;
    fprintf('  Transition accuracy: %.2f%%\n', acc_transition);
    
    % Compute confusion matrices
    cm_static = zeros(config.n_points, config.n_points);
    cm_transition = zeros(config.n_points, config.n_points);
    
    for i = 1:n_test
        cm_static(true_labels(i), predictions_static(i)) = ...
            cm_static(true_labels(i), predictions_static(i)) + 1;
        cm_transition(true_labels(i), predictions_transition(i)) = ...
            cm_transition(true_labels(i), predictions_transition(i)) + 1;
    end
    
    % Store results
    results.(data_field).static_acc = acc_static;
    results.(data_field).transition_acc = acc_transition;
    results.(data_field).improvement = acc_transition - acc_static;
    results.(data_field).cm_static = cm_static;
    results.(data_field).cm_transition = cm_transition;
    results.(data_field).predictions_static = predictions_static;
    results.(data_field).predictions_transition = predictions_transition;
    
    fprintf('  Improvement: %+.2f%%\n', results.(data_field).improvement);
    fprintf('  Time for %s: %.1f seconds\n\n', metric_name, toc);
end

fprintf('Total classification time: %.1f seconds\n\n', toc(total_start));

%% STEP 4: Analysis and Visualization
fprintf('=== STEP 4: Results Summary ===\n\n');

fprintf('Fair Comparison Results (Both methods predict location 1-9):\n');
fprintf('%-10s | %-12s | %-15s | %-12s\n', 'Metric', 'Static', 'Transition', 'Improvement');
fprintf('%s\n', repmat('-', 1, 60));
fprintf('%-10s | %10.2f%% | %13.2f%% | %+10.2f%%\n', 'RSS', results.rss.static_acc, results.rss.transition_acc, results.rss.improvement);
fprintf('%-10s | %10.2f%% | %13.2f%% | %+10.2f%%\n', 'SINR', results.sinr.static_acc, results.sinr.transition_acc, results.sinr.improvement);
fprintf('%-10s | %10.2f%% | %13.2f%% | %+10.2f%%\n', 'CQI', results.cqi.static_acc, results.cqi.transition_acc, results.cqi.improvement);
fprintf('\n');

% Determine winner
if results.rss.improvement > 1
    fprintf('**WINNER: Transition-based approach** (Delta helps!)\n');
    fprintf('Interpretation: Delta provides useful geometric information.\n\n');
elseif results.rss.improvement < -1
    fprintf('**WINNER: Static approach** (Delta hurts!)\n');
    fprintf('Interpretation: Delta variance amplification outweighs benefits.\n\n');
else
    fprintf('**RESULT: Tie** (Delta is neutral)\n');
    fprintf('Interpretation: Delta neither helps nor hurts significantly.\n\n');
end

%% Save results
fprintf('Saving results...\n');
output_dir = fullfile(project_root, 'results', sprintf('exp13e_corrected_%s', datestr(now, 'yyyy-mm-dd_HH-MM-SS')));
if ~exist(output_dir, 'dir'), mkdir(output_dir); end

save(fullfile(output_dir, 'corrected_comparison_results.mat'), ...
     'config', 'walk_path', 'metrics', 'static_data', 'transition_data', ...
     'results', 'static_train', 'trans_train');

fprintf('Results saved to: %s\n\n', output_dir);

% Generate report
fprintf('Generating report...\n');
generate_corrected_report(output_dir, config, static_data, transition_data, results);

fprintf('\n========================================\n');
fprintf('Experiment complete!\n');
fprintf('========================================\n');
