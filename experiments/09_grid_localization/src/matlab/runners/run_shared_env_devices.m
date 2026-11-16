%% Macro cell, ONE shared environment, heterogeneous device classes (2026-11)
%
% WHY THIS FILE EXISTS
% --------------------
% Dudi (2026-11-01) asked whether models fed the differences between consecutive
% reports generalize to unseen devices better than models fed the absolute values.
% That test needs two things the existing data lack:
%   1. One environment shared by all users. In run_multi_user_300_25x25_mixed.m every
%      user segment gets its own qd_layout with whatever RNG state it happens to
%      have, so each user sees its own shadowing map; a model can then fail on a new
%      device because of the environment, not the device.
%   2. Devices that really differ. In the existing runners extra antenna elements are
%      co-located (qd_arrayant('omni') with no_elements = n), so the RSS of a 1- and a
%      4-element device at the same place is identical (checked 2026-11-07: correlation
%      1.00, same mean); only a constant gain offset differed.
%
% What this runner does
%   - Same macro geometry, Voronoi LOS/NLOS map, trajectories and interferers as
%     run_multi_user_300_25x25_mixed.m (ne_bs_voronoi_25x25_config.jsonc).
%   - Shared environment: before each segment's get_channels the RNG is reset to
%     SHARED_SEED + Voronoi cell index, so every user crossing a cell sees the same
%     large- and small-scale map of that cell (checked: identical RSS for the same path
%     under the same seed, whatever the number of receivers or elements).
%   - Four device classes (after Alon's heterogeneous-UE classes, 2026-11-06), 25 % each,
%     with per-device parameters drawn around the class nominal:
%         class        elements    height (m)  gain (dB)     NF (dB)     speed (m/s)
%         midtier      4 (2x2)     1.0-1.8     -2 +/- 1      8 +/- 0.75  0.5-2.0
%         flagship     16 (4x4)    1.0-1.8      0 +/- 1      7 +/- 0.75  0.5-2.0
%         iot          1           0.3-1.3     -6 +/- 1.5   12 +/- 1.5   0.2-1.5
%         vehicle      16 (4x4)    1.6-2.0     +3 +/- 1      7 +/- 0.75  5.0-20.0
%     Elements are spaced half a wavelength apart (planar array), so devices with more
%     elements average more small-scale fading: a difference that is not a constant offset.
%   - Saved per step: the raw received signal and interference power (dBm, before the
%     device gain), and rss / sinr with the device gain and noise figure applied
%     (noise = -174 dBm/Hz + 10 log10(bandwidth) + NF), so Python can re-derive or
%     perturb either.
%   - SHARED_USERS selects a subset of user ids and SHARED_OUT_TAG fixes the folder name,
%     so several MATLAB processes can run one manifest in parallel into one folder
%     (no Parallel Computing Toolbox on this machine).
%
% Output: results/grid_localization/grid_25x25/sim_data_shared_devices_<timestamp>/
%         mat_files/user<k>_ne_bs_25x25.mat  (same layout as the 300-user mixed run,
%         plus p_sig_dbm, p_int_dbm, device_class, noise_figure_db)
%
% Optional overrides (set before running): SHARED_N_USERS (default 300),
% SHARED_N_SUBCARRIERS (default 64), SHARED_MAX_STEPS (default 0 = no cap; for tests),
% SHARED_USERS (default all), SHARED_OUT_TAG (default the timestamp), SHARED_SEED (default
% 20261107), SHARED_UNIFORM_SCENARIO (default '' = the mixed Voronoi map; e.g.
% '3GPP_38.901_UMi_NLOS' gives every cell that scenario, keeping the per-cell segments and
% seeds, for a uniform-NLOS shared environment). Users whose .mat file already exists are skipped, so an interrupted run resumes
% by rerunning the same command with the same SHARED_OUT_TAG.
%
% Requires QuaDRiGa 2.8.1 (found by ensure_quadriga).

clearvars -except SHARED_N_USERS SHARED_N_SUBCARRIERS SHARED_MAX_STEPS SHARED_USERS SHARED_OUT_TAG SHARED_SEED SHARED_UNIFORM_SCENARIO; clc;
% no "close all": it starts the graphics server, which fails when MATLAB runs detached in the background

script_dir      = fileparts(mfilename('fullpath'));
src_matlab_dir  = fileparts(script_dir);
experiment_root = fileparts(fileparts(src_matlab_dir));
workspace_root  = fileparts(fileparts(experiment_root));
addpath(fullfile(src_matlab_dir, 'core'));
addpath(fullfile(src_matlab_dir, 'lib'));
ensure_quadriga();

if ~exist('SHARED_N_USERS', 'var'),       SHARED_N_USERS = 300;      end
if ~exist('SHARED_N_SUBCARRIERS', 'var'), SHARED_N_SUBCARRIERS = 64; end
if ~exist('SHARED_MAX_STEPS', 'var'),     SHARED_MAX_STEPS = 0;      end
if ~exist('SHARED_USERS', 'var'),         SHARED_USERS = [];         end   % subset of user ids
if ~exist('SHARED_OUT_TAG', 'var'),       SHARED_OUT_TAG = '';       end   % fixed folder name
if ~exist('SHARED_SEED', 'var'),          SHARED_SEED = 20261107;    end   % environment seed (second environment: another value)
if ~exist('SHARED_UNIFORM_SCENARIO', 'var'), SHARED_UNIFORM_SCENARIO = ''; end   % '' = mixed Voronoi map

timestamp  = datestr(now, 'yyyy-mm-dd_HH-MM-SS');
if ~isempty(SHARED_OUT_TAG), run_tag = SHARED_OUT_TAG; else, run_tag = timestamp; end
output_dir = fullfile(workspace_root, 'results', 'grid_localization', 'grid_25x25', ...
                      sprintf('sim_data_shared_devices_%s', run_tag));
mat_dir = fullfile(output_dir, 'mat_files');
log_dir = fullfile(output_dir, 'logs');
if ~isfolder(mat_dir), mkdir(mat_dir); end
if ~isfolder(log_dir), mkdir(log_dir); end
diary(fullfile(log_dir, sprintf('main_%s_%d.log', timestamp, feature('getpid')))); diary on;
total_start = tic;

config_name = 'ne_bs_voronoi_25x25_config.jsonc';
config_json = read_jsonc(fullfile(experiment_root, 'configs', config_name));
center_freq = config_json.channel.center_frequency;
bandwidth   = config_json.channel.bandwidth;
lambda      = 299792458 / center_freq;

vcells = config_json.channel.mixed_scenario.voronoi_cells;
n_cells = length(vcells);
voronoi_centers = zeros(n_cells, 2); voronoi_scenarios = cell(n_cells, 1); voronoi_names = cell(n_cells, 1);
for i = 1:n_cells
    voronoi_centers(i, :) = vcells(i).center;
    voronoi_scenarios{i}  = vcells(i).scenario;
    voronoi_names{i}      = vcells(i).name;
end
is_mixed = isempty(SHARED_UNIFORM_SCENARIO);
if ~is_mixed
    % same cells, segments and seeds; one propagation scenario everywhere
    voronoi_scenarios(:) = {SHARED_UNIFORM_SCENARIO};
end
MIN_SEG_LEN = 4;

fprintf('=== Shared-environment macro cell, heterogeneous devices ===\n');
fprintf('Start %s | users %d | subcarriers %d | shared seed %d\n', datestr(now), ...
        SHARED_N_USERS, SHARED_N_SUBCARRIERS, SHARED_SEED);
fprintf('Output: %s\n\n', output_dir);

%% Device classes: name, elements, [h_min h_max], gain nominal, gain sigma, NF, NF sigma, [v_min v_max]
classes = { 'midtier',   4, [1.0 1.8], -2, 1.0,  8, 0.75, [0.5  2.0];
            'flagship', 16, [1.0 1.8],  0, 1.0,  7, 0.75, [0.5  2.0];
            'iot',       1, [0.3 1.3], -6, 1.5, 12, 1.5,  [0.2  1.5];
            'vehicle',  16, [1.6 2.0],  3, 1.0,  7, 0.75, [5.0 20.0] };
n_users = SHARED_N_USERS;
rng(42);
class_id = repmat(1:4, 1, ceil(n_users / 4)); class_id = class_id(randperm(numel(class_id), n_users));
% Columns: [n_ant, gain_db, height_m, walk_seed, speed_ms, n_steps, pat_id, class_id, nf_db]
user_manifest = zeros(n_users, 9);
for u = 1:n_users
    c = classes(class_id(u), :);
    h = c{3}(1) + rand() * diff(c{3});
    gain = c{4} + c{5} * max(-2, min(2, randn()));
    nf   = c{6} + c{7} * max(-2, min(2, randn()));
    speed = c{8}(1) + rand() * diff(c{8});
    p_roll = rand();
    if p_roll <= 0.35, pat_id = 1; elseif p_roll <= 0.70, pat_id = 2; elseif p_roll <= 0.90, pat_id = 3; else, pat_id = 4; end
    n_steps = randi([500, 750]);
    if SHARED_MAX_STEPS > 0, n_steps = min(n_steps, SHARED_MAX_STEPS); end
    user_manifest(u, :) = [c{2}, gain, h, 1000 + u, speed, n_steps, pat_id, class_id(u), nf];
end
for k = 1:4
    fprintf('  class %-9s %3d users\n', classes{k, 1}, sum(class_id == k));
end

geo = struct('bs_pos', [116; 116; 10], 'ibs_pos', [-60, 53, 10; 53, -60, 10], ...
             'grid_sz', config_json.grid.size(1), 'spacing', config_json.grid.spacing, ...
             'grid_offset', config_json.grid.grid_offset, 'centers', voronoi_centers, ...
             'scenarios', {voronoi_scenarios}, 'names', {voronoi_names}, ...
             'fc', center_freq, 'bw', bandwidth, 'n_sc', SHARED_N_SUBCARRIERS, ...
             'lambda', lambda, 'seed', SHARED_SEED, 'min_seg', MIN_SEG_LEN);
class_names = classes(:, 1);

if isempty(SHARED_USERS), SHARED_USERS = 1:n_users; end
n_done = zeros(n_users, 1);
for u = SHARED_USERS(:)'
    if isfile(fullfile(mat_dir, sprintf('user%d_ne_bs_25x25.mat', u)))
        fprintf('user %3d already saved, skipped (resume)\n', u);   % rerun the same command to resume
        n_done(u) = 1;
        continue;
    end
    t_u = tic;
    n_done(u) = simulate_user(u, user_manifest(u, :), class_names, geo, mat_dir, user_manifest);
    fprintf('    (%.0f s)\n', toc(t_u));
end
fprintf('\nUsers saved: %d / %d, snapshots %d\n', sum(n_done > 0), numel(SHARED_USERS), sum(n_done));

experiment_info = struct('config_name', config_name, 'n_users', n_users, 'user_manifest', user_manifest, ...
    'class_names', {class_names}, 'output_dir', output_dir, 'timestamp', timestamp, ...
    'bs_position', geo.bs_pos, 'center_freq_hz', center_freq, 'bandwidth_hz', bandwidth, ...
    'n_subcarriers', SHARED_N_SUBCARRIERS, 'shared_seed', SHARED_SEED, 'mixed_scenario', is_mixed, ...
    'voronoi_centers', voronoi_centers, 'total_time_s', toc(total_start));
experiment_info.voronoi_scenarios = voronoi_scenarios;
experiment_info.voronoi_names = voronoi_names;
save(fullfile(output_dir, 'experiment_info.mat'), 'experiment_info');

sim_config = struct('network_type', '5G NR Sub-6 GHz', 'center_frequency_ghz', center_freq / 1e9, ...
    'bandwidth_mhz', bandwidth / 1e6, 'n_subcarriers', SHARED_N_SUBCARRIERS, ...
    'quadriga_scenario', 'mixed_voronoi', 'mixed_scenario', is_mixed, 'uniform_scenario', SHARED_UNIFORM_SCENARIO, 'voronoi_cells', vcells, ...
    'min_segment_length', MIN_SEG_LEN, 'channel_generation', 'per_segment_shared_seed', ...
    'shared_seed', SHARED_SEED, 'serving_bs_position_m', geo.bs_pos', ...
    'sw_interferer_position_m', [-60, 53, 10], 's_interferer_position_m', [53, -60, 10], ...
    'n_users', n_users, 'device_classes', {class_names}, 'mat_files_directory', 'mat_files', ...
    'timestamp', timestamp);
fid = fopen(fullfile(output_dir, 'simulation_config.json'), 'w');
fprintf(fid, '%s', jsonencode(sim_config)); fclose(fid);
fprintf('Total time %.1f minutes\nOutput: %s\n', toc(total_start) / 60, output_dir);
diary off;


%% ── helpers ──────────────────────────────────────────────────────────────────
function n_valid = simulate_user(uid, prof, class_names, geo, mat_dir, user_manifest)
    n_ant = prof(1); gain_db = prof(2); h_m = prof(3); seed = prof(4);
    speed = prof(5); n_steps = prof(6); pat_id = prof(7); cls = prof(8); nf_db = prof(9);
    pattern_names = {'billiards', 'momentum_walk', 'waypoint_tour', 'straight_transit'};
    [walk_indices, ~] = generate_diverse_trajectories(geo.grid_sz, n_steps, pattern_names{pat_id}, ...
                                                      speed, geo.spacing, seed);
    w_idx = walk_indices(1:n_steps);
    rows = ceil(w_idx / geo.grid_sz); cols = mod(w_idx - 1, geo.grid_sz) + 1;
    x_pts = (cols - 1) * geo.spacing + geo.grid_offset(1);
    y_pts = (rows - 1) * geo.spacing + geo.grid_offset(2);
    positions = [x_pts, y_pts, ones(n_steps, 1) * h_m];

    d2 = (x_pts - geo.centers(:, 1)').^2 + (y_pts - geo.centers(:, 2)').^2;
    [~, cell_idx_per_step] = min(d2, [], 2);
    [seg_start, seg_cell] = build_scenario_segments(cell_idx_per_step, geo.min_seg);
    seg_end = [seg_start(2:end) - 1, n_steps];

    rx = make_rx_array(n_ant, geo.lambda);
    p_sig_dbm = zeros(n_steps, 1); p_int_dbm = zeros(n_steps, 1);
    aoa_az = zeros(n_steps, 1); aoa_el = zeros(n_steps, 1);
    n_valid = 0;
    for k = 1:numel(seg_start)
        lo = seg_start(k); hi = seg_end(k); seg_len = hi - lo + 1;
        l = qd_layout;
        l.simpar.center_frequency = geo.fc;
        l.simpar.show_progress_bars = 0;
        l.no_tx = 3;
        l.tx_position(:, 1) = geo.bs_pos;
        l.tx_array(1) = qd_arrayant('omni');
        for i = 1:2
            l.tx_position(:, i + 1) = geo.ibs_pos(i, :)';
            l.tx_array(i + 1) = qd_arrayant('omni');
        end
        l.no_rx = 1;
        l.rx_array(1) = rx;
        trk = qd_track('linear', 0, 0);
        trk.name = sprintf('UE%dS%d', uid, k);
        trk.positions = positions(lo:hi, :)';
        trk.scenario = {geo.scenarios{seg_cell(k)}};
        l.rx_track(1) = trk;
        rng(geo.seed + seg_cell(k));             % one map per Voronoi cell, shared by all users
        [~] = evalc('ch = l.get_channels();');
        if iscell(ch), c_u = ch{1, 1}; c_1 = ch{1, 2}; c_2 = ch{1, 3};
        else,          c_u = ch(1, 1); c_1 = ch(1, 2); c_2 = ch(1, 3); end
        n_avail = min([c_u.no_snap, c_1.no_snap, c_2.no_snap]);
        truncated = n_avail < seg_len;
        seg_len = min(seg_len, n_avail);
        for t = 1:seg_len
            g = lo + t - 1;
            p_sig = mean(abs(reshape(c_u.fr(geo.bw, geo.n_sc, t), [], 1)).^2);
            p_int = mean(abs(reshape(c_1.fr(geo.bw, geo.n_sc, t), [], 1)).^2) ...
                  + mean(abs(reshape(c_2.fr(geo.bw, geo.n_sc, t), [], 1)).^2);
            p_sig_dbm(g) = 10 * log10(max(p_sig, 1e-18) / 1e-3);
            p_int_dbm(g) = 10 * log10(max(p_int, 1e-18) / 1e-3);
            dx = geo.bs_pos(1) - x_pts(g); dy = geo.bs_pos(2) - y_pts(g); dz = geo.bs_pos(3) - h_m;
            if n_ant > 1
                aoa_az(g) = atan2d(dx, dy);
                aoa_el(g) = atan2d(dz, max(sqrt(dx^2 + dy^2), 0.1));
            end
        end
        n_valid = lo + seg_len - 1;
        if truncated, break; end
    end
    n = n_valid;
    noise_dbm = -174 + 10 * log10(geo.bw) + nf_db;
    p_sig_dbm = p_sig_dbm(1:n); p_int_dbm = p_int_dbm(1:n);
    rss  = p_sig_dbm + gain_db;
    sinr = 10 * log10(10.^(rss / 10) ./ (10.^((p_int_dbm + gain_db) / 10) + 10.^(noise_dbm / 10)));
    aoa_az = aoa_az(1:n); aoa_el = aoa_el(1:n);
    step_index = (1:n)'; grid_point_id = w_idx(1:n); user_id_val = uid; speed_ms = speed;
    x_pos = x_pts(1:n); y_pos = y_pts(1:n);
    delta_t = (geo.spacing / speed) * ones(n, 1);
    timestamp_sec = cumsum(delta_t) - delta_t(1);
    voronoi_cell_id = cell_idx_per_step(1:n);
    voronoi_scenario = geo.scenarios(voronoi_cell_id);
    voronoi_zone_name = geo.names(voronoi_cell_id);
    is_los = ~cellfun(@isempty, strfind(voronoi_scenario, '_LOS'));  %#ok<STRCL1>
    device_class = class_names{cls};
    noise_figure_db = nf_db;
    device_profile = struct('n_antennas', n_ant, 'antenna_gain_db', gain_db, 'ue_height', h_m, ...
                            'device_class', device_class, 'noise_figure_db', nf_db);
    save(fullfile(mat_dir, sprintf('user%d_ne_bs_25x25.mat', uid)), 'rss', 'sinr', 'p_sig_dbm', ...
         'p_int_dbm', 'aoa_az', 'aoa_el', 'delta_t', 'timestamp_sec', 'step_index', 'grid_point_id', ...
         'user_id_val', 'speed_ms', 'x_pos', 'y_pos', 'voronoi_cell_id', 'voronoi_scenario', ...
         'voronoi_zone_name', 'is_los', 'device_profile', 'device_class', 'noise_figure_db', 'user_manifest');
    fprintf('user %3d %-9s %2d el: %d/%d snapshots\n', uid, device_class, n_ant, n, n_steps);
end

function a = make_rx_array(n_ant, lambda)
% Omni elements on a half-wavelength planar grid (1, 2x2 or 4x4), so that elements see
% different small-scale fading (co-located elements would all see the same channel).
    a = qd_arrayant('omni');
    if n_ant <= 1, return; end
    side = round(sqrt(n_ant));
    a.no_elements = n_ant;
    [iy, iz] = meshgrid(0:side - 1, 0:side - 1);
    a.element_position = [zeros(1, n_ant); (iy(:)' - (side - 1) / 2) * lambda / 2; ...
                          (iz(:)' - (side - 1) / 2) * lambda / 2];
end

function [seg_start, seg_cell] = build_scenario_segments(cell_idx, min_len)
% Contiguous runs of one Voronoi cell; runs shorter than min_len join the previous one
% (copied from run_multi_user_300_25x25_mixed.m).
    n = numel(cell_idx);
    if n == 0, seg_start = 1; seg_cell = 1; return; end
    starts = [1; find(diff(cell_idx(:)) ~= 0) + 1];
    cells  = cell_idx(starts);
    keep_start = starts(1); keep_cell = cells(1);
    for i = 2:numel(starts)
        run_end = (i < numel(starts)) * (starts(min(i + 1, numel(starts))) - 1) + (i == numel(starts)) * n;
        if run_end - starts(i) + 1 >= min_len
            keep_start(end + 1, 1) = starts(i); %#ok<AGROW>
            keep_cell(end + 1, 1)  = cells(i);  %#ok<AGROW>
        end
    end
    seg_start = keep_start(:)'; seg_cell = keep_cell(:)';
end
